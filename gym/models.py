from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta, time
import jdatetime
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.db import transaction

User = get_user_model()



class Category(models.Model):

    name = models.CharField(_("نام دسته‌بندی"), max_length=100, unique=True)
    slug = models.SlugField(_("اسلاگ (نامک)"), max_length=110, unique=True, allow_unicode=True,
                            help_text=_("برای استفاده در URLها، معمولا نسخه لاتین و خط‌فاصله‌دار نام است."))
    description = models.TextField(_("توضیحات"), blank=True, null=True)
    is_active = models.BooleanField(_("فعال"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("دسته‌بندی")
        verbose_name_plural = _("دسته‌بندی‌ها")
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    """
    مدلی برای تگ‌گذاری سالن‌ها یا سانس‌ها (مثلاً "فضای باز", "حرفه‌ای").
    از ai_models.py (کامل‌تر)
    """
    name = models.CharField(_("نام تگ"), max_length=100, unique=True)
    slug = models.SlugField(_("اسلاگ (نامک)"), max_length=110, unique=True, allow_unicode=True)
    is_active = models.BooleanField(_("فعال"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("تگ")
        verbose_name_plural = _("تگ‌ها")
        ordering = ['name']

    def __str__(self):
        return self.name


class FacilityFeature(models.Model):
    """
    مدلی برای ویژگی‌های مثبت یا منفی یک سالن (مثلاً "پارکینگ", "رختکن تمیز", "فضای کوچک").
    این مدل جایگزین Feature و Drawback از gym_models.py می‌شود و انعطاف‌پذیری بیشتری دارد.
    از ai_models.py
    """
    FEATURE_TYPE_CHOICES = [
        ('positive', _('مثبت')),
        ('negative', _('منفی')),
        ('neutral', _('خنثی')),
    ]
    name = models.CharField(_("نام ویژگی"), max_length=100, unique=True)
    description = models.TextField(_("توضیحات ویژگی"), blank=True)
    icon_class = models.CharField(_("کلاس آیکون (اختیاری)"), max_length=50, blank=True,
                                  help_text=_("مانند 'fa-wifi' برای Font Awesome"))
    feature_type = models.CharField(_("نوع ویژگی"), max_length=10, choices=FEATURE_TYPE_CHOICES, default='positive')
    is_active = models.BooleanField(_("فعال"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("ویژگی سالن")
        verbose_name_plural = _("ویژگی‌های سالن")
        ordering = ['name']

    def __str__(self):
        return f"{self.get_feature_type_display()} - {self.name}"


class SportFacility(models.Model):
    """
    مدلی برای سالن‌های ورزشی.
    ترکیبی از gym_models.py و ai_models.py با افزودن M2M برای Cat/Tag/Feature.
    """
    name = models.CharField(max_length=200, verbose_name=_("نام سالن"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    capacity = models.IntegerField(verbose_name=_("ظرفیت کلی سالن"))
    hourly_price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name=_("قیمت ساعتی پیش‌فرض سالن"),
                                       help_text=_("در صورتی که سانس قیمت ساعتی نداشته باشد، از این استفاده می‌شود."))
    address = models.TextField(verbose_name=_("آدرس"))
    phone = models.CharField(max_length=20, blank=True, verbose_name=_("تلفن"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    manager = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("مدیر سالن"),
                                related_name='managed_facilities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    categories = models.ManyToManyField(Category, blank=True, related_name='facilities', verbose_name=_("دسته‌بندی‌ها"))
    tags = models.ManyToManyField(Tag, blank=True, related_name='facilities', verbose_name=_("تگ‌ها"))
    features = models.ManyToManyField(FacilityFeature, blank=True, related_name='facilities',
                                      verbose_name=_("ویژگی‌ها"))

    def __str__(self):
        return self.name

    def get_active_sessions(self):
        """دریافت تمام سانس‌های فعال برای این سالن"""
        return self.session_times.filter(is_active=True).order_by('day_of_week', 'start_time')

    def get_average_rating(self):
        """محاسبه میانگین امتیازات برای این سالن"""
        # از ai_models.py
        reviews = Review.objects.filter(
            reservation__session_time__facility=self,
            is_approved=True,
            rating__isnull=False  # فقط نظراتی که امتیاز دارند
        )
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return 0

    class Meta:
        verbose_name = _("سالن ورزشی")
        verbose_name_plural = _("سالن‌های ورزشی")
        ordering = ['name']


class FacilityGallery(models.Model):
    """
    مدلی برای گالری تصاویر سالن.
    از ai_models.py (کامل‌تر)
    """
    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='gallery',
                                 verbose_name=_("سالن ورزشی"))
    image = models.ImageField(_("تصویر"), upload_to='facility_gallery/')
    caption = models.CharField(_("توضیحات تصویر"), max_length=255, blank=True)
    order = models.IntegerField(_("ترتیب نمایش"), default=0)
    is_cover = models.BooleanField(_("تصویر کاور"), default=False,
                                   help_text=_("آیا این تصویر اصلی سالن است؟"))  # از gym_models.py
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("تصویر گالری سالن")
        verbose_name_plural = _("گالری سالن‌ها")
        ordering = ['-is_cover', 'order', '-uploaded_at']
        unique_together = ['facility', 'image']

    def __str__(self):
        return f"{self.facility.name} - {self.caption or self.image.name}"


class SessionOption(models.Model):
    """
    آپشن‌های قابل اضافه شدن به سانس‌ها (مثلاً "توپ", "لباس").
    از ai_models.py
    """
    name = models.CharField(_("نام آپشن"), max_length=100)
    description = models.TextField(_("توضیحات آپشن"), blank=True)
    price = models.DecimalField(_("قیمت آپشن"), max_digits=10, decimal_places=0, default=0,
                                validators=[MinValueValidator(Decimal('0'))])
    is_active = models.BooleanField(_("فعال"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("آپشن سانس")
        verbose_name_plural = _("آپشن‌های سانس")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.price:,} تومان)"


class SessionTime(models.Model):
    """
    مدلی برای تعریف سانس‌های خاص در یک سالن در روزهای هفته.
    ترکیبی از هر دو، با اضافه شدن Dynamic Pricing و تصحیح DAYS_OF_WEEK.
    """
    # DAYS_OF_WEEK: 0 = شنبه, 1 = یکشنبه, ..., 6 = جمعه
    # این لیست با استاندارد ISO (0=دوشنبه) متفاوت است تا با تقویم شمسی همخوانی داشته باشد.
    # هنگام استفاده از date.weekday() نیاز به تبدیل داریم.
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
        ('fixed', _('قیمت ثابت')),
        ('hourly', _('قیمت ساعتی')),
        ('dynamic', _('قیمت پویا (بر اساس قوانین قیمت‌گذاری)')),  # از ai_models.py
    ]

    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='session_times',
                                 verbose_name=_("سالن"))
    session_name = models.CharField(max_length=100, verbose_name=_("نام سانس"))
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK, verbose_name=_("روز هفته"))
    start_time = models.TimeField(verbose_name=_("زمان شروع"))
    end_time = models.TimeField(verbose_name=_("زمان پایان"))
    capacity = models.IntegerField(verbose_name=_("ظرفیت سانس"), help_text=_("تعداد نفرات قابل رزرو در هر سانس"))

    price_type = models.CharField(
        max_length=10,
        choices=PRICE_TYPE_CHOICES,
        default='fixed',
        verbose_name=_("نوع قیمت‌گذاری")
    )
    fixed_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name=_("قیمت ثابت سانس"),
        validators=[MinValueValidator(Decimal('0'))]
    )
    # hourly_price اگر مشخص نشده باشد، از hourly_price سالن استفاده می‌شود
    hourly_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name=_("قیمت ساعتی سانس"),
        validators=[MinValueValidator(Decimal('0'))]
    )
    # فیلدهای مربوط به قیمت‌گذاری پویا (از ai_models.py)
    base_weekday_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name=_("قیمت پایه روزهای عادی (برای قیمت پویا)"),
        validators=[MinValueValidator(Decimal('0'))]
    )
    base_weekend_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name=_("قیمت پایه آخر هفته (برای قیمت پویا)"),
        validators=[MinValueValidator(Decimal('0'))]
    )

    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # آپشن‌های مربوط به این سانس (SessionOption)
    options = models.ManyToManyField(SessionOption, blank=True, related_name='sessions',
                                     verbose_name=_("آپشن‌های قابل انتخاب"))

    def __str__(self):
        return f"{self.facility.name} - {self.session_name} ({self.get_day_of_week_display()}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError(_("زمان شروع باید قبل از زمان پایان باشد."))

        # بررسی فیلدهای قیمت بر اساس نوع قیمت‌گذاری
        if self.price_type == 'fixed' and self.fixed_price is None:
            raise ValidationError(_("برای قیمت‌گذاری ثابت، باید قیمت ثابت تعیین شود."))
        elif self.price_type == 'hourly' and self.hourly_price is None and self.facility.hourly_price is None:
            raise ValidationError(_("برای قیمت‌گذاری ساعتی، باید قیمت ساعتی سانس یا سالن تعیین شود."))
        elif self.price_type == 'dynamic':
            if self.base_weekday_price is None or self.base_weekend_price is None:
                raise ValidationError(_("برای قیمت‌گذاری پویا، باید قیمت پایه روزهای عادی و آخر هفته تعیین شود."))

        if self.capacity <= 0:
            raise ValidationError(_("ظرفیت سانس باید بیشتر از صفر باشد."))
        if self.capacity > self.facility.capacity:
            raise ValidationError(_(f"ظرفیت سانس نمی‌تواند از ظرفیت سالن ({self.facility.capacity}) بیشتر باشد."))

        # Check for overlapping sessions
        overlapping = SessionTime.objects.filter(
            facility=self.facility,
            day_of_week=self.day_of_week,
            is_active=True
        ).exclude(pk=self.pk)

        for session in overlapping:
            if (self.start_time < session.end_time and
                    self.end_time > session.start_time):
                raise ValidationError(
                    _(f"این زمان با سانس '{session.session_name}' ({session.start_time}-{session.end_time}) در همین روز تداخل دارد."))

    def get_duration_hours(self):
        """محاسبه مدت زمان سانس به ساعت (اعشاری)"""
        dt_start = datetime.combine(datetime.today(), self.start_time)
        dt_end = datetime.combine(datetime.today(), self.end_time)
        duration = dt_end - dt_start
        return Decimal(duration.total_seconds()) / Decimal('3600')

    def get_duration_minutes(self):
        """محاسبه مدت زمان سانس به دقیقه"""
        dt_start = datetime.combine(datetime.today(), self.start_time)
        dt_end = datetime.combine(datetime.today(), self.end_time)
        duration = dt_end - dt_start
        return int(duration.total_seconds() // 60)

    def get_price_for_date(self, date):
        """
        محاسبه قیمت نهایی یک سانس برای یک تاریخ مشخص، با در نظر گرفتن قوانین قیمت‌گذاری.
        این متد پیچیده‌ترین منطق قیمت‌گذاری را پوشش می‌دهد.
        از ai_models.py
        """
        base_price = Decimal('0')

        if self.price_type == 'fixed':
            base_price = self.fixed_price if self.fixed_price is not None else Decimal('0')
        elif self.price_type == 'hourly':
            duration_hours = self.get_duration_hours()
            # اگر قیمت ساعتی سانس تعیین شده باشد از آن استفاده می‌شود، در غیر این صورت از قیمت ساعتی سالن
            hourly_rate = self.hourly_price if self.hourly_price is not None else self.facility.hourly_price
            base_price = hourly_rate * duration_hours
        elif self.price_type == 'dynamic':
            # تبدیل روز هفته میلادی به شمسی برای تعیین آخر هفته (پنجشنبه و جمعه)
            # 0=شنبه, 1=یکشنبه, 2=دوشنبه, 3=سه‌شنبه, 4=چهارشنبه, 5=پنج‌شنبه, 6=جمعه
            # date.weekday() برمی‌گرداند 0=دوشنبه, 1=سه‌شنبه, ..., 5=شنبه, 6=یکشنبه
            # تبدیل ISO weekday به Persian weekday: (ISO_weekday + 2) % 7
            # ISO: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
            # Persian: Sat=0, Sun=1, Mon=2, Tue=3, Wed=4, Thu=5, Fri=6
            persian_day_of_week = (date.weekday() + 2) % 7

            # پنجشنبه (5) و جمعه (6) در تقویم شمسی آخر هفته محسوب می‌شوند.
            if persian_day_of_week in [5, 6]:
                base_price = self.base_weekend_price if self.base_weekend_price is not None else Decimal('0')
            else:
                base_price = self.base_weekday_price if self.base_weekday_price is not None else Decimal('0')

        # اعمال قوانین قیمت‌گذاری (PricingRule)
        # قوانین با اولویت بالاتر (عدد بزرگتر) زودتر اعمال می‌شوند
        applicable_rules = self.facility.pricing_rules.filter(
            is_active=True
        ).order_by('-priority')

        final_price = base_price
        for rule in applicable_rules:
            if rule.is_applicable(date, self):
                final_price = rule.apply_to_price(final_price)

        return max(final_price, Decimal('0'))  # اطمینان از عدم وجود قیمت منفی

    def get_price_display(self, date=None):
        """نمایش قیمت به همراه نوع قیمت‌گذاری و جزئیات"""
        price = self.get_price_for_date(date) if date else self.fixed_price  # اگر تاریخ داده نشود، فقط ثابت یا اولیه

        if self.price_type == 'fixed':
            return f"{int(price):,} تومان (ثابت)"
        elif self.price_type == 'hourly':
            hourly_rate = self.hourly_price if self.hourly_price is not None else self.facility.hourly_price
            return f"{int(price):,} تومان (ساعتی - {int(hourly_rate):,} × {self.get_duration_hours():.1f} ساعت)"
        elif self.price_type == 'dynamic':
            return f"{int(price):,} تومان (پویا)"
        return f"{int(price):,} تومان"

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
        verbose_name = _("زمان سانس")
        verbose_name_plural = _("زمان‌های سانس")
        ordering = ['day_of_week', 'start_time']
        # هر سانس برای یک سالن در یک روز هفته با زمان شروع و پایان مشخص باید منحصر به فرد باشد.
        unique_together = ['facility', 'day_of_week', 'start_time', 'end_time']


class PricingRule(models.Model):
    """
    قوانین قیمت‌گذاری پویا برای سالن‌ها یا سانس‌ها.
    از ai_models.py (یکی از نقاط قوت اصلی)
    """
    RULE_TYPE_CHOICES = [
        ('time_of_day', _('ساعت روز')),
        ('day_of_week', _('روز هفته')),
        ('date_range', _('بازه تاریخی')),
        ('special_day', _('روزهای خاص (مانند تعطیلات)')),
        ('peak_hours', _('ساعات اوج مصرف')),
    ]

    ADJUSTMENT_TYPE_CHOICES = [
        ('percentage_increase', _('افزایش درصدی')),
        ('percentage_decrease', _('کاهش درصدی')),
        ('fixed_price', _('قیمت ثابت')),  # قیمت را به این مقدار ثابت تغییر می‌دهد
        ('fixed_increase', _('افزایش ثابت')),
        ('fixed_decrease', _('کاهش ثابت')),
    ]

    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='pricing_rules',
                                 verbose_name=_("سالن"))
    name = models.CharField(max_length=100, verbose_name=_("نام قانون"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES, verbose_name=_("نوع قانون"))

    # فیلدهای مربوط به انواع قوانین
    start_time_rule = models.TimeField(null=True, blank=True, verbose_name=_("ساعت شروع اعمال قانون"))
    end_time_rule = models.TimeField(null=True, blank=True, verbose_name=_("ساعت پایان اعمال قانون"))

    # days_of_week: 0,1,2 (برای شنبه، یکشنبه، دوشنبه شمسی)
    days_of_week = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("روزهای هفته شمسی"),
        help_text=_("شماره روزها با کاما جدا شود (0=شنبه, 1=یکشنبه, ..., 6=جمعه). مثال: 5,6 برای پنجشنبه و جمعه.")
    )

    start_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ شروع اعمال قانون"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ پایان اعمال قانون"))

    price_adjustment_type = models.CharField(
        max_length=20,
        choices=ADJUSTMENT_TYPE_CHOICES,
        verbose_name=_("نوع تنظیم قیمت")
    )
    adjustment_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("مقدار تنظیم قیمت"))

    priority = models.IntegerField(default=0, verbose_name=_("اولویت"),
                                   help_text=_(
                                       "قوانین با اولویت بالاتر (عدد بزرگتر) زودتر اعمال می‌شوند. قوانین 'fixed_price' باید بالاترین اولویت را داشته باشند."))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.facility.name} ({self.get_price_adjustment_type_display()}: {self.adjustment_value})"

    def clean(self):
        if self.rule_type in ['time_of_day', 'peak_hours']:
            if not self.start_time_rule or not self.end_time_rule:
                raise ValidationError(_("برای قوانین ساعتی یا ساعات اوج مصرف، ساعت شروع و پایان قانون باید تعیین شود."))
            if self.start_time_rule >= self.end_time_rule:
                raise ValidationError(_("ساعت شروع قانون باید قبل از ساعت پایان قانون باشد."))
        elif self.rule_type == 'day_of_week':
            if not self.days_of_week:
                raise ValidationError(_("برای قوانین روز هفته، روزهای هفته باید مشخص شود."))
            # اعتبار سنجی فرمت روزهای هفته
            for day_str in self.days_of_week.split(','):
                try:
                    day_int = int(day_str.strip())
                    if not (0 <= day_int <= 6):
                        raise ValueError
                except ValueError:
                    raise ValidationError(_("فرمت 'روزهای هفته شمسی' نادرست است. باید شامل اعداد 0 تا 6 با کاما باشد."))
        elif self.rule_type == 'date_range':
            if not self.start_date or not self.end_date:
                raise ValidationError(_("برای قوانین بازه تاریخی، تاریخ شروع و پایان باید مشخص شود."))
            if self.start_date >= self.end_date:
                raise ValidationError(_("تاریخ شروع قانون باید قبل از تاریخ پایان قانون باشد."))

        if self.price_adjustment_type == 'percentage_increase' and self.adjustment_value <= 0:
            raise ValidationError(_("مقدار افزایش درصدی باید مثبت باشد."))
        if self.price_adjustment_type == 'percentage_decrease' and not (
                Decimal('0') < self.adjustment_value <= Decimal('100')):
            raise ValidationError(_("مقدار کاهش درصدی باید بین 0 تا 100 باشد."))
        if self.price_adjustment_type == 'fixed_increase' and self.adjustment_value <= 0:
            raise ValidationError(_("مقدار افزایش ثابت باید مثبت باشد."))
        if self.price_adjustment_type == 'fixed_decrease' and self.adjustment_value <= 0:
            raise ValidationError(_("مقدار کاهش ثابت باید مثبت باشد."))
        if self.price_adjustment_type == 'fixed_price' and self.adjustment_value < 0:
            raise ValidationError(_("مقدار قیمت ثابت نمی‌تواند منفی باشد."))

    def is_applicable(self, date, session_time):
        """
        بررسی می‌کند که آیا این قانون قیمت‌گذاری برای یک تاریخ و سانس خاص اعمال می‌شود یا خیر.
        """
        if not self.is_active:
            return False

        # تبدیل ISO weekday به Persian weekday برای مقایسه با days_of_week
        # ISO: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        # Persian: Sat=0, Sun=1, Mon=2, Tue=3, Wed=4, Thu=5, Fri=6
        persian_day_of_week = (date.weekday() + 2) % 7

        if self.rule_type == 'day_of_week':
            return str(persian_day_of_week) in [d.strip() for d in self.days_of_week.split(',')]

        elif self.rule_type == 'date_range':
            return self.start_date <= date <= self.end_date

        elif self.rule_type == 'time_of_day' or self.rule_type == 'peak_hours':
            # بررسی تداخل زمانی قانون با زمان سانس
            if self.start_time_rule and self.end_time_rule:
                session_start = session_time.start_time
                session_end = session_time.end_time
                # اگر بازه سانس با بازه قانون تداخل داشته باشد
                return (self.start_time_rule < session_end and self.end_time_rule > session_start)
            return False

        elif self.rule_type == 'special_day':
            # این قانون می‌تواند با مدل Holiday یکپارچه شود.
            # به عنوان مثال، اگر تاریخ ورودی یک تعطیلی باشد، اعمال شود.
            return Holiday.is_holiday(date)

        return False

    def apply_to_price(self, base_price):
        """
        مقدار تنظیم قیمت را بر روی قیمت پایه اعمال می‌کند.
        """
        if self.price_adjustment_type == 'percentage_increase':
            return base_price * (Decimal('1') + self.adjustment_value / Decimal('100'))
        elif self.price_adjustment_type == 'percentage_decrease':
            return base_price * (Decimal('1') - self.adjustment_value / Decimal('100'))
        elif self.price_adjustment_type == 'fixed_price':
            return self.adjustment_value
        elif self.price_adjustment_type == 'fixed_increase':
            return base_price + self.adjustment_value
        elif self.price_adjustment_type == 'fixed_decrease':
            return base_price - self.adjustment_value
        return base_price

    class Meta:
        verbose_name = _("قانون قیمت‌گذاری")
        verbose_name_plural = _("قوانین قیمت‌گذاری")
        ordering = ['-priority', 'name']


class Holiday(models.Model):
    """
    مدلی برای تعریف تعطیلات.
    ترکیبی از هر دو با منطق بهتر برای تعطیلات تکرارشونده و مدیریت تاریخ میلادی/شمسی.
    """
    date = models.DateField(_("تاریخ تعطیلی (میلادی)"), unique=True, null=True, blank=True,
                            help_text=_("تاریخ میلادی را برای تعطیلی‌های یکبار مصرف وارد کنید."))
    description = models.CharField(_("توضیحات"), max_length=200)
    is_recurring = models.BooleanField(_("تعطیلی سالانه"), default=False,
                                       help_text=_("اگر این تعطیلی هر سال تکرار می‌شود (بر اساس ماه و روز شمسی)."))
    jalali_month = models.IntegerField(_("ماه شمسی"), null=True, blank=True,
                                       help_text=_("برای تعطیلی‌های تکرارشونده (1 تا 12)."))
    jalali_day = models.IntegerField(_("روز شمسی"), null=True, blank=True,
                                     help_text=_("برای تعطیلی‌های تکرارشونده (1 تا 31)."))

    def __str__(self):
        if self.is_recurring and self.jalali_month and self.jalali_day:
            return f"{self.jalali_month}/{self.jalali_day} (تکرارشونده) - {self.description}"
        elif self.date:
            try:
                return f"{jdatetime.date.fromgregorian(date=self.date).strftime('%Y/%m/%d')} - {self.description}"
            except ValueError:
                return f"{self.date} - {self.description}"
        return self.description

    def clean(self):
        if self.is_recurring:
            if not (self.jalali_month and 1 <= self.jalali_month <= 12):
                raise ValidationError(_("برای تعطیلی سالانه، ماه شمسی باید بین 1 تا 12 باشد."))
            if not (self.jalali_day and 1 <= self.jalali_day <= 31):
                raise ValidationError(_("برای تعطیلی سالانه، روز شمسی باید بین 1 تا 31 باشد."))
            if self.date:
                raise ValidationError(_("برای تعطیلی سالانه، فیلد 'تاریخ تعطیلی (میلادی)' باید خالی باشد."))
        else:
            if not self.date:
                raise ValidationError(_("برای تعطیلی یکبار مصرف، فیلد 'تاریخ تعطیلی (میلادی)' باید پر شود."))
            if self.jalali_month or self.jalali_day:
                raise ValidationError(_("برای تعطیلی یکبار مصرف، فیلدهای ماه و روز شمسی باید خالی باشند."))

    def save(self, *args, **kwargs):
        # اگر تعطیلی یکبار مصرف باشد، اطمینان حاصل شود که فیلدهای شمسی خالی هستند
        if not self.is_recurring:
            self.jalali_month = None
            self.jalali_day = None
        super().save(*args, **kwargs)

    @classmethod
    def is_holiday(cls, check_date):
        """
        بررسی تعطیل بودن یک روز مشخص (تاریخ میلادی).
        بهبود یافته برای بررسی هم تعطیلات یکبار مصرف و هم تکرارشونده.
        """
        # بررسی تعطیلات یکبار مصرف
        if cls.objects.filter(date=check_date).exists():
            return True

        # بررسی تعطیلات تکرارشونده
        try:
            jalali_date = jdatetime.date.fromgregorian(date=check_date)
            if cls.objects.filter(
                    is_recurring=True,
                    jalali_month=jalali_date.month,
                    jalali_day=jalali_date.day
            ).exists():
                return True
        except ValueError:  # در صورتی که تاریخ میلادی به شمسی تبدیل نشود
            pass

        return False

    @classmethod
    def get_holidays_in_range(cls, start_date, end_date):
        """
        دریافت لیست تعطیلات در یک بازه تاریخی مشخص (میلادی).
        از ai_models.py
        """
        holidays_list = []

        # تعطیلات با تاریخ میلادی ثابت
        fixed_holidays = cls.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            is_recurring=False
        ).values('date', 'description')
        holidays_list.extend(list(fixed_holidays))

        # تعطیلات تکرارشونده
        recurring_holidays = cls.objects.filter(is_recurring=True)

        current_date = start_date
        while current_date <= end_date:
            try:
                jalali_date = jdatetime.date.fromgregorian(date=current_date)
                for holiday in recurring_holidays:
                    if (holiday.jalali_month == jalali_date.month and
                            holiday.jalali_day == jalali_date.day):
                        holidays_list.append({
                            'date': current_date,
                            'description': holiday.description
                        })
            except ValueError:
                # اگر تاریخ میلادی قابل تبدیل به شمسی نباشد، آن را رد کنید
                pass
            current_date += timedelta(days=1)

        # حذف موارد تکراری و مرتب‌سازی
        unique_holidays = {h['date'].isoformat(): h for h in holidays_list}.values()
        return sorted(list(unique_holidays), key=lambda x: x['date'])

    class Meta:
        verbose_name = _("تعطیلی")
        verbose_name_plural = _("تعطیلات")
        ordering = ['date']


class Discount(models.Model):
    """
    مدلی برای تعریف تخفیف‌ها.
    ترکیبی از هر دو با بهبود منطق محاسبه و اعتبارسنجی.
    """
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', _('درصدی')),
        ('fixed', _('مبلغ ثابت')),
    ]

    TARGET_TYPE_CHOICES = [
        ('facility', _('سالن ورزشی')),
        ('session', _('سانس')),
        ('user', _('کاربر')),
        ('code', _('کد تخفیف')),
        ('all', _('همه موارد (تخفیف عمومی)')),  # افزودن تخفیف عمومی
    ]

    name = models.CharField(max_length=100, verbose_name=_("نام تخفیف"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        verbose_name=_("نوع تخفیف")
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("مقدار تخفیف (درصد یا مبلغ)")
    )
    target_type = models.CharField(
        max_length=20,
        choices=TARGET_TYPE_CHOICES,
        verbose_name=_("هدف تخفیف")
    )
    facility = models.ForeignKey(
        SportFacility,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='discounts',
        verbose_name=_("سالن ورزشی مرتبط")
    )
    session_time = models.ForeignKey(
        SessionTime,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='discounts',
        verbose_name=_("سانس مرتبط")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='discounts',
        verbose_name=_("کاربر مرتبط")
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("کد تخفیف (برای نوع 'کد تخفیف')")
    )
    start_date = models.DateField(verbose_name=_("تاریخ شروع"))
    end_date = models.DateField(verbose_name=_("تاریخ پایان"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    min_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name=_("حداقل مبلغ خرید برای اعمال تخفیف"),
        validators=[MinValueValidator(Decimal('0'))]
    )
    max_discount = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name=_("حداکثر مبلغ قابل تخفیف (برای تخفیف درصدی)"),
        validators=[MinValueValidator(Decimal('0'))]
    )
    usage_limit = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("محدودیت تعداد استفاده کلی"),
        help_text=_("تعداد دفعاتی که این تخفیف می‌تواند استفاده شود (null به معنای نامحدود)."),
        validators=[MinValueValidator(0)]
    )
    used_count = models.IntegerField(
        default=0,
        verbose_name=_("تعداد دفعات استفاده شده"),
        editable=False  # این فیلد نباید به صورت دستی ویرایش شود
    )
    user_usage_limit = models.IntegerField(  # محدودیت استفاده برای هر کاربر
        null=True,
        blank=True,
        verbose_name=_("محدودیت استفاده برای هر کاربر"),
        help_text=_("تعداد دفعاتی که هر کاربر می‌تواند از این تخفیف استفاده کند (null به معنای نامحدود)."),
        validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_discount_type_display()} - {self.amount})"

    def clean(self):
        if self.discount_type == 'percentage' and not (Decimal('0') < self.amount <= Decimal('100')):
            raise ValidationError(_("درصد تخفیف باید بین 0 تا 100 باشد."))
        elif self.discount_type == 'fixed' and self.amount < 0:
            raise ValidationError(_("مبلغ ثابت تخفیف نمی‌تواند منفی باشد."))

        if self.end_date < self.start_date:
            raise ValidationError(_("تاریخ پایان باید بعد از تاریخ شروع باشد."))

        # اعتبارسنجی وابستگی‌های هدف تخفیف
        if self.target_type == 'facility' and not self.facility:
            raise ValidationError(_("برای تخفیف سالن، باید سالن مشخص شود."))
        elif self.target_type == 'session' and not self.session_time:
            raise ValidationError(_("برای تخفیف سانس، باید سانس مشخص شود."))
        elif self.target_type == 'user' and not self.user:
            raise ValidationError(_("برای تخفیف کاربر، باید کاربر مشخص شود."))
        elif self.target_type == 'code' and not self.code:
            raise ValidationError(_("برای کد تخفیف، باید کد مشخص شود."))
        elif self.target_type == 'all':  # برای تخفیف عمومی، هیچ کدام از FKها نباید پر شوند
            if self.facility or self.session_time or self.user or self.code:
                raise ValidationError(_("برای تخفیف عمومی، فیلدهای سالن، سانس، کاربر و کد تخفیف باید خالی باشند."))

        # بررسی تداخل برای انواع خاص تخفیف
        if self.target_type != 'code' and self.code:
            raise ValidationError(_("کد تخفیف فقط برای نوع هدف 'کد تخفیف' قابل استفاده است."))

    def calculate_discount_amount(self, original_price, user=None):
        """
        محاسبه مبلغ تخفیف قابل اعمال بر روی قیمت اصلی.
        پارامتر user برای بررسی محدودیت استفاده کاربر.
        """
        if not self.is_active or self.is_expired():
            return Decimal('0')

        if self.min_price is not None and original_price < self.min_price:
            return Decimal('0')

        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return Decimal('0')

        if self.user_usage_limit is not None and user:
            user_used_count = Reservation.objects.filter(
                discount=self,
                user=user,
                status='confirmed'
            ).count()
            if user_used_count >= self.user_usage_limit:
                return Decimal('0')

        if self.discount_type == 'percentage':
            discount_amount = (original_price * self.amount) / Decimal('100')
        else:  # fixed
            discount_amount = self.amount

        if self.max_discount is not None:
            discount_amount = min(discount_amount, self.max_discount)

        return discount_amount

    def is_expired(self):
        """بررسی منقضی شدن تخفیف"""
        return timezone.now().date() > self.end_date

    def get_jalali_start_date(self):
        return jdatetime.date.fromgregorian(date=self.start_date).strftime("%Y/%m/%d")

    def get_jalali_end_date(self):
        return jdatetime.date.fromgregorian(date=self.end_date).strftime("%Y/%m/%d")

    class Meta:
        verbose_name = _("تخفیف")
        verbose_name_plural = _("تخفیف‌ها")
        ordering = ['-created_at']


class ReservationPackage(models.Model):
    """
    پکیج‌های رزرو (مانند اشتراک‌های ماهانه یا فصلی).
    از ai_models.py
    """
    name = models.CharField(max_length=100, verbose_name=_("نام پکیج"))
    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='packages',
                                 verbose_name=_("سالن"))
    duration_months = models.IntegerField(_("مدت پکیج (ماه)"), validators=[MinValueValidator(1)])
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name=_("درصد تخفیف پکیج"),
        # validators=[MinValueValidator(Decimal('0')), models.MaxValueValidator(Decimal('100'))]
    )
    min_sessions_per_month = models.IntegerField(
        default=4,
        verbose_name=_("حداقل تعداد سانس در ماه"),
        help_text=_("برای اعمال تخفیف پکیج، حداقل تعداد رزرو ماهانه.")
    )
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.duration_months} ماه ({self.discount_percentage}% تخفیف)"

    class Meta:
        verbose_name = _("پکیج رزرو")
        verbose_name_plural = _("پکیج‌های رزرو")
        ordering = ['duration_months']


class RecurringReservation(models.Model):
    """
    رزروهای دوره‌ای/تکرارشونده.
    از ai_models.py
    """
    PAYMENT_FREQUENCY_CHOICES = [
        ('weekly', _('هفتگی')),
        ('monthly', _('ماهانه')),
        ('quarterly', _('سه ماهه')),
        ('yearly', _('سالانه')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_reservations',
                             verbose_name=_("کاربر"))
    session_time = models.ForeignKey(SessionTime, on_delete=models.CASCADE, verbose_name=_("سانس مورد نظر"))
    package = models.ForeignKey(
        ReservationPackage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("پکیج مرتبط (اختیاری)")
    )
    start_date = models.DateField(verbose_name=_("تاریخ شروع دوره"))
    end_date = models.DateField(verbose_name=_("تاریخ پایان دوره"))
    payment_frequency = models.CharField(
        max_length=20,
        choices=PAYMENT_FREQUENCY_CHOICES,
        default='monthly',
        verbose_name=_("دوره پرداخت")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.session_time.session_name} ({self.get_jalali_start_date()} تا {self.get_jalali_end_date()})"

    def get_jalali_start_date(self):
        return jdatetime.date.fromgregorian(date=self.start_date).strftime("%Y/%m/%d")

    def get_jalali_end_date(self):
        return jdatetime.date.fromgregorian(date=self.end_date).strftime("%Y/%m/%d")

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError(_("تاریخ پایان باید بعد از تاریخ شروع باشد."))

        # حداکثر مدت رزرو را محدود کنید (مثلاً 2 سال)
        max_duration_date = self.start_date + timedelta(days=365 * 2)  # 2 سال
        if self.end_date > max_duration_date:
            raise ValidationError(_("مدت رزرو دوره‌ای نمی‌تواند بیش از 2 سال باشد."))

        # اگر پکیج انتخاب شده، مطمئن شوید که برای همین سالن است.
        if self.package and self.package.facility != self.session_time.facility:
            raise ValidationError(_("پکیج انتخابی متعلق به سالن این سانس نیست."))

    def generate_individual_reservations(self):
        """
        رزروهای تکی را برای این دوره تکرارشونده ایجاد می‌کند.
        از ai_models.py با بهبودها
        """
        reservations_created = []
        current_date = self.start_date

        # استفاده از timezone.localdate() برای اطمینان از مقایسه صحیح با تاریخ فعلی
        today = timezone.localdate()

        while current_date <= self.end_date:
            # تبدیل ISO weekday به Persian weekday
            persian_day_of_week = (current_date.weekday() + 2) % 7

            if persian_day_of_week == self.session_time.day_of_week:
                if not Holiday.is_holiday(current_date):
                    # از ایجاد رزرو برای گذشته جلوگیری شود (اگر تاریخ شروع در گذشته است)
                    if current_date >= today:
                        if not self.session_time.is_full(current_date):
                            try:
                                # اطمینان از عدم وجود رزرو تکراری (در سطح فردی)
                                existing_reservation = Reservation.objects.filter(
                                    user=self.user,
                                    session_time=self.session_time,
                                    date=current_date,
                                    status__in=['pending', 'confirmed']
                                ).first()

                                if not existing_reservation:
                                    # استفاده از transaction.atomic برای اطمینان از یکپارچگی
                                    with transaction.atomic():
                                        # مبلغ تخفیف پکیج در اینجا به صورت اولیه محاسبه می‌شود
                                        # و در متد calculate_prices در Reservation نهایی خواهد شد.
                                        reservation = Reservation.objects.create(
                                            user=self.user,
                                            session_time=self.session_time,
                                            date=current_date,
                                            recurring_reservation=self,
                                            status='pending',
                                            # نیازی به calculate_prices اینجا نیست، در save رزرو انجام می‌شود
                                        )
                                        reservations_created.append(reservation)
                                else:
                                    print(f"Skipping reservation for {current_date} - already exists for user/session.")
                            except ValidationError as e:
                                print(f"Validation error creating reservation for {current_date}: {e.message}")
                            except Exception as e:
                                print(f"Error creating reservation for {current_date}: {str(e)}")
                        else:
                            print(f"Skipping reservation for {current_date} - session is full.")
                    else:
                        print(f"Skipping reservation for {current_date} - date is in the past.")
                else:
                    print(f"Skipping reservation for {current_date} - it's a holiday.")
            current_date += timedelta(days=1)

        return reservations_created

    def get_total_sessions(self):
        """تعداد کل سانس‌های (قابل رزرو) در این دوره"""
        count = 0
        current_date = self.start_date
        while current_date <= self.end_date:
            persian_day_of_week = (current_date.weekday() + 2) % 7
            if persian_day_of_week == self.session_time.day_of_week:
                if not Holiday.is_holiday(current_date):
                    count += 1
            current_date += timedelta(days=1)
        return count

    class Meta:
        verbose_name = _("رزرو دوره‌ای")
        verbose_name_plural = _("رزروهای دوره‌ای")
        ordering = ['-created_at']


class Reservation(models.Model):
    """
    مدلی برای رزروهای تکی.
    ترکیبی از هر دو با منطق بهبود یافته قیمت‌گذاری و مدیریت تخفیف و Unique Together.
    """
    STATUS_CHOICES = [
        ('pending', _('در انتظار پرداخت')),
        ('confirmed', _('تایید شده')),
        ('cancelled', _('لغو شده')),
        ('completed', _('انجام شده')),
        ('expired', _('منقضی شده (پرداخت نشده)')),  # اضافه شدن وضعیت جدید
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations', verbose_name=_("کاربر"))
    session_time = models.ForeignKey(SessionTime, on_delete=models.CASCADE, related_name='reservations',
                                     verbose_name=_("سانس"))
    date = models.DateField(verbose_name=_("تاریخ رزرو"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_("وضعیت"))

    # ارتباط با رزرو دوره‌ای (از ai_models.py)
    recurring_reservation = models.ForeignKey(
        RecurringReservation,
        on_delete=models.SET_NULL,  # SET_NULL بهتر است تا با حذف رزرو دوره‌ای، رزروهای تکی حذف نشوند
        null=True,
        blank=True,
        related_name='individual_reservations',
        verbose_name=_("رزرو دوره‌ای مرتبط")
    )

    original_price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name=_("قیمت اصلی سانس"))
    # فیلد calculated_price حذف شد چون redundant بود
    discount = models.ForeignKey(
        Discount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations',
        verbose_name=_("تخفیف اعمال شده")
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        verbose_name=_("مبلغ تخفیف اعمال شده")
    )
    final_price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name=_("قیمت نهایی پرداختنی"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, verbose_name=_("یادداشت"))
    cancellation_reason = models.TextField(blank=True, verbose_name=_("دلیل لغو"))
    cancellation_date = models.DateTimeField(null=True, blank=True, verbose_name=_("تاریخ لغو"))

    def clean(self):
        # بررسی تاریخ گذشته
        if self.date < timezone.now().date():
            raise ValidationError(_("تاریخ رزرو نمی‌تواند در گذشته باشد."))

        # محدودیت رزرو بیش از یک سال آینده
        max_future_date = timezone.now().date() + timedelta(days=365)
        if self.date > max_future_date:
            raise ValidationError(_("رزرو بیش از یک سال آینده امکان‌پذیر نیست."))

        # بررسی تعطیل بودن روز
        if Holiday.is_holiday(self.date):
            raise ValidationError(_("این روز تعطیل رسمی است و امکان رزرو وجود ندارد."))

        # بررسی ظرفیت (فقط برای رزروهای جدید یا در حال تغییر وضعیت به confirmed/pending)
        if self._state.adding or self.status in ['pending', 'confirmed']:
            if self.session_time.is_full(self.date) and not (
                    self._state.adding and self.pk):  # اگر در حال اضافه شدن است و pk دارد (یعنی قبلا ایجاد شده بود)
                # اگر رزرو برای خود این شی نیست، و ظرفیت پر است، خطا بده.
                # این شرط برای جلوگیری از خطای "ظرفیت تکمیل است" هنگام ویرایش یک رزرو موجود است.
                if self.session_time.get_remaining_capacity(self.date) == 0 and \
                        not (self.pk and Reservation.objects.filter(pk=self.pk, date=self.date,
                                                                    session_time=self.session_time).exists()):
                    raise ValidationError(_("ظرفیت این سانس تکمیل است."))

        # بررسی رزرو تکراری برای کاربر در همان سانس و تاریخ
        # از ai_models.py
        existing = Reservation.objects.filter(
            user=self.user,
            session_time=self.session_time,
            date=self.date,
            status__in=['confirmed', 'pending']
        ).exclude(pk=self.pk)  # خود شی را از بررسی مستثنی می‌کند تا هنگام ویرایش خطا ندهد.

        if existing.exists():
            raise ValidationError(_("شما قبلاً این سانس را در این تاریخ رزرو کرده‌اید."))

        # بررسی مطابقت روز هفته
        # ISO: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        # Persian: Sat=0, Sun=1, Mon=2, Tue=3, Wed=4, Thu=5, Fri=6
        persian_day_of_week_of_date = (self.date.weekday() + 2) % 7
        if persian_day_of_week_of_date != self.session_time.day_of_week:
            raise ValidationError(
                _("این سانس در این روز هفته برگزار نمی‌شود. روز انتخاب شده با روز تعریف شده برای سانس همخوانی ندارد."))

    def calculate_prices(self):
        """
        محاسبه قیمت‌های رزرو شامل قیمت اصلی سانس، تخفیف‌ها و قیمت نهایی.
        """
        self.original_price = self.session_time.get_price_for_date(self.date)

        # اعمال تخفیف پکیج اگر رزرو بخشی از یک رزرو دوره‌ای با پکیج باشد
        if self.recurring_reservation and self.recurring_reservation.package:
            package_discount_percent = self.recurring_reservation.package.discount_percentage
            self.discount_amount = (self.original_price * package_discount_percent) / Decimal('100')
            self.discount = None  # برای اطمینان که همزمان تخفیف پکیج و تخفیف کد اعمال نشود
        elif self.discount:
            # اگر تخفیف دستی (کد تخفیف یا تخفیف مستقیم) اعمال شده باشد
            # اطمینان از این که تخفیف هنوز فعال است و شرایط آن برقرار است.
            # اگر این رزرو برای اولین بار ذخیره می شود، user را برای calculate_discount_amount بفرستید.
            # اگر در حال آپدیت است، user مشخص است.
            self.discount_amount = self.discount.calculate_discount_amount(self.original_price, user=self.user)
            # اگر تخفیف اعمال نشد (به دلیل محدودیت‌ها)، فیلد discount را خالی کنید
            if self.discount_amount == Decimal('0'):
                self.discount = None

        else:
            self.discount_amount = Decimal('0')

        self.final_price = self.original_price - self.discount_amount
        self.final_price = max(self.final_price, Decimal('0'))  # اطمینان از عدم وجود قیمت منفی

    def save(self, *args, **kwargs):
        # اگر شی جدید است یا فیلدهای اصلی تغییر کرده‌اند، قیمت‌ها را دوباره محاسبه کنید.
        # این به جلوگیری از خطای زیاد محاسبه کمک می‌کند.
        if self._state.adding or (
                self.pk and (
                self.session_time_id != self.__original_session_time_id or
                self.date != self.__original_date or
                self.discount_id != self.__original_discount_id or
                self.recurring_reservation_id != self.__original_recurring_reservation_id
        )
        ):
            self.calculate_prices()

        # اگر وضعیت به لغو شده تغییر کرده است
        if self.status == 'cancelled' and not self.cancellation_date:
            self.cancellation_date = timezone.now()
            # اگر رزرو لغو شد و قبلاً تخفیف اعمال شده بود، used_count را کم کنید.
            # این کار باید در یک ترنزکشن انجام شود تا از Race Condition جلوگیری شود.
            if self.discount and self.discount.used_count > 0:
                with transaction.atomic():
                    discount_to_update = Discount.objects.select_for_update().get(pk=self.discount.pk)
                    discount_to_update.used_count -= 1
                    discount_to_update.save()

        # افزایش used_count تخفیف فقط زمانی که رزرو برای اولین بار confirmed شود
        if self.discount and self.status == 'confirmed' and (
                self._state.adding or self.__original_status != 'confirmed'
        ):
            with transaction.atomic():
                discount_to_update = Discount.objects.select_for_update().get(pk=self.discount.pk)
                # بررسی نهایی محدودیت قبل از افزایش
                if discount_to_update.usage_limit is None or discount_to_update.used_count < discount_to_update.usage_limit:
                    if discount_to_update.user_usage_limit is None or \
                            Reservation.objects.filter(discount=self.discount, user=self.user,
                                                       status='confirmed').count() < discount_to_update.user_usage_limit:
                        discount_to_update.used_count += 1
                        discount_to_update.save()
                    else:
                        raise ValidationError(_("این تخفیف به حداکثر دفعات مجاز برای شما رسیده است."))
                else:
                    raise ValidationError(_("محدودیت استفاده از این تخفیف به پایان رسیده است."))

        super().save(*args, **kwargs)

        # ذخیره وضعیت و FK های اصلی برای مقایسه در دفعات بعدی save
        self.__original_status = self.status
        self.__original_session_time_id = self.session_time_id
        self.__original_date = self.date
        self.__original_discount_id = self.discount_id
        self.__original_recurring_reservation_id = self.recurring_reservation_id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ذخیره وضعیت اصلی برای مقایسه در متد save
        self.__original_status = self.status
        self.__original_session_time_id = self.session_time_id
        self.__original_date = self.date
        self.__original_discount_id = self.discount_id
        self.__original_recurring_reservation_id = self.recurring_reservation_id

    def cancel(self, reason=""):
        """لغو رزرو"""
        if not self.can_cancel:
            raise ValidationError(_("این رزرو قابل لغو نیست."))

        self.status = 'cancelled'
        self.cancellation_reason = reason
        self.cancellation_date = timezone.now()  # اطمینان از ثبت تاریخ لغو
        self.save()  # save() خودش handles کاهش used_count را

    def get_jalali_date(self):
        return jdatetime.date.fromgregorian(date=self.date).strftime("%Y/%m/%d")

    @property
    def is_past(self):
        """بررسی اینکه آیا تاریخ و زمان رزرو در گذشته است."""
        reservation_datetime = datetime.combine(self.date, self.session_time.start_time)
        return timezone.now() > timezone.make_aware(reservation_datetime)

    @property
    def can_cancel(self):
        """بررسی اینکه آیا رزرو قابل لغو است."""
        if self.status not in ['pending', 'confirmed']:
            return False

        # فقط تا 24 ساعت قبل از زمان شروع سانس امکان لغو وجود دارد.
        reservation_datetime = datetime.combine(self.date, self.session_time.start_time)
        # زمان فعلی باید حداقل 24 ساعت قبل از زمان رزرو باشد.
        return timezone.now() <= timezone.make_aware(reservation_datetime - timedelta(hours=24))

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.session_time.facility.name} - {self.session_time.session_name} ({self.get_jalali_date()})"

    class Meta:
        verbose_name = _("رزرو")
        verbose_name_plural = _("رزروها")
        ordering = ['-date', 'session_time__start_time']
        # هر کاربر می‌تواند یک سانس خاص را در یک تاریخ خاص فقط یکبار رزرو کند.
        unique_together = ['user', 'session_time', 'date']


class Review(models.Model):
    """
    مدلی برای نظرات و امتیازدهی به رزروها.
    ترکیبی از هر دو با بهبود verbose_name.
    """
    RATING_CHOICES = [
        (1, _('۱ ستاره ⭐')),
        (2, _('۲ ستاره ⭐⭐')),
        (3, _('۳ ستاره ⭐⭐⭐')),
        (4, _('۴ ستاره ⭐⭐⭐⭐')),
        (5, _('۵ ستاره ⭐⭐⭐⭐⭐')),
    ]

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name=_("رزرو مرتبط"),
        help_text=_("هر رزرو فقط می‌تواند یک نظر داشته باشد.")
    )
    rating = models.IntegerField(
        _("امتیاز"),
        choices=RATING_CHOICES,
        # validators=[MinValueValidator(1), models.MaxValueValidator(5)]
    )
    comment = models.TextField(
        _("نظر کاربر"),
        blank=True,
        null=True  # اجازه خالی بودن نظر
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(
        _("تایید شده توسط مدیر"),
        default=False,
        help_text=_("آیا این نظر در سایت نمایش داده شود؟")
    )

    def clean(self):
        if self.reservation.status != 'completed':
            raise ValidationError(_("فقط برای رزروهای 'انجام شده' می‌توانید نظر ثبت کنید."))

        if not self.reservation.is_past:
            # اگر زمان سانس هنوز نرسیده باشد، نمی‌توان نظر ثبت کرد.
            # اگر می خواهید اجازه دهید در همان روز بعد از پایان سانس نظر ثبت شود،
            # باید is_past را بر اساس تاریخ و زمان (نه فقط تاریخ) چک کنید.
            raise ValidationError(_("فقط پس از اتمام سانس می‌توانید نظر ثبت کنید."))

        # اطمینان از عدم وجود نظر قبلی (OneToOneField این را تا حدودی تضمین می‌کند اما برای clean مفید است)
        if self._state.adding and Review.objects.filter(reservation=self.reservation).exists():
            raise ValidationError(_("برای این رزرو قبلاً نظری ثبت شده است."))

    def __str__(self):
        return f"{self.reservation.user.get_full_name()} - {self.reservation.session_time.facility.name} - {self.get_rating_display()}"

    class Meta:
        verbose_name = _("نظر")
        verbose_name_plural = _("نظرات")
        ordering = ['-created_at']