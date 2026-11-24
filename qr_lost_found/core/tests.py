from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
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

    def test_admin_can_activate_and_download_branded_qr_code(self):
        admin_user = User.objects.create_superuser(
            username='administrator',
            email='administrator@example.com',
            password='Strong-Admin-Password-123!',
        )
        self.client.force_login(admin_user)
        changelist = reverse('admin:core_qrcode_changelist')

        response = self.client.post(changelist, {
            'action': 'activate_qr_codes',
            '_selected_action': [str(self.qr.pk)],
            'index': '0',
        })

        self.assertEqual(response.status_code, 302)
        self.qr.refresh_from_db()
        self.assertTrue(self.qr.is_active)

        response = self.client.post(changelist, {
            'action': 'download_qr_code',
            '_selected_action': [str(self.qr.pk)],
            'index': '0',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertIn('attachment;', response['Content-Disposition'])

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
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Owner')

    def test_registration_creates_profile_and_qr(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'New',
            'last_name': 'Member',
            'username': 'new-member',
            'email': 'new-member@example.com',
            'phone': '03001234567',
            'password1': 'Strong-New-Member-2026!',
            'password2': 'Strong-New-Member-2026!',
        })

        self.assertRedirects(response, reverse('dashboard'))
        new_user = User.objects.get(username='new-member')
        self.assertEqual(new_user.userprofile.full_name, 'New Member')
        self.assertEqual(new_user.userprofile.phone, '03001234567')
        self.assertEqual(QRCode.objects.filter(user=new_user).count(), 1)

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Another',
            'last_name': 'Owner',
            'username': 'another-owner',
            'email': 'OWNER@example.com',
            'phone': '03001234567',
            'password1': 'Strong-New-Owner-2026!',
            'password2': 'Strong-New-Owner-2026!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='another-owner').exists())

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_DELIVERY_CONFIGURED=True,
    )
    def test_finder_post_creates_notification_and_sends_owner_email(self):
        self.qr.is_active = True
        self.qr.save(update_fields=['is_active'])

        response = self.client.post(
            reverse('scan_qr', args=[self.qr.token]),
            {'message': 'Found your bag', 'location': 'Library'},
        )

        self.assertEqual(response.status_code, 200)
        notification = self.qr.notifications.get()
        self.assertEqual(notification.message, 'Found your bag')
        self.assertEqual(notification.location, 'Library')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_mark_read_only_allows_notification_owner(self):
        User.objects.create_user(
            username='other',
            email='other@example.com',
            password='Strong-Other-Password-123!',
        )
        notification = self.qr.notifications.create(
            message='Found item',
            location='Library',
        )
        self.client.login(username='other', password='Strong-Other-Password-123!')

        response = self.client.post(
            reverse('mark_notification_read', args=[notification.id])
        )

        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

        self.client.login(username='owner', password='Strong-Test-Password-123!')
        response = self.client.post(
            reverse('mark_notification_read', args=[notification.id])
        )

        self.assertRedirects(response, reverse('dashboard'))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

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

    def test_invalid_order_is_not_created(self):
        self.client.login(username='owner', password='Strong-Test-Password-123!')

        response = self.client.post(reverse('place_order'), {
            'package': 'invalid',
            'quantity': '100',
        })

        self.assertRedirects(response, reverse('place_order'))
        self.assertFalse(StickerOrder.objects.filter(user=self.user).exists())

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
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_DELIVERY_CONFIGURED=True,
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
