from django.contrib import admin
from .models import Address, City, Province
from unfold.admin import ModelAdmin


@admin.register(Address)
class AddressAdmin(ModelAdmin):
    list_display = ('id',  'city', 'province',)
    search_fields = ('address', 'city', 'province')
    list_filter = ('city', 'province',)

@admin.register(City)
class CityAdmin(ModelAdmin):
    list_display = ('id', 'name', 'province')
    search_fields = ('name',)
    list_filter = ('province',)

@admin.register(Province)
class ProvinceAdmin(ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
