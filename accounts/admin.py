from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import User, Region, District, Mahalla


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'username',
        'full_name_display',
        'role_badge',
        'status_badge',
        'mahalla',
        'phone',
        'telegram_id',
        'created_at'
    ]
    list_filter = ['role', 'status', 'region', 'district', 'created_at']
    search_fields = ['username', 'first_name', 'last_name', 'phone', 'telegram_id']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Shaxsiy ma\'lumotlar'), {
            'fields': ('first_name', 'last_name', 'phone', 'bio', 'avatar')
        }),
        (_('Telegram'), {
            'fields': ('telegram_id', 'telegram_username')
        }),
        (_('Manzil'), {
            'fields': ('region', 'district', 'mahalla')
        }),
        (_('Rol va holat'), {
            'fields': ('role', 'status')
        }),
        (_('Ruxsatlar'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        (_('Vaqtlar'), {
            'fields': ('last_login', 'last_activity', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'last_login', 'last_activity']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'password1', 'password2',
                'first_name', 'last_name', 'phone',
                'role', 'status', 'region', 'district', 'mahalla'
            ),
        }),
    )

    def full_name_display(self, obj):
        return obj.get_full_name() or "-"

    full_name_display.short_description = _("F.I.Sh")

    def role_badge(self, obj):
        colors = {
            'super_admin': '#e74c3c',
            'district_admin': '#3498db',
            'leader': '#27ae60'
        }
        color = colors.get(obj.role, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:3px; font-size:11px;">{}</span>',
            color, obj.get_role_display()
        )

    role_badge.short_description = _("Rol")

    def status_badge(self, obj):
        colors = {
            'active': '#27ae60',
            'inactive': '#f39c12',
            'blocked': '#e74c3c'
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:3px; font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )

    status_badge.short_description = _("Holat")


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'districts_count', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['name']

    def districts_count(self, obj):
        count = obj.districts.count()
        return format_html(
            '<span style="font-weight:bold;">{}</span> ta',
            count
        )

    districts_count.short_description = _("Tumanlar")


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'code', 'mahallas_count', 'is_active', 'created_at']
    list_filter = ['region', 'is_active']
    search_fields = ['name', 'code', 'region__name']
    ordering = ['region', 'name']
    autocomplete_fields = ['region']

    def mahallas_count(self, obj):
        count = obj.mahallas.count()
        return format_html(
            '<span style="font-weight:bold;">{}</span> ta',
            count
        )

    mahallas_count.short_description = _("Mahallalar")


@admin.register(Mahalla)
class MahallaAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'district',
        'region_display',
        'code',
        'population',
        'youth_count',
        'leaders_count',
        'is_active'
    ]
    list_filter = ['district__region', 'district', 'is_active']
    search_fields = ['name', 'code', 'district__name']
    ordering = ['district', 'name']
    autocomplete_fields = ['district']

    def region_display(self, obj):
        return obj.district.region.name

    region_display.short_description = _("Viloyat")

    def leaders_count(self, obj):
        count = obj.users.filter(role='leader').count()
        if count == 0:
            return format_html('<span style="color:#e74c3c;">0</span>')
        return format_html('<span style="color:#27ae60; font-weight:bold;">{}</span>', count)

    leaders_count.short_description = _("Yetakchilar")