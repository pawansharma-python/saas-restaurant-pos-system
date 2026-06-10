import cv2
import numpy as np
import base64
import json
import uuid
from io import BytesIO
from itertools import chain

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from decimal import Decimal

from accounts.models import User
from .models import (
    Restaurant,
    Category,
    MenuItem,
    Table,
    Order,
    OrderItem,
    AddOnGroup,
    AddOnOption,
)
from .forms import (
    CategoryForm,
    MenuItemForm,
    TableForm,
    RestaurantForm,
    StaffCreationForm,
    AddOnGroupForm,
    AddOnOptionForm,
)
from .utils import calculate_distance

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================


def get_current_restaurant(user):
    """
    Safely retrieves the restaurant based on user role.
    """
    if user.role == "RESTAURANT_ADMIN":
        return getattr(user, "owned_restaurant", None)
    return getattr(user, "restaurant", None)


# ==========================================
# 2. MAIN DASHBOARD ROUTER (FIXED)
# ==========================================


@login_required
def dashboard_view(request):
    user = request.user

    # --- A. SUPER ADMIN ---
    if user.role == "SUPERADMIN":
        restaurants = Restaurant.objects.all().select_related("owner")
        users = (
            User.objects.filter(role__in=["RESTAURANT_ADMIN", "MANAGER"])
            .select_related("restaurant")
            .order_by("-date_joined")
        )

        return render(
            request,
            "dashboard/superadmin_home.html",
            {"restaurants": restaurants, "users": users, "is_superadmin": True},
        )

    # --- B. OWNER / MANAGER ---
    elif user.role in ["RESTAURANT_ADMIN", "MANAGER"]:
        try:
            if hasattr(user, "owned_restaurant"):
                restaurant = user.owned_restaurant
            elif user.restaurant:
                restaurant = user.restaurant
            else:
                return redirect("create_restaurant_initial")

            # 1. Live Stats
            today = timezone.now().date()
            today_revenue = (
                Order.objects.filter(
                    restaurant=restaurant, created_at__date=today, payment_status=True
                ).aggregate(Sum("total_amount"))["total_amount__sum"]
                or 0
            )
            today_orders_count = Order.objects.filter(
                restaurant=restaurant, created_at__date=today
            ).count()
            pending_orders = Order.objects.filter(
                restaurant=restaurant, status__in=["RECEIVED", "PREPARING"]
            ).count()

            # 2. Staff Stats (Counts only)
            total_managers = User.objects.filter(
                restaurant=restaurant, role="MANAGER"
            ).count()
            total_waiters = User.objects.filter(
                restaurant=restaurant, role="WAITER"
            ).count()
            total_kitchen = User.objects.filter(
                restaurant=restaurant, role="KITCHEN"
            ).count()

            # 3. Operations (Attendance Removed)
            # present_staff_count hataya gaya

            total_staff_count = restaurant.staff_members.count()
            operational_days = (
                Order.objects.filter(restaurant=restaurant)
                .dates("created_at", "day")
                .count()
            )
            recent_orders = Order.objects.filter(restaurant=restaurant).order_by(
                "-created_at"
            )[:5]

            context = {
                "restaurant": restaurant,
                "today_revenue": today_revenue,
                "today_orders_count": today_orders_count,
                "pending_orders": pending_orders,
                "recent_orders": recent_orders,
                "total_managers": total_managers,
                "total_waiters": total_waiters,
                "total_kitchen": total_kitchen,
                # 'present_staff_count' removed from context
                "total_staff_count": total_staff_count,
                "operational_days": operational_days,
            }
            return render(request, "dashboard/restaurant_home.html", context)

        except Restaurant.DoesNotExist:
            return redirect("create_restaurant_initial")

    # --- C. STAFF ---
    elif user.role in ["WAITER", "KITCHEN"]:
        return redirect("staff_dashboard")

    # --- D. FALLBACK ---
    return redirect("login")


# 2. NEW: SETTINGS VIEW (Edit Restaurant Details)
@login_required
def restaurant_settings(request):
    # Sirf Owner/Manager access karein
    if request.user.role not in ["RESTAURANT_ADMIN", "MANAGER"]:
        return redirect("dashboard")

    restaurant = get_current_restaurant(request.user)

    if request.method == "POST":
        form = RestaurantForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = RestaurantForm(instance=restaurant)

    return render(
        request, "dashboard/settings.html", {"form": form, "restaurant": restaurant}
    )


@login_required
def add_restaurant(request):
    # Sirf Super Admin hi naya restaurant add kar sakta hai
    if request.user.role != "SUPERADMIN":
        return redirect("dashboard")

    if request.method == "POST":
        form = RestaurantForm(request.POST, request.FILES)
        if form.is_valid():
            restaurant = form.save(commit=False)
            # Owner set karo
            restaurant.owner = request.user

            restaurant.save()

            return redirect("dashboard")
    else:
        form = RestaurantForm()

    return render(request, "dashboard/add_restaurant.html", {"form": form})


@login_required
def edit_restaurant(request, pk):
    # Sirf Super Admin hi edit kar sakta hai
    if request.user.role != "SUPERADMIN":
        return redirect("dashboard")

    # Wo restaurant dhoondo jise edit karna hai
    restaurant = get_object_or_404(Restaurant, pk=pk)

    if request.method == "POST":
        # instance=restaurant ka matlab hai purana data form me bhara hua aayega
        form = RestaurantForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = RestaurantForm(instance=restaurant)

    return render(
        request,
        "dashboard/add_restaurant.html",
        {"form": form, "is_edit": True, "restaurant_name": restaurant.name},
    )


# 1. Restaurant Admin Dashboard (Stats & Links)
# Note: dashboard_view logic humne pehle step me likha tha, wo yahan redirect karega.


# --- Updated Views ---


@login_required
def manage_tables(request):
    # Fix: Restaurant fetch logic updated
    restaurant = get_current_restaurant(request.user)

    if not restaurant:
        return render(
            request, "dashboard/error.html", {"message": "No Restaurant Found!"}
        )

    tables = Table.objects.filter(restaurant=restaurant)

    if request.method == "POST":
        form = TableForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.restaurant = restaurant  # Ab yahan sahi restaurant object aayega
            obj.save()
            return redirect("manage_tables")
    else:
        form = TableForm()

    return render(
        request, "dashboard/manage_tables.html", {"tables": tables, "form": form}
    )


# Note: manage_menu aur add_menu_item me bhi yehi logic use karein:


@login_required
def manage_menu(request):
    restaurant = get_current_restaurant(request.user)  # Fix here
    if not restaurant:
        return redirect("dashboard")

    categories = Category.objects.filter(restaurant=restaurant).prefetch_related(
        "items"
    )

    if request.method == "POST":
        if "add_category" in request.POST:
            c_form = CategoryForm(request.POST, request.FILES)
            if c_form.is_valid():
                obj = c_form.save(commit=False)
                obj.restaurant = restaurant
                obj.save()
                return redirect("manage_menu")

    else:
        c_form = CategoryForm()

    return render(
        request,
        "dashboard/manage_menu.html",
        {"categories": categories, "c_form": c_form, "restaurant": restaurant},
    )


@login_required
def add_menu_item(request):
    restaurant = get_current_restaurant(request.user)  # Fix here

    if request.method == "POST":
        # Form ko user pass kar rahe hain taaki wo logic handle kare
        form = MenuItemForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data["category"].restaurant == restaurant:
                form.save()
                return redirect("manage_menu")
    else:
        form = MenuItemForm(request.user)

    return render(request, "dashboard/add_menu_item.html", {"form": form})


@login_required
def edit_menu_item(request, pk):
    restaurant = get_current_restaurant(request.user)
    # Security: Ensure item belongs to the user's restaurant
    item = get_object_or_404(MenuItem, pk=pk, category__restaurant=restaurant)

    if request.method == "POST":
        # 'instance=item' ka matlab hai purane item ko update karna
        form = MenuItemForm(request.user, request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect("manage_menu")
    else:
        # Pre-fill form with existing data
        form = MenuItemForm(request.user, instance=item)

    # Hum 'add_menu_item.html' template hi reuse kar sakte hain title badal kar
    return render(
        request,
        "dashboard/add_menu_item.html",
        {
            "form": form,
            "is_edit": True,  # Template me title change karne ke liye
            "item_name": item.name,
        },
    )


@login_required
def delete_table(request, table_id):
    restaurant = get_current_restaurant(request.user)

    # Security: Sirf wahi table delete hogi jo is user ke restaurant ki hai
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)

    # Delete Logic
    table.delete()

    return redirect("manage_tables")


def guest_menu(request, restaurant_slug, table_id):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
    table = get_object_or_404(Table, unique_id=table_id)

    # 1. Session Isolation: Agar Table ID badal gayi hai to Cart saaf karo
    if request.session.get("table_id") != str(table_id):
        request.session["cart"] = {}
        request.session["table_id"] = str(table_id)
        request.session["restaurant_slug"] = restaurant_slug

    categories = Category.objects.filter(restaurant=restaurant).prefetch_related(
        "items"
    )

    # Cart Data Calculation (Footer ke liye)
    cart = request.session.get("cart", {})

    total_items = 0
    total_price = 0

    for key, item_data in cart.items():
        total_items += int(item_data.get("qty", 0))
        total_price += float(item_data.get("price", 0)) * int(item_data.get("qty", 0))

    return render(
        request,
        "guest/menu.html",
        {
            "restaurant": restaurant,
            "table": table,
            "categories": categories,
            "cart": cart,
            "total_items": total_items,
            "total_price": total_price,
        },
    )


# 1. CUSTOMIZE PAGE VIEW
def item_customize(request, item_id):
    # Table ID session se nikalo (Security)
    if "table_id" not in request.session:
        return redirect("login")  # Ya guest menu redirect

    item = get_object_or_404(MenuItem, pk=item_id)

    # Agar koi customization nahi hai, to seedha add kar do
    if not item.addon_groups.exists():
        return add_to_cart_direct(request, item_id)

    return render(request, "guest/customize_item.html", {"item": item})


# 2. ADD TO CART WITH CUSTOMIZATION (POST Logic)
def add_customized_to_cart(request, item_id):
    if request.method == "POST":
        # FIX: Use pk instead of id for safety
        item = get_object_or_404(MenuItem, pk=item_id)
        cart = request.session.get("cart", {})

        selected_addons = []
        extra_cost = 0
        for group in item.addon_groups.all():
            if group.is_multiple:
                selected_ids = request.POST.getlist(f"group_{group.id}")
                options = AddOnOption.objects.filter(id__in=selected_ids)
            else:
                selected_id = request.POST.get(f"group_{group.id}")
                options = AddOnOption.objects.filter(id=selected_id)

            for opt in options:
                selected_addons.append(f"{opt.name}")
                extra_cost += float(opt.price)

        cart_key = str(uuid.uuid4())[:8]
        cart[cart_key] = {
            "item_id": item.pk,  # CHANGE: .id -> .pk
            "qty": 1,
            "price": float(item.price) + extra_cost,
            "name": item.name,
            "addons": selected_addons,
        }
        request.session["cart"] = cart
        return redirect("cart_detail")


# 3. HELPER: DIRECT ADD (Old logic for simple items)
def add_to_cart_direct(request, item_id):
    item = get_object_or_404(MenuItem, pk=item_id)
    cart = request.session.get("cart", {})
    cart_key = str(uuid.uuid4())[:8]

    cart[cart_key] = {
        "item_id": item.pk,  # CHANGE: .id -> .pk
        "qty": 1,
        "price": float(item.price),
        "name": item.name,
        "addons": [],
    }
    request.session["cart"] = cart
    return redirect(request.META.get("HTTP_REFERER", "/"))


def add_to_cart(request, item_id):
    item = get_object_or_404(MenuItem, pk=item_id)

    cart = request.session.get("cart", {})
    cart_key = str(uuid.uuid4())[:8]

    cart[cart_key] = {
        "item_id": item.pk,
        "qty": 1,
        "price": float(item.price),
        "name": item.name,
        "addons": [],
    }

    request.session["cart"] = cart

    return redirect(request.META.get("HTTP_REFERER", "/"))


# ==========================================
# CART & ORDER LOGIC (FIXED)
# ==========================================

# restaurants/views.py me cart_detail function ko replace karein:
# restaurants/views.py


def cart_detail(request):
    cart = request.session.get("cart", {})
    table_id = request.session.get("table_id")

    if not cart:
        return redirect(request.META.get("HTTP_REFERER", "/"))

    table = get_object_or_404(Table, unique_id=table_id)

    items = []
    subtotal = 0  # Isme sirf items ka total aayega

    for key, val in cart.items():

        # Old cart format support
        if isinstance(val, int):
            try:
                item = MenuItem.objects.get(pk=key)

                val = {
                    "item_id": item.pk,
                    "qty": val,
                    "price": float(item.price),
                    "name": item.name,
                    "addons": [],
                }
            except MenuItem.DoesNotExist:
                continue

        line_total = float(val["price"]) * int(val["qty"])
        subtotal += line_total

        items.append(
            {
                "key": key,
                "item_id": val["item_id"],
                "name": val["name"],
                "qty": val["qty"],
                "price": val["price"],
                "subtotal": line_total,
                "addons": val.get("addons", []),
            }
        )

    # --- TAX CALCULATION (NEW) ---
    tax_rate = 0.05  # 5% GST
    tax_amount = round(subtotal * tax_rate, 2)
    grand_total = round(subtotal + tax_amount, 2)

    return render(
        request,
        "guest/cart.html",
        {
            "items": items,
            "subtotal": subtotal,  # Item Total
            "tax_amount": tax_amount,  # GST
            "total_price": grand_total,  # Final Amount
            "table": table,
            "table_id": table_id,
        },
    )


def increase_quantity(request, item_id):
    cart_key = str(item_id)
    cart = request.session.get("cart", {})

    if cart_key in cart:

        if isinstance(cart[cart_key], int):
            cart[cart_key] += 1
        else:
            cart[cart_key]["qty"] += 1

        request.session["cart"] = cart

    return redirect("cart_detail")


def decrease_quantity(request, item_id):
    cart_key = str(item_id)
    cart = request.session.get("cart", {})

    if cart_key in cart:

        if isinstance(cart[cart_key], int):
            if cart[cart_key] > 1:
                cart[cart_key] -= 1
            else:
                del cart[cart_key]

        else:
            if cart[cart_key]["qty"] > 1:
                cart[cart_key]["qty"] -= 1
            else:
                del cart[cart_key]

        request.session["cart"] = cart

    return redirect("cart_detail")


# restaurants/views.py


# 1. PLACE ORDER (Updated Redirect)
def place_order(request, table_id):
    table = get_object_or_404(Table, unique_id=table_id)
    cart = request.session.get("cart", {})

    print("FULL CART =", cart)

    if not cart:
        return redirect(
            "guest_menu",
            restaurant_slug=table.restaurant.slug,
            table_id=table_id,
        )

    existing_order = Order.objects.filter(
        table=table,
        payment_status=False
    ).first()

    if existing_order:
        order = existing_order
        order.status = "RECEIVED"
        order.save()
    else:
        order = Order.objects.create(
            restaurant=table.restaurant,
            table=table,
            total_amount=0,
            status="RECEIVED",
            payment_status=False,
        )

    for key, val in cart.items():
        print("CART ITEM =", val)

        try:
            food_item = MenuItem.objects.get(pk=val["item_id"])

            order_item = OrderItem.objects.create(
                order=order,
                food_item=food_item,
                quantity=val["qty"],
                price=val["price"],
                customizations=val.get("addons", []),
                is_prepared=False,
            )

            print("ITEM SAVED =", order_item.id)

        except Exception as e:
            print("ORDER ITEM ERROR =", e)

    print("FINAL ITEM COUNT =", order.items.count())

    all_items_total = sum(
        item.price * item.quantity
        for item in order.items.all()
    )

    tax_amount = all_items_total * Decimal("0.05")
    order.total_amount = round(all_items_total + tax_amount, 2)
    order.save()

    request.session["cart"] = {}

    return redirect("order_status", order_id=order.order_id)



# 2. NEW VIEW: ORDER STATUS (Live Status Page)
def order_status(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    # Refresh Total (Just in case)
    subtotal = sum(item.price * item.quantity for item in order.items.all())
    tax_amount = subtotal * Decimal("0.05")

    return render(
        request,
        "guest/order_status.html",
        {"order": order, "subtotal": subtotal, "tax_amount": tax_amount},
    )


def order_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    return render(request, "guest/success.html", {"order": order})


# --- ROLE BASED DASHBOARDS ---


@login_required
def kitchen_dashboard(request):
    if request.user.role not in ["KITCHEN", "RESTAURANT_ADMIN", "SUPERADMIN"]:
        return redirect("dashboard")

    restaurant = get_current_restaurant(request.user)

    # --- CHANGE HERE: Add 'READY' and 'SERVED' to the list ---
    kitchen_orders = Order.objects.filter(
        restaurant=restaurant,
        # Ab hum READY aur SERVED bhi mangwa rahe hain
        status__in=["RECEIVED", "PREPARING", "READY", "SERVED"],
    ).order_by("created_at")

    return render(request, "dashboard/kitchen_home.html", {"orders": kitchen_orders})


@login_required
def waiter_dashboard(request):
    # Sirf Waiter ya Admin/Owner ke liye
    if request.user.role not in ["WAITER", "RESTAURANT_ADMIN", "SUPERADMIN"]:
        return redirect("dashboard")

    restaurant = get_current_restaurant(request.user)

    # 1. Orders jo kitchen ne READY kar diye hain (Pickup ke liye)
    ready_orders = Order.objects.filter(restaurant=restaurant, status="READY")

    # 2. Orders jo table par chal rahe hain (Billing ke liye)
    active_tables = (
        Order.objects.filter(restaurant=restaurant, payment_status=False)
        .exclude(status="COMPLETED")
        .order_by("-updated_at")
    )

    return render(
        request,
        "dashboard/waiter_dashboard.html",
        {"ready_orders": ready_orders, "orders": active_tables},
    )


@login_required
def staff_dashboard(request):
    user = request.user

    if user.role == "KITCHEN":
        return redirect("kitchen_dashboard")
    elif user.role == "WAITER":
        return redirect("waiter_dashboard")
    elif user.role == "RESTAURANT_ADMIN" or user.role == "SUPERADMIN":
        return render(request, "dashboard/owner_choice.html")
    else:
        # --- ERROR YAHAN THA ---
        # Purana code: return redirect('guest_menu')  <-- Ye galat tha kyunki arguments missing the

        # Naya code: Agar koi role nahi hai, to wapas Login par bhej do
        return redirect("login")


@login_required
def manage_staff(request):
    restaurant = get_current_restaurant(request.user)
    if not restaurant:
        return redirect("dashboard")

    # Us restaurant ke sare staff members (Owner ko chodkar)
    staff_members = User.objects.filter(restaurant=restaurant)

    return render(
        request,
        "dashboard/manage_staff.html",
        {"staff_members": staff_members, "restaurant": restaurant},
    )


@login_required
def add_staff(request):
    restaurant = get_current_restaurant(request.user)

    if request.method == "POST":
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.restaurant = restaurant  # Staff ko is restaurant se link karo
            user.save()
            return redirect("manage_staff")
    else:
        form = StaffCreationForm()

    return render(request, "dashboard/add_staff.html", {"form": form})


@login_required
def update_order_status(request, order_id, new_status):
    order = get_object_or_404(Order, order_id=order_id)

    # Security check...
    staff_restaurant = get_current_restaurant(request.user)
    if order.restaurant != staff_restaurant:
        return redirect("dashboard")

    # LOGIC CHANGE:
    # Jab Kitchen bole "READY", iska matlab abhi jitne pending the wo ban gaye.
    if new_status == "READY":
        for item in order.items.all():
            # Cooked quantity ko Total quantity ke barabar kar do
            item.quantity_cooked = item.quantity
            item.save()

    order.status = new_status
    order.save()

    return redirect(request.META.get("HTTP_REFERER", "dashboard"))


# def increase_quantity(request, item_id):
#     cart = request.session.get("cart", {})
#     item_id_str = str(item_id)

#     if item_id_str in cart:
#         cart[item_id_str] += 1
#     else:
#         cart[item_id_str] = 1

#     request.session["cart"] = cart
#     return redirect(request.META.get("HTTP_REFERER", "/"))


# def decrease_quantity(request, item_id):
#     cart = request.session.get("cart", {})
#     item_id_str = str(item_id)

#     if item_id_str in cart:
#         if cart[item_id_str] > 1:
#             cart[item_id_str] -= 1
#         else:
#             del cart[item_id_str]  # 0 hone par remove kar do

#     request.session["cart"] = cart
#     return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def generate_bill(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    # 1. Subtotal Calculate karein (Bina Tax ke item total)
    subtotal = sum(item.price * item.quantity for item in order.items.all())

    # 2. Tax Calculate karein (5%)
    tax_amount = subtotal * Decimal("0.05")

    # Context me bhejein
    return render(
        request,
        "dashboard/bill_page.html",
        {
            "order": order,
            "subtotal": round(subtotal, 2),
            "tax_amount": round(tax_amount, 2),
        },
    )


@login_required
def complete_payment(request, order_id, method):
    order = get_object_or_404(Order, order_id=order_id)

    # Payment Save karein
    order.payment_status = True
    order.status = "COMPLETED"  # Ye karte hi waiter ki screen se gayab ho jayega
    order.payment_method = method  # 'CASH' or 'ONLINE'
    order.save()

    return redirect("waiter_dashboard")


@login_required
def create_restaurant_initial(request):
    # Agar pehle se restaurant hai to dashboard bhej do
    if hasattr(request.user, "owned_restaurant"):
        return redirect("dashboard")

    if request.method == "POST":
        form = RestaurantForm(request.POST, request.FILES)
        if form.is_valid():
            restaurant = form.save(commit=False)
            restaurant.owner = request.user  # Current user ko owner banao
            restaurant.save()
            return redirect("dashboard")
    else:
        # Form me owner field chupana padega kyunki wo auto-set hoga
        form = RestaurantForm()
        # Hum template me owner field render nahi karenge

    return render(request, "dashboard/setup_restaurant.html", {"form": form})


@login_required
def complete_payment(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, order_id=order_id)

        # 1. Form se data nikalo
        payment_method = request.POST.get("payment_method")

        # 2. Online Payment Logic
        if payment_method == "ONLINE":
            order.transaction_id = request.POST.get("txn_id")
            order.payer_name = request.POST.get("payer_name")

            # --- SCREENSHOT UPLOAD LOGIC ---
            # Agar file upload ki gayi hai, to use save karo
            if "payment_screenshot" in request.FILES:
                order.payment_proof = request.FILES["payment_screenshot"]

        # 3. Cash Payment Logic
        else:
            order.transaction_id = f"COD-T{order.table.table_number}-{order.pk}"
            order.payer_name = "Cash @ Counter"

        # 4. Status Update
        order.payment_status = True
        order.payment_method = payment_method
        order.status = "COMPLETED"  # Waiter dashboard se hat jayega

        order.save()

        return redirect("waiter_dashboard")

    return redirect("waiter_dashboard")


# 1. MAIN DETAIL VIEW (Updated with Table Count)
@login_required
def super_restaurant_detail(request, pk):
    if request.user.role != "SUPERADMIN":
        return redirect("dashboard")
    restaurant = get_object_or_404(Restaurant, pk=pk)

    # --- NEW: Fetch Key Users (Owner & Managers) for THIS restaurant ---
    key_users = User.objects.filter(
        restaurant=restaurant, role__in=["RESTAURANT_ADMIN", "MANAGER"]
    )
    # Owner ko bhi list me include karein agar wo 'restaurant' field se linked nahi hai (OneToOne field issue)
    if restaurant.owner not in key_users:
        # Chain them together or create a list
        from itertools import chain

        key_users = list(chain([restaurant.owner], key_users))

    context = {
        "restaurant": restaurant,
        "key_users": key_users,  # <--- Ye naya data hai template ke liye
        "total_staff": restaurant.staff_members.count(),
        "total_revenue": Order.objects.filter(
            restaurant=restaurant, payment_status=True
        ).aggregate(Sum("total_amount"))["total_amount__sum"]
        or 0,
        "total_orders": Order.objects.filter(restaurant=restaurant).count(),
        "total_menu_items": MenuItem.objects.filter(
            category__restaurant=restaurant
        ).count(),
        "total_tables": Table.objects.filter(restaurant=restaurant).count(),
        "recent_orders": Order.objects.filter(restaurant=restaurant).order_by(
            "-created_at"
        )[:5],
        "staff_list": restaurant.staff_members.all(),
    }
    return render(request, "dashboard/super_restaurant_detail.html", context)


# 2. REVENUE REPORT (A to Z History)
@login_required
def super_revenue_report(request, pk):
    if request.user.role != "SUPERADMIN":
        return redirect("dashboard")
    restaurant = get_object_or_404(Restaurant, pk=pk)

    # Sirf Paid Orders (Revenue)
    orders = Order.objects.filter(restaurant=restaurant, payment_status=True).order_by(
        "-created_at"
    )

    # Date Filter Logic
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    # Pagination (20 items per page)
    paginator = Paginator(orders, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "dashboard/reports/revenue.html",
        {
            "restaurant": restaurant,
            "page_obj": page_obj,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


# 3. ORDERS REPORT (Full Detail)
@login_required
def super_orders_report(request, pk):
    if request.user.role != "SUPERADMIN":
        return redirect("dashboard")
    restaurant = get_object_or_404(Restaurant, pk=pk)

    # Sare Orders (Paid/Unpaid/Cancelled)
    orders = (
        Order.objects.filter(restaurant=restaurant)
        .prefetch_related("items__food_item")
        .order_by("-created_at")
    )

    # Date Filter
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    if start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "dashboard/reports/orders.html",
        {
            "restaurant": restaurant,
            "page_obj": page_obj,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


# ... purane reports (Revenue, Orders) ...


@login_required
def super_security_report(request, pk):
    if request.user.role != "SUPERADMIN":
        return redirect("dashboard")
    restaurant = get_object_or_404(Restaurant, pk=pk)

    # 1. Key Users (Owner + Manager) - Ye list dikhegi
    key_users = User.objects.filter(
        restaurant=restaurant, role__in=["RESTAURANT_ADMIN", "MANAGER"]
    )
    if restaurant.owner not in key_users:
        from itertools import chain

        key_users = list(chain([restaurant.owner], key_users))

    # 2. Counts for Cards (Staff & Kitchen) - Sirf ginti chahiye
    waiter_count = User.objects.filter(restaurant=restaurant, role="WAITER").count()
    kitchen_count = User.objects.filter(restaurant=restaurant, role="KITCHEN").count()

    return render(
        request,
        "dashboard/reports/security.html",
        {
            "restaurant": restaurant,
            "users": key_users,
            "waiter_count": waiter_count,  # <--- New
            "kitchen_count": kitchen_count,  # <--- New
        },
    )


# 3. STAFF REPORT
@login_required
def super_staff_report(request, pk):
    if request.user.role != "SUPERADMIN":
        return redirect("dashboard")
    restaurant = get_object_or_404(Restaurant, pk=pk)

    # 1. Check URL Filter (role=WAITER ya role=KITCHEN)
    role_filter = request.GET.get("role")

    # 2. Filter Logic
    if role_filter:
        # Sirf wahi staff dikhao jo manga gaya hai
        staff = restaurant.staff_members.filter(role=role_filter).order_by(
            "-date_joined"
        )
        # Title dynamic banane ke liye
        page_title = f"{role_filter.capitalize()} Directory"
    else:
        # Agar koi filter nahi hai to SAB dikhao
        staff = restaurant.staff_members.all().order_by("role", "-date_joined")
        page_title = "Complete Staff Registry"

    return render(
        request,
        "dashboard/reports/staff.html",
        {
            "restaurant": restaurant,
            "staff": staff,
            "current_role": role_filter,  # Template ko batane ke liye ki kya filter hai
            "page_title": page_title,
        },
    )


# 4. MENU REPORT
@login_required
def super_menu_report(request, pk):
    if request.user.role != "SUPERADMIN":
        return redirect("dashboard")
    restaurant = get_object_or_404(Restaurant, pk=pk)

    # --- CHANGE: Fetch Items instead of Categories for Pagination ---
    items = (
        MenuItem.objects.filter(category__restaurant=restaurant)
        .select_related("category")
        .order_by("category__name", "name")
    )

    # Pagination (20 items per page)
    paginator = Paginator(items, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "dashboard/reports/menu.html",
        {"restaurant": restaurant, "page_obj": page_obj},
    )


# 5. TABLES REPORT (New)
@login_required
def super_tables_report(request, pk):
    if request.user.role != "SUPERADMIN":
        return redirect("dashboard")
    restaurant = get_object_or_404(Restaurant, pk=pk)
    tables = Table.objects.filter(restaurant=restaurant).order_by("table_number")
    return render(
        request,
        "dashboard/reports/tables.html",
        {"restaurant": restaurant, "tables": tables},
    )


# 1. LIST & CREATE GROUPS
@login_required
def manage_addons(request):
    restaurant = get_current_restaurant(request.user)
    groups = AddOnGroup.objects.filter(restaurant=restaurant).prefetch_related(
        "options"
    )

    if request.method == "POST":
        form = AddOnGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.restaurant = restaurant
            group.save()
            return redirect("manage_addons")
    else:
        form = AddOnGroupForm()

    return render(
        request, "dashboard/manage_addons.html", {"groups": groups, "form": form}
    )


# 2. ADD OPTION TO GROUP
@login_required
def add_addon_option(request, group_id):
    restaurant = get_current_restaurant(request.user)
    group = get_object_or_404(AddOnGroup, pk=group_id, restaurant=restaurant)

    if request.method == "POST":
        form = AddOnOptionForm(request.POST)
        if form.is_valid():
            option = form.save(commit=False)
            option.group = group
            option.save()
            return redirect("manage_addons")

    # Iske liye alag page nahi banayenge, wahi modal ya redirect use karenge
    return redirect("manage_addons")


# 3. DELETE GROUP
@login_required
def delete_addon_group(request, group_id):
    restaurant = get_current_restaurant(request.user)
    group = get_object_or_404(AddOnGroup, pk=group_id, restaurant=restaurant)
    group.delete()
    return redirect("manage_addons")


# ... (Previous imports)
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# ==========================================
# 11. PAYMENT GATEWAY (Razorpay)
# ==========================================


@login_required
def start_payment(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    restaurant = order.restaurant  # Get the restaurant associated with the order

    # Check if the restaurant has Razorpay keys set up
    if not restaurant.razorpay_key_id or not restaurant.razorpay_key_secret:
        return JsonResponse(
            {
                "status": "error",
                "message": "Online payment not setup for this restaurant.",
            }
        )

    # Initialize Razorpay Client using the RESTAURANT'S keys
    client = razorpay.Client(
        auth=(restaurant.razorpay_key_id, restaurant.razorpay_key_secret)
    )

    amount_in_paise = int(order.total_amount * 100)

    try:
        razorpay_order = client.order.create(
            {"amount": amount_in_paise, "currency": "INR", "payment_capture": "1"}
        )

        return JsonResponse(
            {
                "razorpay_order_id": razorpay_order["id"],
                "amount": amount_in_paise,
                "key_id": restaurant.razorpay_key_id,  # Send restaurant's key to frontend
                "order_id": order.order_id,
                "email": getattr(request.user, "email", "guest@pos.com")
                or "guest@pos.com",
                "contact": "9999999999",
            }
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


# restaurants/views.py


@csrf_exempt
def verify_payment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            order = Order.objects.get(order_id=data["custom_order_id"])
            restaurant = order.restaurant

            # 1. Setup Client with Restaurant Keys
            client = razorpay.Client(
                auth=(restaurant.razorpay_key_id, restaurant.razorpay_key_secret)
            )

            # 2. Verify Signature
            params_dict = {
                "razorpay_order_id": data["razorpay_order_id"],
                "razorpay_payment_id": data["razorpay_payment_id"],
                "razorpay_signature": data["razorpay_signature"],
            }
            client.utility.verify_payment_signature(params_dict)

            # --- 3. FETCH EXACT DETAILS FROM RAZORPAY (NEW LOGIC) ---
            # Payment ID se puri detail nikalo (UPI ID, Ref No, Method etc.)
            payment_details = client.payment.fetch(data["razorpay_payment_id"])

            # Data Extraction
            # A. Method (UPI, Card, Netbanking)
            pay_method = payment_details.get("method", "ONLINE").upper()
            if pay_method == "UPI":
                # UPI ID (e.g., user@oksbi)
                payer_vpa = payment_details.get("vpa", "UPI User")
                order.payer_name = payer_vpa
            else:
                # Card/Netbanking info
                card_network = payment_details.get("card", {}).get("network", "Bank")
                order.payer_name = f"{pay_method} - {card_network}"

            # B. Transaction Reference (Bank RRN / UPI Ref)
            # 'acquirer_data' me asli bank ref hota hai
            bank_ref_no = payment_details.get("acquirer_data", {}).get(
                "rrn"
            ) or payment_details.get("acquirer_data", {}).get("upi_transaction_id")

            # Agar Bank Ref mil gaya to wo lo, nahi to Razorpay ID hi rakho
            final_txn_id = bank_ref_no if bank_ref_no else data["razorpay_payment_id"]

            # 4. Save to Database
            order.payment_status = True
            order.status = "COMPLETED"
            order.payment_method = pay_method  # UPI / CARD
            order.transaction_id = final_txn_id  # Yahan ab asli Ref No aayega
            order.save()

            return JsonResponse({"status": "success"})

        except Exception as e:
            print(f"Verify Error: {e}")
            return JsonResponse({"status": "failed", "message": str(e)})

    return JsonResponse({"status": "failed"})


# 3. CASH PAYMENT (Purana wala, thoda update kiya hai)
# restaurants/views.py


@login_required
def complete_payment(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, order_id=order_id)

        # 1. Get Data from Form
        payment_method = request.POST.get("payment_method")  # CASH or QR_SCAN
        payer_name = request.POST.get("payer_name")  # Name entered in input
        txn_id = request.POST.get("txn_id")  # Ref No entered in input

        # 2. Set Details
        order.payment_status = True
        order.status = "COMPLETED"
        order.payment_method = payment_method

        # 3. Handle Transaction ID & Name Logic
        if payment_method == "CASH":
            order.transaction_id = f"CASH-{order.pk}"  # Auto-generate for Cash
            order.payer_name = "Walk-in Customer"  # Cash me naam nahi hota
        else:
            # QR Scan / Manual Online
            order.transaction_id = txn_id if txn_id else f"TXN-{order.pk}"
            order.payer_name = payer_name if payer_name else "Unknown Customer"

        # 4. Save
        order.save()

        # Redirect to Success Page (Receipt)
        return redirect("order_success", order_id=order.order_id)

    return redirect("waiter_dashboard")
