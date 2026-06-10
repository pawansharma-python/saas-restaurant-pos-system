from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('SUPERADMIN', 'Super Admin (Developer)'),
        ('RESTAURANT_ADMIN', 'Restaurant Owner'),
        ('MANAGER', 'Manager'),
        ('WAITER', 'Waiter'),
        ('KITCHEN', 'Kitchen Staff'),
        ('CUSTOMER', 'Guest Customer'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CUSTOMER')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    face_encoding = models.JSONField(blank=True, null=True) # For attendance

    # Staff kis restaurant ka hai
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_members')
    failed_attempts = models.IntegerField(default=0)
    is_locked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"