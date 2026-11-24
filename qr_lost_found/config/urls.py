from django.contrib import admin
from django.conf import settings
from django.urls import path
from django.contrib.auth import views as auth_views

from core.forms import EmailOrUsernameAuthenticationForm
from core import views


urlpatterns = [

    path('admin/', admin.site.urls),

    path('', views.home, name='home'),

    path(
        'accounts/register/',
        views.register,
        name='register'
    ),

    path(
        'accounts/login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html',
            form_class=EmailOrUsernameAuthenticationForm,
            redirect_authenticated_user=True
        ),
        name='login'
    ),

    path(
        'accounts/logout/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),

    # PASSWORD RESET ROUTES

    path(
        'accounts/password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.txt',
            html_email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url='/accounts/password-reset/done/',
            extra_context={
                'email_delivery_configured':
                    settings.EMAIL_DELIVERY_CONFIGURED,
            }
        ),
        name='password_reset'
    ),

    path(
        'accounts/password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html',
            extra_context={
                'email_delivery_configured':
                    settings.EMAIL_DELIVERY_CONFIGURED,
            },
        ),
        name='password_reset_done'
    ),

    path(
        'accounts/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url='/accounts/reset/complete/'
        ),
        name='password_reset_confirm'
    ),

    path(
        'accounts/reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),

    path('dashboard/', views.dashboard, name='dashboard'),

    path(
        'notifications/<int:notification_id>/read/',
        views.mark_notification_read,
        name='mark_notification_read'
    ),

    path('profile/', views.profile, name='profile'),

    path(
        'order-stickers/',
        views.place_order,
        name='place_order'
    ),

    path(
        'my-orders/',
        views.my_orders,
        name='my_orders'
    ),

    path(
        'scan/<uuid:token>/',
        views.scan_qr,
        name='scan_qr'
    ),

]