from django.contrib import admin
from django.urls import path
from app1 import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth pages
    path('signup/', views.SignUpPage, name='signup'),
    path('logout/', views.LogoutPage, name='logout'),

    # Home page after login
    path('home/', views.HomePage, name='home'),

    # Default page → Login page
    path('', views.LoginPage, name='login'),
]

# Media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
