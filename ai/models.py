from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
import jdatetime
from decimal import Decimal

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

    def get_average_rating(self):
        """محاسبه میانگین امتیاز سالن"""
        reviews = Review.objects.filter(
            reservation__session_time__facility=self,
            is_approved=True
        )
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return 0

    class Meta:
        verbose_name = "سالن ورزشی"
        verbose_name_plural = "سالن های ورزشی"
        ordering = ['name']

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
        ('dynamic', 'قیمت پویا'),
    ]

    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='session_times', verbose_name="سالن")
    session_name = models.CharField(max_length=100, verbose_name="نام سانس")
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK, verbose_name="روز هفته")
    start_time = models.TimeField(verbose_name="زمان شروع")
    end_time = models.TimeField(verbose_name="زمان پایان")
    capacity = models.IntegerField(verbose_name="ظرفیت سانس", help_text="تعداد نفرات قابل رزرو در هر سانس")
    
    # فیلدهای قیمت‌گذاری
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
    base_weekday_price = models.DecimalField(
        max_digits=10, 
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="قیمت پایه روزهای عادی"
    )
    base_weekend_price = models.DecimalField(
        max_digits=10, 
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="قیمت پایه آخر هفته"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.facility.name} - {self.session_name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("زمان شروع باید قبل از زمان پایان باشد")
        
        # بررسی قیمت‌گذاری
        if self.price_type == 'fixed' and not self.fixed_price:
            raise ValidationError("برای قیمت‌گذاری ثابت، باید قیمت ثابت تعیین شود")
        elif self.price_type == 'hourly' and not self.hourly_price:
            raise ValidationError("برای قیمت‌گذاری ساعتی، باید قیمت ساعتی تعیین شود")
        elif self.price_type == 'dynamic':
            if not self.base_weekday_price or not self.base_weekend_price:
                raise ValidationError("برای قیمت‌گذاری پویا، باید قیمت پایه روزهای عادی و آخر هفته تعیین شود")
        
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
        """محاسبه قیمت پایه سانس"""
        if self.price_type == 'fixed':
            return self.fixed_price or Decimal('0')
        elif self.price_type == 'hourly':
            duration_hours = self.get_duration_hours()
            hourly_rate = self.hourly_price or self.facility.hourly_price
            return hourly_rate * duration_hours
        else:  # dynamic
            return self.base_weekday_price or Decimal('0')

    def get_price_for_date(self, date):
        """محاسبه قیمت برای یک تاریخ خاص با در نظر گرفتن قوانین قیمت‌گذاری"""
        base_price = self.get_price()
        
        # برای قیمت‌گذاری پویا
        if self.price_type == 'dynamic':
            if date.weekday() in [4, 5]:  # پنجشنبه و جمعه
                base_price = self.base_weekend_price
            else:
                base_price = self.base_weekday_price
        
        # اعمال قوانین قیمت‌گذاری
        applicable_rules = self.facility.pricing_rules.filter(
            is_active=True
        ).order_by('-priority')
        
        final_price = base_price
        for rule in applicable_rules:
            if rule.is_applicable(date, self):
                final_price = rule.apply_to_price(final_price)
        
        return max(final_price, 0)

    def get_duration_hours(self):
        """محاسبه مدت زمان سانس به ساعت"""
        duration = datetime.combine(datetime.today(), self.end_time) - datetime.combine(datetime.today(), self.start_time)
        return Decimal(duration.seconds) / Decimal('3600')

    def get_duration_minutes(self):
        """محاسبه مدت زمان سانس به دقیقه"""
        duration = datetime.combine(datetime.today(), self.end_time) - datetime.combine(datetime.today(), self.start_time)
        return duration.seconds // 60

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

class PricingRule(models.Model):
    """قوانین قیمت‌گذاری پویا"""
    RULE_TYPE_CHOICES = [
        ('time_of_day', 'ساعت روز'),
        ('day_of_week', 'روز هفته'),
        ('date_range', 'بازه تاریخی'),
        ('special_day', 'روزهای خاص'),
        ('peak_hours', 'ساعات شلوغ'),
    ]

    ADJUSTMENT_TYPE_CHOICES = [
        ('percentage_increase', 'افزایش درصدی'),
        ('percentage_decrease', 'کاهش درصدی'),
        ('fixed_price', 'قیمت ثابت'),
        ('fixed_increase', 'افزایش ثابت'),
        ('fixed_decrease', 'کاهش ثابت'),
    ]

    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='pricing_rules', verbose_name="سالن")
    name = models.CharField(max_length=100, verbose_name="نام قانون")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES, verbose_name="نوع قانون")
    
    # برای قوانین ساعتی
    start_time = models.TimeField(null=True, blank=True, verbose_name="ساعت شروع")
    end_time = models.TimeField(null=True, blank=True, verbose_name="ساعت پایان")
    
    # برای قوانین روز هفته
    days_of_week = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="روزهای هفته",
        help_text="شماره روزها با کاما جدا شود. مثال: 0,1,2 برای شنبه،یکشنبه،دوشنبه"
    )
    
    # برای قوانین تاریخی
    start_date = models.DateField(null=True, blank=True, verbose_name="تاریخ شروع")
    end_date = models.DateField(null=True, blank=True, verbose_name="تاریخ پایان")
    
    # تنظیمات قیمت
    price_adjustment_type = models.CharField(
        max_length=20,
        choices=ADJUSTMENT_TYPE_CHOICES,
        verbose_name="نوع تنظیم قیمت"
    )
    adjustment_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مقدار تنظیم")
    
    priority = models.IntegerField(default=0, verbose_name="اولویت", help_text="قوانین با اولویت بالاتر زودتر اعمال می‌شوند")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.facility.name}"

    def is_applicable(self, date, session_time):
        """بررسی اینکه آیا قانون برای تاریخ و سانس مشخص قابل اعمال است"""
        if self.rule_type == 'day_of_week':
            return str(date.weekday()) in self.days_of_week.split(',')
        elif self.rule_type == 'date_range':
            return self.start_date <= date <= self.end_date
        elif self.rule_type == 'time_of_day':
            return self.start_time <= session_time.start_time <= self.end_time
        elif self.rule_type == 'peak_hours':
            # ساعات شلوغ معمولاً عصرها
            return session_time.start_time.hour >= 17 and session_time.start_time.hour <= 21
        return False

    def apply_to_price(self, base_price):
        """اعمال قانون روی قیمت پایه"""
        if self.price_adjustment_type == 'percentage_increase':
            return base_price * (1 + self.adjustment_value / 100)
        elif self.price_adjustment_type == 'percentage_decrease':
            return base_price * (1 - self.adjustment_value / 100)
        elif self.price_adjustment_type == 'fixed_price':
            return self.adjustment_value
        elif self.price_adjustment_type == 'fixed_increase':
            return base_price + self.adjustment_value
        elif self.price_adjustment_type == 'fixed_decrease':
            return base_price - self.adjustment_value
        return base_price

    class Meta:
        verbose_name = "قانون قیمت‌گذاری"
        verbose_name_plural = "قوانین قیمت‌گذاری"
        ordering = ['-priority', 'name']

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

    def save(self, *args, **kwargs):
        # اگر تعطیلی تکرارشونده است، ماه و روز شمسی را ذخیره کن
        if self.is_recurring:
            jalali_date = jdatetime.date.fromgregorian(date=self.date)
            self.jalali_month = jalali_date.month
            self.jalali_day = jalali_date.day
        super().save(*args, **kwargs)

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

    @classmethod
    def get_holidays_in_range(cls, start_date, end_date):
        """دریافت تمام تعطیلات در یک بازه"""
        holidays = []
        
        # تعطیلات ثابت
        fixed_holidays = cls.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        holidays.extend(list(fixed_holidays))
        
        # تعطیلات تکرارشونده
        recurring_holidays = cls.objects.filter(is_recurring=True)
        
        current_date = start_date
        while current_date <= end_date:
            jalali_date = jdatetime.date.fromgregorian(date=current_date)
            for holiday in recurring_holidays:
                if (holiday.jalali_month == jalali_date.month and 
                    holiday.jalali_day == jalali_date.day):
                    holidays.append({
                        'date': current_date,
                        'description': holiday.description
                    })
            current_date += timedelta(days=1)
        
        return holidays

    class Meta:
        verbose_name = "تعطیلی"
        verbose_name_plural = "تعطیلات"
        ordering = ['date']

class ReservationPackage(models.Model):
    """پکیج‌های رزرو برای تشویق رزروهای طولانی‌مدت"""
    name = models.CharField(max_length=100, verbose_name="نام پکیج")
    facility = models.ForeignKey(SportFacility, on_delete=models.CASCADE, related_name='packages', verbose_name="سالن")
    duration_months = models.IntegerField(verbose_name="مدت (ماه)")
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        verbose_name="درصد تخفیف"
    )
    min_sessions_per_month = models.IntegerField(
        default=4,
        verbose_name="حداقل سانس در ماه"
    )
    description = models.TextField(blank=True, verbose_name="توضیحات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.duration_months} ماه ({self.discount_percentage}% تخفیف)"

    class Meta:
        verbose_name = "پکیج رزرو"
        verbose_name_plural = "پکیج‌های رزرو"
        ordering = ['duration_months']

class RecurringReservation(models.Model):
    """رزروهای دوره‌ای/یکساله"""
    PAYMENT_FREQUENCY_CHOICES = [
        ('weekly', 'هفتگی'),
        ('monthly', 'ماهانه'),
        ('quarterly', 'سه ماهه'),
        ('yearly', 'سالانه'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_reservations', verbose_name="کاربر")
    session_time = models.ForeignKey(SessionTime, on_delete=models.CASCADE, verbose_name="سانس")
    package = models.ForeignKey(
        ReservationPackage, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="پکیج"
    )
    start_date = models.DateField(verbose_name="تاریخ شروع")
    end_date = models.DateField(verbose_name="تاریخ پایان")
    payment_frequency = models.CharField(
        max_length=20,
        choices=PAYMENT_FREQUENCY_CHOICES,
        default='monthly',
        verbose_name="دوره پرداخت"
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.session_time} ({self.get_jalali_start_date()} تا {self.get_jalali_end_date()})"

    def get_jalali_start_date(self):
        return jdatetime.date.fromgregorian(date=self.start_date).strftime("%Y/%m/%d")

    def get_jalali_end_date(self):
        return jdatetime.date.fromgregorian(date=self.end_date).strftime("%Y/%m/%d")

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError("تاریخ پایان باید بعد از تاریخ شروع باشد")
        
        # حداکثر یک سال
        max_date = self.start_date + timedelta(days=365)
        if self.end_date > max_date:
            raise ValidationError("مدت رزرو نمی‌تواند بیش از یک سال باشد")

    def generate_reservations(self):
        """تولید رزروهای مجزا برای کل دوره"""
        current_date = self.start_date
        reservations = []
        
        while current_date <= self.end_date:
            # چک کردن روز هفته
            if current_date.weekday() == self.session_time.day_of_week:
                # چک کردن تعطیلی
                if not Holiday.is_holiday(current_date):
                    # چک کردن ظرفیت
                    if not self.session_time.is_full(current_date):
                        try:
                            reservation = Reservation.objects.create(
                                user=self.user,
                                session_time=self.session_time,
                                date=current_date,
                                recurring_reservation=self,
                                status='pending'
                            )
                            reservations.append(reservation)
                        except Exception as e:
                            print(f"خطا در ایجاد رزرو برای تاریخ {current_date}: {str(e)}")
            
            current_date += timedelta(days=1)
        
        return reservations

    def get_total_sessions(self):
        """محاسبه تعداد کل سانس‌ها (بدون تعطیلات)"""
        count = 0
        current_date = self.start_date
        
        while current_date <= self.end_date:
            if current_date.weekday() == self.session_time.day_of_week:
                if not Holiday.is_holiday(current_date):
                    count += 1
            current_date += timedelta(days=1)
        
        return count

    def get_total_price(self):
        """محاسبه قیمت کل با احتساب تخفیف پکیج"""
        total = 0
        for reservation in self.individual_reservations.all():
            total += reservation.final_price
        return total

    class Meta:
        verbose_name = "رزرو دوره‌ای"
        verbose_name_plural = "رزروهای دوره‌ای"
        ordering = ['-created_at']

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

    def __str__(self):
        return f"{self.name} ({self.get_discount_type_display()} - {self.amount})"

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

    def get_jalali_start_date(self):
        return jdatetime.date.fromgregorian(date=self.start_date).strftime("%Y/%m/%d")

    def get_jalali_end_date(self):
        return jdatetime.date.fromgregorian(date=self.end_date).strftime("%Y/%m/%d")

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
    session_time = models.ForeignKey(SessionTime, on_delete=models.CASCADE, related_name='reservations', verbose_name="سانس")
    date = models.DateField(verbose_name="تاریخ")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    
    # ارتباط با رزرو دوره‌ای
    recurring_reservation = models.ForeignKey(
        'RecurringReservation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='individual_reservations',
        verbose_name="رزرو دوره‌ای"
    )
    
   # قیمت‌ها
    original_price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="قیمت اصلی")
    calculated_price = models.DecimalField(
        max_digits=10, 
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="قیمت محاسبه شده"
    )
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
    
    # سایر فیلدها
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
        existing = Reservation.objects.filter(
            user=self.user,
            session_time=self.session_time,
            date=self.date,
            status__in=['confirmed', 'pending']
        ).exclude(pk=self.pk)
        
        if existing.exists():
            raise ValidationError("شما قبلاً این سانس را رزرو کرده‌اید")

        # Check if the day of week matches
        if self.date.weekday() != self.session_time.day_of_week:
            raise ValidationError("این سانس در این روز هفته برگزار نمی‌شود")

    def calculate_prices(self):
        """محاسبه قیمت‌های رزرو"""
        # استفاده از قیمت محاسبه شده برای تاریخ خاص
        self.original_price = self.session_time.get_price_for_date(self.date)
        self.calculated_price = self.original_price
        
        # اعمال تخفیف پکیج اگر رزرو دوره‌ای است
        if self.recurring_reservation and self.recurring_reservation.package:
            package_discount = (self.original_price * self.recurring_reservation.package.discount_percentage) / 100
            self.discount_amount = package_discount
        elif self.discount:
            self.discount_amount = self.discount.calculate_discount(self.original_price)
        else:
            self.discount_amount = 0
            
        self.final_price = self.original_price - self.discount_amount

    def save(self, *args, **kwargs):
        self.calculate_prices()
        
        # اگر وضعیت به لغو شده تغییر کرده است
        if self.status == 'cancelled' and not self.cancellation_date:
            self.cancellation_date = timezone.now()
            
        # اگر تخفیف دارد و تایید شده، تعداد استفاده را افزایش دهید
        if self.discount and self.status == 'confirmed' and not self.pk:
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
        unique_together = ['user', 'session_time', 'date']

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


