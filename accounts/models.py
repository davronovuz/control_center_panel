import uuid
import random
import string
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinLengthValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ============================================================
# LOCATION MODELS
# ============================================================

class Region(models.Model):
    """
    Viloyat modeli
    O'zbekiston viloyatlari va Toshkent shahri
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Nomi")
    )
    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_("Kod"),
        help_text=_("Masalan: TAS, SAM, BUX")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Faol"),
        db_index=True
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Tartib")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Viloyat")
        verbose_name_plural = _("Viloyatlar")
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @property
    def districts_count(self):
        return self.districts.filter(is_active=True).count()

    @property
    def leaders_count(self):
        return User.objects.filter(
            district__region=self,
            role=User.Role.LEADER,
            status=User.Status.ACTIVE
        ).count()


class District(models.Model):
    """
    Tuman/Shahar modeli
    Viloyatga tegishli tumanlar
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name='districts',
        verbose_name=_("Viloyat")
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("Nomi")
    )
    code = models.CharField(
        max_length=10,
        verbose_name=_("Kod")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Faol"),
        db_index=True
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Tartib")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Tuman")
        verbose_name_plural = _("Tumanlar")
        ordering = ['region', 'order', 'name']
        unique_together = ['region', 'code']
        indexes = [
            models.Index(fields=['region', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name}"

    @property
    def full_name(self):
        return f"{self.region.name}, {self.name}"

    @property
    def mahallas_count(self):
        return self.mahallas.filter(is_active=True).count()

    @property
    def leaders_count(self):
        return User.objects.filter(
            mahalla__district=self,
            role=User.Role.LEADER,
            status=User.Status.ACTIVE
        ).count()


class Mahalla(models.Model):
    """
    Mahalla/MFY modeli
    Tumanga tegishli mahallalar
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name='mahallas',
        verbose_name=_("Tuman")
    )
    name = models.CharField(
        max_length=150,
        verbose_name=_("Nomi")
    )
    code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Kod")
    )
    population = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Aholi soni")
    )
    households = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Xonadonlar soni")
    )
    address = models.TextField(
        blank=True,
        verbose_name=_("Manzil")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Faol"),
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Mahalla")
        verbose_name_plural = _("Mahallalar")
        ordering = ['district', 'name']
        indexes = [
            models.Index(fields=['district', 'is_active']),
        ]

    def __str__(self):
        return self.name

    @property
    def full_name(self):
        return f"{self.district.region.name}, {self.district.name}, {self.name}"

    @property
    def region(self):
        return self.district.region

    @property
    def has_leader(self):
        return self.users.filter(
            role=User.Role.LEADER,
            status=User.Status.ACTIVE
        ).exists()

    @property
    def leader(self):
        return self.users.filter(
            role=User.Role.LEADER,
            status=User.Status.ACTIVE
        ).first()


# ============================================================
# USER MODEL
# ============================================================

class User(AbstractUser):
    """
    Foydalanuvchi modeli
    Tizimdan foydalanuvchi barcha shaxslar
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', _('Super Admin')
        REGION_ADMIN = 'region_admin', _('Viloyat Admini')
        DISTRICT_ADMIN = 'district_admin', _('Tuman Admini')
        LEADER = 'leader', _('Mahalla Yetakchisi')

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Faol')
        INACTIVE = 'inactive', _('Nofaol')
        BLOCKED = 'blocked', _('Bloklangan')
        PENDING = 'pending', _('Kutilmoqda')

    phone_validator = RegexValidator(
        regex=r'^\+998[0-9]{9}$',
        message=_("Telefon formati: +998XXXXXXXXX")
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # -------- ROLE & STATUS --------
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.LEADER,
        verbose_name=_("Rol"),
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_("Holat"),
        db_index=True
    )

    # -------- CONTACT --------
    phone = models.CharField(
        max_length=13,
        validators=[phone_validator],
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("Telefon raqam")
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name=_("Email")
    )

    # -------- LOCATION --------
    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_("Viloyat")
    )
    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_("Tuman")
    )
    mahalla = models.ForeignKey(
        Mahalla,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_("Mahalla")
    )

    # -------- PROFILE --------
    middle_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Otasining ismi")
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Tug'ilgan sana")
    )
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        null=True,
        blank=True,
        verbose_name=_("Rasm")
    )
    position = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Lavozimi")
    )
    bio = models.TextField(
        blank=True,
        verbose_name=_("Qo'shimcha ma'lumot")
    )

    # -------- SYSTEM --------
    plain_password = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Parol (ochiq)"),
        help_text=_("Faqat birinchi marta ko'rsatish uchun")
    )
    must_change_password = models.BooleanField(
        default=True,
        verbose_name=_("Parolni o'zgartirish kerak")
    )
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Oxirgi faollik")
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Oxirgi IP")
    )
    login_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Kirish soni")
    )

    # -------- NOTIFICATIONS --------
    notify_email = models.BooleanField(
        default=False,
        verbose_name=_("Email bildirishnoma")
    )
    notify_sms = models.BooleanField(
        default=False,
        verbose_name=_("SMS bildirishnoma")
    )
    notify_web = models.BooleanField(
        default=True,
        verbose_name=_("Web bildirishnoma")
    )

    # -------- META --------
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Yaratilgan")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Yangilangan")
    )
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        verbose_name=_("Kim yaratdi")
    )

    class Meta:
        verbose_name = _("Foydalanuvchi")
        verbose_name_plural = _("Foydalanuvchilar")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['role', 'status']),
            models.Index(fields=['phone']),
            models.Index(fields=['region', 'district']),
        ]

    def __str__(self):
        return self.get_full_name() or self.username

    # -------- PROPERTIES --------
    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        return ' '.join(filter(None, parts))

    @property
    def short_name(self):
        if self.first_name and self.last_name:
            return f"{self.last_name} {self.first_name[0]}."
        return self.username

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_region_admin(self):
        return self.role == self.Role.REGION_ADMIN

    @property
    def is_district_admin(self):
        return self.role == self.Role.DISTRICT_ADMIN

    @property
    def is_leader(self):
        return self.role == self.Role.LEADER

    @property
    def is_any_admin(self):
        return self.role in [
            self.Role.SUPER_ADMIN,
            self.Role.REGION_ADMIN,
            self.Role.DISTRICT_ADMIN
        ]

    @property
    def location_display(self):
        parts = []
        if self.region:
            parts.append(self.region.name)
        if self.district:
            parts.append(self.district.name)
        if self.mahalla:
            parts.append(self.mahalla.name)
        return ', '.join(parts) if parts else '-'

    @property
    def unread_notifications_count(self):
        return self.notifications.filter(is_read=False).count()

    # -------- METHODS --------
    def get_full_name(self):
        return self.full_name

    def update_activity(self, ip=None):
        self.last_activity = timezone.now()
        if ip:
            self.last_login_ip = ip
        self.save(update_fields=['last_activity', 'last_login_ip'])

    def increment_login(self):
        self.login_count += 1
        self.save(update_fields=['login_count'])

    def can_view_region(self, region):
        """Bu viloyatni ko'ra oladimi?"""
        if self.is_super_admin:
            return True
        return self.region == region

    def can_view_district(self, district):
        """Bu tumanni ko'ra oladimi?"""
        if self.is_super_admin:
            return True
        if self.is_region_admin:
            return self.region == district.region
        return self.district == district

    def can_view_user(self, user):
        """Bu foydalanuvchini ko'ra oladimi?"""
        if self.is_super_admin:
            return True
        if self.is_region_admin:
            return self.region == user.region
        if self.is_district_admin:
            return self.district == user.district
        return self == user

    def get_visible_leaders(self):
        """Ko'ra oladigan yetakchilar"""
        qs = User.objects.filter(role=User.Role.LEADER)

        if self.is_super_admin:
            return qs
        if self.is_region_admin:
            return qs.filter(region=self.region)
        if self.is_district_admin:
            return qs.filter(district=self.district)

        return qs.none()

    # -------- CLASS METHODS --------
    @classmethod
    def generate_username(cls, first_name, last_name):
        """Unikal username yaratish"""
        # Lotin harflariga o'girish
        base = f"{first_name}_{last_name}".lower()
        base = ''.join(c for c in base if c.isalnum() or c == '_')
        base = base[:20]  # Maksimal uzunlik

        username = base
        counter = 1
        while cls.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1

        return username

    @classmethod
    def generate_password(cls, length=8):
        """Xavfsiz parol yaratish"""
        chars = string.ascii_letters + string.digits
        # Kamida 1 katta harf, 1 kichik harf, 1 raqam
        password = [
            random.choice(string.ascii_uppercase),
            random.choice(string.ascii_lowercase),
            random.choice(string.digits),
        ]
        password += random.choices(chars, k=length - 3)
        random.shuffle(password)
        return ''.join(password)


# ============================================================
# NOTIFICATION MODELS
# ============================================================

class Notification(models.Model):
    """
    Bildirishnoma modeli
    Foydalanuvchilarga yuboriladigan xabarlar
    """

    class Type(models.TextChoices):
        TASK_NEW = 'task_new', _('Yangi vazifa')
        TASK_DEADLINE = 'task_deadline', _('Muddat yaqinlashdi')
        TASK_OVERDUE = 'task_overdue', _('Muddat o\'tdi')
        TASK_APPROVED = 'task_approved', _('Vazifa tasdiqlandi')
        TASK_REJECTED = 'task_rejected', _('Vazifa rad etildi')
        ANNOUNCEMENT = 'announcement', _('E\'lon')
        SYSTEM = 'system', _('Tizim xabari')
        WARNING = 'warning', _('Ogohlantirish')

    class Priority(models.TextChoices):
        LOW = 'low', _('Past')
        NORMAL = 'normal', _('O\'rta')
        HIGH = 'high', _('Yuqori')
        URGENT = 'urgent', _('Shoshilinch')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_("Foydalanuvchi")
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SYSTEM,
        verbose_name=_("Turi"),
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
        verbose_name=_("Muhimlik")
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Sarlavha")
    )
    message = models.TextField(
        verbose_name=_("Xabar")
    )
    link = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("Havola")
    )

    is_read = models.BooleanField(
        default=False,
        verbose_name=_("O'qilgan"),
        db_index=True
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("O'qilgan vaqt")
    )

    # Qo'shimcha ma'lumot (task_id, etc.)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Qo'shimcha")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Yaratilgan"),
        db_index=True
    )

    class Meta:
        verbose_name = _("Bildirishnoma")
        verbose_name_plural = _("Bildirishnomalar")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user}: {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def send(cls, user, type, title, message, link='', priority='normal', metadata=None):
        """Bildirishnoma yaratish"""
        return cls.objects.create(
            user=user,
            type=type,
            priority=priority,
            title=title,
            message=message,
            link=link,
            metadata=metadata or {}
        )

    @classmethod
    def send_bulk(cls, users, type, title, message, link='', priority='normal', metadata=None):
        """Ko'p foydalanuvchiga bildirishnoma"""
        notifications = [
            cls(
                user=user,
                type=type,
                priority=priority,
                title=title,
                message=message,
                link=link,
                metadata=metadata or {}
            )
            for user in users
        ]
        return cls.objects.bulk_create(notifications)


class Announcement(models.Model):
    """
    E'lon modeli
    Umumiy e'lonlar (hammaga yoki tanlanganlarga)
    """

    class Priority(models.TextChoices):
        LOW = 'low', _('Oddiy')
        NORMAL = 'normal', _('O\'rta')
        HIGH = 'high', _('Muhim')
        URGENT = 'urgent', _('Shoshilinch')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Qoralama')
        ACTIVE = 'active', _('Faol')
        ARCHIVED = 'archived', _('Arxivlangan')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Sarlavha")
    )
    content = models.TextField(
        verbose_name=_("Matn")
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
        verbose_name=_("Muhimlik")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Holat")
    )

    # -------- TARGETING --------
    target_all = models.BooleanField(
        default=True,
        verbose_name=_("Hammaga")
    )
    target_region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements',
        verbose_name=_("Viloyat")
    )
    target_district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements',
        verbose_name=_("Tuman")
    )
    target_roles = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Rollar"),
        help_text=_("['leader', 'district_admin']")
    )

    # -------- SCHEDULE --------
    publish_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("E'lon vaqti")
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Tugash vaqti")
    )

    # -------- ATTACHMENT --------
    attachment = models.FileField(
        upload_to='announcements/%Y/%m/',
        null=True,
        blank=True,
        verbose_name=_("Fayl")
    )

    # -------- STATS --------
    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Ko'rildi")
    )

    # -------- META --------
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_announcements',
        verbose_name=_("Yaratuvchi")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Yaratilgan")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Yangilangan")
    )

    class Meta:
        verbose_name = _("E'lon")
        verbose_name_plural = _("E'lonlar")
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        if self.status != self.Status.ACTIVE:
            return False
        now = timezone.now()
        if self.publish_at and now < self.publish_at:
            return False
        if self.expires_at and now > self.expires_at:
            return False
        return True

    def get_target_users(self):
        """E'lon ko'ra oladigan foydalanuvchilar"""
        qs = User.objects.filter(status=User.Status.ACTIVE)

        if not self.target_all:
            if self.target_district:
                qs = qs.filter(district=self.target_district)
            elif self.target_region:
                qs = qs.filter(region=self.target_region)

        if self.target_roles:
            qs = qs.filter(role__in=self.target_roles)

        return qs

    def publish(self):
        """E'lonni faollashtirish"""
        self.status = self.Status.ACTIVE
        if not self.publish_at:
            self.publish_at = timezone.now()
        self.save()

        # Bildirishnoma yuborish
        users = self.get_target_users()
        Notification.send_bulk(
            users=users,
            type=Notification.Type.ANNOUNCEMENT,
            title=self.title,
            message=self.content[:200] + '...' if len(self.content) > 200 else self.content,
            link=f'/announcements/{self.pk}/',
            priority=self.priority
        )