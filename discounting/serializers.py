from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import User, Role, Invoice, Contract, Payment, KYCDocument
from django.contrib.auth.password_validation import validate_password


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'short_name', 'description', 'is_active']


class RoleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['name', 'short_name', 'description', 'is_active']
    
    def validate_short_name(self, value):
        if Role.objects.filter(short_name=value).exists():
            raise serializers.ValidationError("Role with this short name already exists.")
        return value


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_name = serializers.CharField(source='role.short_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'mobile_number', 'created_on', 
                 'is_active', 'role', 'role_name', 'company_name', 'kra_pin']
        read_only_fields = ['id', 'created_on']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    role_name = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'mobile_number', 'password', 'password_confirm', 
                 'company_name', 'kra_pin', 'role_name']
    
    def validate_role_name(self, value):
        if not Role.objects.filter(short_name=value, is_active=True).exists():
            available_roles = Role.objects.filter(is_active=True).values_list('short_name', flat=True)
            raise serializers.ValidationError(
                f"Invalid role. Available roles: {list(available_roles)}"
            )
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        role_name = validated_data.pop('role_name')
        password = validated_data.pop('password')
        
        # Get existing role (no longer creates roles automatically)
        try:
            role = Role.objects.get(short_name=role_name, is_active=True)
        except Role.DoesNotExist:
            raise serializers.ValidationError(f"Role '{role_name}' does not exist.")
        
        user = User.objects.create_user(password=password, role=role, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include email and password.')
        return attrs


class ContractSerializer(serializers.ModelSerializer):
    buyer = UserSerializer(read_only=True)
    supplier = UserSerializer(read_only=True)
    
    class Meta:
        model = Contract
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    contract = ContractSerializer(read_only=True)
    supplier = UserSerializer(read_only=True)
    buyer = UserSerializer(read_only=True)
    financier = UserSerializer(read_only=True)
    
    # Add computed fields for frontend compatibility
    patientName = serializers.CharField(source='contract.buyer.company_name', read_only=True)
    insurerName = serializers.CharField(source='buyer.company_name', read_only=True)
    amount = serializers.DecimalField(source='invoice_amount', max_digits=15, decimal_places=2, read_only=True)
    uploadDate = serializers.DateTimeField(source='submitted_at', read_only=True)
    serviceDescription = serializers.CharField(default='Medical services', read_only=True)
    discountRate = serializers.DecimalField(source='discount_rate', max_digits=5, decimal_places=2, read_only=True)
    fundedAmount = serializers.DecimalField(source='advance_amount', max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = Invoice
        fields = '__all__'


class InvoiceUploadSerializer(serializers.ModelSerializer):
    patientName = serializers.CharField(write_only=True)
    insurerName = serializers.CharField(write_only=True)
    amount = serializers.DecimalField(source='invoice_amount', max_digits=15, decimal_places=2)
    serviceDescription = serializers.CharField(default='Medical services', write_only=True)
    
    class Meta:
        model = Invoice
        fields = ['invoice_number', 'patientName', 'insurerName', 'amount', 
                 'due_date', 'serviceDescription', 'invoice_document']
    
    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        
        # Remove fields that don't belong to Invoice model
        validated_data.pop('patientName', None)
        validated_data.pop('insurerName', None)
        validated_data.pop('serviceDescription', None)
        
        # Set invoice_date to today if not provided
        validated_data['invoice_date'] = validated_data.get('invoice_date', timezone.now().date())
        
        # For now, create a simple contract if none exists
        contract, _ = Contract.objects.get_or_create(
            supplier=user,
            buyer=user,  # In real app, this would be determined differently
            defaults={
                'contract_reference': f'AUTO-{user.id}-001',
                'amount': validated_data['invoice_amount'],
                'date_from': validated_data['invoice_date'],
                'date_to': '2025-12-31'
            }
        )
        
        invoice = Invoice.objects.create(
            contract=contract,
            supplier=user,
            buyer=contract.buyer,
            **validated_data
        )
        return invoice


class PaymentSerializer(serializers.ModelSerializer):
    payer = UserSerializer(read_only=True)
    payee = UserSerializer(read_only=True)
    
    # Add fields for frontend compatibility
    type = serializers.CharField(source='payment_type', read_only=True)
    date = serializers.DateTimeField(source='created_at', read_only=True)
    mpesaRef = serializers.CharField(source='mpesa_receipt_number', read_only=True)
    description = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = '__all__'
    
    def get_description(self, obj):
        return f"{obj.get_payment_type_display()} for Invoice {obj.invoice.invoice_number}"


class FundingRequestSerializer(serializers.Serializer):
    invoiceId = serializers.IntegerField()
    mpesaNumber = serializers.CharField(max_length=15)
    requestedAmount = serializers.DecimalField(max_digits=15, decimal_places=2)


class KYCDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCDocument
        fields = ['id', 'document_type', 'document_file', 'uploaded_at', 'verified', 'verified_at']
        read_only_fields = ['id', 'uploaded_at', 'verified', 'verified_at']


class KYCDocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCDocument
        fields = ['document_type', 'document_file']
    
    def create(self, validated_data):
        user = self.context['request'].user
        document_type = validated_data['document_type']
        
        # Update existing document or create new one
        kyc_doc, _ = KYCDocument.objects.update_or_create(
            user=user,
            document_type=document_type,
            defaults={'document_file': validated_data['document_file']}
        )
        return kyc_doc