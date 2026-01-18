from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Count, Q
import json
import openpyxl

from .models import Region, District, Mahalla, User, Notification, Announcement


# ============================================================
# LOCATION ADMINS
# ============================================================

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'districts_count_display', 'leaders_count_display', 'is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['order', 'name']
    list_editable = ['order', 'is_active']

    def districts_count_display(self, obj):
        count = obj.districts.filter(is_active=True).count()
        return format_html('<span class="badge bg-info">{}</span>', count)

    districts_count_display.short_description = _("Tumanlar")

    def leaders_count_display(self, obj):
        count = User.objects.filter(
            district__region=obj,
            role=User.Role.LEADER,
            status=User.Status.ACTIVE
        ).count()
        return format_html('<span class="badge bg-success">{}</span>', count)

    leaders_count_display.short_description = _("Yetakchilar")


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'code', 'mahallas_count_display', 'leaders_count_display', 'is_active', 'order']
    list_filter = ['region', 'is_active']
    search_fields = ['name', 'code', 'region__name']
    ordering = ['region', 'order', 'name']
    list_editable = ['order', 'is_active']
    autocomplete_fields = ['region']

    def mahallas_count_display(self, obj):
        count = obj.mahallas.filter(is_active=True).count()
        return format_html('<span class="badge bg-info">{}</span>', count)

    mahallas_count_display.short_description = _("Mahallalar")

    def leaders_count_display(self, obj):
        count = User.objects.filter(
            mahalla__district=obj,
            role=User.Role.LEADER,
            status=User.Status.ACTIVE
        ).count()
        return format_html('<span class="badge bg-success">{}</span>', count)

    leaders_count_display.short_description = _("Yetakchilar")


@admin.register(Mahalla)
class MahallaAdmin(admin.ModelAdmin):
    list_display = ['name', 'district', 'region_display', 'code', 'population', 'households', 'leader_display',
                    'is_active']
    list_filter = ['district__region', 'district', 'is_active']
    search_fields = ['name', 'code', 'district__name', 'district__region__name']
    ordering = ['district__region', 'district', 'name']
    list_editable = ['is_active']
    autocomplete_fields = ['district']

    fieldsets = (
        (None, {
            'fields': ('district', 'name', 'code')
        }),
        (_('Statistika'), {
            'fields': ('population', 'households')
        }),
        (_('Qo\'shimcha'), {
            'fields': ('address', 'is_active')
        }),
    )

    def region_display(self, obj):
        return obj.district.region.name

    region_display.short_description = _("Viloyat")

    def leader_display(self, obj):
        leader = obj.users.filter(role=User.Role.LEADER, status=User.Status.ACTIVE).first()
        if leader:
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                leader.get_full_name() or leader.username
            )
        return format_html('<span style="color: red;">✗ Yo\'q</span>')

    leader_display.short_description = _("Yetakchi")


# ============================================================
# USER ADMIN
# ============================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'username',
        'full_name_display',
        'role_badge',
        'status_badge',
        'phone',
        'location_display',
        'last_activity_display',
        'login_count',
        'created_at'
    ]
    list_filter = ['role', 'status', 'region', 'district', 'created_at', 'last_login']
    search_fields = ['username', 'first_name', 'last_name', 'middle_name', 'phone', 'email']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    readonly_fields = [
        'created_at', 'updated_at', 'last_login', 'last_activity',
        'last_login_ip', 'login_count', 'plain_password'
    ]

    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        (_('Shaxsiy ma\'lumotlar'), {
            'fields': ('last_name', 'first_name', 'middle_name', 'birth_date', 'avatar')
        }),
        (_('Kontakt'), {
            'fields': ('phone', 'email')
        }),
        (_('Manzil'), {
            'fields': ('region', 'district', 'mahalla')
        }),
        (_('Lavozim'), {
            'fields': ('position', 'bio')
        }),
        (_('Rol va holat'), {
            'fields': ('role', 'status')
        }),
        (_('Bildirishnomalar'), {
            'fields': ('notify_email', 'notify_sms', 'notify_web'),
            'classes': ('collapse',)
        }),
        (_('Parol'), {
            'fields': ('plain_password', 'must_change_password'),
            'classes': ('collapse',)
        }),
        (_('Ruxsatlar'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        (_('Tizim ma\'lumotlari'), {
            'fields': ('last_login', 'last_activity', 'last_login_ip', 'login_count', 'created_at', 'updated_at',
                       'created_by'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        (_('Shaxsiy ma\'lumotlar'), {
            'classes': ('wide',),
            'fields': ('last_name', 'first_name', 'middle_name', 'phone'),
        }),
        (_('Manzil'), {
            'classes': ('wide',),
            'fields': ('region', 'district', 'mahalla'),
        }),
        (_('Rol'), {
            'classes': ('wide',),
            'fields': ('role', 'status'),
        }),
    )

    autocomplete_fields = ['region', 'district', 'mahalla', 'created_by']
    filter_horizontal = ['groups', 'user_permissions']

    actions = [
        'activate_users',
        'deactivate_users',
        'block_users',
        'reset_passwords',
        'export_users_excel',
        'export_users_json'
    ]

    def full_name_display(self, obj):
        full_name = obj.get_full_name()
        if full_name:
            return full_name
        return format_html('<span style="color: gray;">{}</span>', obj.username)

    full_name_display.short_description = _("F.I.Sh")

    def role_badge(self, obj):
        colors = {
            'super_admin': '#dc3545',
            'region_admin': '#6f42c1',
            'district_admin': '#0d6efd',
            'leader': '#198754'
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:12px; font-size:11px; font-weight:500;">{}</span>',
            color, obj.get_role_display()
        )

    role_badge.short_description = _("Rol")

    def status_badge(self, obj):
        colors = {
            'active': '#198754',
            'inactive': '#ffc107',
            'blocked': '#dc3545',
            'pending': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:12px; font-size:11px; font-weight:500;">{}</span>',
            color, obj.get_status_display()
        )

    status_badge.short_description = _("Holat")

    def location_display(self, obj):
        parts = []
        if obj.region:
            parts.append(obj.region.name)
        if obj.district:
            parts.append(obj.district.name)
        if obj.mahalla:
            parts.append(obj.mahalla.name)

        if parts:
            return format_html(
                '<small>{}</small>',
                ' → '.join(parts)
            )
        return format_html('<span style="color: gray;">—</span>')

    location_display.short_description = _("Manzil")

    def last_activity_display(self, obj):
        if obj.last_activity:
            delta = timezone.now() - obj.last_activity
            if delta.days == 0:
                if delta.seconds < 3600:
                    minutes = delta.seconds // 60
                    return format_html(
                        '<span style="color: green;">{} daqiqa oldin</span>',
                        minutes
                    )
                else:
                    hours = delta.seconds // 3600
                    return format_html(
                        '<span style="color: green;">{} soat oldin</span>',
                        hours
                    )
            elif delta.days < 7:
                return format_html(
                    '<span style="color: orange;">{} kun oldin</span>',
                    delta.days
                )
            else:
                return format_html(
                    '<span style="color: gray;">{}</span>',
                    obj.last_activity.strftime('%d.%m.%Y')
                )
        return format_html('<span style="color: gray;">—</span>')

    last_activity_display.short_description = _("Faollik")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user

            # Yangi user uchun parol generatsiya
            if not obj.password or obj.password == '':
                password = User.generate_password()
                obj.set_password(password)
                obj.plain_password = password

        super().save_model(request, obj, form, change)

    @admin.action(description=_("Tanlangan foydalanuvchilarni faollashtirish"))
    def activate_users(self, request, queryset):
        count = queryset.update(status=User.Status.ACTIVE)
        self.message_user(request, f"{count} ta foydalanuvchi faollashtirildi.")

    @admin.action(description=_("Tanlangan foydalanuvchilarni nofaollashtirish"))
    def deactivate_users(self, request, queryset):
        count = queryset.update(status=User.Status.INACTIVE)
        self.message_user(request, f"{count} ta foydalanuvchi nofaollashtirildi.")

    @admin.action(description=_("Tanlangan foydalanuvchilarni bloklash"))
    def block_users(self, request, queryset):
        count = queryset.exclude(role=User.Role.SUPER_ADMIN).update(status=User.Status.BLOCKED)
        self.message_user(request, f"{count} ta foydalanuvchi bloklandi.")

    @admin.action(description=_("Parolni qayta tiklash"))
    def reset_passwords(self, request, queryset):
        count = 0
        for user in queryset:
            password = User.generate_password()
            user.set_password(password)
            user.plain_password = password
            user.must_change_password = True
            user.save()
            count += 1
        self.message_user(request, f"{count} ta foydalanuvchi paroli yangilandi.")

    @admin.action(description=_("Excel ga eksport"))
    def export_users_excel(self, request, queryset):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Foydalanuvchilar"

        headers = [
            '№', 'Username', 'Familiya', 'Ism', 'Otasining ismi',
            'Telefon', 'Email', 'Rol', 'Holat',
            'Viloyat', 'Tuman', 'Mahalla', 'Parol', 'Yaratilgan'
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = openpyxl.styles.Font(bold=True)

        for row, user in enumerate(queryset, 2):
            ws.cell(row=row, column=1, value=row - 1)
            ws.cell(row=row, column=2, value=user.username)
            ws.cell(row=row, column=3, value=user.last_name)
            ws.cell(row=row, column=4, value=user.first_name)
            ws.cell(row=row, column=5, value=user.middle_name)
            ws.cell(row=row, column=6, value=user.phone)
            ws.cell(row=row, column=7, value=user.email)
            ws.cell(row=row, column=8, value=user.get_role_display())
            ws.cell(row=row, column=9, value=user.get_status_display())
            ws.cell(row=row, column=10, value=str(user.region) if user.region else '')
            ws.cell(row=row, column=11, value=str(user.district) if user.district else '')
            ws.cell(row=row, column=12, value=str(user.mahalla) if user.mahalla else '')
            ws.cell(row=row, column=13, value=user.plain_password)
            ws.cell(row=row, column=14, value=user.created_at.strftime('%d.%m.%Y %H:%M'))

        for col in ws.columns:
            max_length = max(len(str(cell.value or '')) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="foydalanuvchilar.xlsx"'
        wb.save(response)
        return response

    @admin.action(description=_("JSON ga eksport"))
    def export_users_json(self, request, queryset):
        data = []
        for user in queryset:
            data.append({
                'id': str(user.pk),
                'username': user.username,
                'full_name': user.get_full_name(),
                'phone': user.phone,
                'email': user.email,
                'role': user.role,
                'status': user.status,
                'region': str(user.region) if user.region else None,
                'district': str(user.district) if user.district else None,
                'mahalla': str(user.mahalla) if user.mahalla else None,
                'password': user.plain_password,
                'created_at': user.created_at.isoformat()
            })

        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="foydalanuvchilar.json"'
        return response


# ============================================================
# NOTIFICATION ADMIN
# ============================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type_badge', 'priority_badge', 'title', 'is_read_badge', 'created_at']
    list_filter = ['type', 'priority', 'is_read', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'title', 'message']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    readonly_fields = ['created_at', 'read_at']

    fieldsets = (
        (None, {
            'fields': ('user', 'type', 'priority')
        }),
        (_('Xabar'), {
            'fields': ('title', 'message', 'link')
        }),
        (_('Holat'), {
            'fields': ('is_read', 'read_at')
        }),
        (_('Qo\'shimcha'), {
            'fields': ('metadata', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    autocomplete_fields = ['user']

    actions = ['mark_as_read', 'mark_as_unread', 'delete_old_notifications']

    def type_badge(self, obj):
        colors = {
            'task_new': '#0d6efd',
            'task_deadline': '#ffc107',
            'task_overdue': '#dc3545',
            'task_approved': '#198754',
            'task_rejected': '#dc3545',
            'announcement': '#6f42c1',
            'system': '#6c757d',
            'warning': '#fd7e14'
        }
        color = colors.get(obj.type, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; '
            'border-radius:10px; font-size:10px;">{}</span>',
            color, obj.get_type_display()
        )

    type_badge.short_description = _("Turi")

    def priority_badge(self, obj):
        colors = {
            'low': '#198754',
            'normal': '#0d6efd',
            'high': '#ffc107',
            'urgent': '#dc3545'
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="color:{}; font-weight:bold;">●</span>',
            color
        )

    priority_badge.short_description = _("!")

    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ O\'qilgan</span>')
        return format_html('<span style="color: orange;">○ Yangi</span>')

    is_read_badge.short_description = _("Holat")

    @admin.action(description=_("O'qilgan deb belgilash"))
    def mark_as_read(self, request, queryset):
        count = queryset.filter(is_read=False).update(is_read=True, read_at=timezone.now())
        self.message_user(request, f"{count} ta bildirishnoma o'qilgan deb belgilandi.")

    @admin.action(description=_("O'qilmagan deb belgilash"))
    def mark_as_unread(self, request, queryset):
        count = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f"{count} ta bildirishnoma o'qilmagan deb belgilandi.")

    @admin.action(description=_("30 kundan eski bildirishnomalarni o'chirish"))
    def delete_old_notifications(self, request, queryset):
        from datetime import timedelta
        old_date = timezone.now() - timedelta(days=30)
        count = Notification.objects.filter(created_at__lt=old_date, is_read=True).delete()[0]
        self.message_user(request, f"{count} ta eski bildirishnoma o'chirildi.")


# ============================================================
# ANNOUNCEMENT ADMIN
# ============================================================

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority_badge', 'status_badge', 'target_display', 'views_count', 'is_active_display',
                    'created_by', 'created_at']
    list_filter = ['priority', 'status', 'target_all', 'target_region', 'created_at']
    search_fields = ['title', 'content']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    readonly_fields = ['views_count', 'created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('title', 'content', 'priority', 'status')
        }),
        (_('Kimga'), {
            'fields': ('target_all', 'target_region', 'target_district', 'target_roles')
        }),
        (_('Vaqt'), {
            'fields': ('publish_at', 'expires_at')
        }),
        (_('Fayl'), {
            'fields': ('attachment',),
            'classes': ('collapse',)
        }),
        (_('Statistika'), {
            'fields': ('views_count', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    autocomplete_fields = ['target_region', 'target_district', 'created_by']

    actions = ['publish_announcements', 'archive_announcements']

    def priority_badge(self, obj):
        colors = {
            'low': '#198754',
            'normal': '#0d6efd',
            'high': '#ffc107',
            'urgent': '#dc3545'
        }
        icons = {
            'low': '○',
            'normal': '●',
            'high': '◉',
            'urgent': '⚠'
        }
        color = colors.get(obj.priority, '#6c757d')
        icon = icons.get(obj.priority, '●')
        return format_html(
            '<span style="color:{}; font-size:16px;">{}</span>',
            color, icon
        )

    priority_badge.short_description = _("!")

    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'active': '#198754',
            'archived': '#495057'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; '
            'border-radius:10px; font-size:10px;">{}</span>',
            color, obj.get_status_display()
        )

    status_badge.short_description = _("Holat")

    def target_display(self, obj):
        if obj.target_all:
            return format_html('<span style="color: green;">🌍 Hammaga</span>')

        parts = []
        if obj.target_region:
            parts.append(f"📍 {obj.target_region.name}")
        if obj.target_district:
            parts.append(f"🏢 {obj.target_district.name}")
        if obj.target_roles:
            roles = ', '.join(obj.target_roles)
            parts.append(f"👥 {roles}")

        return format_html('<small>{}</small>', ' | '.join(parts) if parts else '—')

    target_display.short_description = _("Kimga")

    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Faol</span>')
        if obj.status == Announcement.Status.DRAFT:
            return format_html('<span style="color: gray;">○ Qoralama</span>')
        if obj.is_expired:
            return format_html('<span style="color: red;">✗ Muddati o\'tgan</span>')
        return format_html('<span style="color: orange;">⏳ Kutilmoqda</span>')

    is_active_display.short_description = _("Faol")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description=_("E'lon qilish"))
    def publish_announcements(self, request, queryset):
        count = 0
        for announcement in queryset.filter(status=Announcement.Status.DRAFT):
            announcement.publish()
            count += 1
        self.message_user(request, f"{count} ta e'lon chop etildi.")

    @admin.action(description=_("Arxivlash"))
    def archive_announcements(self, request, queryset):
        count = queryset.update(status=Announcement.Status.ARCHIVED)
        self.message_user(request, f"{count} ta e'lon arxivlandi.")