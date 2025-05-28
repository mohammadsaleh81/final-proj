import requests
import json

# آدرس URL مورد نظر
url = 'https://holidayapi.ir/jalali/1404/06/02'

# ارسال درخواست GET با استفاده از کتابخانه requests

response = requests.get(url)
response.raise_for_status()  # اگر خطایی در درخواست رخ دهد (مثلا 404 یا 500)، استثنا پرتاب می‌کند

# تبدیل پاسخ JSON به دیکشنری پایتون
data = response.json()

# چاپ داده‌ها
print(data)

print("-" * 20) # برای جدا کردن دو روش

