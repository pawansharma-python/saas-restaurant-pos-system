from django.urls import path
from . import views

urlpatterns = [
    # --- 1. DASHBOARD ---
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # --- 2. SETUP ---
    path('setup/', views.create_restaurant_initial, name='create_restaurant_initial'),
    path('settings/', views.restaurant_settings, name='restaurant_settings'),

    # --- 3. SUPER ADMIN REPORTS ---
    path('restaurant/<int:pk>/', views.super_restaurant_detail, name='super_restaurant_detail'),
    path('restaurant/<int:pk>/revenue/', views.super_revenue_report, name='super_revenue_report'),
    path('restaurant/<int:pk>/orders/', views.super_orders_report, name='super_orders_report'),
    path('restaurant/<int:pk>/menu/', views.super_menu_report, name='super_menu_report'),
    path('restaurant/<int:pk>/tables/', views.super_tables_report, name='super_tables_report'),
    path('restaurant/<int:pk>/staff/', views.super_staff_report, name='super_staff_report'),
    path('restaurant/<int:pk>/security/', views.super_security_report, name='super_security_report'),
    
    path('add-restaurant/', views.add_restaurant, name='add_restaurant'),
    path('edit-restaurant/<int:pk>/', views.edit_restaurant, name='edit_restaurant'),

    # --- 4. MANAGEMENT ---
    path('menu/', views.manage_menu, name='manage_menu'),
    path('menu/add/', views.add_menu_item, name='add_menu_item'),
    path('menu/edit/<str:pk>/', views.edit_menu_item, name='edit_menu_item'),
    
    path('tables/', views.manage_tables, name='manage_tables'),
    path('tables/delete/<str:table_id>/', views.delete_table, name='delete_table'),
    
    path('addons/', views.manage_addons, name='manage_addons'),
    path('addons/add-option/<int:group_id>/', views.add_addon_option, name='add_addon_option'),
    path('addons/delete-group/<int:group_id>/', views.delete_addon_group, name='delete_addon_group'),
    
    path('staff/', views.manage_staff, name='manage_staff'),
    path('staff/add/', views.add_staff, name='add_staff'),

    # --- 5. STAFF PANELS ---
    path('staff-panel/', views.staff_dashboard, name='staff_dashboard'),
    path('kitchen/', views.kitchen_dashboard, name='kitchen_dashboard'),
    path('waiter/', views.waiter_dashboard, name='waiter_dashboard'),
    path('order/update/<str:order_id>/<str:new_status>/', views.update_order_status, name='update_order_status'),
    path('order/bill/<str:order_id>/', views.generate_bill, name='generate_bill'),
    path('order/pay/<str:order_id>/', views.complete_payment, name='complete_payment'),

    # --- 6. GUEST ORDERING ---
    path('menu/<slug:restaurant_slug>/<str:table_id>/', views.guest_menu, name='guest_menu'),
    
    # --- CART ACTIONS ---
    path('cart/add/<str:item_id>/', views.add_to_cart, name='add_to_cart'), 
    path('cart/custom-add/<str:item_id>/', views.add_customized_to_cart, name='add_customized_to_cart'),
    path('item/customize/<str:item_id>/', views.item_customize, name='item_customize'), 
    
    # FIX: Isse wapas 'cart/detail/' kar diya taaki browser confuse na ho
    path('cart/detail/', views.cart_detail, name='cart_detail'),
    
    path('cart/increase/<str:item_id>/', views.increase_quantity, name='increase_quantity'),
    path('cart/decrease/<str:item_id>/', views.decrease_quantity, name='decrease_quantity'),
    
    path('order/place/<str:table_id>/', views.place_order, name='place_order'),
    path('order/success/<str:order_id>/', views.order_success, name='order_success'),
    # NEW URL
    path('order/status/<str:order_id>/', views.order_status, name='order_status'),


    # --- 7. RAZORPAY PAYMENT URLS (Ye Missing Tha) ---
    path('payment/start/<str:order_id>/', views.start_payment, name='start_payment'),
    path('payment/verify/', views.verify_payment, name='verify_payment'),
]