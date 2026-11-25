from django.contrib import admin
from .models import (
    Category, Inventory, Unit, Client, Rental,
    ReturnRecord, Deposit, ConditionRecord, Fine, Favorite
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_fine_rate')
    search_fields = ('name',)

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'daily_price', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'manufacturer')

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('inventory_number', 'inventory', 'size', 'status')
    list_filter = ('status', 'inventory__category')
    search_fields = ('inventory_number',)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'created_at')
    search_fields = ('user__username', 'phone')

class DepositInline(admin.StackedInline):
    model = Deposit
    extra = 0

class ReturnInline(admin.StackedInline):
    model = ReturnRecord
    extra = 0

@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'unit', 'start_date', 'planned_end_date', 'status', 'total_price')
    list_filter = ('status',)
    inlines = [DepositInline, ReturnInline]

@admin.register(ReturnRecord)
class ReturnRecordAdmin(admin.ModelAdmin):
    list_display = ('rental', 'return_date', 'condition_ok')

@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ('return_record', 'damage_category', 'amount', 'is_paid')

@admin.register(ConditionRecord)
class ConditionRecordAdmin(admin.ModelAdmin):
    list_display = ('unit', 'condition', 'check_date')

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('client', 'inventory', 'added_at')
