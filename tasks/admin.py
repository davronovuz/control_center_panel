from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Task, Question, TaskAssignment, Answer, TaskHistory


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['order', 'text', 'question_type', 'is_required', 'choices']
    ordering = ['order']


class TaskAssignmentInline(admin.TabularInline):
    model = TaskAssignment
    extra = 0
    fields = ['leader', 'status', 'progress_display', 'sent_at', 'completed_at']
    readonly_fields = ['progress_display', 'sent_at', 'completed_at']
    ordering = ['-sent_at']

    def progress_display(self, obj):
        percent = obj.progress_percent
        if percent == 100:
            color = '#27ae60'
        elif percent > 50:
            color = '#f39c12'
        else:
            color = '#e74c3c'

        return format_html(
            '<div style="width:100px; background:#ecf0f1; border-radius:3px;">'
            '<div style="width:{}%; background:{}; height:20px; border-radius:3px; '
            'text-align:center; color:white; font-size:11px; line-height:20px;">'
            '{}%</div></div>',
            percent, color, percent
        )

    progress_display.short_description = _("Jarayon")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'task_type_badge',
        'status_badge',
        'priority_badge',
        'target_display',
        'deadline_display',
        'stats_display',
        'created_by',
        'created_at'
    ]
    list_filter = [
        'status',
        'priority',
        'task_type',
        'target_region',
        'target_district',
        'created_at'
    ]
    search_fields = ['title', 'description', 'created_by__username']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    readonly_fields = [
        'stats_total_assigned',
        'stats_total_seen',
        'stats_total_started',
        'stats_total_completed',
        'stats_completion_rate',
        'published_at',
        'completed_at',
        'created_at',
        'updated_at'
    ]

    fieldsets = (
        (_('Asosiy'), {
            'fields': ('title', 'description', 'task_type', 'status', 'priority')
        }),
        (_('Manzil (kimga)'), {
            'fields': ('target_region', 'target_district', 'target_mahallas')
        }),
        (_('Muddat'), {
            'fields': ('deadline', 'start_date', 'reminder_enabled', 'reminder_hours')
        }),
        (_('Fayllar'), {
            'fields': ('source_file', 'result_file'),
            'classes': ('collapse',)
        }),
        (_('Statistika'), {
            'fields': (
                'stats_total_assigned',
                'stats_total_seen',
                'stats_total_started',
                'stats_total_completed',
                'stats_completion_rate'
            ),
            'classes': ('collapse',)
        }),
        (_('Qo\'shimcha'), {
            'fields': ('notes', 'meta'),
            'classes': ('collapse',)
        }),
        (_('Tizim'), {
            'fields': ('created_by', 'published_at', 'completed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ['target_mahallas']
    autocomplete_fields = ['target_region', 'target_district', 'created_by']
    inlines = [QuestionInline, TaskAssignmentInline]

    actions = ['publish_tasks', 'complete_tasks', 'update_stats']

    def task_type_badge(self, obj):
        icons = {
            'survey': '📋',
            'excel': '📊',
            'report': '📝',
            'mixed': '🔀'
        }
        icon = icons.get(obj.task_type, '📄')
        return format_html('{} {}', icon, obj.get_task_type_display())

    task_type_badge.short_description = _("Turi")

    def status_badge(self, obj):
        colors = {
            'draft': '#95a5a6',
            'active': '#27ae60',
            'paused': '#f39c12',
            'completed': '#3498db',
            'cancelled': '#e74c3c',
            'archived': '#7f8c8d'
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:3px; font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )

    status_badge.short_description = _("Holat")

    def priority_badge(self, obj):
        colors = {
            'low': '#27ae60',
            'medium': '#f39c12',
            'high': '#e67e22',
            'urgent': '#e74c3c'
        }
        color = colors.get(obj.priority, '#95a5a6')
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color, obj.get_priority_display()
        )

    priority_badge.short_description = _("Muhimlik")

    def target_display(self, obj):
        if obj.target_mahallas.exists():
            count = obj.target_mahallas.count()
            return format_html('<span title="Mahallalar">{} ta mahalla</span>', count)
        elif obj.target_district:
            return obj.target_district.name
        elif obj.target_region:
            return obj.target_region.name
        return _("Hammaga")

    target_display.short_description = _("Kimga")

    def deadline_display(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span style="color:#e74c3c; font-weight:bold;">'
                '⚠️ {} (o\'tgan)</span>',
                obj.deadline.strftime('%d.%m.%Y %H:%M')
            )

        remaining = obj.time_remaining
        if remaining:
            return format_html(
                '{}<br><small style="color:#7f8c8d;">{} qoldi</small>',
                obj.deadline.strftime('%d.%m.%Y %H:%M'),
                remaining
            )
        return obj.deadline.strftime('%d.%m.%Y %H:%M')

    deadline_display.short_description = _("Muddat")

    def stats_display(self, obj):
        total = obj.stats_total_assigned
        completed = obj.stats_total_completed
        rate = obj.stats_completion_rate

        if total == 0:
            return format_html('<span style="color:#95a5a6;">—</span>')

        if rate >= 80:
            color = '#27ae60'
        elif rate >= 50:
            color = '#f39c12'
        else:
            color = '#e74c3c'

        return format_html(
            '<span style="color:{}; font-weight:bold;">{}/{}</span> '
            '<small>({}%)</small>',
            color, completed, total, int(rate)
        )

    stats_display.short_description = _("Bajarilish")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description=_("Tanlangan vazifalarni e'lon qilish"))
    def publish_tasks(self, request, queryset):
        count = 0
        for task in queryset.filter(status=Task.Status.DRAFT):
            if task.publish():
                count += 1
        self.message_user(request, f"{count} ta vazifa e'lon qilindi.")

    @admin.action(description=_("Tanlangan vazifalarni yakunlash"))
    def complete_tasks(self, request, queryset):
        count = queryset.filter(status=Task.Status.ACTIVE).update(
            status=Task.Status.COMPLETED,
            completed_at=timezone.now()
        )
        self.message_user(request, f"{count} ta vazifa yakunlandi.")

    @admin.action(description=_("Statistikani yangilash"))
    def update_stats(self, request, queryset):
        for task in queryset:
            task.update_stats()
        self.message_user(request, f"{queryset.count()} ta vazifa statistikasi yangilandi.")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        'order',
        'text_short',
        'task',
        'question_type_badge',
        'is_required_badge',
        'answers_count'
    ]
    list_filter = ['question_type', 'is_required', 'task']
    search_fields = ['text', 'task__title']
    ordering = ['task', 'order']
    autocomplete_fields = ['task']

    def text_short(self, obj):
        if len(obj.text) > 50:
            return obj.text[:50] + "..."
        return obj.text

    text_short.short_description = _("Savol")

    def question_type_badge(self, obj):
        icons = {
            'text': '📝',
            'number': '🔢',
            'choice': '☑️',
            'multiple': '✅',
            'yes_no': '❓',
            'date': '📅',
            'phone': '📞',
            'email': '📧'
        }
        icon = icons.get(obj.question_type, '📄')
        return format_html('{} {}', icon, obj.get_question_type_display())

    question_type_badge.short_description = _("Turi")

    def is_required_badge(self, obj):
        if obj.is_required:
            return format_html('<span style="color:#27ae60;">✓ Ha</span>')
        return format_html('<span style="color:#95a5a6;">✗ Yo\'q</span>')

    is_required_badge.short_description = _("Majburiy")

    def answers_count(self, obj):
        count = obj.answers.count()
        return format_html('<span style="font-weight:bold;">{}</span>', count)

    answers_count.short_description = _("Javoblar")


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'task',
        'leader',
        'leader_mahalla',
        'status_badge',
        'progress_bar',
        'sent_at',
        'completed_at'
    ]
    list_filter = ['status', 'task', 'task__target_region', 'sent_at']
    search_fields = ['task__title', 'leader__username', 'leader__first_name']
    ordering = ['-sent_at']
    autocomplete_fields = ['task', 'leader']

    readonly_fields = [
        'sent_at',
        'seen_at',
        'started_at',
        'completed_at',
        'reminder_sent_count',
        'last_reminder_at'
    ]

    def leader_mahalla(self, obj):
        if obj.leader.mahalla:
            return obj.leader.mahalla.name
        return "-"

    leader_mahalla.short_description = _("Mahalla")

    def status_badge(self, obj):
        colors = {
            'pending': '#95a5a6',
            'seen': '#3498db',
            'in_progress': '#f39c12',
            'completed': '#27ae60',
            'overdue': '#e74c3c'
        }

        status = obj.status
        if obj.is_overdue and status != 'completed':
            status = 'overdue'

        color = colors.get(status, '#95a5a6')
        label = obj.get_status_display()

        if obj.is_overdue and obj.status != 'completed':
            label = _("Muddati o'tdi")

        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:3px; font-size:11px;">{}</span>',
            color, label
        )

    status_badge.short_description = _("Holat")

    def progress_bar(self, obj):
        percent = obj.progress_percent
        answered = obj.answered_count
        total = obj.task.questions.count()

        if percent == 100:
            color = '#27ae60'
        elif percent > 50:
            color = '#f39c12'
        elif percent > 0:
            color = '#e67e22'
        else:
            color = '#e74c3c'

        return format_html(
            '<div style="width:120px; background:#ecf0f1; border-radius:3px;" '
            'title="{}/{} savol">'
            '<div style="width:{}%; background:{}; height:18px; border-radius:3px; '
            'text-align:center; color:white; font-size:10px; line-height:18px;">'
            '{}%</div></div>',
            answered, total, percent, color, percent
        )

    progress_bar.short_description = _("Jarayon")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = [
        'assignment',
        'question_order',
        'question_text_short',
        'value_display',
        'is_valid_badge',
        'created_at'
    ]
    list_filter = ['is_valid', 'question__question_type', 'created_at']
    search_fields = [
        'assignment__leader__username',
        'assignment__task__title',
        'question__text'
    ]
    ordering = ['-created_at']
    autocomplete_fields = ['assignment', 'question']

    readonly_fields = ['created_at', 'updated_at']

    def question_order(self, obj):
        return f"#{obj.question.order}"

    question_order.short_description = _("№")

    def question_text_short(self, obj):
        text = obj.question.text
        if len(text) > 40:
            return text[:40] + "..."
        return text

    question_text_short.short_description = _("Savol")

    def value_display(self, obj):
        val = obj.display_value
        if len(str(val)) > 50:
            return str(val)[:50] + "..."
        return val

    value_display.short_description = _("Javob")

    def is_valid_badge(self, obj):
        if obj.is_valid:
            return format_html('<span style="color:#27ae60;">✓</span>')
        return format_html(
            '<span style="color:#e74c3c;" title="{}">✗</span>',
            ", ".join(obj.validation_errors or [])
        )

    is_valid_badge.short_description = _("✓")


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'task',
        'action_badge',
        'actor',
        'description_short',
        'created_at'
    ]
    list_filter = ['action', 'created_at']
    search_fields = ['task__title', 'actor__username', 'description']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    readonly_fields = [
        'task',
        'assignment',
        'action',
        'actor',
        'description',
        'old_data',
        'new_data',
        'created_at'
    ]

    def action_badge(self, obj):
        colors = {
            'created': '#3498db',
            'published': '#27ae60',
            'assigned': '#9b59b6',
            'seen': '#1abc9c',
            'started': '#f39c12',
            'answered': '#2ecc71',
            'completed': '#27ae60',
            'reminder': '#e67e22',
            'edited': '#3498db',
            'cancelled': '#e74c3c'
        }
        color = colors.get(obj.action, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; '
            'border-radius:3px; font-size:10px;">{}</span>',
            color, obj.get_action_display()
        )

    action_badge.short_description = _("Harakat")

    def description_short(self, obj):
        if len(obj.description) > 50:
            return obj.description[:50] + "..."
        return obj.description or "-"

    description_short.short_description = _("Tavsif")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False