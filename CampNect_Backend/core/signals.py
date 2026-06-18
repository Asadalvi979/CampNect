from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import MentorshipRequest, Mentorship, Notification


def send_notification_email(recipient, subject, text_content, html_content):
    if recipient.email and settings.EMAIL_HOST_USER:
        msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [recipient.email])
        msg.attach_alternative(html_content, 'text/html')
        msg.send()


@receiver(post_save, sender=MentorshipRequest)
def mentorship_request_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            recipient=instance.alumni,
            sender=instance.student,
            notification_type=Notification.Type.MENTORSHIP_REQUEST,
            title=f"Mentorship request from {instance.student.get_full_name() or instance.student.cms}",
            message=instance.subject,
            related_object_id=instance.id,
        )

        student_name = instance.student.get_full_name() or instance.student.cms
        email_subject = f"New mentorship request from {student_name}"
        email_text = f"{student_name} has sent you a mentorship request.\n\nSubject: {instance.subject}\nReason: {instance.reason}"
        email_html = render_to_string('emails/mentorship_request.html', {
            'student_name': student_name,
            'alumni_name': instance.alumni.get_full_name() or instance.alumni.cms,
            'subject': instance.subject,
            'reason': instance.reason,
            'dashboard_url': f"{settings.SITE_URL}/dashboard/",
        })
        send_notification_email(instance.alumni, email_subject, email_text, email_html)

    elif instance.status == 'rejected' and not kwargs.get('created'):
        Notification.objects.create(
            recipient=instance.student,
            sender=instance.alumni,
            notification_type=Notification.Type.MENTORSHIP_REJECTED,
            title=f"Mentorship request was not accepted",
            message=f"Your request to {instance.alumni.get_full_name() or instance.alumni.cms} was not accepted.",
            related_object_id=instance.id,
        )


@receiver(post_save, sender=Mentorship)
def mentorship_accepted_notification(sender, instance, created, **kwargs):
    if instance.status == 'accepted':
        Notification.objects.create(
            recipient=instance.mentee,
            sender=instance.mentor,
            notification_type=Notification.Type.MENTORSHIP_ACCEPTED,
            title=f"Mentorship accepted by {instance.mentor.get_full_name() or instance.mentor.cms}",
            message="Your mentorship request has been accepted. Start your journey!",
            related_object_id=instance.id,
        )

        mentor_name = instance.mentor.get_full_name() or instance.mentor.cms
        email_subject = f"Mentorship accepted by {mentor_name}"
        email_text = f"Great news! {mentor_name} has accepted your mentorship request.\n\nYou can now start your mentorship journey together."
        email_html = render_to_string('emails/mentorship_accepted.html', {
            'mentor_name': mentor_name,
            'mentee_name': instance.mentee.get_full_name() or instance.mentee.cms,
            'dashboard_url': f"{settings.SITE_URL}/dashboard/",
        })
        send_notification_email(instance.mentee, email_subject, email_text, email_html)
