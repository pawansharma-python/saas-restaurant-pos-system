from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Custom User Admin configuration
class CustomUserAdmin(UserAdmin):
    model = User
    
    # List view me kya dikhega
    list_display = ['username', 'email', 'role', 'restaurant', 'is_staff']
    list_filter = ['role', 'restaurant', 'is_staff', 'is_active']
    
    # Edit page par fields kaise dikhenge
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'restaurant', 'phone_number', 'profile_picture', 'face_encoding')}),
    )
    
    # New user create karte waqt fields
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role', 'restaurant', 'phone_number', 'profile_picture')}),
    )

# Model register karein
admin.site.register(User, CustomUserAdmin)


# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from .models import User

# class CustomUserAdmin(UserAdmin):
#     model = User
    
#     # 'restaurant' ko hata diya hai
#     list_display = ['username', 'email', 'role', 'is_staff'] 
#     list_filter = ['role', 'is_staff', 'is_active']
    
#     fieldsets = UserAdmin.fieldsets + (
#         ('Custom Fields', {'fields': ('role', 'phone_number', 'profile_picture', 'face_encoding')}),
#     )
    
#     add_fieldsets = UserAdmin.add_fieldsets + (
#         ('Custom Fields', {'fields': ('role', 'phone_number', 'profile_picture')}),
#     )

# admin.site.register(User, CustomUserAdmin)