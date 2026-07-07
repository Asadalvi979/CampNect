from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import User, OTP, Community, CommunityMember, Note, Announcement, CollaborationPost, Message, Connection, Mentorship, Notification, ContactMessage

TEST_EMAIL = 'test@riphah.edu.pk'
TEST_PASS = 'pass123'


class UserModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            cms='12345', email='test@riphah.edu.pk',
            password='testpass123', first_name='Test', last_name='User',
            role='student', semester=3, department='CS',
        )

    def test_create_user(self):
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(self.user.cms, '12345')
        self.assertTrue(self.user.check_password('testpass123'))

    def test_user_str(self):
        self.assertIn('Test User', str(self.user))

    def test_can_connect_with_alumni_sem1to4(self):
        self.assertFalse(self.user.can_connect_with_alumni())

    def test_can_connect_with_alumni_sem5plus(self):
        self.user.semester = 5
        self.assertTrue(self.user.can_connect_with_alumni())

    def test_is_student_or_senior(self):
        self.assertTrue(self.user.is_student_or_senior())
        self.user.role = 'alumni'
        self.assertFalse(self.user.is_student_or_senior())

    def test_create_superuser(self):
        admin = User.objects.create_superuser(cms='admin1', email='admin@test.com', password='admin123')
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, 'admin')


class OTPSystemTests(TestCase):
    def setUp(self):
        self.otp = OTP.objects.create(
            email='test@riphah.edu.pk', code='123456',
            expires_at=timezone.now() + timedelta(seconds=300),
        )

    def test_otp_not_expired(self):
        self.assertFalse(self.otp.is_expired())

    def test_otp_expired(self):
        self.otp.expires_at = timezone.now() - timedelta(seconds=1)
        self.otp.save()
        self.assertTrue(self.otp.is_expired())

    def test_otp_str(self):
        self.assertIn('test@riphah.edu.pk', str(self.otp))


class CommunityModelTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(cms='creator1', email=TEST_EMAIL, password=TEST_PASS, role='student')
        self.community = Community.objects.create(name='Test Community', description='Test desc', created_by=self.creator)
        self.member = CommunityMember.objects.create(user=self.creator, community=self.community, is_admin=True)

    def test_community_created(self):
        self.assertEqual(Community.objects.count(), 1)

    def test_community_member_added(self):
        self.assertEqual(self.community.members.count(), 1)

    def test_member_str(self):
        self.assertIn('creator1', str(self.member))


class NoteModelTests(TestCase):
    def setUp(self):
        self.uploader = User.objects.create_user(cms='noteuser', email=TEST_EMAIL, password=TEST_PASS, role='student')
        self.note = Note.objects.create(
            title='Test Note', subject='Math', file='notes/test.pdf',
            uploaded_by=self.uploader,
        )

    def test_note_created(self):
        self.assertEqual(Note.objects.count(), 1)

    def test_note_str(self):
        self.assertEqual(str(self.note), 'Test Note')


class AnnouncementModelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(cms='annadmin', email=TEST_EMAIL, password=TEST_PASS, role='admin', is_staff=True)
        self.ann = Announcement.objects.create(title='Test Announcement', content='Test content', posted_by=self.admin)

    def test_announcement_created(self):
        self.assertEqual(Announcement.objects.count(), 1)

    def test_get_by_line_default(self):
        self.assertEqual(self.ann.get_by_line(), self.admin.get_full_name() or self.admin.cms)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            cms='testuser', email='test@riphah.edu.pk', password='pass123',
            first_name='Test', last_name='User', role='student', semester=3, department='CS',
            is_active=True, is_email_verified=True,
        )

    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_login_page(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_success(self):
        response = self.client.post(reverse('login'), {'cms': 'testuser', 'password': 'pass123'})
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_failure(self):
        response = self.client.post(reverse('login'), {'cms': 'testuser', 'password': 'wrongpass'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid CMS')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f'{reverse("login")}?next={reverse("dashboard")}')

    def test_authenticated_dashboard(self):
        self.client.login(cms='testuser', password='pass123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, f'{reverse("login")}?next={reverse("profile")}')

    def test_registration_page(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    def test_privacy_page(self):
        response = self.client.get(reverse('privacy'))
        self.assertEqual(response.status_code, 200)

    def test_terms_page(self):
        response = self.client.get(reverse('terms'))
        self.assertEqual(response.status_code, 200)


class ContactFormTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_contact_page_get(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contact.html')

    def test_contact_form_submission(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test message.',
        })
        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(ContactMessage.objects.count(), 1)
        msg = ContactMessage.objects.first()
        self.assertEqual(msg.name, 'Test User')
        self.assertEqual(msg.subject, 'Test Subject')

    def test_contact_form_invalid(self):
        response = self.client.post(reverse('contact'), {
            'name': '',
            'email': '',
            'subject': '',
            'message': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All fields are required')


class NotificationModelTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user(cms='sender1', email=TEST_EMAIL, password=TEST_PASS, role='student')
        self.recipient = User.objects.create_user(cms='recip1', email=TEST_EMAIL, password=TEST_PASS, role='alumni')
        self.notif = Notification.objects.create(
            recipient=self.recipient, sender=self.sender,
            notification_type=Notification.Type.MENTORSHIP_REQUEST,
            title='Test Notification', message='Test message',
        )

    def test_notification_created(self):
        self.assertEqual(Notification.objects.count(), 1)

    def test_unread_default(self):
        self.assertFalse(self.notif.is_read)

    def test_notification_str(self):
        self.assertIn('recip1', str(self.notif))

    def test_notification_types_defined(self):
        self.assertIn(Notification.Type.NEW_MESSAGE, [t[0] for t in Notification.Type.choices])
        self.assertIn(Notification.Type.CONNECTION, [t[0] for t in Notification.Type.choices])
        self.assertIn(Notification.Type.COMMUNITY_JOIN, [t[0] for t in Notification.Type.choices])
