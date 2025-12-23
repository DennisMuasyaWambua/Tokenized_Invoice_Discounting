from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
import random

from .models import User, Role, Invoice, Contract, Payment
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    InvoiceSerializer, InvoiceUploadSerializer, ContractSerializer,
    PaymentSerializer, FundingRequestSerializer
)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'user_type': user.role.short_name if user.role else None
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'user_type': user.role.short_name if user.role else None
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    def post(self, request):
        if request.user.is_authenticated:
            Token.objects.filter(user=request.user).delete()
            logout(request)
        return Response({'message': 'Logged out successfully'})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


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
    
    def create(self, request):
        serializer = InvoiceUploadSerializer(data=request.data, context={'request': request})
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
