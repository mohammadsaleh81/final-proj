"""
اسکریپت ایجاد داده‌های تستی برای سیستم رزرو سالن‌های ورزشی
"""

import os
import sys
import django
import random
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

# Import factories
from ai.factories import (
    UserFactory, SportFacilityFactory, SessionTimeFactory,
    PricingRuleFactory, HolidayFactory, ReservationPackageFactory,
    RecurringReservationFactory, DiscountFactory, ReservationFactory,
    
)

from ai.models import (
    SportFacility, SessionTime, PricingRule, Holiday,
    ReservationPackage, RecurringReservation, Discount,
    Reservation, Review
)


class TestDataGenerator:
    def __init__(self):
        self.users = []
        self.facilities = []
        self.session_times = []
        self.reservations = []
        
    def clear_existing_data(self):
        """حذف داده‌های موجود"""
        print("🗑️  در حال حذف داده‌های قبلی...")
        
        Review.objects.all().delete()
        Reservation.objects.all().delete()
        RecurringReservation.objects.all().delete()
        Discount.objects.all().delete()
        ReservationPackage.objects.all().delete()
        Holiday.objects.all().delete()
        PricingRule.objects.all().delete()
        SessionTime.objects.all().delete()
        SportFacility.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        
        print("✅ داده‌های قبلی حذف شدند")
    
    def create_superuser(self):
        """ایجاد سوپریوزر"""
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                first_name='مدیر',
                last_name='سیستم'
            )
            print(f"👤 سوپریوزر ایجاد شد: admin / admin123")
        else:
            print("👤 سوپریوزر قبلاً وجود دارد")
    
    def create_users(self, count=50):
        """ایجاد کاربران"""
        print(f"👥 در حال ایجاد {count} کاربر...")
        
        # ایجاد مدیران سالن
        managers = UserFactory.create_batch(10)
        for manager in managers:
            manager.is_staff = True
            manager.save()
        
        # ایجاد کاربران عادی
        regular_users = UserFactory.create_batch(count - 10)
        
        self.users = managers + regular_users
        print(f"✅ {count} کاربر ایجاد شد")
        
        return self.users
    
    def create_facilities(self, count=10):
        """ایجاد سالن‌های ورزشی"""
        print(f"🏢 در حال ایجاد {count} سالن ورزشی...")
        
        managers = [u for u in self.users if u.is_staff]
        
        for i in range(count):
            facility = SportFacilityFactory(
                manager=random.choice(managers)
            )
            self.facilities.append(facility)
        
        print(f"✅ {count} سالن ورزشی ایجاد شد")
        return self.facilities
    
    def create_session_times(self):
        """ایجاد سانس‌ها برای هر سالن"""
        print("⏰ در حال ایجاد سانس‌ها...")
        
        session_times_data = [
            ('سانس صبحگاهی', 6, 8),
            ('سانس صبح', 8, 10),
            ('سانس ظهر', 12, 14),
            ('سانس عصر', 16, 18),
            ('سانس شب', 18, 20),
            ('سانس آخر شب', 20, 22),
        ]
        
        count = 0
        for facility in self.facilities:
            # برای هر روز هفته
            for day in range(7):
                # تعداد تصادفی سانس برای هر روز (3 تا 6)
                num_sessions = random.randint(3, 6)
                selected_sessions = random.sample(session_times_data, num_sessions)
                
                for session_name, start_hour, end_hour in selected_sessions:
                    session = SessionTimeFactory(
                        facility=facility,
                        session_name=session_name,
                        day_of_week=day,
                        start_time=f"{start_hour:02d}:00",
                        end_time=f"{end_hour:02d}:00"
                    )
                    self.session_times.append(session)
                    count += 1
        
        print(f"✅ {count} سانس ایجاد شد")
        return self.session_times
    
    def create_pricing_rules(self):
        """ایجاد قوانین قیمت‌گذاری"""
        print("💰 در حال ایجاد قوانین قیمت‌گذاری...")
        
        count = 0
        for facility in self.facilities:
            # قانون تخفیف صبحگاهی
            PricingRuleFactory(
                facility=facility,
                name='تخفیف صبحگاهی',
                rule_type='time_of_day',
                start_time='06:00',
                end_time='10:00',
                price_adjustment_type='percentage_decrease',
                adjustment_value=20,
                priority=1
            )
            count += 1
            
            # قانون افزایش قیمت آخر هفته
            PricingRuleFactory(
                facility=facility,
                name='افزایش قیمت آخر هفته',
                rule_type='day_of_week',
                days_of_week='4,5',  # پنجشنبه و جمعه
                price_adjustment_type='percentage_increase',
                adjustment_value=15,
                priority=2
            )
            count += 1
            
            # قانون ساعات شلوغ
            if random.choice([True, False]):
                PricingRuleFactory(
                    facility=facility,
                    name='ساعات شلوغ',
                    rule_type='peak_hours',
                    price_adjustment_type='percentage_increase',
                    adjustment_value=10,
                    priority=3
                )
                count += 1
        
        print(f"✅ {count} قانون قیمت‌گذاری ایجاد شد")
    
    def create_holidays(self):
        """ایجاد تعطیلات"""
        print("📅 در حال ایجاد تعطیلات...")
        
        # تعطیلات ثابت
        fixed_holidays = [
            ('2024-03-20', 'عید نوروز', True),
            ('2024-03-21', 'عید نوروز', True),
            ('2024-03-22', 'عید نوروز', True),
            ('2024-03-23', 'عید نوروز', True),
            ('2024-04-01', 'روز طبیعت', True),
            ('2024-02-11', 'پیروزی انقلاب', True),
            ('2024-06-04', 'رحلت امام خمینی', True),
        ]
        
        for date_str, desc, is_recurring in fixed_holidays:
            Holiday.objects.create(
                date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                description=desc,
                is_recurring=is_recurring
            )
        
        # تعطیلات تصادفی
        HolidayFactory.create_batch(10)
        
        print(f"✅ تعطیلات ایجاد شد")
    
    def create_packages_and_discounts(self):
        """ایجاد پکیج‌ها و تخفیف‌ها"""
        print("🎁 در حال ایجاد پکیج‌ها و تخفیف‌ها...")
        
        # پکیج‌ها
        for facility in self.facilities:
            ReservationPackageFactory.create_batch(4, facility=facility)
        
        # تخفیف‌های سالن
        for facility in random.sample(self.facilities, 5):
            DiscountFactory(
                target_type='facility',
                facility=facility,
                name=f'تخفیف ویژه {facility.name}'
            )
        
        # تخفیف‌های سانس
        for session in random.sample(self.session_times, 10):
            DiscountFactory(
                target_type='session',
                session_time=session,
                name=f'تخفیف {session.session_name}'
            )
        
        # کدهای تخفیف عمومی
        discount_codes = ['WELCOME20', 'SUMMER50', 'VIP30', 'STUDENT15', 'NEWYEAR25']
        for code in discount_codes:
            DiscountFactory(
                target_type='code',
                code=code,
                name=f'کد تخفیف {code}'
            )
        
        print("✅ پکیج‌ها و تخفیف‌ها ایجاد شدند")
    
    def create_reservations(self):
        """ایجاد رزروها"""
        print("📝 در حال ایجاد رزروها...")
        
        regular_users = [u for u in self.users if not u.is_staff]
        
        # رزروهای عادی
        count = 0
        for _ in range(200):
            user = random.choice(regular_users)
            session = random.choice(self.session_times)
            
            # محاسبه تاریخ بر اساس روز هفته سانس
            days_ahead = random.randint(1, 30)
            date = timezone.now().date() + timedelta(days=days_ahead)
            
            # پیدا کردن تاریخی که مطابق با روز هفته سانس باشد
            while date.weekday() != session.day_of_week:
                date += timedelta(days=1)
            
            # بررسی تعطیلی
            if not Holiday.is_holiday(date):
                try:
                    reservation = ReservationFactory(
                        user=user,
                        session_time=session,
                        date=date,
                        status=random.choice(['pending', 'confirmed', 'confirmed', 'confirmed'])
                    )
                    self.reservations.append(reservation)
                    count += 1
                except:
                    pass  # در صورت تکراری بودن رزرو
        
        # رزروهای گذشته (برای نمایش آمار)
        for _ in range(100):
            user = random.choice(regular_users)
            session = random.choice(self.session_times)
            
            days_ago = random.randint(1, 60)
            date = timezone.now().date() - timedelta(days=days_ago)
            
            while date.weekday() != session.day_of_week:
                date -= timedelta(days=1)
            
            if not Holiday.is_holiday(date):
                try:
                    reservation = Reservation.objects.create(
                        user=user,
                        session_time=session,
                        date=date,
                        status='completed',
                        original_price=session.get_price(),
                        final_price=session.get_price()
                    )
                    self.reservations.append(reservation)
                    count += 1
                except:
                    pass
        
        print(f"✅ {count} رزرو ایجاد شد")
        
        # رزروهای دوره‌ای
        print("🔄 در حال ایجاد رزروهای دوره‌ای...")
        for _ in range(20):
            user = random.choice(regular_users)
            session = random.choice(self.session_times)
            package = random.choice(ReservationPackage.objects.filter(
                facility=session.facility
            ))
            
            recurring = RecurringReservationFactory(
                user=user,
                session_time=session,
                package=package
            )
            
            # ایجاد رزروهای مربوطه
            recurring.generate_reservations()
        
        print("✅ رزروهای دوره‌ای ایجاد شدند")
    
    
    def print_summary(self):
        """نمایش خلاصه داده‌های ایجاد شده"""
        print("\n" + "="*50)
        print("📊 خلاصه داده‌های ایجاد شده:")
        print("="*50)
        print(f"👥 کاربران: {User.objects.count()}")
        print(f"🏢 سالن‌های ورزشی: {SportFacility.objects.count()}")
        print(f"⏰ سانس‌ها: {SessionTime.objects.count()}")
        print(f"💰 قوانین قیمت‌گذاری: {PricingRule.objects.count()}")
        print(f"📅 تعطیلات: {Holiday.objects.count()}")
        print(f"🎁 پکیج‌ها: {ReservationPackage.objects.count()}")
        print(f"🏷️ تخفیف‌ها: {Discount.objects.count()}")
        print(f"📝 رزروها: {Reservation.objects.count()}")
        print(f"🔄 رزروهای دوره‌ای: {RecurringReservation.objects.count()}")
        print(f"⭐ نظرات: {Review.objects.count()}")
        print("="*50)
    
    # @transaction.atomic
    def generate_all(self, clear_existing=True):
        """اجرای کامل فرآیند تولید داده"""
        print("🚀 شروع ایجاد داده‌های تستی...")
        print("="*50)
        
        if clear_existing:
            self.clear_existing_data()
        
        self.create_superuser()
        self.create_users(50)
        self.create_facilities(10)
        self.create_session_times()
        self.create_pricing_rules()
        self.create_holidays()
        self.create_packages_and_discounts()
        self.create_reservations()
        
        self.print_summary()
        print("\n✅ داده‌های تستی با موفقیت ایجاد شدند!")


# if __name__ == '__main__':
generator = TestDataGenerator()
    
    # می‌توانید با clear_existing=False داده‌های قبلی را حفظ کنید
generator.generate_all(clear_existing=True)


# 