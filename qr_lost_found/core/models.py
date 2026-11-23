import uuid

from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
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
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
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