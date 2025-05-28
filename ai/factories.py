import factory
import factory.fuzzy
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User
from faker import Faker
import random
from datetime import datetime, timedelta, time
from django.utils import timezone
import jdatetime

from .models import (
    SportFacility, SessionTime, PricingRule, Holiday,
    ReservationPackage, RecurringReservation, Discount,
    Reservation, Review
)

# ایجاد faker فارسی
fake = Faker('fa_IR')
fake_en = Faker('en_US')

# لیست نام‌های سالن‌های ورزشی
SPORT_FACILITY_NAMES = [
    'مجموعه ورزشی آزادی',
    'سالن ورزشی شهید چمران',
    'باشگاه پرسپولیس',
    'مجموعه ورزشی انقلاب',
    'سالن بدنسازی قهرمانان',
    'باشگاه استقلال',
    'مجموعه ورزشی شهدای هفتم تیر',
    'سالن ورزشی المپیک',
    'باشگاه ورزشی ایرانیان',
    'مجموعه ورزشی آرارات',
]

# لیست نام سانس‌ها
SESSION_NAMES = [
    'سانس صبحگاهی',
    'سانس ویژه بانوان',
    'سانس عمومی آقایان',
    'سانس خصوصی',
    'سانس نیمه خصوصی',
    'کلاس یوگا',
    'کلاس پیلاتس',
    'کلاس ایروبیک',
    'تمرین تیمی',
    'سانس آزاد',
]

# Factory Classes
class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n:04d}')
    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    is_active = True
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.set_password(extracted)
        else:
            self.set_password('password123')

class SportFacilityFactory(DjangoModelFactory):
    class Meta:
        model = SportFacility
    
    name = factory.LazyAttribute(lambda _: random.choice(SPORT_FACILITY_NAMES) + f' - شعبه {fake.city()}')
    description = factory.LazyAttribute(lambda _: f'سالن ورزشی مجهز با امکانات کامل در {fake.city()}')
    capacity = factory.fuzzy.FuzzyInteger(50, 200, step=10)
    hourly_price = factory.fuzzy.FuzzyDecimal(50000, 200000, precision=0)
    address = factory.LazyAttribute(lambda _: fake.address())
    phone = factory.LazyAttribute(lambda _: fake.phone_number())
    facilities = factory.LazyAttribute(lambda _: 'رختکن، دوش آب گرم، پارکینگ، بوفه، وای‌فای رایگان')
    is_active = True
    manager = factory.SubFactory(UserFactory)

class SessionTimeFactory(DjangoModelFactory):
    class Meta:
        model = SessionTime
    
    facility = factory.SubFactory(SportFacilityFactory)
    session_name = factory.LazyAttribute(lambda _: random.choice(SESSION_NAMES))
    day_of_week = factory.fuzzy.FuzzyInteger(0, 6)
    start_time = factory.LazyAttribute(
        lambda _: time(random.choice([6, 8, 10, 14, 16, 18, 20]), 0)
    )
    end_time = factory.LazyAttribute(
        lambda obj: time(obj.start_time.hour + 2, 0)
    )
    capacity = factory.fuzzy.FuzzyInteger(10, 50, step=5)
    price_type = factory.fuzzy.FuzzyChoice(['fixed', 'hourly', 'dynamic'])
    fixed_price = factory.LazyAttribute(
        lambda obj: factory.fuzzy.FuzzyDecimal(80000, 150000, precision=0).fuzz() if obj.price_type == 'fixed' else None
    )
    hourly_price = factory.LazyAttribute(
        lambda obj: factory.fuzzy.FuzzyDecimal(40000, 80000, precision=0).fuzz() if obj.price_type == 'hourly' else None
    )
    base_weekday_price = factory.LazyAttribute(
        lambda obj: factory.fuzzy.FuzzyDecimal(70000, 120000, precision=0).fuzz() if obj.price_type == 'dynamic' else None
    )
    base_weekend_price = factory.LazyAttribute(
        lambda obj: factory.fuzzy.FuzzyDecimal(90000, 150000, precision=0).fuzz() if obj.price_type == 'dynamic' else None
    )
    is_active = True

class PricingRuleFactory(DjangoModelFactory):
    class Meta:
        model = PricingRule
    
    facility = factory.SubFactory(SportFacilityFactory)
    name = factory.LazyAttribute(lambda _: f'قانون {random.choice(["تخفیف صبحگاهی", "افزایش آخر هفته", "تخفیف ساعات خلوت", "قیمت ویژه"])}')
    description = factory.LazyAttribute(lambda obj: f'توضیحات {obj.name}')
    rule_type = factory.fuzzy.FuzzyChoice(['time_of_day', 'day_of_week', 'date_range', 'peak_hours'])
    
    # فیلدهای شرطی بر اساس نوع قانون
    start_time = factory.LazyAttribute(
        lambda obj: time(6, 0) if obj.rule_type == 'time_of_day' else None
    )
    end_time = factory.LazyAttribute(
        lambda obj: time(10, 0) if obj.rule_type == 'time_of_day' else None
    )
    days_of_week = factory.LazyAttribute(
        lambda obj: '4,5' if obj.rule_type == 'day_of_week' else ''
    )
    start_date = factory.LazyAttribute(
        lambda obj: timezone.now().date() if obj.rule_type == 'date_range' else None
    )
    end_date = factory.LazyAttribute(
        lambda obj: timezone.now().date() + timedelta(days=30) if obj.rule_type == 'date_range' else None
    )
    
    price_adjustment_type = factory.fuzzy.FuzzyChoice([
        'percentage_increase', 'percentage_decrease', 'fixed_increase', 'fixed_decrease'
    ])
    adjustment_value = factory.fuzzy.FuzzyDecimal(5, 30, precision=2)
    priority = factory.fuzzy.FuzzyInteger(1, 10)
    is_active = True

class HolidayFactory(DjangoModelFactory):
    class Meta:
        model = Holiday
    
    date = factory.LazyAttribute(
        lambda _: fake.date_between(start_date='today', end_date='+1y')
    )
    description = factory.LazyAttribute(
        lambda _: random.choice([
            'عید نوروز', 'عید فطر', 'عید قربان', 'تاسوعا', 'عاشورا',
            'نیمه شعبان', '۲۲ بهمن', '۱۳ فروردین', 'روز کارگر'
        ])
    )
    is_recurring = factory.fuzzy.FuzzyChoice([True, False])

class ReservationPackageFactory(DjangoModelFactory):
    class Meta:
        model = ReservationPackage
    
    name = factory.LazyAttribute(
        lambda obj: f'پکیج {obj.duration_months} ماهه ویژه'
    )
    facility = factory.SubFactory(SportFacilityFactory)
    duration_months = factory.fuzzy.FuzzyChoice([1, 3, 6, 12])
    discount_percentage = factory.LazyAttribute(
        lambda obj: {1: 5, 3: 10, 6: 15, 12: 20}[obj.duration_months]
    )
    min_sessions_per_month = factory.fuzzy.FuzzyInteger(4, 8)
    description = factory.LazyAttribute(
        lambda obj: f'پکیج {obj.duration_months} ماهه با {obj.discount_percentage}% تخفیف'
    )
    is_active = True

class RecurringReservationFactory(DjangoModelFactory):
    class Meta:
        model = RecurringReservation
    
    user = factory.SubFactory(UserFactory)
    session_time = factory.SubFactory(SessionTimeFactory)
    package = factory.SubFactory(ReservationPackageFactory)
    start_date = factory.LazyAttribute(
        lambda _: timezone.now().date() + timedelta(days=random.randint(1, 7))
    )
    end_date = factory.LazyAttribute(
        lambda obj: obj.start_date + timedelta(days=random.choice([30, 90, 180, 365]))
    )
    payment_frequency = factory.fuzzy.FuzzyChoice(['monthly', 'quarterly', 'yearly'])
    is_active = True

class DiscountFactory(DjangoModelFactory):
    class Meta:
        model = Discount
    
    name = factory.LazyAttribute(
        lambda _: random.choice([
            'تخفیف دانشجویی', 'تخفیف ویژه نوروز', 'کد تخفیف VIP',
            'تخفیف اولین خرید', 'جشنواره تابستانه'
        ])
    )
    description = factory.LazyAttribute(lambda obj: f'توضیحات {obj.name}')
    discount_type = factory.fuzzy.FuzzyChoice(['percentage', 'fixed'])
    amount = factory.LazyAttribute(
        lambda obj: factory.fuzzy.FuzzyDecimal(5, 30, precision=2).fuzz() 
        if obj.discount_type == 'percentage' 
        else factory.fuzzy.FuzzyDecimal(5000, 50000, precision=0).fuzz()
    )
    target_type = factory.fuzzy.FuzzyChoice(['facility', 'session', 'user', 'code'])
    
    # فیلدهای شرطی
    code = factory.LazyAttribute(
        lambda obj: fake_en.lexify('????-????').upper() if obj.target_type == 'code' else None
    )
    start_date = factory.LazyAttribute(lambda _: timezone.now().date())
    end_date = factory.LazyAttribute(
        lambda _: timezone.now().date() + timedelta(days=random.randint(30, 90))
    )
    is_active = True
    min_price = factory.fuzzy.FuzzyDecimal(50000, 100000, precision=0)
    max_discount = factory.fuzzy.FuzzyDecimal(50000, 200000, precision=0)
    usage_limit = factory.fuzzy.FuzzyInteger(10, 100)

class ReservationFactory(DjangoModelFactory):
    class Meta:
        model = Reservation
    
    user = factory.SubFactory(UserFactory)
    session_time = factory.SubFactory(SessionTimeFactory)
    date = factory.LazyAttribute(
        lambda obj: timezone.now().date() + timedelta(
            days=((obj.session_time.day_of_week - timezone.now().date().weekday()) % 7) + 7
        )
    )
    status = factory.fuzzy.FuzzyChoice(['pending', 'confirmed', 'cancelled', 'completed'])
    discount = factory.SubFactory(DiscountFactory)
    notes = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=100))
