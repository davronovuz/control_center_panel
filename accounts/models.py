from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator


class User(AbstractUser):
    """
    Asosiy foydalanuvchi modeli.
    Admin va Yetakchilar uchun yagona model.
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        DISTRICT_ADMIN = 'district_admin', 'Tuman Admin'
        LEADER = 'leader', 'Yoshlar Yetakchisi'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        INACTIVE = 'inactive', 'Nofaol'
        BLOCKED = 'blocked', 'Bloklangan'

    phone_regex = RegexValidator(
        regex=r'^\+998[0-9]{9}$',
        message="Telefon raqam formati: +998XXXXXXXXX"
    )

    # Asosiy maydonlar
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.LEADER,
        verbose_name="Rol"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Holat"
    )
    phone = models.CharField(
        max_length=13,
        validators=[phone_regex],
        unique=True,
        null=True,
        blank=True,
        verbose_name="Telefon raqam"
    )
    telegram_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        verbose_name="Telegram ID",
        db_index=True
    )
    telegram_username = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Telegram username"
    )

    # Manzil ma'lumotlari
    region = models.ForeignKey(
        'Region',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Viloyat",
        related_name="users"
    )
    district = models.ForeignKey(
        'District',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Tuman",
        related_name="users"
    )
    mahalla = models.ForeignKey(
        'Mahalla',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Mahalla",
        related_name="users"
    )

    # Qo'shimcha
    bio = models.TextField(blank=True, verbose_name="Qo'shimcha ma'lumot")
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name="Rasm"
    )
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Oxirgi faollik"
    )

    # Vaqt belgilari
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['role', 'status']),
            models.Index(fields=['telegram_id']),
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username}"

    @property
    def is_admin(self):
        return self.role in [self.Role.SUPER_ADMIN, self.Role.DISTRICT_ADMIN]

    @property
    def is_leader(self):
        return self.role == self.Role.LEADER

    @property
    def full_address(self):
        parts = []
        if self.region:
            parts.append(self.region.name)
        if self.district:
            parts.append(self.district.name)
        if self.mahalla:
            parts.append(self.mahalla.name)
        return ", ".join(parts) if parts else "Ko'rsatilmagan"


class Region(models.Model):
    """Viloyat modeli"""

    name = models.CharField(max_length=100, unique=True, verbose_name="Nomi")
    code = models.CharField(max_length=10, unique=True, verbose_name="Kod")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Viloyat"
        verbose_name_plural = "Viloyatlar"
        ordering = ['name']

    def __str__(self):
        return self.name


class District(models.Model):
    """Tuman modeli"""

    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name="districts",
        verbose_name="Viloyat"
    )
    name = models.CharField(max_length=100, verbose_name="Nomi")
    code = models.CharField(max_length=10, verbose_name="Kod")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tuman"
        verbose_name_plural = "Tumanlar"
        ordering = ['name']
        unique_together = ['region', 'code']

    def __str__(self):
        return f"{self.name} ({self.region.name})"


class Mahalla(models.Model):
    """Mahalla modeli"""

    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name="mahallas",
        verbose_name="Tuman"
    )
    name = models.CharField(max_length=100, verbose_name="Nomi")
    code = models.CharField(max_length=20, verbose_name="Kod")
    population = models.PositiveIntegerField(default=0, verbose_name="Aholi soni")
    youth_count = models.PositiveIntegerField(default=0, verbose_name="Yoshlar soni")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mahalla"
        verbose_name_plural = "Mahallalar"
        ordering = ['name']
        unique_together = ['district', 'code']

    def __str__(self):
        return f"{self.name} ({self.district.name})"

    @property
    def region(self):
        return self.district.region