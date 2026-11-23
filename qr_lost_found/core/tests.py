from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from .models import QRCode, StickerOrder


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

    def test_profile_update_changes_profile_and_user_name(self):
        self.client.login(username='owner', password='Strong-Test-Password-123!')

        response = self.client.post(reverse('profile'), {
            'full_name': 'Updated Owner',
            'email': 'updated-owner@example.com',
            'phone': '03001234567',
        })

        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'updated-owner@example.com')
        self.assertEqual(self.user.first_name, 'Updated Owner')

    def test_customer_can_place_and_view_sticker_order(self):
        self.client.login(username='owner', password='Strong-Test-Password-123!')

        response = self.client.post(reverse('place_order'), {
            'package': 'three',
            'quantity': '2',
        })

        self.assertRedirects(response, reverse('my_orders'))
        order = StickerOrder.objects.get(user=self.user)
        self.assertEqual(order.package, 'three')
        self.assertEqual(order.quantity, 2)

    def test_logout_and_login_flow(self):
        self.client.login(username='owner', password='Strong-Test-Password-123!')
        self.assertTrue(
            self.client.get(reverse('dashboard')).status_code == 200
        )

        self.client.post(reverse('logout'))

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

        login = self.client.login(
            username='owner',
            password='Strong-Test-Password-123!',
        )
        self.assertTrue(login)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_password_reset_email_is_generated_and_confirm_flow_works(self):
        response = self.client.post(
            reverse('password_reset'),
            {'email': self.user.email},
        )

        self.assertRedirects(
            response,
            reverse('password_reset_done'),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset', mail.outbox[0].subject.lower())

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        confirm_url = reverse(
            'password_reset_confirm',
            kwargs={'uidb64': uid, 'token': token},
        )

        confirm_response = self.client.get(confirm_url)
        set_password_url = confirm_response.url

        response = self.client.post(
            set_password_url,
            {
                'new_password1': 'New-Strong-Test-2026!',
                'new_password2': 'New-Strong-Test-2026!',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(
            self.user.check_password('New-Strong-Test-2026!')
        )
