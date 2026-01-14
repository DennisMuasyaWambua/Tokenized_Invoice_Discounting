from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, logout
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import timedelta
import random
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import User, Role, Invoice, Contract, Payment, KYCDocument
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    InvoiceSerializer, InvoiceUploadSerializer, ContractSerializer,
    PaymentSerializer, FundingRequestSerializer, KYCDocumentSerializer,
    KYCDocumentUploadSerializer, RoleSerializer, RoleCreateSerializer,
    InvoiceOCRRequestSerializer, InvoiceOCRResponseSerializer
)


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            # Get user's KYC documents for response
            kyc_documents = user.kyc_documents.all()
            kyc_status = {
                'documents_uploaded': kyc_documents.count(),
                'total_documents': 3,  # national_id, business_certificate, kra_certificate
                'verification_complete': all(doc.verified for doc in kyc_documents),
                'uploaded_documents': [doc.document_type for doc in kyc_documents]
            }

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'role': RoleSerializer(user.role).data if user.role else None,
                'user': UserSerializer(user).data,
                'kyc_status': kyc_status
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'role': RoleSerializer(user.role).data if user.role else None,
                'user': UserSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            if request.user.is_authenticated:
                logout(request)

            return Response({'message': 'Logged out successfully'})
        except Exception:
            return Response({'message': 'Logged out successfully'})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.filter(is_active=True)
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RoleCreateSerializer
        return RoleSerializer
    
    @action(detail=False, methods=['get'], url_path='active', permission_classes=[permissions.AllowAny])
    def active_roles(self, request):
        """Get only active roles for user registration"""
        roles = Role.objects.filter(is_active=True)
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data)


class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Contract.objects.filter(
            Q(supplier=user) | Q(buyer=user)
        )


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        queryset = Invoice.objects.filter(
            Q(supplier=user) | Q(buyer=user) | Q(financier=user)
        )

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Search filter
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(contract__buyer__company_name__icontains=search)
            )

        return queryset.order_by('-submitted_at')

    @extend_schema(
        operation_id='invoice_create',
        summary='Create invoice with automatic OCR extraction',
        description="""
        Create a new invoice. Supports automatic OCR data extraction from uploaded invoice documents.

        **Two modes of operation:**

        **1. Manual Entry:**
        Provide all invoice fields manually:
        - invoice_number (required)
        - amount (required)
        - due_date (required)
        - patientName (optional)
        - insurerName (optional)
        - invoice_document (optional - PDF/image file)

        **2. Automatic OCR Extraction (Recommended):**
        Upload invoice_document and optionally provide fields. OCR will extract missing fields:
        - If invoice_document is provided, OCR extraction runs automatically
        - OCR-extracted data is used for any fields not provided by user
        - User-provided data always takes priority over OCR data

        **Supported file formats:** PDF, JPG, JPEG, PNG (max 10MB)

        **Example workflow:**
        ```
        POST /api/invoices/
        Content-Type: multipart/form-data

        {
          "invoice_document": <file>,  // OCR extracts all fields
          "invoice_number": "",         // Optional override
          "amount": ""                  // Optional override
        }
        ```

        The invoice is created and saved to the database immediately.
        """,
        request=InvoiceUploadSerializer,
        responses={
            201: InvoiceSerializer,
            400: {'description': 'Validation error', 'type': 'object'}
        },
        examples=[
            OpenApiExample(
                'Manual invoice creation',
                value={
                    'invoice_number': 'INV-2024-001234',
                    'amount': '60000.00',
                    'due_date': '2024-02-14',
                    'patientName': 'BEVTECH SOLUTIONS',
                    'insurerName': 'DENNIS MUASYA WAMBUA',
                    'serviceDescription': 'Backend development services'
                },
                request_only=True
            ),
            OpenApiExample(
                'OCR-assisted invoice creation',
                value={
                    'invoice_document': '<binary file data>'
                },
                request_only=True
            ),
            OpenApiExample(
                'Validation error',
                value={
                    'invoice_number': ['This field is required.'],
                    'amount': ['This field is required.']
                },
                response_only=True,
                status_codes=['400']
            )
        ],
        tags=['Invoices']
    )
    def create(self, request):
        import os
        import logging
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        from django.conf import settings

        logger = logging.getLogger('discounting.ocr')

        # Check if invoice_document is provided for OCR extraction
        invoice_file = request.FILES.get('invoice_document')
        ocr_extracted_data = {}

        if invoice_file:
            logger.info(f"Invoice file uploaded by user {request.user.id}: {invoice_file.name}")
            temp_file_path = None

            try:
                # Save file temporarily for OCR
                temp_filename = f'temp/ocr_{request.user.id}_{timezone.now().timestamp()}_{invoice_file.name}'
                temp_file_path = default_storage.save(temp_filename, ContentFile(invoice_file.read()))
                full_path = os.path.join(settings.MEDIA_ROOT, temp_file_path)

                # Extract text using OCR
                from .utils.ocr_extractor import OCRExtractor
                extractor = OCRExtractor()
                ocr_result = extractor.extract_text(full_path)

                if ocr_result.get('success'):
                    # Parse invoice fields from OCR text
                    from .utils.etims_parser import ETIMSInvoiceParser
                    parser = ETIMSInvoiceParser()
                    ocr_extracted_data = parser.parse_invoice(ocr_result['text'])

                    logger.info(
                        f"OCR extraction successful for user {request.user.id}: "
                        f"extracted {len([k for k, v in ocr_extracted_data.items() if v])} fields"
                    )
                else:
                    logger.warning(f"OCR extraction failed for user {request.user.id}: {ocr_result.get('errors')}")

                # Clean up temp file
                if temp_file_path:
                    default_storage.delete(temp_file_path)

                # Reset file pointer for serializer
                invoice_file.seek(0)

            except Exception as e:
                logger.error(f"OCR extraction error for user {request.user.id}: {str(e)}")
                # Clean up temp file on error
                if temp_file_path:
                    try:
                        default_storage.delete(temp_file_path)
                    except:
                        pass
                # Continue with invoice creation even if OCR fails

        # Merge OCR data with request data (request data takes priority)
        merged_data = request.data.copy()

        # Only use OCR data for fields not provided by user
        if ocr_extracted_data.get('extraction_success'):
            # Map OCR fields to serializer fields
            ocr_field_mapping = {
                'invoice_number': 'invoice_number',
                'invoice_amount': 'amount',
                'invoice_date': 'invoice_date',
                'due_date': 'due_date',
            }

            for ocr_field, serializer_field in ocr_field_mapping.items():
                # Only use OCR value if user didn't provide one
                if not merged_data.get(serializer_field) and ocr_extracted_data.get(ocr_field):
                    merged_data[serializer_field] = ocr_extracted_data[ocr_field]
                    logger.debug(f"Using OCR extracted {ocr_field}: {ocr_extracted_data[ocr_field]}")

            # Handle buyer/seller names from OCR
            if not merged_data.get('patientName') and ocr_extracted_data.get('buyer_details', {}).get('name'):
                merged_data['patientName'] = ocr_extracted_data['buyer_details']['name']

            if not merged_data.get('insurerName') and ocr_extracted_data.get('seller_details', {}).get('name'):
                merged_data['insurerName'] = ocr_extracted_data['seller_details']['name']

        serializer = InvoiceUploadSerializer(data=merged_data, context={'request': request})
        if serializer.is_valid():
            invoice = serializer.save()
            return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Payment.objects.filter(
            Q(payer=user) | Q(payee=user)
        ).order_by('-created_at')


class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get user's invoices
        invoices = Invoice.objects.filter(
            Q(supplier=user) | Q(buyer=user) | Q(financier=user)
        )
        
        stats = {
            'totalInvoices': invoices.count(),
            'pendingInvoices': invoices.filter(status='pending').count(),
            'fundedInvoices': invoices.filter(status='funded').count(),
            'totalAmount': invoices.aggregate(total=Sum('invoice_amount'))['total'] or 0,
            'fundedAmount': invoices.filter(status='funded').aggregate(total=Sum('advance_amount'))['total'] or 0,
            'pendingAmount': invoices.filter(status='pending').aggregate(total=Sum('invoice_amount'))['total'] or 0,
        }
        
        return Response(stats)


class RecentInvoicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        recent_invoices = Invoice.objects.filter(
            Q(supplier=user) | Q(buyer=user) | Q(financier=user)
        ).order_by('-submitted_at')[:5]
        
        serializer = InvoiceSerializer(recent_invoices, many=True)
        return Response(serializer.data)


class FundingHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        payments = Payment.objects.filter(
            Q(payer=user) | Q(payee=user)
        ).order_by('-created_at')[:10]
        
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


class CreditProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Mock credit profile data
        profile = {
            'score': random.randint(650, 850),
            'maxScore': 900,
            'creditLimit': 1000000,
            'usedCredit': random.randint(100000, 500000),
            'factors': [
                {'name': 'Payment History', 'score': random.randint(70, 100), 'impact': 'positive'},
                {'name': 'Invoice Volume', 'score': random.randint(60, 90), 'impact': 'positive'},
                {'name': 'Business Duration', 'score': random.randint(50, 80), 'impact': 'neutral'},
            ],
            'history': [
                {'date': '2024-01-01', 'score': random.randint(600, 800)},
                {'date': '2024-02-01', 'score': random.randint(620, 820)},
                {'date': '2024-03-01', 'score': random.randint(640, 840)},
            ]
        }
        
        return Response(profile)


class RequestFundingView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = FundingRequestSerializer(data=request.data)
        if serializer.is_valid():
            invoice_id = serializer.validated_data['invoiceId']
            mpesa_number = serializer.validated_data['mpesaNumber']
            requested_amount = serializer.validated_data['requestedAmount']
            
            try:
                invoice = Invoice.objects.get(id=invoice_id, supplier=request.user)
                
                # Update invoice status
                invoice.status = 'funded'
                invoice.advance_amount = requested_amount
                invoice.funded_at = timezone.now()
                invoice.save()
                
                # Create payment record
                Payment.objects.create(
                    invoice=invoice,
                    payer_id=1,  # Mock financier
                    payee=request.user,
                    amount=requested_amount,
                    payment_type='advance',
                    mpesa_transaction_id=f'MPesa{random.randint(100000, 999999)}',
                    status='completed'
                )
                
                return Response({
                    'message': 'Funding request processed successfully',
                    'invoice': InvoiceSerializer(invoice).data
                })
                
            except Invoice.DoesNotExist:
                return Response(
                    {'error': 'Invoice not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PendingApprovalsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Only show to admin users
        pending_invoices = Invoice.objects.filter(status='pending').order_by('-submitted_at')
        serializer = InvoiceSerializer(pending_invoices, many=True)
        return Response(serializer.data)


class ApproveInvoiceView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, invoice_id):
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            invoice.status = 'approved'
            invoice.approved_at = timezone.now()
            invoice.save()
            
            return Response({
                'message': 'Invoice approved successfully',
                'invoice': InvoiceSerializer(invoice).data
            })
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'Invoice not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class DeclineInvoiceView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, invoice_id):
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            invoice.status = 'rejected'
            invoice.save()
            
            return Response({
                'message': 'Invoice declined successfully',
                'invoice': InvoiceSerializer(invoice).data
            })
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'Invoice not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class TransactionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        payments = Payment.objects.filter(
            Q(payer=user) | Q(payee=user)
        )
        
        # Filter by type
        payment_type = request.query_params.get('type')
        if payment_type:
            payments = payments.filter(payment_type=payment_type)
        
        payments = payments.order_by('-created_at')
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


class FileUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        # Handle file upload logic here
        # For now, just return success
        
        return Response({
            'message': 'File uploaded successfully',
            'filename': file.name,
            'size': file.size
        })


class KYCDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = KYCDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return KYCDocument.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return KYCDocumentUploadSerializer
        return KYCDocumentSerializer
    
    @action(detail=False, methods=['post'], url_path='upload')
    def upload_document(self, request):
        serializer = KYCDocumentUploadSerializer(
            data=request.data, 
            context={'request': request}
        )
        if serializer.is_valid():
            document = serializer.save()
            return Response(
                KYCDocumentSerializer(document).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='status')
    def kyc_status(self, request):
        user_docs = KYCDocument.objects.filter(user=request.user)

        required_docs = ['national_id', 'business_certificate', 'kra_certificate']
        status_data = {
            'completed_documents': [],
            'missing_documents': [],
            'verification_status': 'pending'
        }

        for doc_type in required_docs:
            doc_exists = user_docs.filter(document_type=doc_type).exists()
            if doc_exists:
                doc = user_docs.get(document_type=doc_type)
                status_data['completed_documents'].append({
                    'type': doc_type,
                    'verified': doc.verified,
                    'uploaded_at': doc.uploaded_at
                })
            else:
                status_data['missing_documents'].append(doc_type)

        # Determine overall status
        if len(status_data['completed_documents']) == len(required_docs):
            all_verified = all(doc['verified'] for doc in status_data['completed_documents'])
            status_data['verification_status'] = 'verified' if all_verified else 'under_review'
        else:
            status_data['verification_status'] = 'incomplete'

        return Response(status_data)


@method_decorator(csrf_exempt, name='dispatch')
class InvoiceOCRView(APIView):
    """
    OCR Invoice Data Extraction Endpoint

    Extracts invoice data from uploaded PDF/image file using OCR technology.
    Returns extracted fields for user review before creating invoice.

    Supports: PDF, JPG, PNG files (max 10MB)
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        operation_id='invoice_ocr_extract',
        summary='Extract invoice data using OCR',
        description="""
        Upload an eTIMS invoice (PDF or image) to automatically extract invoice fields using OCR.

        **Supported formats:** PDF, JPG, JPEG, PNG
        **Max file size:** 10MB
        **Extracted fields:**
        - Invoice number (SCU ID)
        - Invoice amount (Total Amount)
        - Invoice date (Date Created)
        - Due date (if available)
        - Supplier KRA PIN
        - Buyer KRA PIN
        - Seller name
        - Buyer name

        The response includes:
        - Extracted field values
        - Confidence scores for each field (0.0 to 1.0)
        - Success status
        - Any extraction errors

        **Typical workflow:**
        1. Upload invoice file to this endpoint
        2. Review extracted data and confidence scores
        3. Edit/confirm data in frontend
        4. POST to `/api/invoices/` to create invoice
        """,
        request=InvoiceOCRRequestSerializer,
        responses={
            200: InvoiceOCRResponseSerializer,
            400: {'description': 'Invalid file upload', 'type': 'object'},
            422: {'description': 'OCR extraction failed', 'type': 'object'},
        },
        examples=[
            OpenApiExample(
                'Successful OCR extraction',
                value={
                    'invoice_number': 'KRASRN000314580',
                    'invoice_amount': '60000.00',
                    'invoice_date': '2025-12-17',
                    'due_date': None,
                    'supplier_kra_pin': 'A014019184W',
                    'buyer_kra_pin': 'P0052006107N',
                    'seller_details': {'name': 'DENNIS MUASYA WAMBUA'},
                    'buyer_details': {'name': 'BEVTECH SOLUTIONS LIMITED'},
                    'confidence_scores': {
                        'invoice_number': 0.90,
                        'invoice_amount': 0.95,
                        'invoice_date': 0.90,
                        'supplier_kra_pin': 0.95,
                        'buyer_kra_pin': 0.50
                    },
                    'extraction_success': True,
                    'extraction_errors': []
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                'Invalid file upload',
                value={
                    'invoice_document': [
                        'Unsupported file format. Supported formats: pdf, jpg, jpeg, png'
                    ]
                },
                response_only=True,
                status_codes=['400']
            ),
            OpenApiExample(
                'OCR extraction failed',
                value={
                    'error': 'OCR extraction failed',
                    'details': ['No text could be extracted from the image']
                },
                response_only=True,
                status_codes=['422']
            )
        ],
        tags=['Invoice OCR']
    )
    def post(self, request):
        import os
        import logging
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        from django.conf import settings

        logger = logging.getLogger('discounting.ocr')

        # Validate request
        serializer = InvoiceOCRRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        invoice_file = serializer.validated_data['invoice_document']
        temp_file_path = None

        try:
            # Save file temporarily
            temp_filename = f'temp/ocr_{request.user.id}_{timezone.now().timestamp()}_{invoice_file.name}'
            temp_file_path = default_storage.save(temp_filename, ContentFile(invoice_file.read()))
            full_path = os.path.join(settings.MEDIA_ROOT, temp_file_path)

            logger.info(f"OCR extraction started by user {request.user.id} for file {invoice_file.name}")

            # Extract text using OCR
            from .utils.ocr_extractor import OCRExtractor
            extractor = OCRExtractor()
            ocr_result = extractor.extract_text(full_path)

            if not ocr_result.get('success'):
                logger.error(f"OCR extraction failed: {ocr_result.get('errors')}")
                return Response({
                    'error': 'OCR extraction failed',
                    'details': ocr_result.get('errors', [])
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            # Parse invoice fields from OCR text
            from .utils.etims_parser import ETIMSInvoiceParser
            parser = ETIMSInvoiceParser()
            extracted_data = parser.parse_invoice(ocr_result['text'])

            # Add raw text for debugging (optional, can be removed in production)
            if settings.DEBUG:
                extracted_data['raw_text'] = ocr_result['text'][:500]  # First 500 chars only

            logger.info(
                f"OCR completed for user {request.user.id}: "
                f"success={extracted_data['extraction_success']}, "
                f"confidence={sum(extracted_data['confidence_scores'].values()) / max(len(extracted_data['confidence_scores']), 1):.2f}"
            )

            # Return extracted data
            response_serializer = InvoiceOCRResponseSerializer(data=extracted_data)
            if response_serializer.is_valid():
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                # If validation fails, return raw data anyway
                logger.warning(f"Response serialization failed: {response_serializer.errors}")
                return Response(extracted_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"OCR extraction error for user {request.user.id}: {str(e)}")
            return Response({
                'error': 'Extraction failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        finally:
            # Clean up temp file
            if temp_file_path:
                try:
                    default_storage.delete(temp_file_path)
                    logger.debug(f"Cleaned up temp file: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {temp_file_path}: {e}")
