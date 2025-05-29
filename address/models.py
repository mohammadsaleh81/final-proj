from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _


class Province(models.Model):
    name = models.CharField(_("نام استان"), max_length=60, null=False)
    slug = models.CharField(_("اسلاگ"), max_length=60)
    lat = models.DecimalField(_("عرض جغرافیایی"), max_digits=9, decimal_places=6, blank=True, null=True)
    lng = models.DecimalField(_("طول جغرافیایی"), max_digits=9, decimal_places=6, blank=True, null=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name=_("شناسه یکتا"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("استان")
        verbose_name_plural = _("استان‌ها")


class City(models.Model):
    name = models.CharField(_("نام شهر"), max_length=60, null=False)
    slug = models.CharField(_("اسلاگ"), max_length=60)
    lat = models.DecimalField(_("عرض جغرافیایی"), max_digits=9, decimal_places=6, blank=True, null=True)
    lng = models.DecimalField(_("طول جغرافیایی"), max_digits=9, decimal_places=6, blank=True, null=True)
    province = models.ForeignKey(Province, on_delete=models.PROTECT, verbose_name=_("استان"))
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name=_("شناسه یکتا"))


    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("شهر")
        verbose_name_plural = _("شهرها")


class Address (models.Model):
    address = models.CharField(verbose_name=_('آدرس کامل'), max_length=100, null=False)
    province = models.ForeignKey(Province, on_delete=models.PROTECT, null=True, verbose_name=_("استان"))
    city = models.ForeignKey(City, on_delete=models.PROTECT, null=True, verbose_name=_("شهر"))
    phone = models.CharField(
        verbose_name = _('شماره تلفن'),
        max_length=11,
        null=False, blank=False,
    )
    zipcode = models.CharField(
        verbose_name = _('کد پستی'),
        max_length=12,
        null=True, blank=True,
    )

    def __str__(self):
        return self.address

    class Meta:
        verbose_name = _("آدرس")
        verbose_name_plural = _("آدرس‌ها")

