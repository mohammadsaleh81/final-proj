import json
import uuid
from address.models import Province, City

# مسیر فایل JSON
with open("address/city.json", encoding="utf-8") as f:
    data = json.load(f)

# تفکیک استان‌ها و شهرها
provinces = [item for item in data if item["type"] == "province"]
cities = [item for item in data if item["type"] == "county"]

# ساخت دیکشنری برای استان‌ها با ID برای دسترسی سریع
province_obj_map = {}

# ایجاد یا یافتن استان‌ها
for item in provinces:
    province, _ = Province.objects.get_or_create(
        name=item["name"],
        defaults={
            "slug": item["slug"],
            "uuid": uuid.uuid4()
        }
    )
    province_obj_map[item["id"]] = province

# ایجاد یا یافتن شهرها
for item in cities:
    province_id = item["province_id"]
    province = province_obj_map.get(province_id)
    if not province:
        continue  # پرش در صورت نبود استان

    City.objects.get_or_create(
        name=item["name"],
        province=province,
        defaults={
            "slug": item["slug"],
            "uuid": uuid.uuid4()
        }
    )

print("✅ همه استان‌ها و شهرها با موفقیت اضافه شدند.")
