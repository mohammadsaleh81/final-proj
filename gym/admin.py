# from django.contrib import admin
# from django.utils.html import format_html
# from django.urls import reverse
# from django.contrib import messages
# from django.shortcuts import redirect
# from django.http import HttpResponse
# import csv
#
# from unfold.admin import ModelAdmin, TabularInline
# from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
# from unfold.contrib.forms.widgets import WysiwygWidget
# from unfold.contrib.filters.admin import RangeDateFilter, DropdownFilter, AutocompleteSelectFilter, AutocompleteSelectMultipleFilter, TextFilter, ChoicesRadioFilter
#
#
# from .models import SportFacility, SessionTime, Holiday, Reservation
#
# class SessionTimeInline(TabularInline):
#     model = SessionTime
#     extra = 1
#     show_change_link = True
#     fields = ('session_name', 'day_of_week', 'start_time', 'end_time',
#              'price_type', 'fixed_price', 'hourly_price', 'is_active')
#
#     # Group fields into tabs
#     tabs = [
#         ("اطلاعات اصلی", {"fields": ('session_name', 'day_of_week', 'start_time', 'end_time')}),
#         ("قیمت‌گذاری", {"fields": ('price_type', 'fixed_price', 'hourly_price')}),
#         ("تنظیمات", {"fields": ('is_active',)}),
#     ]
#
# class FacilityFilter(AutocompleteSelectFilter):
#     title = 'سالن'
#     field_name = 'facility'
#
# class UserFilter(AutocompleteSelectFilter):
#     title = 'کاربر'
#     field_name = 'user'
#     search_fields = ['username', 'first_name', 'last_name']
#
# @admin.register(SportFacility)
# class SportFacilityAdmin(ModelAdmin):
#     list_display = ('name', 'capacity', 'hourly_price', 'active_sessions_count',
#                    'total_reservations_display', 'is_active')
#
#     search_fields = ('name', 'description', 'address')
#     list_editable = ('is_active', 'hourly_price')
#     inlines = [SessionTimeInline]
#
#     # Group fields into tabs
#     tabs = True
#     fieldsets = (
#         ("اطلاعات اصلی", {
#             'fields': (('name', 'manager'), 'description', 'capacity'),
#             'classes': ('tab-primary',),
#         }),
#         ("قیمت‌گذاری", {
#             'fields': ('hourly_price',),
#             'classes': ('tab-success',),
#         }),
#         ("اطلاعات تماس", {
#             'fields': ('address', 'phone', 'facilities'),
#             'classes': ('tab-info',),
#         }),
#         ("تنظیمات", {
#             'fields': ('is_active',),
#             'classes': ('tab-danger',),
#         }),
#     )
#
#     def active_sessions_count(self, obj):
#         count = obj.session_times.filter(is_active=True).count()
#         return format_html(
#             '<span class="text-success font-bold">{}</span>',
#             count
#         )
#     active_sessions_count.short_description = 'سانس های فعال'
#
#     def total_reservations_display(self, obj):
#         count = obj.get_total_reservations()
#         return format_html(
#             '<span class="text-primary font-bold">{}</span>',
#             count
#         )
#     total_reservations_display.short_description = 'کل رزروها'
#
# @admin.register(SessionTime)
# class SessionTimeAdmin(ModelAdmin):
#     list_display = ('facility', 'session_name', 'get_day_display', 'start_time', 'end_time',
#                    'price_type_display', 'get_price_display', 'total_reservations_display', 'is_active')
#     list_filter = (
#         # ('facility', DropdownFilter),
#         ('day_of_week', ChoicesRadioFilter),
#         ('price_type', ChoicesRadioFilter),
#         ('is_active', ChoicesRadioFilter),
#     )
#     search_fields = ('facility__name', 'session_name')
#     list_editable = ('is_active',)
#
#     # Group fields into tabs
#     tabs = True
#     fieldsets = (
#         ("اطلاعات اصلی", {
#             'fields': (('facility', 'session_name'),),
#             'classes': ('tab-primary',),
#         }),
#         ("زمان‌بندی", {
#             'fields': (('day_of_week', 'start_time', 'end_time'),),
#             'classes': ('tab-info',),
#         }),
#         ("قیمت‌گذاری", {
#             'fields': ('price_type', ('fixed_price', 'hourly_price')),
#             'classes': ('tab-success',),
#             'description': 'قیمت می‌تواند به صورت ثابت یا ساعتی تعیین شود. در صورت عدم تعیین قیمت ساعتی، از قیمت ساعتی سالن استفاده می‌شود.'
#         }),
#         ("تنظیمات", {
#             'fields': ('is_active',),
#             'classes': ('tab-danger',),
#         }),
#     )
#
#     def get_day_display(self, obj):
#         return obj.get_day_of_week_display()
#     get_day_display.short_description = 'روز هفته'
#
#     def price_type_display(self, obj):
#         return obj.get_price_type_display()
#     price_type_display.short_description = 'نوع قیمت‌گذاری'
#
#     def get_price_display(self, obj):
#         price = obj.get_price()
#         return format_html(
#             '<span style="color: green; font-weight: bold;">{}</span>',
#             obj.get_price_display()
#         )
#     get_price_display.short_description = 'قیمت'
#
#     def total_reservations_display(self, obj):
#         count = obj.get_total_reservations()
#         return format_html(
#             '<span style="color: blue; font-weight: bold;">{}</span>',
#             count
#         )
#     total_reservations_display.short_description = 'تعداد رزرو'
#
# @admin.register(Holiday)
# class HolidayAdmin(ModelAdmin):
#     list_display = ('date', 'get_jalali_date', 'description', 'is_recurring', 'recurring_display')
#     list_filter = (
#         ('is_recurring', ChoicesRadioFilter),
#         ('date', RangeDateFilter),
#     )
#     search_fields = ('description',)
#     ordering = ('date',)
#
#     # Group fields into tabs
#     tabs = True
#     fieldsets = (
#         ("اطلاعات اصلی", {
#             'fields': ('date', 'description'),
#             'classes': ('tab-primary',),
#         }),
#         ("تنظیمات تکرار", {
#             'fields': ('is_recurring', ('jalali_month', 'jalali_day')),
#             'classes': ('tab-info',),
#         }),
#     )
#
#     def recurring_display(self, obj):
#         if obj.is_recurring:
#             return f"{obj.jalali_month}/{obj.jalali_day}"
#         return "-"
#     recurring_display.short_description = 'تاریخ تکرار'
#
# @admin.register(Reservation)
# class ReservationAdmin(ModelAdmin):
#     list_display = ('user_display', 'facility_name', 'session_info', 'date', 'get_jalali_date',
#                    'price_display', 'status_colored', 'action_buttons')
#     list_filter = (
#         ('status', ChoicesRadioFilter),
#         ('date', RangeDateFilter),
#         # FacilityFilter,
#         # UserFilter,
#     )
#     search_fields = ('user__username', 'user__first_name', 'user__last_name',
#                     'session_time__facility__name')
#     readonly_fields = ('created_at', 'updated_at')
#     ordering = ('-date', '-created_at')
#
#     actions = ['mark_as_completed', 'export_to_csv']
#
#     # Group fields into tabs
#     tabs = True
#     fieldsets = (
#         ("اطلاعات رزرو", {
#             'fields': (('user', 'session_time'), 'date'),
#             'classes': ('tab-primary',),
#         }),
#         ("وضعیت و قیمت", {
#             'fields': ('status', 'price', 'notes'),
#             'classes': ('tab-info',),
#         }),
#         ("اطلاعات سیستم", {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('tab-secondary',),
#         }),
#     )
#
#     def get_form(self, request, obj=None, **kwargs):
#         form = super().get_form(request, obj, **kwargs)
#         form.base_fields['notes'].widget = WysiwygWidget()
#         return form
#
#     def user_display(self, obj):
#         return f"{obj.user.get_full_name()} ({obj.user.username})"
#     user_display.short_description = 'کاربر'
#
#     def facility_name(self, obj):
#         return obj.session_time.facility.name
#     facility_name.short_description = 'سالن'
#
#     def session_info(self, obj):
#         return f"{obj.session_time.get_day_of_week_display()} ({obj.session_time.start_time} - {obj.session_time.end_time})"
#     session_info.short_description = 'زمان سانس'
#
#     def price_display(self, obj):
#         return format_html(
#             '<span style="color: green; font-weight: bold;">{:,} تومان</span>',
#             int(obj.price)
#         )
#     price_display.short_description = 'قیمت'
#
#     def status_colored(self, obj):
#         colors = {
#             'pending': 'orange',
#             'confirmed': 'green',
#             'cancelled': 'red',
#             'completed': 'blue'
#         }
#         return format_html(
#             '<span style="color: {};">{}</span>',
#             colors.get(obj.status, 'black'),
#             obj.get_status_display()
#         )
#     status_colored.short_description = 'وضعیت'
#
#     def action_buttons(self, obj):
#         buttons = []
#         if obj.can_cancel:
#             cancel_url = reverse('admin:cancel_reservation', args=[obj.pk])
#             buttons.append(
#                 f'<a href="{cancel_url}" class="button" style="background-color: #dc3545; color: white;">لغو</a>'
#             )
#
#         if obj.status == 'confirmed' and not obj.is_past:
#             complete_url = reverse('admin:complete_reservation', args=[obj.pk])
#             buttons.append(
#                 f'<a href="{complete_url}" class="button" style="background-color: #28a745; color: white;">تکمیل</a>'
#             )
#
#         return format_html(' '.join(buttons))
#     action_buttons.short_description = 'عملیات'
#
#     def mark_as_completed(self, request, queryset):
#         updated = queryset.filter(status='confirmed').update(status='completed')
#         self.message_user(request, f"{updated} رزرو به عنوان تکمیل شده علامت‌گذاری شد.")
#     mark_as_completed.short_description = "علامت‌گذاری به عنوان تکمیل شده"
#
#     def export_to_csv(self, request, queryset):
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="reservations.csv"'
#         response.write('\ufeff')  # BOM for UTF-8
#
#         writer = csv.writer(response)
#         writer.writerow(['کاربر', 'سالن', 'سانس', 'تاریخ', 'قیمت', 'وضعیت'])
#
#         for reservation in queryset:
#             writer.writerow([
#                 reservation.user.get_full_name(),
#                 reservation.session_time.facility.name,
#                 f"{reservation.session_time.get_day_of_week_display()} ({reservation.session_time.start_time}-{reservation.session_time.end_time})",
#                 reservation.get_jalali_date(),
#                 reservation.price,
#                 reservation.get_status_display()
#             ])
#
#         return response
#     export_to_csv.short_description = "صادرات به Excel"
#
# # Admin site customization
# admin.site.site_header = "پنل مدیریت سالن های ورزشی"
# admin.site.site_title = "مدیریت سالن ها"
# admin.site.index_title = "خوش آمدید به پنل مدیریت"
