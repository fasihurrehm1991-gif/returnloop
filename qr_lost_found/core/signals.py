from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import QRCode


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_qr(sender, instance, created, **kwargs):

    if created:
        QRCode.objects.get_or_create(user=instance)