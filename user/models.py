from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class CustomUserManager(UserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError(_('شماره تلفن الزامی است'))
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractUser):
    gender_types = [("Male", _("مرد")), ("Female", _("زن"))]
    gender = models.CharField(
        _("جنسیت"),
        max_length=10,
        blank=True,
        null=True,
        choices=gender_types
    )
    job_types = [
        ("Admin", _("ادمین")),
        ("User", _("کاربر")),
        ("Support", _("پشتیبان")),
        ("Coach", _("مربی")),
        ("Store", _("فروشگاه")),
        ("Provider", _("ارائه‌دهنده")),
    ]
    job = models.CharField(
        _("نقش"),
        max_length=10,
        choices=job_types,
        default="User"
    )

    phone_number = models.CharField(
        _("شماره تلفن"),
        max_length=30,
        unique=True,
        null=False,
        blank=False
    )
    fullname = models.CharField(_("نام کامل"), max_length=100, null=True, blank=True)
    reject_comment = models.TextField(_("دلیل رد (اختیاری)"), null=True, blank=True)

    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _('username'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        null=True,
        blank=True
    )

    email = models.EmailField(_('آدرس ایمیل'), null=True, blank=True)

    is_user_active = models.BooleanField(_("کاربر فعال است؟"), null=True, default=False)
    is_complete_data = models.BooleanField(_("اطلاعات کامل است؟"), null=True, default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = _("کاربر")
        verbose_name_plural = _("کاربران")


class ProfilePic(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_("کاربر"))
    profile_pic = models.ImageField(_("عکس پروفایل"), upload_to="photos/profile/")

    def __str__(self):
        return _("عکس پروفایل برای کاربر {user}").format(user=self.user)

    class Meta:
        verbose_name = _("عکس پروفایل")
        verbose_name_plural = _("عکس‌های پروفایل")


class OTP(models.Model):
    phone_number = models.CharField(_("شماره تلفن"), max_length=15)
    code = models.CharField(_("کد تایید"), max_length=6)
    created_at = models.DateTimeField(_("زمان ایجاد"), auto_now_add=True)
    expires_at = models.DateTimeField(_("زمان انقضا"))

    def is_valid(self):
        return self.expires_at > timezone.now()

    def __str__(self):
        return f"{self.phone_number} - {self.code}"

    class Meta:
        verbose_name = _("کد یکبار مصرف")
        verbose_name_plural = _("کدهای یکبار مصرف")