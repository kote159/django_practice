from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Client, Rental, ReturnRecord, Unit, Inventory, Category, Fine

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    phone = forms.CharField(max_length=20, label='Телефон')
    first_name = forms.CharField(max_length=50, label='Имя', required=False)
    last_name = forms.CharField(max_length=50, label='Фамилия', required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
            Client.objects.create(user=user, phone=self.cleaned_data['phone'])
        return user


class RentalCreateForm(forms.ModelForm):
    class Meta:
        model = Rental
        fields = ('client', 'unit', 'start_date', 'planned_end_date', 'total_price')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'planned_end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    deposit_amount = forms.DecimalField(label='Сумма залога', min_value=0, initial=5000)


class ReturnForm(forms.ModelForm):
    class Meta:
        model = ReturnRecord
        fields = ('return_date', 'condition_ok', 'damage_description')
        widgets = {
            'return_date': forms.DateInput(attrs={'type': 'date'}),
        }

    damage_category = forms.ChoiceField(
        choices=Fine.DAMAGE_CHOICES,
        required=False,
        label='Категория повреждения'
    )


class InventoryFilterForm(forms.Form):
    q = forms.CharField(required=False, label='Поиск')
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='Все категории'
    )
    status = forms.ChoiceField(
        choices=[('', 'Любой статус')] + list(Unit.STATUS_CHOICES),
        required=False
    )
    sort = forms.ChoiceField(
        choices=[
            ('name', 'По названию'),
            ('daily_price', 'По цене ↑'),
            ('-daily_price', 'По цене ↓'),
            ('category', 'По категории'),
        ],
        required=False,
        initial='name'
    )
