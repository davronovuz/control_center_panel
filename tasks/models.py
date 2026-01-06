import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    FileExtensionValidator
)
from django.core.exceptions import ValidationError
from django.utils import timezone


class Task(models.Model):
    """
    Asosiy vazifa modeli.
    Admin yaratadi, yetakchilarga yuboriladi.
    """

    class Type(models.TextChoices):
        SURVEY = 'survey', _("📋 So'rovnoma")
        EXCEL = 'excel', _("📊 Excel to'ldirish")
        REPORT = 'report', _("📝 Hisobot yig'ish")
        MIXED = 'mixed', _("🔀 Aralash")

    class Status(models.TextChoices):
        DRAFT = 'draft', _("Qoralama")
        ACTIVE = 'active', _("Faol")
        PAUSED = 'paused', _("To'xtatilgan")
        COMPLETED = 'completed', _("Yakunlangan")
        CANCELLED = 'cancelled', _("Bekor qilingan")
        ARCHIVED = 'archived', _("Arxivlangan")

    class Priority(models.TextChoices):
        LOW = 'low', _("Past")
        MEDIUM = 'medium', _("O'rta")
        HIGH = 'high', _("Yuqori")
        URGENT = 'urgent', _("Shoshilinch")

    # ==================== IDENTIFIKATSIYA ====================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # ==================== ASOSIY MA'LUMOTLAR ====================
    title = models.CharField(
        _("Sarlavha"),
        max_length=255,
        db_index=True
    )

    description = models.TextField(
        _("Tavsif"),
        blank=True,
        help_text=_("Vazifa haqida batafsil ma'lumot")
    )

    task_type = models.CharField(
        _("Vazifa turi"),
        max_length=20,
        choices=Type.choices,
        default=Type.SURVEY,
        db_index=True
    )

    status = models.CharField(
        _("Holat"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )

    priority = models.CharField(
        _("Muhimlik"),
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True
    )

    # ==================== MANZIL TARGETING ====================
    target_region = models.ForeignKey(
        'accounts.Region',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name=_("Viloyat"),
        help_text=_("Bo'sh = barcha viloyatlar")
    )

    target_district = models.ForeignKey(
        'accounts.District',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name=_("Tuman"),
        help_text=_("Bo'sh = barcha tumanlar")
    )

    target_mahallas = models.ManyToManyField(
        'accounts.Mahalla',
        blank=True,
        related_name='tasks',
        verbose_name=_("Mahallalar"),
        help_text=_("Bo'sh = barcha mahallalar")
    )

    # ==================== MUDDAT ====================
    deadline = models.DateTimeField(
        _("Muddat"),
        db_index=True
    )

    start_date = models.DateTimeField(
        _("Boshlanish"),
        null=True,
        blank=True,
        help_text=_("Bo'sh = darhol boshlanadi")
    )

    # ==================== ESLATMA SOZLAMALARI ====================
    reminder_enabled = models.BooleanField(
        _("Eslatma yuborish"),
        default=True
    )

    reminder_hours = models.PositiveIntegerField(
        _("Eslatma vaqti"),
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(168)],
        help_text=_("Muddat tugashiga necha soat qolganda")
    )

    # ==================== FAYL ====================
    source_file = models.FileField(
        _("Yuklangan fayl"),
        upload_to='tasks/source/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['xlsx', 'xls', 'csv'])],
        help_text=_("Excel shablon fayl")
    )

    result_file = models.FileField(
        _("Natija fayl"),
        upload_to='tasks/results/%Y/%m/',
        null=True,
        blank=True
    )

    # ==================== STATISTIKA (avtomatik yangilanadi) ====================
    stats_total_assigned = models.PositiveIntegerField(
        _("Jami tayinlangan"),
        default=0
    )

    stats_total_seen = models.PositiveIntegerField(
        _("Ko'rganlar"),
        default=0
    )

    stats_total_started = models.PositiveIntegerField(
        _("Boshlaganlar"),
        default=0
    )

    stats_total_completed = models.PositiveIntegerField(
        _("Bajarganlar"),
        default=0
    )

    stats_completion_rate = models.DecimalField(
        _("Bajarilish foizi"),
        max_digits=5,
        decimal_places=2,
        default=0.00
    )

    # ==================== YARATUVCHI ====================
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_tasks',
        verbose_name=_("Yaratuvchi")
    )

    # ==================== VAQT BELGILARI ====================
    created_at = models.DateTimeField(
        _("Yaratilgan"),
        auto_now_add=True,
        db_index=True
    )

    updated_at = models.DateTimeField(
        _("Yangilangan"),
        auto_now=True
    )

    published_at = models.DateTimeField(
        _("E'lon qilingan"),
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        _("Yakunlangan"),
        null=True,
        blank=True
    )

    # ==================== QO'SHIMCHA ====================
    notes = models.TextField(
        _("Ichki eslatmalar"),
        blank=True,
        help_text=_("Faqat adminlar ko'radi")
    )

    meta = models.JSONField(
        _("Qo'shimcha ma'lumot"),
        default=dict,
        blank=True
    )

    class Meta:
        verbose_name = _("Vazifa")
        verbose_name_plural = _("Vazifalar")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['status', '-deadline']),
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['-deadline']),
        ]

    def __str__(self):
        return self.title

    # ==================== VALIDATSIYA ====================
    def clean(self):
        super().clean()

        if self.deadline and self.deadline < timezone.now():
            if self.status == self.Status.DRAFT:
                raise ValidationError({
                    'deadline': _("Muddat kelajakda bo'lishi kerak")
                })

        if self.start_date and self.deadline:
            if self.start_date >= self.deadline:
                raise ValidationError({
                    'start_date': _("Boshlanish muddatdan oldin bo'lishi kerak")
                })

    def save(self, *args, **kwargs):
        if self.pk:
            old = Task.objects.filter(pk=self.pk).first()
            if old and old.status != self.status:
                if self.status == self.Status.ACTIVE and not self.published_at:
                    self.published_at = timezone.now()
                elif self.status == self.Status.COMPLETED:
                    self.completed_at = timezone.now()

        super().save(*args, **kwargs)

    # ==================== PROPERTIES ====================
    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_overdue(self):
        if self.status in [self.Status.COMPLETED, self.Status.CANCELLED]:
            return False
        return timezone.now() > self.deadline

    @property
    def time_remaining(self):
        """Qolgan vaqtni qaytaradi"""
        if not self.is_active:
            return None

        delta = self.deadline - timezone.now()

        if delta.total_seconds() < 0:
            return _("Muddat o'tgan")

        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        if days > 0:
            return f"{days} kun {hours} soat"
        elif hours > 0:
            return f"{hours} soat {minutes} daqiqa"
        else:
            return f"{minutes} daqiqa"

    @property
    def questions_count(self):
        return self.questions.count()

    # ==================== METHODS ====================
    def get_target_leaders(self):
        """Vazifa yuborilishi kerak bo'lgan yetakchilar"""
        from accounts.models import User

        leaders = User.objects.filter(
            role=User.Role.LEADER,
            status=User.Status.ACTIVE
        )

        if self.target_mahallas.exists():
            leaders = leaders.filter(mahalla__in=self.target_mahallas.all())
        elif self.target_district:
            leaders = leaders.filter(mahalla__district=self.target_district)
        elif self.target_region:
            leaders = leaders.filter(mahalla__district__region=self.target_region)

        return leaders.distinct()

    def publish(self):
        """Vazifani faollashtirish va yetakchilarga yuborish"""
        if self.status != self.Status.DRAFT:
            return False

        self.status = self.Status.ACTIVE
        self.published_at = timezone.now()
        self.save()

        # Har bir yetakchi uchun assignment yaratish
        leaders = self.get_target_leaders()
        assignments = []

        for leader in leaders:
            assignments.append(
                TaskAssignment(
                    task=self,
                    leader=leader,
                    status=TaskAssignment.Status.PENDING
                )
            )

        TaskAssignment.objects.bulk_create(assignments, ignore_conflicts=True)
        self.update_stats()

        return True

    def update_stats(self):
        """Statistikani yangilash"""
        assignments = self.assignments.all()

        self.stats_total_assigned = assignments.count()
        self.stats_total_seen = assignments.filter(
            status__in=[
                TaskAssignment.Status.SEEN,
                TaskAssignment.Status.IN_PROGRESS,
                TaskAssignment.Status.COMPLETED
            ]
        ).count()
        self.stats_total_started = assignments.filter(
            status__in=[
                TaskAssignment.Status.IN_PROGRESS,
                TaskAssignment.Status.COMPLETED
            ]
        ).count()
        self.stats_total_completed = assignments.filter(
            status=TaskAssignment.Status.COMPLETED
        ).count()

        if self.stats_total_assigned > 0:
            self.stats_completion_rate = round(
                (self.stats_total_completed / self.stats_total_assigned) * 100, 2
            )

        self.save(update_fields=[
            'stats_total_assigned',
            'stats_total_seen',
            'stats_total_started',
            'stats_total_completed',
            'stats_completion_rate'
        ])

    def generate_result_file(self):
        """Natija Excel faylini yaratish"""
        # Keyinroq implement qilamiz
        pass


class Question(models.Model):
    """
    Savol modeli.
    Har bir vazifada bir nechta savol bo'lishi mumkin.
    """

    class Type(models.TextChoices):
        TEXT = 'text', _("Matn")
        NUMBER = 'number', _("Raqam")
        CHOICE = 'choice', _("Tanlov")
        MULTIPLE = 'multiple', _("Ko'p tanlov")
        YES_NO = 'yes_no', _("Ha/Yo'q")
        DATE = 'date', _("Sana")
        PHONE = 'phone', _("Telefon")
        EMAIL = 'email', _("Email")

    # ==================== IDENTIFIKATSIYA ====================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # ==================== BOG'LANISH ====================
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_("Vazifa")
    )

    # ==================== ASOSIY ====================
    order = models.PositiveIntegerField(
        _("Tartib"),
        default=1,
        db_index=True
    )

    text = models.TextField(
        _("Savol matni")
    )

    question_type = models.CharField(
        _("Javob turi"),
        max_length=20,
        choices=Type.choices,
        default=Type.TEXT
    )

    is_required = models.BooleanField(
        _("Majburiy"),
        default=True
    )

    # ==================== TANLOV UCHUN ====================
    choices = models.JSONField(
        _("Variantlar"),
        null=True,
        blank=True,
        help_text=_("['Variant 1', 'Variant 2', ...]")
    )

    # ==================== VALIDATSIYA ====================
    validation = models.JSONField(
        _("Tekshirish qoidalari"),
        null=True,
        blank=True,
        help_text=_("{'min': 0, 'max': 100, 'min_length': 10, 'regex': '^[0-9]+$'}")
    )

    error_message = models.CharField(
        _("Xatolik xabari"),
        max_length=255,
        blank=True,
        help_text=_("Noto'g'ri javob kiritilganda")
    )

    # ==================== QO'SHIMCHA ====================
    help_text = models.CharField(
        _("Yordam matni"),
        max_length=255,
        blank=True
    )

    placeholder = models.CharField(
        _("Placeholder"),
        max_length=255,
        blank=True
    )

    excel_column = models.CharField(
        _("Excel ustun nomi"),
        max_length=100,
        blank=True,
        help_text=_("Natija Excelda qaysi ustun nomi bo'ladi")
    )

    # ==================== VAQT ====================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Savol")
        verbose_name_plural = _("Savollar")
        ordering = ['task', 'order']
        unique_together = ['task', 'order']

    def __str__(self):
        return f"{self.order}. {self.text[:50]}"

    def clean(self):
        super().clean()

        if self.question_type in [self.Type.CHOICE, self.Type.MULTIPLE]:
            if not self.choices or len(self.choices) < 2:
                raise ValidationError({
                    'choices': _("Kamida 2 ta variant kerak")
                })

    def validate_answer(self, value):
        """Javobni tekshirish"""
        errors = []

        # Majburiy tekshirish
        if self.is_required and not value:
            errors.append(self.error_message or _("Bu maydon majburiy"))
            return errors

        if not value:
            return errors

        # Tur bo'yicha tekshirish
        if self.question_type == self.Type.NUMBER:
            try:
                num = float(value)
                if self.validation:
                    if 'min' in self.validation and num < self.validation['min']:
                        errors.append(f"Minimal qiymat: {self.validation['min']}")
                    if 'max' in self.validation and num > self.validation['max']:
                        errors.append(f"Maksimal qiymat: {self.validation['max']}")
            except (ValueError, TypeError):
                errors.append(_("Raqam kiriting"))

        elif self.question_type == self.Type.CHOICE:
            if self.choices and value not in self.choices:
                errors.append(_("Noto'g'ri tanlov"))

        elif self.question_type == self.Type.MULTIPLE:
            if self.choices:
                if isinstance(value, list):
                    for v in value:
                        if v not in self.choices:
                            errors.append(f"Noto'g'ri tanlov: {v}")

        elif self.question_type == self.Type.YES_NO:
            valid = ['ha', 'yo\'q', 'yes', 'no', 'true', 'false', '1', '0']
            if str(value).lower() not in valid:
                errors.append(_("Ha yoki Yo'q deb javob bering"))

        elif self.question_type == self.Type.TEXT:
            if self.validation:
                if 'min_length' in self.validation and len(str(value)) < self.validation['min_length']:
                    errors.append(f"Kamida {self.validation['min_length']} ta belgi")
                if 'max_length' in self.validation and len(str(value)) > self.validation['max_length']:
                    errors.append(f"Ko'pi bilan {self.validation['max_length']} ta belgi")

        elif self.question_type == self.Type.PHONE:
            import re
            pattern = r'^\+998[0-9]{9}$'
            if not re.match(pattern, str(value)):
                errors.append(_("Telefon formati: +998XXXXXXXXX"))

        elif self.question_type == self.Type.EMAIL:
            import re
            pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            if not re.match(pattern, str(value)):
                errors.append(_("Email formati noto'g'ri"))

        return errors


class TaskAssignment(models.Model):
    """
    Vazifa tayinlash modeli.
    Har bir yetakchi uchun alohida holat.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', _("Yuborildi")
        SEEN = 'seen', _("Ko'rdi")
        IN_PROGRESS = 'in_progress', _("Jarayonda")
        COMPLETED = 'completed', _("Bajarildi")
        OVERDUE = 'overdue', _("Muddati o'tdi")

    # ==================== IDENTIFIKATSIYA ====================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # ==================== BOG'LANISH ====================
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_("Vazifa")
    )

    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_assignments',
        verbose_name=_("Yetakchi")
    )

    # ==================== HOLAT ====================
    status = models.CharField(
        _("Holat"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    current_question_order = models.PositiveIntegerField(
        _("Joriy savol"),
        default=0,
        help_text=_("Yetakchi qaysi savolda turibdi")
    )

    # ==================== VAQT BELGILARI ====================
    sent_at = models.DateTimeField(
        _("Yuborilgan"),
        auto_now_add=True
    )

    seen_at = models.DateTimeField(
        _("Ko'rilgan"),
        null=True,
        blank=True
    )

    started_at = models.DateTimeField(
        _("Boshlangan"),
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        _("Yakunlangan"),
        null=True,
        blank=True
    )

    # ==================== ESLATMA ====================
    reminder_sent_count = models.PositiveIntegerField(
        _("Eslatmalar soni"),
        default=0
    )

    last_reminder_at = models.DateTimeField(
        _("Oxirgi eslatma"),
        null=True,
        blank=True
    )

    # ==================== VAQT ====================
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Tayinlash")
        verbose_name_plural = _("Tayinlashlar")
        unique_together = ['task', 'leader']
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['task', 'status']),
            models.Index(fields=['leader', 'status']),
        ]

    def __str__(self):
        return f"{self.leader} - {self.task.title}"

    # ==================== PROPERTIES ====================
    @property
    def progress_percent(self):
        """Bajarilish foizi"""
        total = self.task.questions.count()
        if total == 0:
            return 0
        answered = self.answers.count()
        return int((answered / total) * 100)

    @property
    def is_overdue(self):
        """Muddati o'tdimi"""
        if self.status == self.Status.COMPLETED:
            return False
        return timezone.now() > self.task.deadline

    @property
    def answered_count(self):
        return self.answers.count()

    @property
    def remaining_count(self):
        return self.task.questions.count() - self.answered_count

    # ==================== METHODS ====================
    def mark_seen(self):
        """Ko'rilgan deb belgilash"""
        if self.status == self.Status.PENDING:
            self.status = self.Status.SEEN
            self.seen_at = timezone.now()
            self.save(update_fields=['status', 'seen_at', 'updated_at'])
            self.task.update_stats()

    def mark_started(self):
        """Boshlangan deb belgilash"""
        if self.status in [self.Status.PENDING, self.Status.SEEN]:
            self.status = self.Status.IN_PROGRESS
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at', 'updated_at'])
            self.task.update_stats()

    def mark_completed(self):
        """Yakunlangan deb belgilash"""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])
        self.task.update_stats()

    def get_next_question(self):
        """Keyingi savolni olish"""
        answered_orders = self.answers.values_list('question__order', flat=True)
        return self.task.questions.exclude(order__in=answered_orders).first()

    def get_current_question(self):
        """Joriy savolni olish"""
        return self.task.questions.filter(order=self.current_question_order).first()

    def check_completion(self):
        """Bajarilganini tekshirish"""
        total = self.task.questions.count()
        answered = self.answers.count()

        if total > 0 and answered >= total:
            self.mark_completed()
            return True
        return False


class Answer(models.Model):
    """
    Javob modeli.
    Yetakchining har bir savolga javobi.
    """

    # ==================== IDENTIFIKATSIYA ====================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # ==================== BOG'LANISH ====================
    assignment = models.ForeignKey(
        TaskAssignment,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_("Tayinlash")
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_("Savol")
    )

    # ==================== JAVOB QIYMATLARI ====================
    value_text = models.TextField(
        _("Matn"),
        null=True,
        blank=True
    )

    value_number = models.DecimalField(
        _("Raqam"),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )

    value_choice = models.CharField(
        _("Tanlov"),
        max_length=255,
        null=True,
        blank=True
    )

    value_multiple = models.JSONField(
        _("Ko'p tanlov"),
        null=True,
        blank=True
    )

    value_boolean = models.BooleanField(
        _("Ha/Yo'q"),
        null=True,
        blank=True
    )

    value_date = models.DateField(
        _("Sana"),
        null=True,
        blank=True
    )

    # ==================== VALIDATSIYA ====================
    is_valid = models.BooleanField(
        _("To'g'ri"),
        default=True
    )

    validation_errors = models.JSONField(
        _("Xatolar"),
        null=True,
        blank=True
    )

    # ==================== VAQT ====================
    created_at = models.DateTimeField(
        _("Kiritilgan"),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _("Yangilangan"),
        auto_now=True
    )

    class Meta:
        verbose_name = _("Javob")
        verbose_name_plural = _("Javoblar")
        unique_together = ['assignment', 'question']
        ordering = ['question__order']

    def __str__(self):
        return f"{self.assignment.leader} - {self.question.order}"

    # ==================== PROPERTIES ====================
    @property
    def value(self):
        """Javob qiymatini olish"""
        q_type = self.question.question_type

        if q_type == Question.Type.NUMBER:
            return self.value_number
        elif q_type == Question.Type.DATE:
            return self.value_date
        elif q_type == Question.Type.CHOICE:
            return self.value_choice
        elif q_type == Question.Type.MULTIPLE:
            return self.value_multiple
        elif q_type == Question.Type.YES_NO:
            return self.value_boolean

        return self.value_text

    @property
    def display_value(self):
        """Ko'rsatish uchun qiymat"""
        val = self.value

        if val is None:
            return "-"

        if self.question.question_type == Question.Type.YES_NO:
            return "Ha" if val else "Yo'q"

        if self.question.question_type == Question.Type.DATE and val:
            return val.strftime('%d.%m.%Y')

        if self.question.question_type == Question.Type.MULTIPLE and val:
            return ", ".join(val)

        return str(val)

    # ==================== METHODS ====================
    def set_value(self, value):
        """Javob qiymatini saqlash"""
        q_type = self.question.question_type

        if q_type == Question.Type.NUMBER:
            self.value_number = float(value) if value else None
        elif q_type == Question.Type.DATE:
            self.value_date = value
        elif q_type == Question.Type.CHOICE:
            self.value_choice = str(value) if value else None
        elif q_type == Question.Type.MULTIPLE:
            self.value_multiple = value if isinstance(value, list) else [value]
        elif q_type == Question.Type.YES_NO:
            if isinstance(value, bool):
                self.value_boolean = value
            else:
                self.value_boolean = str(value).lower() in ['ha', 'yes', 'true', '1']
        else:
            self.value_text = str(value) if value else None

        # Validatsiya
        errors = self.question.validate_answer(value)
        self.is_valid = len(errors) == 0
        self.validation_errors = errors if errors else None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Bajarilganini tekshirish
        self.assignment.check_completion()


class TaskHistory(models.Model):
    """
    Vazifa tarixini saqlash modeli.
    Har bir o'zgarish qayd qilinadi.
    """

    class Action(models.TextChoices):
        CREATED = 'created', _("Yaratildi")
        PUBLISHED = 'published', _("E'lon qilindi")
        ASSIGNED = 'assigned', _("Tayinlandi")
        SEEN = 'seen', _("Ko'rildi")
        STARTED = 'started', _("Boshlandi")
        ANSWERED = 'answered', _("Javob berildi")
        COMPLETED = 'completed', _("Yakunlandi")
        REMINDER = 'reminder', _("Eslatma yuborildi")
        EDITED = 'edited', _("Tahrirlandi")
        CANCELLED = 'cancelled', _("Bekor qilindi")

    # ==================== IDENTIFIKATSIYA ====================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # ==================== BOG'LANISH ====================
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name=_("Vazifa")
    )

    assignment = models.ForeignKey(
        TaskAssignment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='history',
        verbose_name=_("Tayinlash")
    )

    # ==================== HARAKAT ====================
    action = models.CharField(
        _("Harakat"),
        max_length=20,
        choices=Action.choices,
        db_index=True
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='task_actions',
        verbose_name=_("Bajaruvchi")
    )

    # ==================== MA'LUMOT ====================
    description = models.TextField(
        _("Tavsif"),
        blank=True
    )

    old_data = models.JSONField(
        _("Eski qiymat"),
        null=True,
        blank=True
    )

    new_data = models.JSONField(
        _("Yangi qiymat"),
        null=True,
        blank=True
    )

    # ==================== VAQT ====================
    created_at = models.DateTimeField(
        _("Vaqt"),
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        verbose_name = _("Tarix")
        verbose_name_plural = _("Tarix")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task.title} - {self.get_action_display()}"