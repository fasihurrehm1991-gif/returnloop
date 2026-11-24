import logging
import smtplib

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from email.mime.image import MIMEImage

from .models import (
    QRCode,
    QRScan,
    FinderNotification,
    UserProfile,
    StickerOrder
)

from .forms import UserProfileForm


logger = logging.getLogger(__name__)


class RegistrationForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )

    phone = forms.CharField(
        required=True,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your phone number'
        })
    )

    class Meta:
        model = User

        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
        ]

        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name'
            }),

            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name'
            }),

            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }

    def clean_email(self):

        email = self.cleaned_data.get('email')

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )

        return email

    def save(self, commit=True):

        user = super().save(commit=False)

        user.email = self.cleaned_data['email']

        if commit:
            user.save()

        return user


def home(request):

    return render(request, 'welcome.html')


def register(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':

        form = RegistrationForm(request.POST)

        if form.is_valid():

            user = form.save()

            full_name = (
                f"{user.first_name} {user.last_name}"
            ).strip()

            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': full_name,
                    'phone': form.cleaned_data['phone']
                }
            )

            QRCode.objects.get_or_create(user=user)

            login(request, user)

            messages.success(
                request,
                'Your ReturnLoop account has been created successfully!'
            )

            return redirect('dashboard')

    else:

        form = RegistrationForm()

    return render(
        request,
        'registration/register.html',
        {'form': form}
    )


@login_required
def dashboard(request):

    notifications = FinderNotification.objects.filter(
        qr_code__user=request.user
    ).order_by('-created_at')

    unread_count = notifications.filter(
        is_read=False
    ).count()

    orders = StickerOrder.objects.filter(
        user=request.user
    ).order_by('-created_at')[:3]

    qr_code = QRCode.objects.filter(
        user=request.user
    ).first()

    qr_is_active = (
        qr_code.is_active if qr_code else False
    )

    recent_scans = QRScan.objects.filter(
        qr_code__user=request.user
    ).order_by('-scanned_at')[:10]

    total_scans = QRScan.objects.filter(
        qr_code__user=request.user
    ).count()

    return render(
        request,
        'dashboard.html',
        {
            'notifications': notifications,
            'unread_count': unread_count,
            'recent_orders': orders,
            'qr_is_active': qr_is_active,
            'recent_scans': recent_scans,
            'total_scans': total_scans
        }
    )


@login_required
@require_POST
def mark_notification_read(request, notification_id):

    notification = get_object_or_404(
        FinderNotification,
        id=notification_id,
        qr_code__user=request.user
    )

    if not notification.is_read:

        notification.is_read = True

        notification.save(
            update_fields=['is_read']
        )

        messages.success(
            request,
            'Notification marked as read.'
        )

    return redirect('dashboard')


@login_required
def profile(request):

    user_profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': (
                request.user.get_full_name()
                or request.user.username
            )
        }
    )

    if request.method == 'POST':

        form = UserProfileForm(
            request.POST,
            instance=user_profile,
            user=request.user
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Your profile has been updated successfully!'
            )

            return redirect('profile')

    else:

        form = UserProfileForm(
            instance=user_profile,
            user=request.user
        )

    return render(
        request,
        'profile.html',
        {'form': form}
    )


# =====================================================
# CUSTOMER STICKER ORDERING
# =====================================================

@login_required
def place_order(request):

    if request.method == 'POST':

        package = request.POST.get('package', '').strip()
        quantity = request.POST.get('quantity', '1').strip()

        valid_packages = dict(
            StickerOrder.PACKAGE_CHOICES
        )

        if package not in valid_packages:

            messages.error(
                request,
                'Please select a valid sticker package.'
            )

            return redirect('place_order')

        try:
            quantity = int(quantity)

        except (ValueError, TypeError):

            messages.error(
                request,
                'Please enter a valid quantity.'
            )

            return redirect('place_order')

        if quantity < 1 or quantity > 50:

            messages.error(
                request,
                'Quantity must be between 1 and 50.'
            )

            return redirect('place_order')

        StickerOrder.objects.create(
            user=request.user,
            package=package,
            quantity=quantity,
            order_status='pending',
            payment_status='unpaid'
        )

        messages.success(
            request,
            'Your sticker order has been placed successfully!'
        )

        return redirect('my_orders')

    return render(
        request,
        'order_sticker.html',
        {
            'packages': StickerOrder.PACKAGE_CHOICES
        }
    )


# =====================================================
# CUSTOMER ORDER HISTORY
# =====================================================

@login_required
def my_orders(request):

    orders = StickerOrder.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(
        request,
        'my_orders.html',
        {
            'orders': orders
        }
    )


# =====================================================
# QR SCANNING AND FINDER NOTIFICATIONS
# =====================================================

def scan_qr(request, token):

    qr_code = get_object_or_404(
        QRCode,
        token=token,
        is_active=True
    )

    if request.method == 'POST':

        message = request.POST.get('message', '').strip()
        location = request.POST.get('location', '').strip()

        if message:

            FinderNotification.objects.create(
                qr_code=qr_code,
                message=message,
                location=location
            )

            owner_email = qr_code.user.email

            if owner_email and settings.EMAIL_DELIVERY_CONFIGURED:

                owner_name = (
                    qr_code.user.get_full_name()
                    or qr_code.user.username
                )

                dashboard_url = request.build_absolute_uri(
                    reverse('dashboard')
                )

                email_context = {
                    'owner_name': owner_name,
                    'message': message,
                    'location': location or 'Not provided',
                    'date': timezone.localtime().strftime(
                        '%d %B %Y, %I:%M %p'
                    ),
                    'dashboard_url': dashboard_url,
                }

                html_message = render_to_string(
                    'emails/found_notification.html',
                    email_context
                )

                plain_message = (
                    f"Hello {owner_name},\n\n"
                    "Someone has submitted a found-item notification "
                    "for your ReturnLoop QR code.\n\n"
                    f"Message: {message}\n"
                    f"Location: {location or 'Not provided'}\n\n"
                    "Please log in to your ReturnLoop dashboard "
                    "to view your notification."
                )

                email = EmailMultiAlternatives(
                    subject='Someone Found Your Belonging - ReturnLoop',
                    body=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[owner_email]
                )

                email.attach_alternative(
                    html_message,
                    'text/html'
                )

                logo_path = (
                    settings.BASE_DIR
                    / 'static'
                    / 'images'
                    / 'returnloop-logo.png.png'
                )

                try:
                    with open(logo_path, 'rb') as logo_file:
                        logo = MIMEImage(logo_file.read())
                        logo.add_header(
                            'Content-ID',
                            '<returnloop_logo>'
                        )
                        logo.add_header(
                            'Content-Disposition',
                            'inline',
                            filename='returnloop-logo.png.png'
                        )
                        email.attach(logo)
                except OSError:
                    logger.warning(
                        'ReturnLoop logo could not be attached to finder '
                        'notification email for QR code %s',
                        qr_code.token
                    )

                try:
                    email.send(fail_silently=False)
                except (OSError, smtplib.SMTPException):
                    logger.exception(
                        'Could not send finder notification email '
                        'for QR code %s',
                        qr_code.token
                    )
                    messages.warning(
                        request,
                        'Your message was saved, but the owner email '
                        'could not be delivered.'
                    )

            elif not settings.EMAIL_DELIVERY_CONFIGURED:
                messages.warning(
                    request,
                    'Your message was saved. Email alerts are not set up '
                    'yet; the owner can still view it in their dashboard.'
                )

            return render(request, 'finder_success.html')

        messages.error(request, 'Please enter a message for the owner.')

    else:

        QRScan.objects.create(qr_code=qr_code)

    return render(request, 'finder.html')