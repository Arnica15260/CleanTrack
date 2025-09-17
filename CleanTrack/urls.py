from django.contrib import admin
from django.urls import path
from CleanTrack import views

# 🔹 এই দুইটা import করতে হবে
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('contact/', views.contact, name='contact'),
]

# 🔹 Static files serve করার জন্য
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
