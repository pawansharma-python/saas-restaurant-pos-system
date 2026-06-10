from django.urls import path
from . import views

urlpatterns = [
    # ...
    path('setup/restaurant/', views.create_restaurant_initial, name='create_restaurant_initial'),
    # ...
]