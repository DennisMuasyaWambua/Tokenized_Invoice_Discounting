from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'invoices', views.InvoiceViewSet)
router.register(r'users', views.UserViewSet)
router.register(r'contracts', views.ContractViewSet)
router.register(r'payments', views.PaymentViewSet)
router.register(r'roles', views.RoleViewSet)
router.register(r'kyc-documents', views.KYCDocumentViewSet, basename='kyc-documents')

urlpatterns = [
    # API Router URLs
    path('api/', include(router.urls)),

    # OCR Extraction endpoint
    path('api/invoices/extract/', csrf_exempt(views.InvoiceOCRView.as_view()), name='invoice-ocr-extract'),

    # Authentication endpoints
    path('api/auth/login/', csrf_exempt(views.LoginView.as_view()), name='login'),
    path('api/auth/register/', csrf_exempt(views.RegisterView.as_view()), name='register'),
    path('api/auth/logout/', csrf_exempt(views.LogoutView.as_view()), name='logout'),
    path('api/auth/token/refresh/', csrf_exempt(TokenRefreshView.as_view()), name='token_refresh'),
    
    # Dashboard endpoints
    path('api/dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('api/dashboard/recent-invoices/', views.RecentInvoicesView.as_view(), name='recent-invoices'),
    path('api/dashboard/funding-history/', views.FundingHistoryView.as_view(), name='funding-history'),
    
    # Credit profile
    path('api/credit/profile/', views.CreditProfileView.as_view(), name='credit-profile'),
    
    # Funding operations
    path('api/funding/request/', views.RequestFundingView.as_view(), name='request-funding'),
    
    # Admin operations
    path('api/admin/approvals/', views.PendingApprovalsView.as_view(), name='pending-approvals'),
    path('api/admin/invoices/<int:invoice_id>/approve/', views.ApproveInvoiceView.as_view(), name='approve-invoice'),
    path('api/admin/invoices/<int:invoice_id>/decline/', views.DeclineInvoiceView.as_view(), name='decline-invoice'),
    
    # Transactions
    path('api/transactions/', views.TransactionsView.as_view(), name='transactions'),
    
    # File upload
    path('api/upload/', views.FileUploadView.as_view(), name='file-upload'),
]