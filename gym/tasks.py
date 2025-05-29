
# tasks.py - برای Celery اگر استفاده می‌کنید
from celery import shared_task
from datetime import date, timedelta
from .models import RecurringReservation, GeneratedReservation
from .utils import generate_recurring_reservations

@shared_task
def generate_future_reservations():
    """تولید خودکار رزروهای آینده"""
    active_reservations = RecurringReservation.objects.filter(
        status='ACTIVE',
        end_date__gte=date.today()
    )
    
    for reservation in active_reservations:
        #dd بررسی نیاز به تولید رزروهای جدید
        last_reservation = reservation.generated_reservations.order_by('-reservation_date').first()
        
        if not last_reservation or last_reservation.reservation_date < date.today() + timedelta(days=7):
            generate_recurring_reservations(reservation)

@shared_task
def send_daily_reminders():
    """ارسال یادآوری روزانه"""
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_reservations = GeneratedReservation.objects.filter(
        reservation_date=tomorrow,
        status='CONFIRMED'
    )
    
    for reservation in tomorrow_reservations:
        # ارسال SMS یا ایمیل یادآوری
        pass

@shared_task
def cleanup_old_data():
    """پاک کردن دیتاهای قدیمی"""
    cutoff_date = date.today() - timedelta(days=90)
    
    # حذف رزروهای قدیمی تکمیل شده
    GeneratedReservation.objects.filter(
        reservation_date__lt=cutoff_date,
        status__in=['COMPLETED', 'CANCELLED']
    ).delete()