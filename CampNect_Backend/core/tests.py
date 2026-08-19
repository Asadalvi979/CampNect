from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
import tempfile
from .models import User, OTP, Community, CommunityMember, Note, Announcement, CollaborationPost, Message, Connection, Mentorship, Notification, ContactMessage, CommunityMessage, MentorshipMessage, CollaborationMessage

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

    def test_clean_semester_out_of_range(self):
        self.user.semester = 9
        with self.assertRaises(ValidationError):
            self.user.clean()

    def test_clean_semester_valid(self):
        self.user.semester = 4
        self.user.clean()  # should not raise

    def test_clean_semester_none_ok(self):
        self.user.semester = None
        self.user.clean()  # should not raise

    def test_save_rejects_new_bad_semester(self):
        user = User(cms='newsem', email='newsem@test.com', password='x', role='student', semester=9)
        with self.assertRaises(ValidationError):
            user.save()

    def test_save_partial_update_does_not_brick_legacy_bad_semester(self):
        # Simulate a legacy user with an out-of-range semester value in the DB
        # (written before validation existed) by bypassing save().
        User.objects.filter(pk=self.user.pk).update(semester=9)
        self.user.refresh_from_db()
        self.assertEqual(self.user.semester, 9)
        # System-level partial writes (e.g. last_login, profile_pic) must not raise.
        self.user.save(update_fields=['profile_pic'])
        # A full save that does NOT change the (legacy bad) value must not raise either.
        self.user.save()

    def test_save_rejects_change_to_bad_semester_on_existing_user(self):
        self.user.semester = 9
        with self.assertRaises(ValidationError):
            self.user.save()


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

    def test_custom_404_page(self):
        response = self.client.get('/this-page-does-not-exist-12345/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_append_slash_redirect(self):
        # Without the catch-all URL, APPEND_SLASH redirects /dashboard -> /dashboard/
        response = self.client.get('/dashboard')
        self.assertIn(response.status_code, [301, 302])
        self.assertTrue(response.url.endswith('/dashboard/'))


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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class MediaAccessTests(TestCase):
    """Protected media: files are only served to authorized users."""

    def setUp(self):
        self.alice = User.objects.create_user(cms='alice', email='alice@test.com', password=TEST_PASS, role='student', semester=6)
        self.bob = User.objects.create_user(cms='bob', email='bob@test.com', password=TEST_PASS, role='student', semester=6)
        self.eve = User.objects.create_user(cms='eve', email='eve@test.com', password=TEST_PASS, role='student', semester=3)
        self.client_alice = Client(); self.client_alice.login(cms='alice', password=TEST_PASS)
        self.client_bob = Client(); self.client_bob.login(cms='bob', password=TEST_PASS)
        self.client_eve = Client(); self.client_eve.login(cms='eve', password=TEST_PASS)

    def _file(self, name):
        return SimpleUploadedFile(name, b'campnect-file-content', content_type='text/plain')

    def _get(self, client, file_field):
        return client.get('/media/' + file_field.name)

    def test_media_requires_login(self):
        msg = Message.objects.create(sender=self.alice, receiver=self.bob, text='hi', file=self._file('hi.txt'))
        resp = Client().get('/media/' + msg.file.name)
        self.assertIn(resp.status_code, [301, 302])  # redirected to login

    def test_dm_file_sender_receiver_only(self):
        msg = Message.objects.create(sender=self.alice, receiver=self.bob, text='hi', file=self._file('hi.txt'))
        self.assertEqual(self._get(self.client_alice, msg.file).status_code, 200)
        self.assertEqual(self._get(self.client_bob, msg.file).status_code, 200)
        self.assertEqual(self._get(self.client_eve, msg.file).status_code, 403)

    def test_community_file_members_only(self):
        comm = Community.objects.create(name='CS Club', created_by=self.alice)
        CommunityMember.objects.create(user=self.alice, community=comm)
        cm = CommunityMessage.objects.create(community=comm, sender=self.alice, text='x', file=self._file('note.pdf'))
        self.assertEqual(self._get(self.client_alice, cm.file).status_code, 200)
        self.assertEqual(self._get(self.client_bob, cm.file).status_code, 403)

    def test_mentorship_file_participants_only(self):
        m = Mentorship.objects.create(mentor=self.alice, mentee=self.bob, status='accepted')
        mm = MentorshipMessage.objects.create(mentorship=m, sender=self.alice, text='x', file=self._file('guide.pdf'))
        self.assertEqual(self._get(self.client_alice, mm.file).status_code, 200)
        self.assertEqual(self._get(self.client_bob, mm.file).status_code, 200)
        self.assertEqual(self._get(self.client_eve, mm.file).status_code, 403)

    def test_notes_and_profiles_any_authenticated_user(self):
        note = Note.objects.create(title='Notes', subject='Math', file=self._file('math.pdf'), uploaded_by=self.alice)
        self.assertEqual(self._get(self.client_eve, note.file).status_code, 200)

    def test_unknown_media_path_404(self):
        resp = self.client_alice.get('/media/chat_files/does-not-exist.txt')
        self.assertEqual(resp.status_code, 404)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AdminApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(cms='admin1', email='admin1@test.com', password=TEST_PASS, role='admin')
        self.admin.is_staff = True
        self.admin.save()
        self.client.login(cms='admin1', password=TEST_PASS)

    def _post(self, **data):
        return self.client.post('/admin-api/', data)

    def test_admin_cannot_demote_self(self):
        resp = self._post(action='update_user', user_id=self.admin.id, role='student')
        self.assertEqual(resp.status_code, 400)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, 'admin')

    def test_admin_cannot_deactivate_self(self):
        resp = self._post(action='update_user', user_id=self.admin.id, is_active='0')
        self.assertEqual(resp.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_can_update_other_users(self):
        other = User.objects.create_user(cms='stu1', email='stu1@test.com', password=TEST_PASS, role='student')
        resp = self._post(action='update_user', user_id=other.id, role='senior', is_active='1')
        self.assertEqual(resp.status_code, 200)
        other.refresh_from_db()
        self.assertEqual(other.role, 'senior')

    def test_admin_cannot_delete_self(self):
        resp = self._post(action='delete_user', user_id=self.admin.id)
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    def test_admin_delete_user_removes_note_file(self):
        other = User.objects.create_user(cms='stu2', email='stu2@test.com', password=TEST_PASS, role='student')
        note = Note.objects.create(title='T', subject='S', file=SimpleUploadedFile('del.pdf', b'x', content_type='application/pdf'), uploaded_by=other)
        file_name = note.file.name
        resp = self._post(action='delete_user', user_id=other.id)
        self.assertEqual(resp.status_code, 200)
        from django.core.files.storage import default_storage
        self.assertFalse(default_storage.exists(file_name))
        self.assertFalse(Note.objects.filter(id=note.id).exists())

    def test_admin_delete_note_removes_file(self):
        other = User.objects.create_user(cms='stu3', email='stu3@test.com', password=TEST_PASS, role='student')
        note = Note.objects.create(title='T', subject='S', file=SimpleUploadedFile('del2.pdf', b'x', content_type='application/pdf'), uploaded_by=other)
        file_name = note.file.name
        resp = self._post(action='delete_note', note_id=note.id)
        self.assertEqual(resp.status_code, 200)
        from django.core.files.storage import default_storage
        self.assertFalse(default_storage.exists(file_name))
        self.assertFalse(Note.objects.filter(id=note.id).exists())


class DashboardPaginationTests(TestCase):
    """The feed shares one ?page= param across announcements and collab posts."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            cms='pageuser', email='page@riphah.edu.pk', password='pass123',
            first_name='Page', last_name='User', role='student', semester=6,
            is_active=True, is_email_verified=True,
        )
        self.client.login(cms='pageuser', password='pass123')

    def test_prev_link_shown_when_only_collab_posts_have_earlier_page(self):
        Announcement.objects.create(title='Only ann', content='x', posted_by=self.user)
        for i in range(15):
            CollaborationPost.objects.create(title=f'Post {i}', description='x', posted_by=self.user)
        response = self.client.get(reverse('dashboard'), {'page': 2, 'tab': 'all'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Previous')
        self.assertContains(response, '?page=1&amp;tab=all')

    def test_next_link_hidden_when_no_more_pages(self):
        Announcement.objects.create(title='Only ann', content='x', posted_by=self.user)
        for i in range(3):
            CollaborationPost.objects.create(title=f'Post {i}', description='x', posted_by=self.user)
        response = self.client.get(reverse('dashboard'), {'page': 1})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Next')


class ChatDeleteTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.alice = User.objects.create_user(
            cms='chatalice', email='alice@riphah.edu.pk', password='pass123',
            role='student', semester=6, is_active=True, is_email_verified=True,
        )
        self.bob = User.objects.create_user(
            cms='chatbob', email='bob@riphah.edu.pk', password='pass123',
            role='student', semester=6, is_active=True, is_email_verified=True,
        )
        self.client.login(cms='chatalice', password='pass123')
        self.msg = Message.objects.create(sender=self.alice, receiver=self.bob, text='hello')

    def test_ajax_delete_removes_message(self):
        resp = self.client.post(reverse('chat'), {'action': 'delete_message', 'message_id': self.msg.id, '_ajax': '1'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])
        self.assertFalse(Message.objects.filter(id=self.msg.id).exists())

    def test_delete_broadcast_safe_without_channels(self):
        # broadcast_message_deleted must silently no-op when Channels is unavailable.
        from .consumers import broadcast_message_deleted
        broadcast_message_deleted('chat_1_2', 999)  # should not raise
        self.assertTrue(Message.objects.filter(id=self.msg.id).exists())
