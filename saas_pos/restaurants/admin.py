from django.contrib import admin
from .models import Restaurant, Category, MenuItem, Table, Order, OrderItem, AddOnOption, AddOnGroup

# 1. Restaurant
@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'slug', 'is_active')

# 2. Table
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('table_number', 'restaurant', 'unique_id')
    list_filter = ('restaurant',)

# 3. Add-ons Configuration
class AddOnOptionInline(admin.TabularInline):
    model = AddOnOption
    extra = 1

@admin.register(AddOnGroup)
class AddOnGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'is_required', 'is_multiple')
    list_filter = ('restaurant',)
    inlines = [AddOnOptionInline]

# 4. Menu Item (Corrected)
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_available')
    list_filter = ('category__restaurant', 'is_available')
    filter_horizontal = ('addon_groups',) # Checkbox select box dikhayega

# 5. Order & Order Items (Better View)
# Isse Order kholne par uske andar ke items dikhenge
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('food_item', 'quantity', 'price', 'customizations', 'created_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'restaurant', 'table', 'total_amount', 'status', 'payment_status', 'created_at')
    list_filter = ('restaurant', 'status', 'payment_status', 'created_at')
    search_fields = ('order_id', 'transaction_id')
    inlines = [OrderItemInline]

# 6. Baaki Models
admin.site.register(Category)