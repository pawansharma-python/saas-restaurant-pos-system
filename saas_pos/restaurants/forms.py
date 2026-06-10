from django import forms
from .models import Category, MenuItem, Table, Restaurant, AddOnGroup, AddOnOption
from django.contrib.auth.forms import UserCreationForm
from accounts.models import User

# --- 1. RESTAURANT SETTINGS FORM ---
class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = [
            'name', 'address', 'phone', 'logo', 
            'payment_qr', 'razorpay_key_id', 'razorpay_key_secret', 'upi_id', 'payment_qr', # upi_id yahan add kiya
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Restaurant Name'}),
            'address': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Contact Number'}),
            'upi_id': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'e.g. restaurant@upi'}),
            'razorpay_key_id': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'razorpay_key_secret': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5'}),
        }

# --- 2. CATEGORY FORM ---
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'e.g. Starters'}),
        }

# --- 3. ADD-ON GROUPS & OPTIONS ---
class AddOnGroupForm(forms.ModelForm):
    class Meta:
        model = AddOnGroup
        fields = ['name', 'is_required', 'is_multiple']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'e.g. Choose Size'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'w-5 h-5'}),
            'is_multiple': forms.CheckboxInput(attrs={'class': 'w-5 h-5'}),
        }

class AddOnOptionForm(forms.ModelForm):
    class Meta:
        model = AddOnOption
        fields = ['name', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'e.g. Medium'}),
            'price': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': '0'}),
        }

# --- 4. MENU ITEM FORM (With Addons) ---
class MenuItemForm(forms.ModelForm):
    addon_groups = forms.ModelMultipleChoiceField(
        queryset=AddOnGroup.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-2'}),
        required=False
    )

    class Meta:
        model = MenuItem
        fields = ['category', 'name', 'description', 'price', 'image', 'is_veg', 'is_available', 'preparation_time', 'addon_groups']
        widgets = {
            'category': forms.Select(attrs={'class': 'w-full p-2 border rounded'}),
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': 2}),
            'price': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded'}),
            'preparation_time': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded'}),
            'is_veg': forms.CheckboxInput(attrs={'class': 'w-5 h-5'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'w-5 h-5'}),
        }

    def __init__(self, user, *args, **kwargs):
        super(MenuItemForm, self).__init__(*args, **kwargs)
        
        restaurant = None
        if hasattr(user, 'owned_restaurant'):
            restaurant = user.owned_restaurant
        elif user.restaurant:
            restaurant = user.restaurant
            
        if restaurant:
            self.fields['category'].queryset = Category.objects.filter(restaurant=restaurant)
            self.fields['addon_groups'].queryset = AddOnGroup.objects.filter(restaurant=restaurant)
        else:
            self.fields['category'].queryset = Category.objects.none()
            self.fields['addon_groups'].queryset = AddOnGroup.objects.none()

# --- 5. TABLE FORM ---
class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['table_number']
        widgets = {
            'table_number': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'e.g. T-01 or Table 5'}),
        }

# --- 6. STAFF CREATION FORM ---
class StaffCreationForm(UserCreationForm):
    STAFF_ROLES = (
        ('KITCHEN', 'Kitchen Staff'),
        ('WAITER', 'Waiter'),
        ('MANAGER', 'Manager'),
    )
    
    role = forms.ChoiceField(choices=STAFF_ROLES, widget=forms.Select(attrs={'class': 'w-full p-2 border rounded'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}))
    phone_number = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'role', 'phone_number')
        
    def __init__(self, *args, **kwargs):
        super(StaffCreationForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'w-full p-2 border rounded'})