import uuid

from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    MEMBER_TYPE_CHOICES = [
        ("student", "Student"),
        ("staff", "Staff"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    member_type = models.CharField(
        max_length=10,
        choices=MEMBER_TYPE_CHOICES,
        blank=True,
        default=""
    )
    institution_name = models.CharField(
        max_length=180,
        blank=True,
        default=""
    )
    affiliation_id = models.CharField(
        max_length=50,
        blank=True,
        default=""
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class QRCode(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    is_active = models.BooleanField(default=False)
    generated_at = models.DateTimeField(auto_now_add=True)
    replaced_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"QR Code - {self.user.username}"


class StickerOrder(models.Model):

    PACKAGE_CHOICES = [
        ("single", "Single Sticker"),
        ("three", "Pack of 3"),
        ("five", "Pack of 5"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("generated", "Generated"),
        ("paid", "Paid"),
        ("delivered", "Delivered"),
        ("active", "Active"),
        ("cancelled", "Cancelled"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
    ]

    PAYMENT_CHOICES = [
        ("unpaid", "Unpaid"),
        ("pending", "Payment Verification"),
        ("paid", "Paid"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    package = models.CharField(
        max_length=20,
        choices=PACKAGE_CHOICES
    )
    quantity = models.PositiveIntegerField(default=1)
    amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    order_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default="unpaid"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"


class FinderNotification(models.Model):

    qr_code = models.ForeignKey(
        QRCode,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    message = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.qr_code.user.username}"


class QRScan(models.Model):

    qr_code = models.ForeignKey(
        QRCode,
        on_delete=models.CASCADE,
        related_name="scans"
    )
    scanned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scan - {self.qr_code.user.username}"


class SupportMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=180)
    message = models.TextField(max_length=3000)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_messages"
    )
    is_resolved = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.email}"