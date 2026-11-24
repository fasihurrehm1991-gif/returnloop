from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from .models import (
    FinderNotification,
    QRCode,
    StickerOrder,
    SupportMessage,
)


class QRFlowTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='Strong-Test-Password-123!',
        )
        self.qr = QRCode.objects.create(user=self.user)

    def test_user_creation_does_not_issue_qr_automatically(self):
        new_user = User.objects.create_user(
            username='no-qr',
            email='no-qr@example.com',
            password='Strong-Test-Password-123!',
        )
        self.assertFalse(QRCode.objects.filter(user=new_user).exists())

    def test_homepage_buttons_match_the_users_login_state(self):
        guest_page = self.client.get(reverse('home'))
        self.assertContains(guest_page, 'Create Account')
        self.assertContains(guest_page, 'Log in')
        self.assertNotContains(guest_page, 'Admin Login')
        self.assertEqual(
            guest_page.content.count(b'href="/accounts/register/"'),
            1,
        )
        self.assertEqual(
            guest_page.content.count(b'href="/accounts/login/"'),
            1,
        )

        self.client.force_login(self.user)
        member_page = self.client.get(reverse('home'))
        self.assertContains(member_page, 'Welcome back')
        self.assertContains(member_page, 'Open Dashboard')
        self.assertContains(member_page, 'Order Stickers')
        self.assertNotContains(member_page, 'Create Account')
        self.assertNotContains(member_page, 'Log in')
        self.assertNotContains(member_page, 'Already Have an Account')
        self.assertNotContains(member_page, 'Admin Login')

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
        StickerOrder.objects.create(
            user=self.user,
            package='single',
            amount_due='500.00',
            order_status='delivered',
            payment_status='paid',
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

    def test_admin_can_replace_qr_and_old_token_becomes_unusable(self):
        old_token = self.qr.token
        admin_user = User.objects.create_superuser(
            username='qr-admin',
            email='qr-admin@example.com',
            password='Strong-Admin-Password-123!',
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse('admin:core_qrcode_changelist'),
            {
                'action': 'replace_qr_codes',
                '_selected_action': [str(self.qr.pk)],
                'index': '0',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.qr.refresh_from_db()
        self.assertNotEqual(self.qr.token, old_token)
        self.assertFalse(self.qr.is_active)
        self.assertIsNotNone(self.qr.replaced_at)

    def test_qr_cannot_be_activated_before_a_paid_delivered_order(self):
        admin_user = User.objects.create_superuser(
            username='activation-admin',
            email='activation-admin@example.com',
            password='Strong-Admin-Password-123!',
        )
        self.client.force_login(admin_user)

        self.client.post(
            reverse('admin:core_qrcode_changelist'),
            {
                'action': 'activate_qr_codes',
                '_selected_action': [str(self.qr.pk)],
                'index': '0',
            },
        )

        self.qr.refresh_from_db()
        self.assertFalse(self.qr.is_active)

    def test_customer_dashboard_does_not_expose_qr_token_or_image(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, str(self.qr.token))
        self.assertNotContains(response, 'download_qr_code')

    def test_admin_dashboard_shows_returnloop_business_statistics(self):
        admin_user = User.objects.create_superuser(
            username='stats-admin',
            email='stats-admin@example.com',
            password='Strong-Admin-Password-123!',
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ReturnLoop overview')
        self.assertContains(response, 'Recorded paid sales')

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
        profile_page = self.client.get(reverse('profile'))
        self.assertEqual(profile_page.status_code, 200)

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

    def test_registration_saves_institution_details_without_issuing_qr(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'New',
            'last_name': 'Member',
            'username': 'new-member',
            'email': 'new-member@example.com',
            'phone': '03001234567',
            'member_type': 'student',
            'institution_name': 'Example University',
            'affiliation_id': 'STU-100',
            'password1': 'Strong-New-Member-2026!',
            'password2': 'Strong-New-Member-2026!',
        })

        self.assertRedirects(response, reverse('dashboard'))
        new_user = User.objects.get(username='new-member')
        self.assertEqual(new_user.userprofile.full_name, 'New Member')
        self.assertEqual(new_user.userprofile.phone, '03001234567')
        self.assertEqual(new_user.userprofile.member_type, 'student')
        self.assertEqual(
            new_user.userprofile.institution_name,
            'Example University',
        )
        self.assertEqual(new_user.userprofile.affiliation_id, 'STU-100')
        self.assertFalse(QRCode.objects.filter(user=new_user).exists())

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Another',
            'last_name': 'Owner',
            'username': 'another-owner',
            'email': 'OWNER@example.com',
            'phone': '03001234567',
            'member_type': 'staff',
            'institution_name': 'Example University',
            'password1': 'Strong-New-Owner-2026!',
            'password2': 'Strong-New-Owner-2026!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='another-owner').exists())

    def test_registration_honeypot_displays_validation_error(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Automated',
            'last_name': 'Member',
            'username': 'automated-member',
            'email': 'automated@example.com',
            'phone': '03001234567',
            'member_type': 'student',
            'institution_name': 'Example University',
            'website': 'bot.example',
            'password1': 'Strong-Automated-Member-2026!',
            'password2': 'Strong-Automated-Member-2026!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please leave the hidden field empty.')
        self.assertFalse(User.objects.filter(username='automated-member').exists())

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

    def test_finder_honeypot_and_rate_limit_reject_spam(self):
        self.qr.is_active = True
        self.qr.save(update_fields=['is_active'])
        url = reverse('scan_qr', args=[self.qr.token])

        response = self.client.post(
            url,
            {'message': 'Found your bag', 'website': 'bot.example'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please leave the hidden field empty.')
        self.assertFalse(self.qr.notifications.exists())

        for _ in range(5):
            FinderNotification.objects.create(
                qr_code=self.qr,
                message='Existing notification',
            )

        response = self.client.post(
            url,
            {'message': 'Another message', 'location': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Too many messages')
        self.assertEqual(self.qr.notifications.count(), 5)

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
        order.amount_due = '1200.00'
        order.save(update_fields=['amount_due'])
        orders_page = self.client.get(reverse('my_orders'))
        self.assertEqual(orders_page.status_code, 200)
        self.assertContains(orders_page, 'PKR 1200.00')

    def test_invalid_order_is_not_created(self):
        self.client.login(username='owner', password='Strong-Test-Password-123!')

        response = self.client.post(reverse('place_order'), {
            'package': 'invalid',
            'quantity': '100',
        })

        self.assertRedirects(response, reverse('place_order'))
        self.assertFalse(StickerOrder.objects.filter(user=self.user).exists())

    def test_order_admin_workflow_issues_qr_confirms_payment_and_activates(self):
        admin_user = User.objects.create_superuser(
            username='order-admin',
            email='order-admin@example.com',
            password='Strong-Admin-Password-123!',
        )
        order = StickerOrder.objects.create(
            user=self.user,
            package='three',
            amount_due='1200.00',
        )
        self.client.force_login(admin_user)
        changelist = reverse('admin:core_stickerorder_changelist')

        self.client.post(changelist, {
            'action': 'generate_order_qr_codes',
            '_selected_action': [str(order.pk)],
            'index': '0',
        })
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'generated')
        self.assertTrue(QRCode.objects.filter(user=self.user).exists())

        self.client.post(changelist, {
            'action': 'mark_payments_paid',
            '_selected_action': [str(order.pk)],
            'index': '0',
        })
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'paid')
        self.assertEqual(order.payment_status, 'paid')

        self.client.post(changelist, {
            'action': 'mark_orders_delivered',
            '_selected_action': [str(order.pk)],
            'index': '0',
        })
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'delivered')

        self.client.post(changelist, {
            'action': 'activate_delivered_orders',
            '_selected_action': [str(order.pk)],
            'index': '0',
        })
        order.refresh_from_db()
        self.qr.refresh_from_db()
        self.assertEqual(order.order_status, 'active')
        self.assertTrue(self.qr.is_active)

    def test_admin_paid_action_requires_amount_to_be_recorded(self):
        admin_user = User.objects.create_superuser(
            username='payment-admin',
            email='payment-admin@example.com',
            password='Strong-Admin-Password-123!',
        )
        order = StickerOrder.objects.create(
            user=self.user,
            package='single',
            order_status='generated',
        )
        self.client.force_login(admin_user)

        self.client.post(
            reverse('admin:core_stickerorder_changelist'),
            {
                'action': 'mark_payments_paid',
                '_selected_action': [str(order.pk)],
                'index': '0',
            },
        )

        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'unpaid')
        self.assertEqual(order.order_status, 'generated')

    def test_contact_form_saves_support_message_and_rejects_honeypot(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Finder',
            'email': 'finder@example.com',
            'subject': 'Order question',
            'message': 'Can you help me with an order?',
            'website': '',
        })
        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(SupportMessage.objects.count(), 1)

        response = self.client.post(reverse('contact'), {
            'name': 'Bot',
            'email': 'bot@example.com',
            'subject': 'Spam',
            'message': 'Automated message',
            'website': 'bot.example',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please leave the hidden field empty.')
        self.assertEqual(SupportMessage.objects.count(), 1)

    def test_about_pricing_and_contact_pages_are_available(self):
        for route in ('about', 'pricing', 'contact'):
            with self.subTest(route=route):
                self.assertEqual(
                    self.client.get(reverse(route)).status_code,
                    200,
                )

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

    def test_login_accepts_username_or_email(self):
        for identifier in (self.user.username, self.user.email.upper()):
            with self.subTest(identifier_type='email' if '@' in identifier else 'username'):
                self.client.logout()
                response = self.client.post(reverse('login'), {
                    'username': identifier,
                    'password': 'Strong-Test-Password-123!',
                })
                self.assertRedirects(response, reverse('dashboard'))

    def test_password_reset_done_page_reports_email_delivery_status(self):
        response = self.client.get(reverse('password_reset_done'))
        configured = response.context['email_delivery_configured']

        self.assertEqual(configured, settings.EMAIL_DELIVERY_CONFIGURED)
        if configured:
            self.assertContains(response, "we've sent instructions")
            self.assertNotContains(
                response,
                'Password reset email delivery is not configured yet.',
            )
        else:
            self.assertContains(
                response,
                'Password reset email delivery is not configured yet.',
            )
            self.assertNotContains(response, "we've sent instructions")

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
