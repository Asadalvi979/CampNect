from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import User, Community, CommunityMember, Announcement, Connection, Mentorship, MentorshipRequest, Message, Notification
from django.db.models import Q


class Command(BaseCommand):
    help = "Seeds the database with initial demo data"

    def handle(self, *args, **options):
        if User.objects.count() > 0:
            self.stdout.write("Users already exist, skipping seed.")
            return

        self.stdout.write("Seeding database with demo data...")

        # Create users
        admin = User.objects.create_user(cms="admin01", email="admin@campnect.com", password="test123", first_name="Admin", last_name="User", role="admin", department="Administration", is_email_verified=True, is_staff=True)
        s1 = User.objects.create_user(cms="0044", email="asad@riphah.edu.pk", password="test123", first_name="Asadullah", last_name="Sadiq", role="student", semester=5, department="Software Engineering", is_email_verified=True, bio="Passionate about web development and AI.")
        User.objects.create_user(cms="0045", email="hannan@riphah.edu.pk", password="test123", first_name="M. Hannan", last_name="Mujahid", role="student", semester=4, department="Computer Science", is_email_verified=True)
        User.objects.create_user(cms="0079", email="tayyab@riphah.edu.pk", password="test123", first_name="Muhammad", last_name="Tayyab", role="student", semester=4, department="Software Engineering", is_email_verified=True)
        a1 = User.objects.create_user(cms="1000", email="alumni1@riphah.edu.pk", password="test123", first_name="Alumni", last_name="One", role="alumni", department="Computer Science", is_email_verified=True, graduation_year=2024, current_company="TechCorp", current_position="Software Engineer", industry="Technology", skills="Python, Django, React, AWS")
        User.objects.create_user(cms="1002", email="alumni2@riphah.edu.pk", password="test123", first_name="Alumni", last_name="Two", role="alumni", department="Software Engineering", is_email_verified=True, graduation_year=2023, current_company="DevStudio", current_position="Full Stack Developer", industry="Technology")
        senior = User.objects.create_user(cms="0011", email="ali@riphah.edu.pk", password="test123", first_name="Ali", last_name="Hassan", role="senior", semester=6, department="Software Engineering", is_email_verified=True)
        User.objects.create_user(cms="1234", email="malik@riphah.edu.pk", password="test123", first_name="Malik", last_name="Ahmed", role="student", semester=2, department="Computer Science", is_email_verified=True)

        self.stdout.write("  Created 8 users")

        # Create community
        comm = Community.objects.create(name="Web Development Club", description="For web dev enthusiasts", category="cs", created_by=admin)
        CommunityMember.objects.create(user=admin, community=comm, is_admin=True, role='founder')
        CommunityMember.objects.create(user=s1, community=comm, role='member')
        CommunityMember.objects.create(user=senior, community=comm, role='member')
        self.stdout.write("  Created 1 community with 3 members")

        # Announcements
        ann = Announcement.objects.create(title="Welcome to CampNect!", content="Welcome to CampNect - your campus connection platform. Connect with peers, alumni, and mentors to enhance your university experience!", posted_by=admin, is_pinned=True)
        Announcement.objects.create(title="Mentorship Program Launch", content="We are excited to announce the launch of our mentorship program. Alumni can now mentor current students!", posted_by=admin)
        self.stdout.write("  Created 2 announcements")

        # Connection
        Connection.objects.create(follower=s1, following=senior)
        Connection.objects.create(follower=senior, following=s1)
        Connection.objects.create(follower=a1, following=s1)
        self.stdout.write("  Created 3 connections")

        # Mentorship
        mentorship = Mentorship.objects.create(mentor=a1, mentee=senior, status='accepted')
        Mentorship.objects.create(mentor=a1, mentee=s1, status='pending')
        self.stdout.write("  Created 2 mentorships")

        # Mentorship Requests
        MentorshipRequest.objects.create(student=senior, alumni=a1, subject="Career Guidance in Tech", reason="I want guidance on entering the tech industry after graduation.", status='accepted')
        self.stdout.write("  Created 1 mentorship request")

        # Messages
        Message.objects.create(sender=s1, receiver=senior, text="Hey Ali! How are you?")
        Message.objects.create(sender=senior, receiver=s1, text="I'm good! Ready for the project?")
        Message.objects.create(sender=s1, receiver=senior, text="Yes, let's start working on it this weekend.")
        self.stdout.write("  Created 3 messages")

        # Notifications
        Notification.objects.create(recipient=a1, sender=senior, notification_type=Notification.Type.MENTORSHIP_REQUEST, title=f"Mentorship request from {senior.first_name} {senior.last_name}", message="Career Guidance in Tech")
        Notification.objects.create(recipient=senior, sender=a1, notification_type=Notification.Type.MENTORSHIP_ACCEPTED, title=f"Mentorship accepted by {a1.first_name} {a1.last_name}", message="Your mentorship request has been accepted!")
        self.stdout.write("  Created 2 notifications")

        self.stdout.write(self.style.SUCCESS("Database seeded successfully! Users password: test123"))
