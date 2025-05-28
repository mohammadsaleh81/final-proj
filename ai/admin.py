from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from django.urls import reverse
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.contrib.filters.admin import RangeDateFilter, DropdownFilter, AutocompleteSelectFilter, AutocompleteSelectMultipleFilter, TextFilter, ChoicesRadioFilter, RelatedDropdownFilter

import jdatetime
from datetime import datetime, timedelta

from .models import (
    SportFacility, SessionTime, PricingRule, Holiday, 
    ReservationPackage, RecurringReservation, Discount, 
    Reservation, Review
)

# Inline Classes
class SessionTimeInline(TabularInline):
    model = SessionTime
    extra = 1
    fields = ['session_name', 'day_of_week', 'start_time', 'end_time', 'capacity', 'price_type', 'is_active']
    readonly_fields = ['get_total_reservations']
    
    @display(description="تعداد رزرو")
    def get_total_reservations(self, obj):
        if obj.pk:
            count = obj.get_total_reservations()
            return format_html('<span class="badge badge-info">{}</span>', count)
        return "-"

class PricingRuleInline(TabularInline):
    model = PricingRule
    extra = 0
    fields = ['name', 'rule_type', 'price_adjustment_type', 'adjustment_value', 'priority', 'is_active']

class ReservationPackageInline(TabularInline):
    model = ReservationPackage
    extra = 0
    fields = ['name', 'duration_months', 'discount_percentage', 'min_sessions_per_month', 'is_active']

# Main Admin Classes
@admin.register(SportFacility)
class SportFacilityAdmin(ModelAdmin):
    list_display = ['name', 'display_capacity', 'display_hourly_price', 'display_rating', 'display_status', 'manager']
    list_filter = [
        'is_active',
        ('manager', RelatedDropdownFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ['name', 'address', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'display_statistics']
    inlines = [SessionTimeInline, PricingRuleInline, ReservationPackageInline]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'description', 'manager', 'is_active'),
            'classes': ['tab']
        }),
        ('اطلاعات ظرفیت و قیمت', {
            'fields': ('capacity', 'hourly_price'),
            'classes': ['tab']
        }),
        ('اطلاعات تماس', {
            'fields': ('address', 'phone'),
            'classes': ['tab']
        }),
        ('امکانات', {
            'fields': ('facilities',),
            'classes': ['tab']
        }),
        ('آمار', {
            'fields': ('display_statistics',),
            'classes': ['tab']
        }),
    )
    
    @display(description="ظرفیت", ordering="capacity")
    def display_capacity(self, obj):
        return format_html(
            '<span class="badge badge-primary">{} نفر</span>',
            obj.capacity
        )
    
    @display(description="قیمت ساعتی", ordering="hourly_price")
    def display_hourly_price(self, obj):
        return format_html(
            '<span class="badge badge-success">{:,} تومان</span>',
            int(obj.hourly_price)
        )
    
    @display(description="امتیاز")
    def display_rating(self, obj):
        rating = obj.get_average_rating()
        if rating:
            stars = '⭐' * int(rating)
            return format_html(
                '<span title="{:.1f}">{}</span>',
                rating, stars
            )
        return "-"
    
    @display(description="وضعیت", boolean=True)
    def display_status(self, obj):
        return obj.is_active
    
    @display(description="آمار کلی")
    def display_statistics(self, obj):
        if not obj.pk:
            return "-"
        
        stats = Reservation.objects.filter(
            session_time__facility=obj
        ).aggregate(
            total=Count('id'),
            confirmed=Count('id', filter=Q(status='confirmed')),
            revenue=Sum('final_price', filter=Q(status='confirmed'))
        )
        
        return format_html(
            '''
            <div class="statistics-box">
                <div class="stat-item">
                    <strong>کل رزروها:</strong> <span class="badge badge-info">{}</span>
                </div>
                <div class="stat-item">
                    <strong>رزروهای تایید شده:</strong> <span class="badge badge-success">{}</span>
                </div>
                <div class="stat-item">
                    <strong>درآمد کل:</strong> <span class="badge badge-warning">{:,} تومان</span>
                </div>
            </div>
            ''',
            stats['total'] or 0,
            stats['confirmed'] or 0,
            int(stats['revenue'] or 0)
        )
    
    @action(description="غیرفعال کردن سالن‌های انتخابی")
    def deactivate_facilities(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} سالن غیرفعال شد.", level="success")
    
    @action(description="فعال کردن سالن‌های انتخابی")
    def activate_facilities(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} سالن فعال شد.", level="success")

@admin.register(SessionTime)
class SessionTimeAdmin(ModelAdmin):
    list_display = ['facility', 'session_name', 'display_day', 'display_time', 'display_capacity_status', 'display_price', 'is_active']
    list_filter = [
        'is_active',
        ('facility', RelatedDropdownFilter),
        'day_of_week',
        'price_type',
    ]
    search_fields = ['session_name', 'facility__name']
    readonly_fields = ['created_at', 'updated_at', 'display_price_details']
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('facility', 'session_name', 'day_of_week', 'is_active'),
        }),
        ('زمان‌بندی', {
            'fields': ('start_time', 'end_time'),
        }),
        ('ظرفیت', {
            'fields': ('capacity',),
        }),
        ('قیمت‌گذاری', {
            'fields': ('price_type', 'fixed_price', 'hourly_price', 'base_weekday_price', 'base_weekend_price', 'display_price_details'),
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    
    @display(description="روز هفته", ordering="day_of_week")
    def display_day(self, obj):
        return obj.get_day_of_week_display()
    
    @display(description="زمان")
    def display_time(self, obj):
        return format_html(
            '<span class="badge badge-info">{} - {}</span>',
            obj.start_time.strftime('%H:%M'),
            obj.end_time.strftime('%H:%M')
        )
    
    @display(description="وضعیت ظرفیت")
    def display_capacity_status(self, obj):
        today = timezone.now().date()
        remaining = obj.get_remaining_capacity(today)
        percentage = (remaining / obj.capacity) * 100 if obj.capacity > 0 else 0
        
        if percentage > 70:
            badge_class = "badge-success"
        elif percentage > 30:
            badge_class = "badge-warning"
        else:
            badge_class = "badge-danger"
        
        return format_html(
            '<span class="badge {}">{}/{} ({:.0f}%)</span>',
            badge_class, remaining, obj.capacity, percentage
        )
    
    @display(description="قیمت")
    def display_price(self, obj):
        price = obj.get_price()
        return format_html(
            '<span class="badge badge-success">{:,} تومان</span>',
            int(price)
        )
    
    @display(description="جزئیات قیمت‌گذاری")
    def display_price_details(self, obj):
        if not obj.pk:
            return "-"
        
        if obj.price_type == 'dynamic':
            return format_html(
                '''
                <div class="price-details">
                    <p><strong>قیمت روزهای عادی:</strong> {:,} تومان</p>
                    <p><strong>قیمت آخر هفته:</strong> {:,} تومان</p>
                    <p><strong>مدت زمان:</strong> {} دقیقه</p>
                </div>
                ''',
                int(obj.base_weekday_price or 0),
                int(obj.base_weekend_price or 0),
                obj.get_duration_minutes()
            )
        else:
            return format_html(
                '<div class="price-details"><strong>قیمت:</strong> {:,} تومان</div>',
                int(obj.get_price())
            )

@admin.register(PricingRule)
class PricingRuleAdmin(ModelAdmin):
    list_display = ['name', 'facility', 'rule_type', 'display_adjustment', 'priority', 'is_active']
    list_filter = [
        'is_active',
        ('facility', RelatedDropdownFilter),
        'rule_type',
        'price_adjustment_type',
    ]
    search_fields = ['name', 'facility__name']
    ordering = ['-priority', 'name']
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('facility', 'name', 'description', 'is_active', 'priority'),
        }),
        ('نوع قانون', {
            'fields': ('rule_type',),
        }),
        ('شرایط اعمال', {
            'fields': ('start_time', 'end_time', 'days_of_week', 'start_date', 'end_date'),
            'description': 'بر اساس نوع قانون، فیلدهای مربوطه را پر کنید',
        }),
        ('تنظیمات قیمت', {
            'fields': ('price_adjustment_type', 'adjustment_value'),
        }),
    )
    
    @display(description="تنظیم قیمت")
    def display_adjustment(self, obj):
        if obj.price_adjustment_type in ['percentage_increase', 'percentage_decrease']:
            return format_html(
                '<span class="badge badge-info">{} {}%</span>',
                obj.get_price_adjustment_type_display(),
                obj.adjustment_value
            )
        else:
            return format_html(
                '<span class="badge badge-info">{} {:,} تومان</span>',
                obj.get_price_adjustment_type_display(),
                int(obj.adjustment_value)
            )

@admin.register(Holiday)
class HolidayAdmin(ModelAdmin):
    list_display = ['display_jalali_date', 'description', 'display_type', 'display_recurring_info']
    list_filter = [
        'is_recurring',
        ('date', RangeDateFilter),
    ]
    search_fields = ['description']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('اطلاعات تعطیلی', {
            'fields': ('date', 'description'),
        }),
        ('تنظیمات تکرار', {
            'fields': ('is_recurring',),
            'description': 'برای تعطیلات سالانه مانند عید نوروز این گزینه را فعال کنید',
        }),
    )
    
    @display(description="تاریخ", ordering="date")
    def display_jalali_date(self, obj):
        return format_html(
            '<span class="badge badge-primary">{}</span>',
            obj.get_jalali_date()
        )
    
    @display(description="نوع")
    def display_type(self, obj):
        if obj.is_recurring:
            return format_html('<span class="badge badge-warning">سالانه</span>')
        return format_html('<span class="badge badge-info">یکبار</span>')
    
    @display(description="اطلاعات تکرار")
    def display_recurring_info(self, obj):
        if obj.is_recurring and obj.jalali_month and obj.jalali_day:
            months = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                     'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
            return f"هر سال {obj.jalali_day} {months[obj.jalali_month-1]}"
        return "-"

@admin.register(ReservationPackage)
class ReservationPackageAdmin(ModelAdmin):
    list_display = ['name', 'facility', 'display_duration', 'display_discount', 'min_sessions_per_month', 'is_active']
    list_filter = [
        'is_active',
        ('facility', RelatedDropdownFilter),
        'duration_months',
    ]
    search_fields = ['name', 'facility__name']
    
    @display(description="مدت")
    def display_duration(self, obj):
        return format_html(
            '<span class="badge badge-info">{} ماه</span>',
            obj.duration_months
        )
    
    @display(description="تخفیف")
    def display_discount(self, obj):
        return format_html(
            '<span class="badge badge-success">{}%</span>',
            obj.discount_percentage
        )

@admin.register(RecurringReservation)
class RecurringReservationAdmin(ModelAdmin):
    list_display = ['user', 'session_time', 'display_period', 'display_package', 'payment_frequency', 'is_active']
    list_filter = [
        'is_active',
        'payment_frequency',
        ('user', RelatedDropdownFilter),
        ('session_time__facility', RelatedDropdownFilter),
        ('start_date', RangeDateFilter),
    ]
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'session_time__session_name']
    readonly_fields = ['display_statistics', 'created_at', 'updated_at']
    
    fieldsets = (
        ('اطلاعات کاربر و سانس', {
            'fields': ('user', 'session_time', 'package'),
        }),
        ('دوره زمانی', {
            'fields': ('start_date', 'end_date'),
        }),
        ('تنظیمات', {
            'fields': ('payment_frequency', 'is_active'),
        }),
        ('آمار', {
            'fields': ('display_statistics',),
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    
    @display(description="دوره")
    def display_period(self, obj):
        return format_html(
            '<span class="badge badge-info">{} تا {}</span>',
            obj.get_jalali_start_date(),
            obj.get_jalali_end_date()
        )
    
    @display(description="پکیج")
    def display_package(self, obj):
        if obj.package:
            return format_html(
                '<span class="badge badge-success">{}</span>',
                obj.package.name
            )
        return "-"
    
    @display(description="آمار رزروها")
    def display_statistics(self, obj):
        if not obj.pk:
            return "-"
        
        total_sessions = obj.get_total_sessions()
        generated = obj.individual_reservations.count()
        confirmed = obj.individual_reservations.filter(status='confirmed').count()
        
        return format_html(
            '''
            <div class="statistics-box">
                <p><strong>تعداد کل سانس‌ها:</strong> {}</p>
                <p><strong>رزروهای ایجاد شده:</strong> {}</p>
                <p><strong>رزروهای تایید شده:</strong> {}</p>
            </div>
            ''',
            total_sessions,
            generated,
            confirmed
        )
    
    @action(description="ایجاد رزروها")
    def generate_reservations(self, request, queryset):
        total = 0
        for recurring in queryset:
            reservations = recurring.generate_reservations()
            total += len(reservations)
        self.message_user(request, f"{total} رزرو ایجاد شد.", level="success")

@admin.register(Discount)
class DiscountAdmin(ModelAdmin):
    list_display = ['name', 'display_target', 'display_type_amount', 'display_validity', 'display_usage', 'is_active']
    list_filter = [
        'is_active',
        'discount_type',
        'target_type',
        ('start_date', RangeDateFilter),
        ('end_date', RangeDateFilter),
    ]
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['used_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'description', 'is_active'),
        }),
        ('نوع و مقدار تخفیف', {
            'fields': ('discount_type', 'amount', 'min_price', 'max_discount'),
        }),
        ('هدف تخفیف', {
            'fields': ('target_type', 'facility', 'session_time', 'user', 'code'),
        }),
        ('مدت اعتبار', {
            'fields': ('start_date', 'end_date'),
        }),
        ('محدودیت‌ها', {
            'fields': ('usage_limit', 'used_count'),
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    
    @display(description="هدف")
    def display_target(self, obj):
        if obj.target_type == 'facility' and obj.facility:
            return format_html('<span class="badge badge-info">سالن: {}</span>', obj.facility.name)
        elif obj.target_type == 'session' and obj.session_time:
            return format_html('<span class="badge badge-info">سانس: {}</span>', obj.session_time)
        elif obj.target_type == 'user' and obj.user:
            return format_html('<span class="badge badge-info">کاربر: {}</span>', obj.user.get_full_name())
        elif obj.target_type == 'code':
            return format_html('<span class="badge badge-warning">کد: {}</span>', obj.code)
        return "-"
    
    @display(description="نوع و مقدار")
    def display_type_amount(self, obj):
        if obj.discount_type == 'percentage':
            return format_html('<span class="badge badge-success">{}%</span>', obj.amount)
        else:
            return format_html('<span class="badge badge-success">{:,} تومان</span>', int(obj.amount))
    
    @display(description="اعتبار")
    def display_validity(self, obj):
        if obj.is_expired():
            return format_html('<span class="badge badge-danger">منقضی شده</span>')
        else:
            days_left = (obj.end_date - timezone.now().date()).days
            if days_left <= 7:
                return format_html('<span class="badge badge-warning">{} روز باقی‌مانده</span>', days_left)
            else:
                return format_html('<span class="badge badge-success">تا {}</span>', obj.get_jalali_end_date())
    
    @display(description="استفاده")
    def display_usage(self, obj):
        if obj.usage_limit:
            percentage = (obj.used_count / obj.usage_limit) * 100
            if percentage >= 90:
                badge_class = "badge-danger"
            elif percentage >= 70:
                badge_class = "badge-warning"
            else:
                badge_class = "badge-success"
            
            return format_html(
                '<span class="badge {}">{}/{} ({}%)</span>',
                badge_class, obj.used_count, obj.usage_limit, int(percentage)
            )
        else:
            return format_html('<span class="badge badge-info">{} بار</span>', obj.used_count)

@admin.register(Reservation)
class ReservationAdmin(ModelAdmin):
    list_display = ['display_user', 'display_session', 'display_date', 'display_status', 'display_prices', 'display_actions']
    list_filter = [
        'status',
        ('date', RangeDateFilter),
        ('session_time__facility', RelatedDropdownFilter),
        ('user', RelatedDropdownFilter),
        'recurring_reservation',
    ]
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'session_time__session_name']
    readonly_fields = ['created_at', 'updated_at', 'cancellation_date', 'display_price_breakdown']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('اطلاعات رزرو', {
            'fields': ('user', 'session_time', 'date', 'status'),
        }),
        ('قیمت‌ها', {
            'fields': ('display_price_breakdown', 'discount'),
        }),
        ('اطلاعات تکمیلی', {
            'fields': ('recurring_reservation', 'notes'),
        }),
        ('لغو رزرو', {
            'fields': ('cancellation_reason', 'cancellation_date'),
            'classes': ['collapse'],
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    
    @display(description="کاربر")
    def display_user(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.user.get_full_name() or obj.user.username,
            obj.user.username
        )
    
    @display(description="سانس")
    def display_session(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{} ({}-{})</small>',
            obj.session_time.facility.name,
            obj.session_time.session_name,
            obj.session_time.start_time.strftime('%H:%M'),
            obj.session_time.end_time.strftime('%H:%M')
        )
    
    @display(description="تاریخ", ordering="date")
    def display_date(self, obj):
        jalali_date = obj.get_jalali_date()
        weekday = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه'][obj.date.weekday()]
        
        if obj.is_past:
            badge_class = "badge-secondary"
        elif obj.date == timezone.now().date():
            badge_class = "badge-warning"
        else:
            badge_class = "badge-info"
        
        return format_html(
            '<span class="badge {}">{}<br><small>{}</small></span>',
            badge_class, jalali_date, weekday
        )
    
    @display(description="وضعیت")
    def display_status(self, obj):
        status_badges = {
            'pending': 'badge-warning',
            'confirmed': 'badge-success',
            'cancelled': 'badge-danger',
            'completed': 'badge-info',
        }
        return format_html(
            '<span class="badge {}">{}</span>',
            status_badges.get(obj.status, 'badge-secondary'),
            obj.get_status_display()
        )
    
    @display(description="قیمت")
    def display_prices(self, obj):
        if obj.discount_amount > 0:
            return format_html(
                '<del>{:,}</del><br><strong>{:,} تومان</strong>',
                int(obj.original_price),
                int(obj.final_price)
            )
        else:
            return format_html('<strong>{:,} تومان</strong>', int(obj.final_price))
    
    @display(description="جزئیات قیمت")
    def display_price_breakdown(self, obj):
        if not obj.pk:
            return "-"
        
        html = f'''
        <div class="price-breakdown">
            <table class="table table-sm">
                <tr>
                    <td>قیمت پایه:</td>
                    <td>{int(obj.original_price):,} تومان</td>
                </tr>
        '''
        
        if obj.discount:
            html += f'''
                <tr>
                    <td>تخفیف ({obj.discount.name}):</td>
                    <td class="text-danger">- {int(obj.discount_amount):,} تومان</td>
                </tr>
            '''
        elif obj.recurring_reservation and obj.recurring_reservation.package:
            html += f'''
                <tr>
                    <td>تخفیف پکیج:</td>
                    <td class="text-danger">- {int(obj.discount_amount):,} تومان</td>
                </tr>
            '''
        
        html += f'''
                <tr class="font-weight-bold">
                    <td>قیمت نهایی:</td>
                    <td>{int(obj.final_price):,} تومان</td>
                </tr>
            </table>
        </div>
        '''
        
        return format_html(html)
    
    @display(description="عملیات")
    def display_actions(self, obj):
        actions = []
        
        if obj.status == 'pending':
            actions.append(
                format_html(
                    '<a class="btn btn-sm btn-success" href="{}">تایید</a>',
                    reverse('admin:confirm_reservation', args=[obj.pk])
                )
            )
        
        if obj.can_cancel:
            actions.append(
                format_html(
                    '<a class="btn btn-sm btn-danger" href="{}">لغو</a>',
                    reverse('admin:cancel_reservation', args=[obj.pk])
                )
            )
        
        if obj.status == 'confirmed' and obj.is_past and not hasattr(obj, 'review'):
            actions.append(
                format_html(
                    '<a class="btn btn-sm btn-info" href="{}">ثبت نظر</a>',
                    reverse('admin:add_review', args=[obj.pk])
                )
            )
        
        return format_html(' '.join(actions)) if actions else "-"
    
    @action(description="تایید رزروهای انتخابی")
    def confirm_reservations(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='confirmed')
        self.message_user(request, f"{updated} رزرو تایید شد.", level="success")
    
    @action(description="لغو رزروهای انتخابی")
    def cancel_reservations(self, request, queryset):
        cancellable = queryset.filter(status__in=['pending', 'confirmed'])
        count = 0
        for reservation in cancellable:
            if reservation.can_cancel:
                reservation.cancel("لغو دسته‌جمعی توسط مدیر")
                count += 1
        self.message_user(request, f"{count} رزرو لغو شد.", level="success")
    
    @action(description="تکمیل رزروهای گذشته")
    def complete_past_reservations(self, request, queryset):
        past_confirmed = queryset.filter(
            status='confirmed',
            date__lt=timezone.now().date()
        )
        updated = past_confirmed.update(status='completed')
        self.message_user(request, f"{updated} رزرو تکمیل شد.", level="success")

@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ['display_user', 'display_facility', 'display_rating', 'display_date', 'is_approved', 'display_actions']
    list_filter = [
        'is_approved',
        'rating',
        ('reservation__session_time__facility', RelatedDropdownFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ['reservation__user__username', 'reservation__user__first_name', 'comment']
    readonly_fields = ['reservation', 'created_at', 'updated_at', 'display_reservation_info']
    
    fieldsets = (
        ('اطلاعات رزرو', {
            'fields': ('display_reservation_info',),
        }),
        ('نظر', {
            'fields': ('rating', 'comment'),
        }),
        ('وضعیت', {
            'fields': ('is_approved',),
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    
    @display(description="کاربر")
    def display_user(self, obj):
        user = obj.reservation.user
        return format_html(
            '<strong>{}</strong>',
            user.get_full_name() or user.username
        )
    
    @display(description="سالن")
    def display_facility(self, obj):
        return obj.reservation.session_time.facility.name
    
    @display(description="امتیاز")
    def display_rating(self, obj):
        stars = '⭐' * obj.rating
        return format_html('<span style="font-size: 1.2em;">{}</span>', stars)
    
    @display(description="تاریخ")
    def display_date(self, obj):
        jalali = jdatetime.datetime.fromgregorian(datetime=obj.created_at).strftime('%Y/%m/%d %H:%M')
        return format_html('<small>{}</small>', jalali)
    
    @display(description="اطلاعات رزرو")
    def display_reservation_info(self, obj):
        if not obj.pk:
            return "-"
        
        reservation = obj.reservation
        return format_html(
            '''
            <div class="reservation-info">
                <p><strong>کاربر:</strong> {}</p>
                <p><strong>سالن:</strong> {}</p>
                <p><strong>سانس:</strong> {} ({} - {})</p>
                <p><strong>تاریخ:</strong> {}</p>
            </div>
            ''',
            reservation.user.get_full_name(),
            reservation.session_time.facility.name,
            reservation.session_time.session_name,
            reservation.session_time.start_time.strftime('%H:%M'),
            reservation.session_time.end_time.strftime('%H:%M'),
            reservation.get_jalali_date()
        )
    
    @display(description="عملیات")
    def display_actions(self, obj):
        if not obj.is_approved:
            return format_html(
                '<a class="btn btn-sm btn-success" href="{}">تایید</a>',
                reverse('admin:approve_review', args=[obj.pk])
            )
        return "-"
    
    @action(description="تایید نظرات انتخابی")
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} نظر تایید شد.", level="success")
    
    @action(description="رد نظرات انتخابی")
    def reject_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} نظر رد شد.", level="success")

    # تنظیمات اضافی برای نمایش بهتر در Unfold
admin.site.site_header = "پنل مدیریت سالن‌های ورزشی"
admin.site.site_title = "مدیریت رزرو"
admin.site.index_title = "خوش آمدید به پنل مدیریت"