from django import forms
from .models import User, MentorshipRequest, CollaborationPost, Note, Community


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'bio', 'skills', 'profile_pic']


class MentorshipRequestForm(forms.ModelForm):
    class Meta:
        model = MentorshipRequest
        fields = ['subject', 'reason']
        widgets = {
            'subject': forms.TextInput(attrs={'placeholder': 'e.g. Web Development Career Guidance'}),
            'reason': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Explain why you want mentorship...'}),
        }


class NoteUploadForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['subject', 'title', 'description', 'file']


class CollaborationPostForm(forms.ModelForm):
    class Meta:
        model = CollaborationPost
        fields = ['title', 'description', 'required_skills', 'roles_needed']


class CommunityCreateForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ['name', 'description', 'category', 'message_permission']
