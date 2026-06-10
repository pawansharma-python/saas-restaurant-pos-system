from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RestaurantSignupForm
from restaurants.models import Restaurant # Import zaroor karein

def signup_view(request):
    if request.method == 'POST':
        form = RestaurantSignupForm(request.POST, request.FILES)
        
        if form.is_valid():
            user = form.save()
            rest_name = form.cleaned_data.get('restaurant_name')
            
            # --- LOGIC UPDATE: Owner OR Manager dono ke liye restaurant banao ---
            if user.role in ['RESTAURANT_ADMIN', 'MANAGER']:
                Restaurant.objects.create(
                    owner=user,  # Manager bhi owner field me save hoga (temporarily)
                    name=rest_name,
                    address="Update address in dashboard",
                    logo=None
                )
            
            login(request, user)
            return redirect('dashboard')
    else:
        form = RestaurantSignupForm()
    
    return render(request, 'registration/signup.html', {'form': form})