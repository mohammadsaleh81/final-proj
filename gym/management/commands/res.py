# management/commands/generate_reservations.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from myapp.models import RecurringReservation
from myapp.utils import generate_recurring_reservations

class Command(BaseCommand):
    help = 'تولید رزروهای آینده برای رزروهای دوره‌ای'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='تعداد روزهای آینده برای تولید رزرو'
        )

    def handle(self, *args, **options):
        days = options['days']
        active_reservations = RecurringReservation.objects.filter(
            status='ACTIVE',
            end_date__gte=timezone.now().date()
        )
        
        self.stdout.write(f'در حال تولید رزروها برای {days} روز آینده...')
        
        for reservation in active_reservations:
            # حذف رزروهای آینده و تولید مجدد
            future_date = timezone.now().date() + timedelta(days=1)
            reservation.generated_reservations.filter(
                reservation_date__gte=future_date
            ).delete()
            
            generate_recurring_reservations(reservation)
            
        self.stdout.write(
            self.style.SUCCESS(f'رزروهای {active_reservations.count()} کاربر بازتولید شد.')
        )


# management/commands/add_holidays.py
from django.core.management.base import BaseCommand
from myapp.models import PublicHoliday
from datetime import date

class Command(BaseCommand):
    help = 'اضافه کردن تعطیلات رسمی ایران'

    def handle(self, *args, **options):
        # تعطیلات ثابت ایران (تاریخ میلادی تقریبی)
        holidays_2024 = [
            ('نوروز', date(2024, 3, 20)),
            ('نوروز', date(2024, 3, 21)),
            ('نوروز', date(2024, 3, 22)),
            ('نوروز', date(2024, 3, 23)),
            ('روز طبیعت', date(2024, 4, 2)),
            ('رحلت امام خمینی', date(2024, 6, 4)),
            ('قیام 15 خرداد', date(2024, 6, 5)),
            ('شهادت امام علی', date(2024, 7, 16)),
            ('عید فطر', date(2024, 4, 10)),
            ('عید فطر', date(2024, 4, 11)),
            ('عید قربان', date(2024, 6, 17)),
            ('غدیر خم', date(2024, 7, 25)),
            ('تاسوعا', date(2024, 8, 26)),
            ('عاشورا', date(2024, 8, 27)),
            ('اربعین', date(2024, 10, 6)),
            ('رحلت پیامبر', date(2024, 11, 4)),
            ('شهادت امام رضا', date(2024, 11, 6)),
            ('ولادت پیامبر', date(2024, 12, 15)),
            ('پیروزی انقلاب', date(2024, 2, 11)),
            ('ملی شدن نفت', date(2024, 3, 19)),
        ]
        
        created_count = 0
        for title, holiday_date in holidays_2024:
            holiday, created = PublicHoliday.objects.get_or_create(
                holiday_date=holiday_date,
                defaults={'title': title}
            )
            if created:
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'{created_count} تعطیل جدید اضافه شد.')
        )


# management/commands/cleanup_old_reservations.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from gym.models import GeneratedReservation

class Command(BaseCommand):
    help = 'پاک کردن رزروهای قدیمی'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='رزروهای قدیمی‌تر از این تعداد روز پاک شوند'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now().date() - timedelta(days=days)
        
        old_reservations = GeneratedReservation.objects.filter(
            reservation_date__lt=cutoff_date,
            status__in=['COMPLETED', 'CANCELLED']
        )
        
        count = old_reservations.count()
        old_reservations.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'{count} رزرو قدیمی پاک شد.')
        )



# settings.py additions
"""
# اضافه کردن به INSTALLED_APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'myapp',  # نام اپ شما
]

# تنظیمات ایمیل
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-password'

# تنظیمات Celery (اختیاری)
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_BEAT_SCHEDULE = {
    'generate-future-reservations': {
        'task': 'myapp.tasks.generate_future_reservations',
        'schedule': crontab(hour=2, minute=0),  # هر روز ساعت 2 صبح
    },
    'send-daily-reminders': {
        'task': 'myapp.tasks.send_daily_reminders',
        'schedule': crontab(hour=20, minute=0),  # هر روز ساعت 8 شب
    },
    'cleanup-old-data': {
        'task': 'myapp.tasks.cleanup_old_data',
        'schedule': crontab(day_of_month=1, hour=3, minute=0),  # اول هر ماه
    },
}

# تنظیمات زبان فارسی
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_L10N = True
USE_TZ = True
"""