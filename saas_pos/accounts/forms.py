from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class RestaurantSignupForm(UserCreationForm):
    restaurant_name = forms.CharField(max_length=100, required=True, help_text="Enter your Restaurant Name")
    
    # --- YAHAN HUMNE CHOICES LIMIT KAR DIYE ---
    ALLOWED_ROLES = (
        ('RESTAURANT_ADMIN', 'Restaurant Owner'),
        ('MANAGER', 'Manager'),
    )
    
    role = forms.ChoiceField(
        choices=ALLOWED_ROLES, 
        widget=forms.Select(attrs={'class': 'w-full p-2 border rounded'}),
        required=True,
        label="I am a"
    )
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'first_name', 
            'last_name', 
            'username', 
            'email', 
            'phone_number', 
            'role',            # Ye ab upar wali filtered list use karega
            'profile_picture'
        )
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = True
        if commit:
            user.save()
        return user