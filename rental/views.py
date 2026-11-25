from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from datetime import date
from decimal import Decimal

from .models import (
    Category, Inventory, Unit, Client, Rental,
    ReturnRecord, Deposit, ConditionRecord, Fine, Favorite
)
from .forms import RegisterForm, RentalCreateForm, ReturnForm, InventoryFilterForm


def is_staff_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def home(request):
    categories = Category.objects.all()[:6]
    popular = Inventory.objects.filter(is_active=True)[:8]
    return render(request, 'rental/home.html', {
        'categories': categories,
        'popular': popular,
    })


def catalog(request):
    form = InventoryFilterForm(request.GET or None)
    qs = Inventory.objects.filter(is_active=True).select_related('category')

    if form.is_valid():
        q = form.cleaned_data.get('q')
        category = form.cleaned_data.get('category')
        status = form.cleaned_data.get('status')
        sort = form.cleaned_data.get('sort') or 'name'

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(manufacturer__icontains=q))
        if category:
            qs = qs.filter(category=category)
        if status:
            qs = qs.filter(units__status=status).distinct()
        qs = qs.order_by(sort)

    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    # Preserve filters in pagination
    query = request.GET.copy()
    if 'page' in query:
        del query['page']

    return render(request, 'rental/catalog.html', {
        'page_obj': page_obj,
        'form': form,
        'query_string': query.urlencode(),
    })


def inventory_detail(request, pk):
    item = get_object_or_404(Inventory.objects.select_related('category'), pk=pk, is_active=True)
    units = item.units.all()
    return render(request, 'rental/detail.html', {
        'item': item,
        'units': units,
    })


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна! Добро пожаловать.')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'rental/register.html', {'form': form})


class UserLoginView(LoginView):
    template_name = 'rental/login.html'


@login_required
def cabinet(request):
    try:
        client = request.user.client_profile
    except Client.DoesNotExist:
        messages.warning(request, 'Профиль клиента не найден.')
        return redirect('home')

    rentals = client.rentals.select_related('unit__inventory').order_by('-created_at')
    return render(request, 'rental/cabinet.html', {
        'client': client,
        'rentals': rentals,
    })


@login_required
def request_rental(request, unit_id):
    unit = get_object_or_404(Unit, pk=unit_id)
    if unit.status != Unit.STATUS_AVAILABLE:
        messages.error(request, 'Эта единица сейчас недоступна.')
        return redirect('inventory_detail', pk=unit.inventory_id)

    try:
        client = request.user.client_profile
    except Client.DoesNotExist:
        messages.error(request, 'Сначала заполните профиль клиента.')
        return redirect('home')

    if request.method == 'POST':
        start = request.POST.get('start_date')
        end = request.POST.get('planned_end_date')
        if not start or not end:
            messages.error(request, 'Укажите даты.')
            return redirect('request_rental', unit_id=unit.id)

        # Check overlapping rentals
        overlap = Rental.objects.filter(
            unit=unit,
            status=Rental.STATUS_ACTIVE,
            start_date__lte=end,
            planned_end_date__gte=start,
        ).exists()
        if overlap:
            messages.error(request, 'На выбранные даты единица уже занята.')
            return redirect('request_rental', unit_id=unit.id)

        days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
        price = unit.inventory.daily_price * days

        with transaction.atomic():
            rental = Rental.objects.create(
                client=client,
                unit=unit,
                start_date=start,
                planned_end_date=end,
                total_price=price,
                status=Rental.STATUS_ACTIVE,
                employee=request.user if request.user.is_staff else None,
            )
            Deposit.objects.create(rental=rental, amount=Decimal('5000.00'))
            unit.status = Unit.STATUS_RENTED
            unit.save(update_fields=['status'])

        messages.success(request, f'Аренда оформлена! Номер выдачи #{rental.id}')
        return redirect('cabinet')

    return render(request, 'rental/request_rental.html', {'unit': unit})


@login_required
@user_passes_test(is_staff_user)
def staff_rentals(request):
    rentals = Rental.objects.select_related('client__user', 'unit__inventory').order_by('-created_at')
    status = request.GET.get('status')
    if status:
        rentals = rentals.filter(status=status)
    paginator = Paginator(rentals, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'rental/staff_rentals.html', {'page_obj': page_obj})


@login_required
@user_passes_test(is_staff_user)
def staff_create_rental(request):
    if request.method == 'POST':
        form = RentalCreateForm(request.POST)
        if form.is_valid():
            unit = form.cleaned_data['unit']
            start = form.cleaned_data['start_date']
            end = form.cleaned_data['planned_end_date']

            if unit.status != Unit.STATUS_AVAILABLE:
                messages.error(request, 'Единица не доступна для выдачи.')
                return redirect('staff_create_rental')

            overlap = Rental.objects.filter(
                unit=unit,
                status=Rental.STATUS_ACTIVE,
                start_date__lte=end,
                planned_end_date__gte=start,
            ).exists()
            if overlap:
                messages.error(request, 'Пересечение дат с существующей арендой.')
                return redirect('staff_create_rental')

            with transaction.atomic():
                rental = form.save(commit=False)
                rental.employee = request.user
                rental.status = Rental.STATUS_ACTIVE
                rental.save()
                Deposit.objects.create(
                    rental=rental,
                    amount=form.cleaned_data.get('deposit_amount') or Decimal('5000')
                )
                unit.status = Unit.STATUS_RENTED
                unit.save(update_fields=['status'])
                ConditionRecord.objects.create(
                    unit=unit,
                    condition=ConditionRecord.CONDITION_GOOD,
                    employee=request.user,
                    rental=rental,
                    description='Состояние при выдаче'
                )
            messages.success(request, f'Выдача #{rental.id} оформлена.')
            return redirect('staff_rentals')
    else:
        form = RentalCreateForm()
    return render(request, 'rental/staff_create_rental.html', {'form': form})


@login_required
@user_passes_test(is_staff_user)
def staff_return(request, rental_id):
    rental = get_object_or_404(Rental.objects.select_related('unit', 'client'), pk=rental_id)
    if rental.status != Rental.STATUS_ACTIVE:
        messages.warning(request, 'Эта выдача уже закрыта.')
        return redirect('staff_rentals')

    if request.method == 'POST':
        form = ReturnForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                ret = form.save(commit=False)
                ret.rental = rental
                ret.employee = request.user
                ret.save()

                rental.status = Rental.STATUS_CLOSED
                rental.actual_end_date = form.cleaned_data['return_date']
                rental.save(update_fields=['status', 'actual_end_date'])

                unit = rental.unit
                if form.cleaned_data['condition_ok']:
                    unit.status = Unit.STATUS_AVAILABLE
                    ConditionRecord.objects.create(
                        unit=unit,
                        condition=ConditionRecord.CONDITION_GOOD,
                        employee=request.user,
                        rental=rental,
                        description='Возврат без повреждений'
                    )
                else:
                    # Повреждение → ремонт + штраф
                    unit.status = Unit.STATUS_REPAIR
                    damage_cat = form.cleaned_data.get('damage_category') or Fine.DAMAGE_MEDIUM
                    ConditionRecord.objects.create(
                        unit=unit,
                        condition=ConditionRecord.CONDITION_DAMAGED,
                        employee=request.user,
                        rental=rental,
                        description=form.cleaned_data.get('damage_description', '')
                    )
                    Fine.objects.create(
                        return_record=ret,
                        damage_category=damage_cat,
                        amount=Fine.DAMAGE_AMOUNTS.get(damage_cat, Decimal('2500'))
                    )
                unit.save(update_fields=['status'])

                # Вернуть залог (если нет штрафа или частично)
                try:
                    dep = rental.deposit
                    dep.is_returned = True
                    dep.returned_at = timezone.now()
                    dep.save()
                except Deposit.DoesNotExist:
                    pass

            messages.success(request, 'Возврат оформлен.')
            return redirect('staff_rentals')
    else:
        form = ReturnForm(initial={'return_date': date.today()})

    return render(request, 'rental/staff_return.html', {
        'rental': rental,
        'form': form,
    })


@login_required
@user_passes_test(is_staff_user)
def dashboard(request):
    total_units = Unit.objects.count()
    available = Unit.objects.filter(status=Unit.STATUS_AVAILABLE).count()
    rented = Unit.objects.filter(status=Unit.STATUS_RENTED).count()
    in_repair = Unit.objects.filter(status=Unit.STATUS_REPAIR).count()
    active_rentals = Rental.objects.filter(status=Rental.STATUS_ACTIVE).count()
    total_fines = Fine.objects.aggregate(s=Sum('amount'))['s'] or 0
    paid_fines = Fine.objects.filter(is_paid=True).aggregate(s=Sum('amount'))['s'] or 0
    repair_share = round(in_repair / total_units * 100, 1) if total_units else 0

    # Simple chart data (last 6 months count) - simplified
    from django.db.models.functions import TruncMonth
    monthly = (
        Rental.objects
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(cnt=Count('id'))
        .order_by('month')[:6]
    )

    return render(request, 'rental/dashboard.html', {
        'total_units': total_units,
        'available': available,
        'rented': rented,
        'in_repair': in_repair,
        'active_rentals': active_rentals,
        'total_fines': total_fines,
        'paid_fines': paid_fines,
        'repair_share': repair_share,
        'monthly': list(monthly),
    })


def units_availability_api(request, inventory_id):
    """JSON endpoint for fetch without reload"""
    units = Unit.objects.filter(
        inventory_id=inventory_id,
        status=Unit.STATUS_AVAILABLE
    ).values('id', 'inventory_number', 'size', 'status')
    return JsonResponse({'units': list(units)})
