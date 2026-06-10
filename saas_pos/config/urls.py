"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views # Import this
from django.views.generic import RedirectView # <-- Ye Import karein

# --- YE LINE MISSING THI (Isko add karein) ---
from accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- YE LINE ADD KAREIN (Root URL Redirect) ---
    # Agar koi khali domain khole, to use 'login' par bhej do
    path('', RedirectView.as_view(pattern_name='login', permanent=False)), 
    # ----------------------------------------------

     # Custom Login Route
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    
    # Logout Route (Simply logs out and redirects to LOGOUT_REDIRECT_URL in settings)
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('', include('restaurants.urls')), # Dashboard URLs
    # Auth URLs (Login/Logout ke liye Django ka built-in use karenge abhi)
    path('accounts/', include('django.contrib.auth.urls')), 
    path('signup/', account_views.signup_view, name='signup'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)