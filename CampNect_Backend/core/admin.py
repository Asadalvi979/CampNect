from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Community, CommunityMember, Discussion, Note, Message, Announcement, CollaborationPost, Event, OTP


class UserAdmin(BaseUserAdmin):
    list_display = ('cms', 'email', 'first_name', 'last_name', 'role', 'semester', 'department', 'is_staff')
    list_filter = ('role', 'semester', 'department', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('cms', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'bio', 'skills', 'profile_pic')}),
        ('Role & Academics', {'fields': ('role', 'semester', 'department')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('cms', 'email', 'first_name', 'last_name', 'role', 'semester', 'department', 'password1', 'password2'),
        }),
    )
    search_fields = ('cms', 'email', 'first_name', 'last_name')
    ordering = ('cms',)


admin.site.register(User, UserAdmin)
admin.site.register(Community)
admin.site.register(CommunityMember)
admin.site.register(Discussion)
admin.site.register(Note)
admin.site.register(Message)
admin.site.register(Announcement)
admin.site.register(CollaborationPost)
admin.site.register(Event)
admin.site.register(OTP)
