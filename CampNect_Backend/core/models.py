from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator


class UserManager(BaseUserManager):
    def create_user(self, cms, email=None, password=None, **extra_fields):
        if not cms:
            raise ValueError('CMS number is required')
        email = self.normalize_email(email) if email else None
        user = self.model(cms=cms, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, cms, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(cms, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        SENIOR = 'senior', 'Senior'
        ALUMNI = 'alumni', 'Alumni'
        ADMIN = 'admin', 'Admin'

    username = None
    cms = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT, db_index=True)
    semester = models.IntegerField(null=True, blank=True, db_index=True)
    department = models.CharField(max_length=100, blank=True)
    is_email_verified = models.BooleanField(default=False)
    bio = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    profile_pic = models.ImageField(upload_to='profiles/', blank=True, validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'gif', 'webp'])])
    graduation_year = models.IntegerField(null=True, blank=True)
    current_company = models.CharField(max_length=200, blank=True)
    current_position = models.CharField(max_length=200, blank=True)
    industry = models.CharField(max_length=100, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'cms'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'role']

    def __str__(self):
        return f"{self.get_full_name()} ({self.cms})"

    def can_connect_with_alumni(self):
        return self.semester is not None and self.semester >= 5

    def is_student_or_senior(self):
        return self.role in [self.Role.STUDENT, self.Role.SENIOR]

    def clean_semester(self):
        if self.semester is not None and (self.semester < 1 or self.semester > 8):
            raise ValidationError({'semester': 'Semester must be between 1 and 8.'})

    def clean(self):
        super().clean()
        self.clean_semester()

    def save(self, *args, **kwargs):
        self._enforce_semester_on_save(kwargs.get('update_fields'), kwargs.get('using'))
        super().save(*args, **kwargs)

    def _enforce_semester_on_save(self, update_fields, using=None):
        """Reject an out-of-range semester only when it is genuinely being written.

        System-level partial writes (e.g. Django's ``last_login`` update, profile
        picture uploads) must never fail because of legacy data, so those pass
        through untouched. Form-driven validation still runs in ``clean()``.
        """
        if self.semester is None or 1 <= self.semester <= 8:
            return
        if self._state.adding:
            self.clean_semester()  # raises
            return
        if update_fields is not None and 'semester' not in update_fields:
            return
        persisted = User.objects.filter(pk=self.pk).using(using).values_list('semester', flat=True).first()
        if persisted != self.semester:
            self.clean_semester()  # raises


class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='otps')
    email = models.EmailField(null=True, blank=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"{self.email or self.user.cms} - {self.code}"


class Community(models.Model):
    class Category(models.TextChoices):
        CS = 'cs', 'Computer Science'
        SE = 'se', 'Software Engineering'
        AI = 'ai', 'AI & ML'
        GENERAL = 'general', 'General'

    class MessagePermission(models.TextChoices):
        ALL_MEMBERS = 'all_members', 'All Members'
        ADMINS_ONLY = 'admins_only', 'Admins Only'

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL, db_index=True)
    message_permission = models.CharField(max_length=20, choices=MessagePermission.choices, default=MessagePermission.ALL_MEMBERS)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_communities')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CommunityMember(models.Model):
    class MemberRole(models.TextChoices):
        MEMBER = 'member', 'Member'
        MODERATOR = 'moderator', 'Moderator'
        FOUNDER = 'founder', 'Founder'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='members')
    is_admin = models.BooleanField(default=False)
    role = models.CharField(max_length=15, choices=MemberRole.choices, default=MemberRole.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'community')

    def is_moderator_or_above(self):
        return self.role in [self.MemberRole.MODERATOR, self.MemberRole.FOUNDER] or self.is_admin

    def __str__(self):
        return f"{self.user.cms} - {self.community.name}"


class Discussion(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='discussions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussions')
    content = models.TextField()
    post_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Discussion by {self.user.cms} in {self.community.name}"


class Note(models.Model):
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100)
    semester = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='notes/', validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'zip', 'rar'])])
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes')
    upload_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['subject']),
            models.Index(fields=['-upload_date']),
        ]

    def __str__(self):
        return self.title


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField(blank=True, default='')
    file = models.FileField(upload_to='chat_files/', blank=True, null=True, validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt'])])
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.sender.cms} to {self.receiver.cms}"


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    by_line = models.CharField(max_length=100, blank=True, default='')
    date_posted = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_pinned', '-date_posted']

    def __str__(self):
        return self.title

    def get_by_line(self):
        return self.by_line or self.posted_by.get_full_name() or self.posted_by.cms


class CollaborationPost(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    required_skills = models.TextField(blank=True)
    roles_needed = models.TextField(blank=True)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collaboration_posts')
    mentor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='mentored_projects')
    date_posted = models.DateTimeField(auto_now_add=True)

    def get_skills_list(self):
        return [s.strip() for s in self.required_skills.split(',') if s.strip()] if self.required_skills else []

    def get_roles_list(self):
        return [r.strip() for r in self.roles_needed.split(',') if r.strip()] if self.roles_needed else []

    def __str__(self):
        return self.title


class CollaborationMessage(models.Model):
    post = models.ForeignKey(CollaborationPost, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    file = models.FileField(upload_to='collaboration_chat/', blank=True, validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt'])])
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.cms} on {self.post.title}"


class Mentorship(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    mentor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentorships_as_mentor')
    mentee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentorships_as_mentee')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        unique_together = ('mentor', 'mentee')

    def __str__(self):
        return f"{self.mentor.cms} -> {self.mentee.cms} ({self.status})"


class MentorshipMessage(models.Model):
    mentorship = models.ForeignKey(Mentorship, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    file = models.FileField(upload_to='mentorship_chat/', blank=True, validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt'])])
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.cms} in mentorship"


class MentorshipRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentorship_requests_sent')
    alumni = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentorship_requests_received')
    subject = models.CharField(max_length=200)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'alumni')

    def __str__(self):
        return f"{self.student.cms} -> {self.alumni.cms} ({self.subject}) - {self.status}"


class CommunityMessage(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    file = models.FileField(upload_to='community_chat/', blank=True, validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt'])])
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.cms} in {self.community.name}"


class AnnouncementLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcement_likes')
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'announcement')


class AnnouncementComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcement_comments')
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)


class CollaborationPostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collab_likes')
    post = models.ForeignKey(CollaborationPost, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


class CollaborationPostComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collab_comments')
    post = models.ForeignKey(CollaborationPost, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)


class CollaborationPostInterest(models.Model):
    INTEREST_STATUS = [
        ('interested', 'Interested'),
        ('team', 'Team Member'),
        ('declined', 'Declined'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collab_interests')
    post = models.ForeignKey(CollaborationPost, on_delete=models.CASCADE, related_name='interests')
    status = models.CharField(max_length=20, choices=INTEREST_STATUS, default='interested')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'time']

    def __str__(self):
        return self.title


class Connection(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.cms} follows {self.following.cms}"


class Notification(models.Model):
    class Type(models.TextChoices):
        MENTORSHIP_REQUEST = 'mentorship_request', 'Mentorship Request'
        MENTORSHIP_ACCEPTED = 'mentorship_accepted', 'Mentorship Accepted'
        MENTORSHIP_REJECTED = 'mentorship_rejected', 'Mentorship Rejected'
        NEW_MESSAGE = 'new_message', 'New Message'
        CONNECTION = 'connection', 'New Connection'
        COMMUNITY_JOIN = 'community_join', 'Community Joined'

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    notification_type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    related_object_id = models.IntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.cms} - {self.title}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} - {self.subject}'


class CareerOpportunity(models.Model):
    class OppType(models.TextChoices):
        INTERNSHIP = 'internship', 'Internship'
        JOB = 'job', 'Job'

    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=100, blank=True)
    apply_url = models.URLField(blank=True)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='opportunities')
    opp_type = models.CharField(max_length=15, choices=OppType.choices, default=OppType.INTERNSHIP)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} at {self.company}"
