import uuid
from django.db import models
from django.conf import settings as django_settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TaskTemplate(models.Model):
    """Vazifa shabloni"""

    class Type(models.TextChoices):
        TABLE = 'table', _('Jadval')
        SURVEY = 'survey', _('So\'rovnoma')
        REPORT = 'report', _('Hisobot')
        FILE = 'file', _('Fayl yuklash')
        MIXED = 'mixed', _('Aralash')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Shablon nomi")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Tavsif")
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.TABLE,
        verbose_name=_("Turi")
    )
    structure = models.JSONField(
        default=dict,
        verbose_name=_("Struktura")
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Sozlamalar")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Faol")
    )
    is_system = models.BooleanField(
        default=False,
        verbose_name=_("Tizimga tegishli")
    )
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_templates',
        verbose_name=_("Yaratuvchi")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Shablon")
        verbose_name_plural = _("Shablonlar")
        ordering = ['name']

    def __str__(self):
        return self.name


class Task(models.Model):
    """Vazifa modeli"""

    class Type(models.TextChoices):
        TABLE = 'table', _('Jadval')
        SURVEY = 'survey', _('So\'rovnoma')
        REPORT = 'report', _('Hisobot')
        FILE = 'file', _('Fayl yuklash')
        MIXED = 'mixed', _('Aralash')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Qoralama')
        ACTIVE = 'active', _('Faol')
        PAUSED = 'paused', _('To\'xtatilgan')
        COMPLETED = 'completed', _('Yakunlangan')
        CANCELLED = 'cancelled', _('Bekor qilingan')
        ARCHIVED = 'archived', _('Arxivlangan')

    class Priority(models.TextChoices):
        LOW = 'low', _('Past')
        MEDIUM = 'medium', _('O\'rta')
        HIGH = 'high', _('Yuqori')
        URGENT = 'urgent', _('Shoshilinch')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Sarlavha")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Tavsif")
    )
    instructions = models.TextField(
        blank=True,
        verbose_name=_("Ko'rsatmalar")
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.TABLE,
        verbose_name=_("Turi"),
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Holat"),
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name=_("Muhimlik"),
        db_index=True
    )
    template = models.ForeignKey(
        TaskTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name=_("Shablon")
    )

    # Targeting
    target_all = models.BooleanField(
        default=False,
        verbose_name=_("Hammaga")
    )
    target_region = models.ForeignKey(
        'accounts.Region',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name=_("Viloyat")
    )
    target_district = models.ForeignKey(
        'accounts.District',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name=_("Tuman")
    )
    target_mahallas = models.ManyToManyField(
        'accounts.Mahalla',
        blank=True,
        related_name='tasks',
        verbose_name=_("Mahallalar")
    )

    # Schedule
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Boshlanish")
    )
    deadline = models.DateTimeField(
        verbose_name=_("Muddat")
    )

    # Table settings
    allow_multiple_rows = models.BooleanField(
        default=False,
        verbose_name=_("Ko'p qator")
    )
    min_rows = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Minimal qatorlar")
    )
    max_rows = models.PositiveIntegerField(
        default=100,
        verbose_name=_("Maksimal qatorlar")
    )

    # File settings
    allowed_extensions = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Ruxsat etilgan formatlar")
    )
    max_file_size = models.PositiveIntegerField(
        default=10,
        verbose_name=_("Maksimal hajm (MB)")
    )
    max_files = models.PositiveIntegerField(
        default=5,
        verbose_name=_("Maksimal fayllar soni")
    )

    # Workflow
    requires_approval = models.BooleanField(
        default=False,
        verbose_name=_("Tasdiqlash kerak")
    )
    allow_edit_after_submit = models.BooleanField(
        default=True,
        verbose_name=_("Yuborilgandan keyin tahrirlash")
    )
    auto_save = models.BooleanField(
        default=True,
        verbose_name=_("Avtomatik saqlash")
    )

    # Reminders
    reminder_enabled = models.BooleanField(
        default=True,
        verbose_name=_("Eslatma yuborish")
    )
    reminder_days = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Eslatma kunlari")
    )

    # Recurring
    is_recurring = models.BooleanField(
        default=False,
        verbose_name=_("Takrorlanuvchi")
    )
    recurring_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', _('Har kuni')),
            ('weekly', _('Har hafta')),
            ('monthly', _('Har oy')),
            ('quarterly', _('Har chorak')),
            ('yearly', _('Har yil')),
        ],
        blank=True,
        verbose_name=_("Takrorlanish turi")
    )
    recurring_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Takrorlanish tugashi")
    )
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_tasks',
        verbose_name=_("Asosiy vazifa")
    )

    # Statistics
    total_assigned = models.PositiveIntegerField(default=0, verbose_name=_("Tayinlangan"))
    total_started = models.PositiveIntegerField(default=0, verbose_name=_("Boshlangan"))
    total_submitted = models.PositiveIntegerField(default=0, verbose_name=_("Yuborilgan"))
    total_approved = models.PositiveIntegerField(default=0, verbose_name=_("Tasdiqlangan"))
    total_rejected = models.PositiveIntegerField(default=0, verbose_name=_("Rad etilgan"))

    # Meta
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
        verbose_name=_("Yaratuvchi")
    )
    published_at = models.DateTimeField(null=True, blank=True, verbose_name=_("E'lon qilingan"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Yakunlangan"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Yangilangan"))

    class Meta:
        verbose_name = _("Vazifa")
        verbose_name_plural = _("Vazifalar")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority', '-deadline']),
            models.Index(fields=['type', 'status']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_overdue(self):
        if self.status in [self.Status.COMPLETED, self.Status.CANCELLED, self.Status.ARCHIVED]:
            return False
        return timezone.now() > self.deadline

    @property
    def completion_rate(self):
        if self.total_assigned == 0:
            return 0
        if self.requires_approval:
            return round((self.total_approved / self.total_assigned) * 100, 1)
        return round((self.total_submitted / self.total_assigned) * 100, 1)

    @property
    def time_remaining(self):
        if self.status != self.Status.ACTIVE:
            return None

        delta = self.deadline - timezone.now()
        total_seconds = delta.total_seconds()

        if total_seconds < 0:
            return _("Muddat o'tgan")

        days = delta.days
        hours = delta.seconds // 3600

        if days > 0:
            return f"{days} kun {hours} soat"
        return f"{hours} soat"

    @property
    def status_color(self):
        colors = {
            'draft': 'secondary',
            'active': 'success',
            'paused': 'warning',
            'completed': 'info',
            'cancelled': 'danger',
            'archived': 'dark',
        }
        return colors.get(self.status, 'secondary')

    @property
    def priority_color(self):
        colors = {
            'low': 'success',
            'medium': 'info',
            'high': 'warning',
            'urgent': 'danger',
        }
        return colors.get(self.priority, 'secondary')

    def get_target_leaders(self):
        from accounts.models import User

        qs = User.objects.filter(
            role=User.Role.LEADER,
            status=User.Status.ACTIVE
        )

        if self.target_mahallas.exists():
            qs = qs.filter(mahalla__in=self.target_mahallas.all())
        elif self.target_district:
            qs = qs.filter(district=self.target_district)
        elif self.target_region:
            qs = qs.filter(region=self.target_region)
        elif not self.target_all:
            return qs.none()

        return qs.distinct()

    def publish(self, user=None):
        if self.status != self.Status.DRAFT:
            return False, _("Faqat qoralama vazifani e'lon qilish mumkin")

        if self.type == self.Type.TABLE and not self.columns.exists():
            return False, _("Jadval uchun kamida 1 ta ustun kerak")

        if self.type == self.Type.SURVEY and not self.questions.exists():
            return False, _("So'rovnoma uchun kamida 1 ta savol kerak")

        leaders = self.get_target_leaders()
        if not leaders.exists():
            return False, _("Hech qanday yetakchi tanlanmagan")

        from accounts.models import Notification

        assignments = []
        for leader in leaders:
            assignments.append(TaskAssignment(task=self, leader=leader))

        TaskAssignment.objects.bulk_create(assignments, ignore_conflicts=True)

        self.status = self.Status.ACTIVE
        self.published_at = timezone.now()
        self.total_assigned = leaders.count()
        self.save()

        Notification.send_bulk(
            users=leaders,
            type=Notification.Type.TASK_NEW,
            title=_("Yangi vazifa"),
            message=f"Sizga '{self.title}' vazifasi berildi.",
            link=f'/leader/tasks/{self.pk}/',
            priority='high' if self.priority in ['high', 'urgent'] else 'normal',
            metadata={'task_id': str(self.pk)}
        )

        return True, _("Vazifa muvaffaqiyatli e'lon qilindi")

    def update_stats(self):
        assignments = self.assignments.all()

        self.total_assigned = assignments.count()
        self.total_started = assignments.exclude(started_at=None).count()
        self.total_submitted = assignments.filter(
            status__in=[
                TaskAssignment.Status.SUBMITTED,
                TaskAssignment.Status.APPROVED,
                TaskAssignment.Status.REJECTED
            ]
        ).count()
        self.total_approved = assignments.filter(status=TaskAssignment.Status.APPROVED).count()
        self.total_rejected = assignments.filter(status=TaskAssignment.Status.REJECTED).count()

        self.save(update_fields=[
            'total_assigned', 'total_started', 'total_submitted',
            'total_approved', 'total_rejected'
        ])

    def complete(self):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save()

    def duplicate(self, user=None):
        new_task = Task.objects.create(
            title=f"{self.title} (nusxa)",
            description=self.description,
            instructions=self.instructions,
            type=self.type,
            template=self.template,
            target_all=self.target_all,
            target_region=self.target_region,
            target_district=self.target_district,
            deadline=self.deadline,
            allow_multiple_rows=self.allow_multiple_rows,
            min_rows=self.min_rows,
            max_rows=self.max_rows,
            allowed_extensions=self.allowed_extensions,
            max_file_size=self.max_file_size,
            max_files=self.max_files,
            requires_approval=self.requires_approval,
            allow_edit_after_submit=self.allow_edit_after_submit,
            auto_save=self.auto_save,
            reminder_enabled=self.reminder_enabled,
            reminder_days=self.reminder_days,
            created_by=user
        )

        for column in self.columns.all():
            TaskColumn.objects.create(
                task=new_task,
                title=column.title,
                data_type=column.data_type,
                choices=column.choices,
                required=column.required,
                order=column.order,
                width=column.width,
                help_text=column.help_text,
                validation=column.validation,
                default_value=column.default_value
            )

        for question in self.questions.all():
            TaskQuestion.objects.create(
                task=new_task,
                text=question.text,
                answer_type=question.answer_type,
                choices=question.choices,
                required=question.required,
                order=question.order,
                help_text=question.help_text,
                validation=question.validation
            )

        return new_task


class TaskColumn(models.Model):
    """Jadval ustuni"""

    class DataType(models.TextChoices):
        TEXT = 'text', _('Matn')
        TEXTAREA = 'textarea', _('Katta matn')
        NUMBER = 'number', _('Raqam')
        DECIMAL = 'decimal', _('O\'nlik son')
        DATE = 'date', _('Sana')
        DATETIME = 'datetime', _('Sana va vaqt')
        TIME = 'time', _('Vaqt')
        CHOICE = 'choice', _('Tanlov')
        MULTIPLE = 'multiple', _('Ko\'p tanlov')
        BOOLEAN = 'boolean', _('Ha/Yo\'q')
        PHONE = 'phone', _('Telefon')
        EMAIL = 'email', _('Email')
        URL = 'url', _('Havola')
        FILE = 'file', _('Fayl')
        IMAGE = 'image', _('Rasm')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='columns', verbose_name=_("Vazifa"))
    title = models.CharField(max_length=255, verbose_name=_("Ustun nomi"))
    data_type = models.CharField(max_length=20, choices=DataType.choices, default=DataType.TEXT,
                                 verbose_name=_("Ma'lumot turi"))
    choices = models.JSONField(null=True, blank=True, verbose_name=_("Tanlov variantlari"))
    required = models.BooleanField(default=True, verbose_name=_("Majburiy"))
    validation = models.JSONField(default=dict, blank=True, verbose_name=_("Validatsiya"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Tartib"))
    width = models.PositiveIntegerField(default=150, verbose_name=_("Kenglik (px)"))
    help_text = models.CharField(max_length=500, blank=True, verbose_name=_("Yordam matni"))
    placeholder = models.CharField(max_length=255, blank=True, verbose_name=_("Placeholder"))
    default_value = models.CharField(max_length=500, blank=True, verbose_name=_("Default qiymat"))
    is_calculated = models.BooleanField(default=False, verbose_name=_("Hisoblanadigan"))
    formula = models.CharField(max_length=500, blank=True, verbose_name=_("Formula"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Ustun")
        verbose_name_plural = _("Ustunlar")
        ordering = ['task', 'order']
        unique_together = ['task', 'order']

    def __str__(self):
        return f"{self.task.title} - {self.title}"

    def validate_value(self, value):
        errors = []

        if self.required and (value is None or value == ''):
            errors.append(_("Bu maydon majburiy"))
            return errors

        if value is None or value == '':
            return errors

        if self.data_type in ['number', 'decimal']:
            try:
                num = float(value)
                if 'min' in self.validation and num < self.validation['min']:
                    errors.append(f"Minimal qiymat: {self.validation['min']}")
                if 'max' in self.validation and num > self.validation['max']:
                    errors.append(f"Maksimal qiymat: {self.validation['max']}")
            except (ValueError, TypeError):
                errors.append(_("Raqam kiriting"))

        elif self.data_type in ['text', 'textarea']:
            value_len = len(str(value))
            if 'min_length' in self.validation and value_len < self.validation['min_length']:
                errors.append(f"Kamida {self.validation['min_length']} ta belgi")
            if 'max_length' in self.validation and value_len > self.validation['max_length']:
                errors.append(f"Ko'pi bilan {self.validation['max_length']} ta belgi")

        elif self.data_type == 'choice' and self.choices:
            valid_values = [c.get('value') for c in self.choices]
            if value not in valid_values:
                errors.append(_("Noto'g'ri tanlov"))

        elif self.data_type == 'phone':
            import re
            if not re.match(r'^\+998[0-9]{9}$', str(value)):
                errors.append(_("Format: +998XXXXXXXXX"))

        elif self.data_type == 'email':
            import re
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', str(value)):
                errors.append(_("Email formati noto'g'ri"))

        return errors


class TaskQuestion(models.Model):
    """So'rovnoma savoli"""

    class AnswerType(models.TextChoices):
        TEXT = 'text', _('Qisqa matn')
        TEXTAREA = 'textarea', _('Uzun matn')
        NUMBER = 'number', _('Raqam')
        DATE = 'date', _('Sana')
        CHOICE = 'choice', _('Tanlov')
        MULTIPLE = 'multiple', _('Ko\'p tanlov')
        BOOLEAN = 'boolean', _('Ha/Yo\'q')
        RATING = 'rating', _('Baho (1-5)')
        FILE = 'file', _('Fayl')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='questions', verbose_name=_("Vazifa"))
    text = models.TextField(verbose_name=_("Savol matni"))
    answer_type = models.CharField(max_length=20, choices=AnswerType.choices, default=AnswerType.TEXT,
                                   verbose_name=_("Javob turi"))
    choices = models.JSONField(null=True, blank=True, verbose_name=_("Tanlov variantlari"))
    required = models.BooleanField(default=True, verbose_name=_("Majburiy"))
    validation = models.JSONField(default=dict, blank=True, verbose_name=_("Validatsiya"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Tartib"))
    help_text = models.TextField(blank=True, verbose_name=_("Yordam matni"))
    depends_on = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='dependent_questions', verbose_name=_("Bog'liq savol"))
    depends_on_value = models.CharField(max_length=255, blank=True, verbose_name=_("Bog'liq qiymat"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Savol")
        verbose_name_plural = _("Savollar")
        ordering = ['task', 'order']

    def __str__(self):
        return f"{self.task.title} - Savol {self.order}"


class TaskAssignment(models.Model):
    """Vazifa tayinlash"""

    class Status(models.TextChoices):
        PENDING = 'pending', _('Kutilmoqda')
        VIEWED = 'viewed', _('Ko\'rildi')
        IN_PROGRESS = 'in_progress', _('Jarayonda')
        SUBMITTED = 'submitted', _('Yuborildi')
        APPROVED = 'approved', _('Tasdiqlandi')
        REJECTED = 'rejected', _('Rad etildi')
        OVERDUE = 'overdue', _('Muddati o\'tdi')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='assignments', verbose_name=_("Vazifa"))
    leader = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='task_assignments', verbose_name=_("Yetakchi"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("Holat"),
                              db_index=True)

    viewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Ko'rilgan"))
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Boshlangan"))
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Yuborilgan"))
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tasdiqlangan"))
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Rad etilgan"))

    approved_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_assignments', verbose_name=_("Kim tasdiqladi"))
    rejection_reason = models.TextField(blank=True, verbose_name=_("Rad etish sababi"))
    admin_notes = models.TextField(blank=True, verbose_name=_("Admin izohi"))

    progress = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)],
                                           verbose_name=_("Jarayon (%)"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Tayinlangan"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Yangilangan"))

    class Meta:
        verbose_name = _("Tayinlash")
        verbose_name_plural = _("Tayinlashlar")
        unique_together = ['task', 'leader']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', 'status']),
            models.Index(fields=['leader', 'status']),
        ]

    def __str__(self):
        return f"{self.leader} - {self.task.title}"

    @property
    def is_overdue(self):
        if self.status in [self.Status.SUBMITTED, self.Status.APPROVED]:
            return False
        return self.task.is_overdue

    @property
    def status_color(self):
        colors = {
            'pending': 'secondary',
            'viewed': 'info',
            'in_progress': 'warning',
            'submitted': 'primary',
            'approved': 'success',
            'rejected': 'danger',
            'overdue': 'danger',
        }
        return colors.get(self.status, 'secondary')

    @property
    def can_edit(self):
        if self.task.status != Task.Status.ACTIVE:
            return False
        if self.status == self.Status.APPROVED:
            return False
        if self.status == self.Status.SUBMITTED and not self.task.allow_edit_after_submit:
            return False
        return True

    def mark_viewed(self):
        if self.status == self.Status.PENDING:
            self.status = self.Status.VIEWED
            self.viewed_at = timezone.now()
            self.save(update_fields=['status', 'viewed_at', 'updated_at'])

    def start(self):
        if self.status in [self.Status.PENDING, self.Status.VIEWED]:
            self.status = self.Status.IN_PROGRESS
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at', 'updated_at'])
            self.task.update_stats()

    def submit(self):
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.progress = 100
        self.save(update_fields=['status', 'submitted_at', 'progress', 'updated_at'])
        self.task.update_stats()

        TaskHistory.objects.create(
            task=self.task,
            assignment=self,
            action=TaskHistory.Action.SUBMITTED,
            actor=self.leader,
            description=_("Vazifa yuborildi")
        )

    def approve(self, user, notes=''):
        from accounts.models import Notification

        self.status = self.Status.APPROVED
        self.approved_at = timezone.now()
        self.approved_by = user
        self.admin_notes = notes
        self.save()
        self.task.update_stats()

        Notification.send(
            user=self.leader,
            type=Notification.Type.TASK_APPROVED,
            title=_("Vazifa tasdiqlandi"),
            message=f"'{self.task.title}' vazifangiz tasdiqlandi.",
            link=f'/leader/tasks/{self.task.pk}/'
        )

        TaskHistory.objects.create(
            task=self.task,
            assignment=self,
            action=TaskHistory.Action.APPROVED,
            actor=user,
            description=notes or _("Vazifa tasdiqlandi")
        )

    def reject(self, user, reason):
        from accounts.models import Notification

        self.status = self.Status.REJECTED
        self.rejected_at = timezone.now()
        self.approved_by = user
        self.rejection_reason = reason
        self.save()
        self.task.update_stats()

        Notification.send(
            user=self.leader,
            type=Notification.Type.TASK_REJECTED,
            title=_("Vazifa rad etildi"),
            message=f"'{self.task.title}' vazifangiz rad etildi. Sabab: {reason}",
            link=f'/leader/tasks/{self.task.pk}/',
            priority='high'
        )

        TaskHistory.objects.create(
            task=self.task,
            assignment=self,
            action=TaskHistory.Action.REJECTED,
            actor=user,
            description=reason
        )

    def calculate_progress(self):
        if self.task.type == Task.Type.TABLE:
            total_cells = self.task.columns.filter(required=True).count()
            if total_cells == 0:
                return 100
            filled_cells = self.responses.filter(
                column__required=True
            ).exclude(value_text='', value_text__isnull=True).count()
            return int((filled_cells / total_cells) * 100)

        elif self.task.type == Task.Type.SURVEY:
            total_questions = self.task.questions.filter(required=True).count()
            if total_questions == 0:
                return 100
            answered = self.responses.filter(
                question__required=True
            ).exclude(value_text='', value_text__isnull=True).count()
            return int((answered / total_questions) * 100)

        return 0

    def update_progress(self):
        self.progress = self.calculate_progress()
        self.save(update_fields=['progress', 'updated_at'])


class TaskResponse(models.Model):
    """Vazifa javobi"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE, related_name='responses',
                                   verbose_name=_("Tayinlash"))
    column = models.ForeignKey(TaskColumn, on_delete=models.CASCADE, null=True, blank=True, related_name='responses',
                               verbose_name=_("Ustun"))
    question = models.ForeignKey(TaskQuestion, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name='responses', verbose_name=_("Savol"))
    row_index = models.PositiveIntegerField(default=0, verbose_name=_("Qator raqami"))

    value_text = models.TextField(blank=True, null=True, verbose_name=_("Matn"))
    value_number = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True, verbose_name=_("Raqam"))
    value_date = models.DateField(null=True, blank=True, verbose_name=_("Sana"))
    value_datetime = models.DateTimeField(null=True, blank=True, verbose_name=_("Sana va vaqt"))
    value_boolean = models.BooleanField(null=True, blank=True, verbose_name=_("Ha/Yo'q"))
    value_choice = models.CharField(max_length=500, blank=True, verbose_name=_("Tanlov"))
    value_json = models.JSONField(null=True, blank=True, verbose_name=_("JSON"))
    value_file = models.FileField(upload_to='responses/%Y/%m/', null=True, blank=True, verbose_name=_("Fayl"))

    is_valid = models.BooleanField(default=True, verbose_name=_("To'g'ri"))
    validation_errors = models.JSONField(default=list, blank=True, verbose_name=_("Xatolar"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Yangilangan"))

    class Meta:
        verbose_name = _("Javob")
        verbose_name_plural = _("Javoblar")
        ordering = ['row_index', 'column__order', 'question__order']
        indexes = [
            models.Index(fields=['assignment', 'column']),
            models.Index(fields=['assignment', 'question']),
        ]

    def __str__(self):
        return f"{self.assignment} - Response"

    @property
    def data_type(self):
        if self.column:
            return self.column.data_type
        if self.question:
            return self.question.answer_type
        return 'text'

    @property
    def value(self):
        dtype = self.data_type

        if dtype in ['text', 'textarea', 'phone', 'email', 'url']:
            return self.value_text
        elif dtype in ['number', 'decimal', 'rating']:
            return self.value_number
        elif dtype == 'date':
            return self.value_date
        elif dtype == 'datetime':
            return self.value_datetime
        elif dtype == 'boolean':
            return self.value_boolean
        elif dtype in ['choice', 'multiple']:
            return self.value_choice or self.value_json
        elif dtype in ['file', 'image']:
            return self.value_file

        return self.value_text

    @property
    def display_value(self):
        val = self.value

        if val is None or val == '':
            return '-'

        dtype = self.data_type

        if dtype == 'boolean':
            return _('Ha') if val else _("Yo'q")
        elif dtype == 'date' and val:
            return val.strftime('%d.%m.%Y')
        elif dtype == 'datetime' and val:
            return val.strftime('%d.%m.%Y %H:%M')
        elif dtype == 'multiple' and isinstance(val, list):
            return ', '.join(str(v) for v in val)
        elif dtype in ['file', 'image'] and val:
            return val.name.split('/')[-1]

        return str(val)

    def set_value(self, value):
        dtype = self.data_type

        self.value_text = None
        self.value_number = None
        self.value_date = None
        self.value_datetime = None
        self.value_boolean = None
        self.value_choice = None
        self.value_json = None

        if value is None or value == '':
            self.save()
            return

        try:
            if dtype in ['text', 'textarea', 'phone', 'email', 'url']:
                self.value_text = str(value)
            elif dtype in ['number', 'decimal', 'rating']:
                self.value_number = float(value)
            elif dtype == 'date':
                if isinstance(value, str):
                    from datetime import datetime
                    self.value_date = datetime.strptime(value, '%Y-%m-%d').date()
                else:
                    self.value_date = value
            elif dtype == 'datetime':
                if isinstance(value, str):
                    from datetime import datetime
                    self.value_datetime = datetime.fromisoformat(value)
                else:
                    self.value_datetime = value
            elif dtype == 'boolean':
                if isinstance(value, bool):
                    self.value_boolean = value
                else:
                    self.value_boolean = str(value).lower() in ['true', '1', 'ha', 'yes']
            elif dtype == 'choice':
                self.value_choice = str(value)
            elif dtype == 'multiple':
                if isinstance(value, list):
                    self.value_json = value
                else:
                    self.value_json = [value]
            else:
                self.value_text = str(value)
        except Exception:
            self.value_text = str(value)

        self.validate()
        self.save()

    def validate(self):
        errors = []

        if self.column:
            errors = self.column.validate_value(self.value)

        self.validation_errors = errors
        self.is_valid = len(errors) == 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.assignment.update_progress()


class TaskHistory(models.Model):
    """Vazifa tarixi"""

    class Action(models.TextChoices):
        CREATED = 'created', _('Yaratildi')
        UPDATED = 'updated', _('Yangilandi')
        PUBLISHED = 'published', _("E'lon qilindi")
        ASSIGNED = 'assigned', _('Tayinlandi')
        VIEWED = 'viewed', _("Ko'rildi")
        STARTED = 'started', _('Boshlandi')
        SAVED = 'saved', _('Saqlandi')
        SUBMITTED = 'submitted', _('Yuborildi')
        APPROVED = 'approved', _('Tasdiqlandi')
        REJECTED = 'rejected', _('Rad etildi')
        COMPLETED = 'completed', _('Yakunlandi')
        CANCELLED = 'cancelled', _('Bekor qilindi')
        REMINDER = 'reminder', _('Eslatma yuborildi')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history', verbose_name=_("Vazifa"))
    assignment = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='history', verbose_name=_("Tayinlash"))
    action = models.CharField(max_length=20, choices=Action.choices, verbose_name=_("Harakat"), db_index=True)
    actor = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='task_history', verbose_name=_("Kim"))
    description = models.TextField(blank=True, verbose_name=_("Tavsif"))
    changes = models.JSONField(default=dict, blank=True, verbose_name=_("O'zgarishlar"))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("IP manzil"))
    user_agent = models.TextField(blank=True, verbose_name=_("User Agent"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Vaqt"), db_index=True)

    class Meta:
        verbose_name = _("Tarix")
        verbose_name_plural = _("Tarix")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', '-created_at']),
        ]

    def __str__(self):
        return f"{self.task.title} - {self.get_action_display()}"

    @property
    def action_color(self):
        colors = {
            'created': 'primary',
            'updated': 'info',
            'published': 'success',
            'assigned': 'info',
            'viewed': 'secondary',
            'started': 'warning',
            'saved': 'light',
            'submitted': 'primary',
            'approved': 'success',
            'rejected': 'danger',
            'completed': 'success',
            'cancelled': 'danger',
            'reminder': 'warning',
        }
        return colors.get(self.action, 'secondary')

    @property
    def action_icon(self):
        icons = {
            'created': 'bi-plus-circle',
            'updated': 'bi-pencil',
            'published': 'bi-send',
            'assigned': 'bi-person-plus',
            'viewed': 'bi-eye',
            'started': 'bi-play',
            'saved': 'bi-save',
            'submitted': 'bi-check-circle',
            'approved': 'bi-check2-all',
            'rejected': 'bi-x-circle',
            'completed': 'bi-trophy',
            'cancelled': 'bi-slash-circle',
            'reminder': 'bi-bell',
        }
        return icons.get(self.action, 'bi-circle')