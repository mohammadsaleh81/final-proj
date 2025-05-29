import requests
from datetime import datetime, date
from gym.models import Holiday
import jdatetime

years  = [1404, 1405, 1406]

for y in years:
    res = requests.get(f'https://api.persian-calendar.ir/api/v1/calendar/{y}/holidays')
    print(res.status_code)


    data = res.json()['data']


    for day in data:

        # d = jdatetime.date.fromgregorian(date=day['date']).strftime("%Y/%m/%d")
        item = day['date'].split('/')
        year = item[0]
        month = item[1]
        dayy = item[2]
        # print(year, '      ',  month, '     ', dayy)
        print("******************")

        jday = jdatetime.date(int(year), int(month), int(dayy))
        ff = jdatetime.date.togregorian(jday)
        print(type(ff))

        hol = Holiday()
        hol.date = ff
        hol.description = day['holidayDesription']
        hol.jalali_month = month
        hol.jalali_day = dayy
        hol.save()


