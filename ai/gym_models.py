from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
import jdatetime
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

User = get_user_model()


class Category(models.Model):
    name = models.CharField(_("نام دسته‌بندی"), max_length=100, unique=True)
    slug = models.SlugField(_("اسلاگ (نامک)"), max_length=110, unique=True,
                            help_text=_("برای استفاده در URLها، معمولا نسخه لاتین و خط‌فاصله‌دار نام است."))
    description = models.TextField(_("توضیحات"), blank=True, null=True)

    class Meta:
        verbose_name = _("دسته‌بندی")
        verbose_name_plural = _("دسته‌بندی‌ها")
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(_("نام تگ"), max_length=100, unique=True)
    slug = models.SlugField(_("اسلاگ (نامک)"), max_length=110, unique=True)

    class Meta:
        verbose_name = _("تگ")
        verbose_name_plural = _("تگ‌ها")
        ordering = ['name']

    def __str__(self):
        return self.name


class SportFacility(models.Model):
    name = models.CharField(max_length=200, verbose_name="نام سالن")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    capacity = models.IntegerField(verbose_name="ظرفیت")
    hourly_price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="قیمت ساعتی")
    address = models.TextField(verbose_name="آدرس")
    phone = models.CharField(max_length=20, blank=True, verbose_name="تلفن")
    facilities = models.TextField(blank=True, verbose_name="امکانات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    manager = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="مدیر سالن")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_active_sessions(self):
        """Get all active sessions for this facility"""
        return self.session_times.filter(is_active=True).order_by('day_of_week', 'start_time')

    def get_total_reservations(self):
        """Get total confirmed reservations for this facility"""
        return self.session_times.filter(reservations__status='confirmed').count()

    class Meta:
        verbose_name = "سالن ورزشی"
        verbose_name_plural = "سالن های ورزشی"
        ordering = ['name']


class FacilityImage(models.Model):
    UPLOADED_BY = (('admin', 'ادمین'), ('user', 'کاربر'))
    uploaded_by = models.CharField(_("��پلود شده بوسیله"), max_length=50, choices=UPLOADED_BY, default='admin')
    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='images',
                                 verbose_name=_("سالن ورزشی"))
    image = models.ImageField(_("تصویر"), upload_to='facility_images/')
    caption = models.CharField(_("عنوان تصویر"), max_length=200, blank=True, null=True)
    is_cover = models.BooleanField(_("تصویر کاور"), default=False, help_text=_("آیا این تصویر اصلی سالن است؟"))
    alt_text = models.CharField(_("متن جایگزین تصویر"), max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _("تصویر سالن")
        verbose_name_plural = _("گالری تصاویر سالن")
        ordering = ['-is_cover', 'id']  # کاور اول نمایش داده شود

    def __str__(self):
        return f"{self.facility.name} - {self.caption or 'Image'}"


class Feature(models.Model):
    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='features',
                                 verbose_name=_("سالن ورزشی"))
    text = models.CharField(_("متن ویژگی"), max_length=255)

    class Meta:
        verbose_name = _("ویژگی مثبت (امکانات)")
        verbose_name_plural = _("ویژگی‌های مثبت (امکانات)")

    def __str__(self):
        return f"{self.facility.name} - {self.text}"


class Drawback(models.Model):
    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='drawbacks',
                                 verbose_name=_("سالن ورزشی"))
    text = models.CharField(_("متن عیب"), max_length=255)

    class Meta:
        verbose_name = _("ویژگی منفی (عیب)")
        verbose_name_plural = _("ویژگی‌های منفی (معایب)")

    def __str__(self):
        return f"{self.facility.name} - {self.text}"


class OptionalService(models.Model):
    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='optional_services',
                                 verbose_name=_("سالن ورزشی"))
    name = models.CharField(_("نام آپشن"), max_length=150)
    price = models.DecimalField(_("قیمت آپشن"), max_digits=10, decimal_places=0,
                                validators=[MinValueValidator(Decimal('0.00'))])
    description = models.TextField(_("توضیحات آپشن"), blank=True, null=True)

    class Meta:
        verbose_name = _("آپشن انتخابی")
        verbose_name_plural = _("آپشن‌های انتخابی")
        unique_together = ('facility', 'name')  # هر آپشن برای هر سالن باید نام منحصر به فرد داشته باشد

    def __str__(self):
        return f"{self.facility.name} - {self.name} ({self.price})"


class SessionTime(models.Model):
    DAYS_OF_WEEK = [
        (0, "شنبه"),
        (1, "یکشنبه"),
        (2, "دوشنبه"),
        (3, "سه‌شنبه"),
        (4, "چهارشنبه"),
        (5, "پنج‌شنبه"),
        (6, "جمعه"),
    ]

    PRICE_TYPE_CHOICES = [
        ('fixed', 'قیمت ثابت'),
        ('hourly', 'قیمت ساعتی'),
    ]

    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='session_times',
                                 verbose_name="سالن")
    session_name = models.CharField(max_length=100, verbose_name="نام سانس")
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK, verbose_name="روز هفته")
    start_time = models.TimeField(verbose_name="زمان شروع")
    end_time = models.TimeField(verbose_name="زمان پایان")
    capacity = models.IntegerField(verbose_name="ظرفیت سانس", help_text="تعداد نفرات قابل رزرو در هر سانس")

    # فیلدهای جدید برای قیمت‌گذاری انعطاف‌پذیر
    price_type = models.CharField(
        max_length=10,
        choices=PRICE_TYPE_CHOICES,
        default='fixed',
        verbose_name="نوع قیمت‌گذاری"
    )
    fixed_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="قیمت ثابت سانس"
    )
    hourly_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="قیمت ساعتی سانس"
    )

    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.facility.name} - {self.session_name} ({self.start_time} - {self.end_time})"

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("زمان شروع باید قبل از زمان پایان باشد")

        # بررسی قیمت‌گذاری
        if self.price_type == 'fixed' and not self.fixed_price:
            raise ValidationError("برای قیمت‌گذاری ثابت، باید قیمت ثابت تعیین شود")
        elif self.price_type == 'hourly' and not self.hourly_price:
            raise ValidationError("برای قیمت‌گذاری ساعتی، باید قیمت ساعتی تعیین شود")

        # بررسی ظرفیت
        if self.capacity <= 0:
            raise ValidationError("ظرفیت سانس باید بیشتر از صفر باشد")
        if self.capacity > self.facility.capacity:
            raise ValidationError("ظرفیت سانس نمی‌تواند از ظرفیت سالن بیشتر باشد")

        # Check for overlapping sessions
        overlapping = SessionTime.objects.filter(
            facility=self.facility,
            day_of_week=self.day_of_week,
            is_active=True
        ).exclude(pk=self.pk)

        for session in overlapping:
            if (self.start_time < session.end_time and
                    self.end_time > session.start_time):
                raise ValidationError("این زمان با سانس دیگری تداخل دارد")

    def get_price(self):
        """محاسبه قیمت سانس"""
        if self.price_type == 'fixed':
            return self.fixed_price or Decimal('0')

        # محاسبه بر اساس قیمت ساعتی
        duration_hours = Decimal(
            (datetime.combine(datetime.today(), self.end_time) -
             datetime.combine(datetime.today(), self.start_time)).seconds
        ) / Decimal('3600')

        # اگر قیمت ساعتی سانس تعیین شده باشد از آن استفاده می‌شود
        # در غیر این صورت از قیمت ساعتی سالن استفاده می‌شود
        hourly_rate = self.hourly_price or self.facility.hourly_price
        return hourly_rate * duration_hours

    def get_duration_minutes(self):
        """محاسبه مدت زمان سانس به دقیقه"""
        duration = datetime.combine(datetime.today(), self.end_time) - datetime.combine(datetime.today(),
                                                                                        self.start_time)
        return duration.seconds // 60

    def get_price_display(self):
        """نمایش قیمت به همراه نوع قیمت‌گذاری"""
        price = self.get_price()
        if self.price_type == 'fixed':
            return f"{int(price):,} تومان (ثابت)"
        return f"{int(price):,} تومان (ساعتی - {int(self.hourly_price or self.facility.hourly_price):,} × {self.get_duration_minutes() / 60:.1f} ساعت)"

    def get_remaining_capacity(self, date):
        """محاسبه ظرفیت باقیمانده برای یک تاریخ خاص"""
        reserved_count = self.reservations.filter(
            date=date,
            status__in=['confirmed', 'pending']
        ).count()
        return max(0, self.capacity - reserved_count)

    def is_full(self, date):
        """بررسی پر بودن ظرفیت برای یک تاریخ خاص"""
        return self.get_remaining_capacity(date) == 0

    def get_total_reservations(self):
        """Get total confirmed reservations for this session"""
        return self.reservations.filter(status='confirmed').count()

    class Meta:
        verbose_name = "زمان سانس"
        verbose_name_plural = "زمان‌های سانس"
        ordering = ['day_of_week', 'start_time']
        unique_together = ['facility', 'day_of_week', 'start_time', 'end_time']


class Holiday(models.Model):
    date = models.DateField(unique=True, verbose_name="تاریخ تعطیلی")
    description = models.CharField(max_length=200, verbose_name="توضیحات")
    is_recurring = models.BooleanField(default=False, verbose_name="تعطیلی سالانه")
    jalali_month = models.IntegerField(null=True, blank=True, verbose_name="ماه شمسی")
    jalali_day = models.IntegerField(null=True, blank=True, verbose_name="روز شمسی")

    def __str__(self):
        return f"{self.get_jalali_date()} - {self.description}"

    def get_jalali_date(self):
        return jdatetime.date.fromgregorian(date=self.date).strftime("%Y/%m/%d")

    @classmethod
    def is_holiday(cls, check_date):
        """بررسی تعطیل بودن یک روز"""
        # تبدیل به تاریخ شمسی
        jalali_date = jdatetime.date.fromgregorian(date=check_date)

        return (
                cls.objects.filter(date=check_date).exists() or
                cls.objects.filter(
                    is_recurring=True,
                    jalali_month=jalali_date.month,
                    jalali_day=jalali_date.day
                ).exists()
        )

    class Meta:
        verbose_name = "تعطیلی"
        verbose_name_plural = "تعطیلات"
        ordering = ['date']


class Discount(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'درصدی'),
        ('fixed', 'مبلغ ثابت'),
    ]

    TARGET_TYPE_CHOICES = [
        ('facility', 'سالن ورزشی'),
        ('session', 'سانس'),
        ('user', 'کاربر'),
        ('code', 'کد تخفیف'),
    ]

    name = models.CharField(max_length=100, verbose_name="نام تخفیف")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        verbose_name="نوع تخفیف"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="مقدار تخفیف"
    )
    target_type = models.CharField(
        max_length=20,
        choices=TARGET_TYPE_CHOICES,
        verbose_name="نوع هدف"
    )
    facility = models.ForeignKey(
        SportFacility,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='discounts',
        verbose_name="سالن ورزشی"
    )
    session_time = models.ForeignKey(
        SessionTime,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='discounts',
        verbose_name="سانس"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='discounts',
        verbose_name="کاربر"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name="کد تخفیف"
    )
    start_date = models.DateField(verbose_name="تاریخ شروع")
    end_date = models.DateField(verbose_name="تاریخ پایان")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    min_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="حداقل مبلغ"
    )
    max_discount = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="حداکثر مبلغ تخفیف"
    )
    usage_limit = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="محدودیت استفاده"
    )
    used_count = models.IntegerField(
        default=0,
        verbose_name="تعداد استفاده"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.discount_type == 'percentage' and self.amount > 100:
            raise ValidationError("درصد تخفیف نمی‌تواند بیشتر از 100 باشد")

        if self.end_date < self.start_date:
            raise ValidationError("تاریخ پایان باید بعد از تاریخ شروع باشد")

        if self.target_type == 'facility' and not self.facility:
            raise ValidationError("برای تخفیف سالن باید سالن مشخص شود")
        elif self.target_type == 'session' and not self.session_time:
            raise ValidationError("برای تخفیف سانس باید سانس مشخص شود")
        elif self.target_type == 'user' and not self.user:
            raise ValidationError("برای تخفیف کاربر باید کاربر مشخص شود")
        elif self.target_type == 'code' and not self.code:
            raise ValidationError("برای کد تخفیف باید کد مشخص شود")

    def calculate_discount(self, original_price):
        """محاسبه مبلغ تخفیف"""
        if not self.is_active or self.is_expired():
            return 0

        if self.min_price and original_price < self.min_price:
            return 0

        if self.usage_limit and self.used_count >= self.usage_limit:
            return 0

        if self.discount_type == 'percentage':
            discount_amount = (original_price * self.amount) / 100
        else:
            discount_amount = self.amount

        if self.max_discount:
            discount_amount = min(discount_amount, self.max_discount)

        return discount_amount

    def is_expired(self):
        """بررسی منقضی شدن تخفیف"""
        return timezone.now().date() > self.end_date

    def __str__(self):
        return f"{self.name} ({self.get_discount_type_display()} - {self.amount})"

    class Meta:
        verbose_name = "تخفیف"
        verbose_name_plural = "تخفیف‌ها"
        ordering = ['-created_at']


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('confirmed', 'تایید شده'),
        ('cancelled', 'لغو شده'),
        ('completed', 'انجام شده'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations', verbose_name="کاربر")
    session_time = models.ForeignKey(SessionTime, on_delete=models.CASCADE, related_name='reservations',
                                     verbose_name="سانس")
    date = models.DateField(verbose_name="تاریخ")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    original_price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="قیمت اصلی")
    discount = models.ForeignKey(
        Discount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations',
        verbose_name="تخفیف"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        verbose_name="مبلغ تخفیف"
    )
    final_price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="قیمت نهایی")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, verbose_name="یادداشت")
    cancellation_reason = models.TextField(blank=True, verbose_name="دلیل لغو")
    cancellation_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ لغو")

    def clean(self):
        # Check if the date is not in the past
        if self.date < timezone.now().date():
            raise ValidationError("تاریخ رزرو نمی‌تواند در گذشته باشد")

        # Check if the date is not more than a year in the future
        max_future_date = timezone.now().date() + timedelta(days=365)
        if self.date > max_future_date:
            raise ValidationError("رزرو بیش از یک سال آینده امکان‌پذیر نیست")

        # Check if the date is not a holiday
        if Holiday.is_holiday(self.date):
            raise ValidationError("این روز تعطیل است")

        # Check if there's enough capacity
        if self.session_time.is_full(self.date):
            raise ValidationError("ظرفیت این سانس تکمیل است")

        # Check if there's already a reservation for this user on this date and session
        if Reservation.objects.filter(
                user=self.user,
                session_time=self.session_time,
                date=self.date,
                status__in=['confirmed', 'pending']
        ).exclude(pk=self.pk).exists():
            raise ValidationError("شما قبلاً این سانس را رزرو کرده‌اید")

        # Check if the day of week matches
        if self.date.weekday() != self.session_time.day_of_week:
            raise ValidationError("این سانس در این روز هفته برگزار نمی‌شود")

    def calculate_prices(self):
        """محاسبه قیمت‌های رزرو"""
        self.original_price = self.session_time.get_price()
        self.discount_amount = self.discount.calculate_discount(self.original_price) if self.discount else 0
        self.final_price = self.original_price - self.discount_amount

    def save(self, *args, **kwargs):
        self.calculate_prices()

        # اگر وضعیت به لغو شده تغییر کرده است
        if self.status == 'cancelled' and not self.cancellation_date:
            self.cancellation_date = timezone.now()

        # اگر تخفیف دارد، تعداد استفاده را افزایش دهید
        if self.discount and self.status == 'confirmed':
            self.discount.used_count += 1
            self.discount.save()

        super().save(*args, **kwargs)

    def cancel(self, reason=""):
        """لغو رزرو"""
        if not self.can_cancel:
            raise ValidationError("این رزرو قابل لغو نیست")

        self.status = 'cancelled'
        self.cancellation_reason = reason
        self.save()

    def get_jalali_date(self):
        return jdatetime.date.fromgregorian(date=self.date).strftime("%Y/%m/%d")

    @property
    def is_past(self):
        """Check if the reservation date is in the past"""
        return self.date < timezone.now().date()

    @property
    def can_cancel(self):
        """Check if the reservation can be cancelled"""
        if self.is_past or self.status not in ['pending', 'confirmed']:
            return False

        # فقط تا 24 ساعت قبل از زمان رزرو امکان لغو وجود دارد
        reservation_datetime = datetime.combine(self.date, self.session_time.start_time)
        return timezone.now() <= timezone.make_aware(reservation_datetime - timedelta(hours=24))

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.session_time} - {self.get_jalali_date()}"

    class Meta:
        verbose_name = "رزرو"
        verbose_name_plural = "رزروها"
        ordering = ['-date', 'session_time__start_time']
        unique_together = ['session_time', 'date']


class Review(models.Model):
    RATING_CHOICES = [
        (1, '⭐'),
        (2, '⭐⭐'),
        (3, '⭐⭐⭐'),
        (4, '⭐⭐⭐⭐'),
        (5, '⭐⭐⭐⭐⭐'),
    ]

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name="رزرو"
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        verbose_name="امتیاز"
    )
    comment = models.TextField(
        blank=True,
        verbose_name="نظر"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(
        default=False,
        verbose_name="تایید شده"
    )

    def clean(self):
        if self.reservation.status != 'completed':
            raise ValidationError("فقط برای رزروهای انجام شده می‌توانید نظر ثبت کنید")

        if not self.reservation.is_past:
            raise ValidationError("فقط پس از اتمام سانس می‌توانید نظر ثبت کنید")

    def __str__(self):
        return f"{self.reservation.user.get_full_name()} - {self.reservation.session_time.facility.name} - {self.get_rating_display()}"

    class Meta:
        verbose_name = "نظر"
        verbose_name_plural = "نظرات"
        ordering = ['-created_at']
