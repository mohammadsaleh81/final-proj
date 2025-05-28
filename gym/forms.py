
# forms.py - فرم‌های سفارشی برای ادمین
from django import forms
from .models import HallSession, RecurringReservation

class HallSessionForm(forms.ModelForm):
    """فرم سفارشی برای سانس‌ها"""
    available_days = forms.MultipleChoiceField(
        choices=HallSession.WEEKDAYS,
        widget=forms.CheckboxSelectMultiple,
        label="روزهای فعال"
    )

    class Meta:
        model = HallSession
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.available_days:
            self.fields['available_days'].initial = self.instance.available_days

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.available_days = [int(day) for day in self.cleaned_data['available_days']]
        if commit:
            instance.save()
        return instance


class RecurringReservationForm(forms.ModelForm):
    """فرم سفارشی برای رزروهای دوره‌ای"""
    
    class Meta:
        model = RecurringReservation
        fields = '__all__'
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        session = cleaned_data.get('session')
        day_of_week = cleaned_data.get('day_of_week')

        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError("تاریخ شروع باید کمتر از تاریخ پایان باشد")

        if session and day_of_week:
            if day_of_week not in session.available_days:
                raise forms.ValidationError("روز انتخاب شده در سانس فعال نیست")

        return cleaned_data

