from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from core.views.static_views import custom_404
from core.views.media_views import protected_media

handler404 = custom_404

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^media/(?P<path>.*)$', protected_media, name='protected_media'),
    path('', include('core.urls')),
]
