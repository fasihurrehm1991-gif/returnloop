from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import QRCode


class QRFlowTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='Strong-Test-Password-123!',
        )
        self.qr = QRCode.objects.get(user=self.user)

    def test_registration_creates_one_qr_code(self):
        self.assertEqual(QRCode.objects.filter(user=self.user).count(), 1)

    def test_inactive_qr_code_cannot_be_scanned(self):
        response = self.client.get(
            reverse('scan_qr', args=[self.qr.token])
        )
        self.assertEqual(response.status_code, 404)

    def test_active_qr_code_records_a_scan_without_owner_details(self):
        self.qr.is_active = True
        self.qr.save(update_fields=['is_active'])

        response = self.client.get(
            reverse('scan_qr', args=[self.qr.token])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.user.email)
