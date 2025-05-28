from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from gym.models import SportFacility, SessionTime, Holiday, Reservation
from django.utils import timezone
import jdatetime
from datetime import time, timedelta, datetime
import random
from decimal import Decimal

class Command(BaseCommand):
    help = 'Generates test data for the gym reservation system'

    def handle(self, *args, **options):
        self.stdout.write('شروع تولید داده‌های تست...')

        # ایجاد کاربران
        self.create_users()
        
        # ایجاد سالن‌ها
        self.create_facilities()
        
        # ایجاد سانس‌ها
        self.create_sessions()
        
        # ایجاد تعطیلات
        self.create_holidays()
        
        # ایجاد رزروها
        self.create_reservations()

        self.stdout.write(self.style.SUCCESS('داده‌های تست با موفقیت ایجاد شدند!'))

    def create_users(self):
        # ایجاد کاربر ادمین
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write('کاربر ادمین ایجاد شد')

        # ایجاد مدیران سالن
        managers = [
            ('manager1', 'علی', 'محمدی', '09121234567'),
            ('manager2', 'رضا', 'احمدی', '09129876543'),
            ('manager3', 'حسین', 'کریمی', '09123456789'),
        ]

        for username, first_name, last_name, phone in managers:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    password='manager123',
                    first_name=first_name,
                    last_name=last_name,
                    email=f'{username}@example.com',
                    is_staff=True
                )
                self.stdout.write(f'مدیر سالن ایجاد شد: {first_name} {last_name}')

        # ایجاد کاربران عادی
        users = [
            ('user1', 'مریم', 'حسینی'),
            ('user2', 'زهرا', 'رضایی'),
            ('user3', 'محمد', 'علوی'),
            ('user4', 'سارا', 'موسوی'),
            ('user5', 'امیر', 'صادقی'),
        ]

        for username, first_name, last_name in users:
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(
                    username=username,
                    password='user123',
                    first_name=first_name,
                    last_name=last_name,
                    email=f'{username}@example.com'
                )
                self.stdout.write(f'کاربر عادی ایجاد شد: {first_name} {last_name}')

    def create_facilities(self):
        facilities_data = [
            {
                'name': 'سالن فوتسال المپیک',
                'description': 'سالن استاندارد فوتسال با کفپوش حرفه‌ای و امکانات کامل',
                'capacity': 25,
                'hourly_price': Decimal('350000'),
                'address': 'تهران، منطقه ۵، بلوار اصلی، مجموعه ورزشی المپیک',
                'phone': '021-44556677',
                'facilities': 'رختکن مجهز، دوش آب گرم، پارکینگ اختصاصی، بوفه، سرویس بهداشتی',
                'manager': 'manager1'
            },
            {
                'name': 'باشگاه بدنسازی تندرستی',
                'description': 'مجهز به جدیدترین دستگاه‌های بدنسازی و تجهیزات پیشرفته',
                'capacity': 40,
                'hourly_price': Decimal('200000'),
                'address': 'تهران، منطقه ۳، خیابان دولت، کوچه ورزش',
                'phone': '021-22334455',
                'facilities': 'سونا، جکوزی، کافی‌شاپ، پارکینگ، فروشگاه مکمل',
                'manager': 'manager2'
            },
            {
                'name': 'سالن رزمی قهرمان',
                'description': 'سالن تخصصی ورزش‌های رزمی با تاتامی استاندارد',
                'capacity': 30,
                'hourly_price': Decimal('250000'),
                'address': 'تهران، منطقه ۲، ستارخان، خیابان ورزش',
                'phone': '021-66778899',
                'facilities': 'تاتامی، کیسه بوکس، رختکن، دوش، پارکینگ',
                'manager': 'manager3'
            },
        ]

        for data in facilities_data:
            manager = User.objects.get(username=data.pop('manager'))
            if not SportFacility.objects.filter(name=data['name']).exists():
                facility = SportFacility.objects.create(
                    **data,
                    manager=manager,
                    is_active=True
                )
                self.stdout.write(f'سالن ورزشی ایجاد شد: {facility.name}')

    def create_sessions(self):
        facilities = SportFacility.objects.all()
        
        # تعریف سانس‌های مختلف برای هر سالن
        session_templates = {
            'سالن فوتسال المپیک': [
                ('صبح زود', time(6, 0), time(8, 0), Decimal('300000')),
                ('صبح', time(8, 0), time(10, 0), Decimal('400000')),
                ('ظهر', time(12, 0), time(14, 0), Decimal('350000')),
                ('عصر ۱', time(16, 0), time(18, 0), Decimal('450000')),
                ('عصر ۲', time(18, 0), time(20, 0), Decimal('500000')),
                ('شب', time(20, 0), time(22, 0), Decimal('600000')),
            ],
            'باشگاه بدنسازی تندرستی': [
                ('صبح', time(7, 0), time(9, 0), Decimal('150000')),
                ('صبح ویژه بانوان', time(9, 0), time(11, 0), Decimal('180000')),
                ('ظهر', time(12, 0), time(14, 0), Decimal('150000')),
                ('عصر ویژه بانوان', time(15, 0), time(17, 0), Decimal('200000')),
                ('عصر', time(17, 0), time(19, 0), Decimal('250000')),
                ('شب', time(19, 0), time(22, 0), Decimal('300000')),
            ],
            'سالن رزمی قهرمان': [
                ('صبح', time(8, 0), time(10, 0), Decimal('200000')),
                ('ظهر کودکان', time(14, 0), time(16, 0), Decimal('180000')),
                ('عصر نوجوانان', time(16, 0), time(18, 0), Decimal('220000')),
                ('عصر بزرگسالان', time(18, 0), time(20, 0), Decimal('250000')),
                ('شب پیشرفته', time(20, 0), time(22, 0), Decimal('300000')),
            ],
        }

        for facility in facilities:
            sessions = session_templates.get(facility.name, [])
            for name, start, end, price in sessions:
                # ایجاد سانس برای روزهای مختلف هفته
                for day in range(7):  # 0=شنبه to 6=جمعه
                    # برخی سانس‌ها فقط در روزهای خاص فعال باشند
                    if 'بانوان' in name and day == 6:  # جمعه تعطیل
                        continue
                    if 'کودکان' in name and day in [6, 5]:  # پنجشنبه و جمعه تعطیل
                        continue

                    if not SessionTime.objects.filter(
                        facility=facility,
                        day_of_week=day,
                        start_time=start,
                        end_time=end
                    ).exists():
                        session = SessionTime.objects.create(
                            facility=facility,
                            day_of_week=day,
                            start_time=start,
                            end_time=end,
                            price=price,
                            session_name=name,
                            is_active=True
                        )
                        self.stdout.write(f'سانس ایجاد شد: {session}')

    def create_holidays(self):
        # تعطیلات رسمی سال
        holidays_data = [
            ('عید نوروز', 1, 1, True),
            ('عید نوروز', 1, 2, True),
            ('عید نوروز', 1, 3, True),
            ('عید نوروز', 1, 4, True),
            ('روز طبیعت', 1, 13, True),
            ('عید فطر', 2, 14, True),
            ('عید فطر', 2, 15, True),
            ('شهادت امام علی', 3, 21, True),
            ('عید قربان', 4, 10, True),
            ('تاسوعا', 5, 19, True),
            ('عاشورا', 5, 20, True),
            ('اربعین', 7, 7, True),
            ('رحلت پیامبر', 8, 8, True),
            ('شهادت امام رضا', 9, 30, True),
            ('یلدا', 10, 30, True),
            ('۲۲ بهمن', 11, 22, True),
        ]

        # تعطیلات غیر تکرار شونده (مثل تعمیرات)
        today = timezone.now().date()
        maintenance_dates = [
            today + timedelta(days=15),
            today + timedelta(days=45),
            today + timedelta(days=75),
        ]

        # ایجاد تعطیلات تکرار شونده
        for description, month, day, is_recurring in holidays_data:
            if not Holiday.objects.filter(jalali_month=month, jalali_day=day, is_recurring=is_recurring).exists():
                j_date = jdatetime.date(1402, month, day)
                g_date = j_date.togregorian()
                
                holiday = Holiday.objects.create(
                    date=g_date,
                    description=description,
                    is_recurring=is_recurring,
                    jalali_month=month,
                    jalali_day=day
                )
                self.stdout.write(f'تعطیلی ایجاد شد: {holiday}')

        # ایجاد تعطیلات تعمیرات
        for date in maintenance_dates:
            if not Holiday.objects.filter(date=date).exists():
                holiday = Holiday.objects.create(
                    date=date,
                    description='تعمیرات دوره‌ای سالن',
                    is_recurring=False
                )
                self.stdout.write(f'تعطیلی تعمیرات ایجاد شد: {holiday}')

    def create_reservations(self):
        users = User.objects.filter(is_staff=False, is_superuser=False)
        sessions = SessionTime.objects.filter(is_active=True)
        today = timezone.now().date()

        # ایجاد رزروهای تست برای ۶۰ روز آینده
        for i in range(60):
            date = today + timedelta(days=i)
            
            # بررسی تعطیلی
            if not Holiday.is_holiday(date):
                # انتخاب تصادفی ۵ سانس برای هر روز
                available_sessions = [s for s in sessions if s.day_of_week == date.weekday()]
                selected_sessions = random.sample(available_sessions, min(5, len(available_sessions)))
                
                for session in selected_sessions:
                    user = random.choice(users)
                    
                    # تعیین وضعیت بر اساس تاریخ
                    if date < today:
                        status = random.choice(['completed', 'cancelled'])
                    elif date == today:
                        status = random.choice(['confirmed', 'pending'])
                    else:
                        status = random.choice(['confirmed', 'pending', 'cancelled'])

                    try:
                        reservation = Reservation.objects.create(
                            user=user,
                            session_time=session,
                            date=date,
                            status=status,
                            notes=f'رزرو تستی برای {session.session_name}'
                        )
                        self.stdout.write(f'رزرو ایجاد شد: {reservation}')
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'خطا در ایجاد رزرو: {str(e)}')) 
                        # داده‌های تست با موفقیت ایجاد شدند!