from django.contrib import admin
from django.urls import path, include

from CleanTrack import views  # home/about
from users.views import contact_view  # ✅ use the working contact handler

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Public pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),

    # ✅ Route /contact/ to users.views.contact_view (saves + shows messages)
    path('contact/', contact_view, name='contact'),

    # Auth / user features
    path('users/', include(('users.urls', 'users'), namespace='users')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
