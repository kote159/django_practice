from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    description = models.TextField('Описание', blank=True)
    base_fine_rate = models.DecimalField(
        'Базовая ставка штрафа',
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Inventory(models.Model):
    name = models.CharField('Название', max_length=200)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='inventories',
        verbose_name='Категория'
    )
    description = models.TextField('Описание', blank=True)
    manufacturer = models.CharField('Производитель', max_length=100, blank=True)
    daily_price = models.DecimalField(
        'Цена за сутки',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    image = models.ImageField('Фото', upload_to='inventory/', blank=True, null=True)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Вид инвентаря'
        verbose_name_plural = 'Виды инвентаря'
        ordering = ['name']

    def __str__(self):
        return self.name


class Unit(models.Model):
    STATUS_AVAILABLE = 'available'
    STATUS_RENTED = 'rented'
    STATUS_REPAIR = 'repair'
    STATUS_WRITTEN_OFF = 'written_off'
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, 'Доступен'),
        (STATUS_RENTED, 'Выдан'),
        (STATUS_REPAIR, 'В ремонте'),
        (STATUS_WRITTEN_OFF, 'Списан'),
    ]

    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.PROTECT,
        related_name='units',
        verbose_name='Вид инвентаря'
    )
    inventory_number = models.CharField('Инвентарный номер', max_length=50, unique=True)
    size = models.CharField('Размер / комплектация', max_length=30, blank=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_AVAILABLE
    )
    purchase_date = models.DateField('Дата поступления', null=True, blank=True)
    notes = models.TextField('Примечания', blank=True)

    class Meta:
        verbose_name = 'Единица инвентаря'
        verbose_name_plural = 'Единицы инвентаря'
        ordering = ['inventory_number']

    def __str__(self):
        return f'{self.inventory_number} ({self.inventory.name})'


class Client(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='client_profile',
        verbose_name='Пользователь'
    )
    phone = models.CharField('Телефон', max_length=20)
    passport_data = models.CharField('Паспортные данные', max_length=100, blank=True)
    created_at = models.DateTimeField('Дата регистрации', auto_now_add=True)

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} ({self.phone})'


class Rental(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_CLOSED = 'closed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Активна'),
        (STATUS_CLOSED, 'Закрыта'),
        (STATUS_CANCELLED, 'Отменена'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='rentals',
        verbose_name='Клиент'
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name='rentals',
        verbose_name='Единица'
    )
    start_date = models.DateField('Дата выдачи')
    planned_end_date = models.DateField('Плановая дата возврата')
    actual_end_date = models.DateField('Фактическая дата возврата', null=True, blank=True)
    total_price = models.DecimalField(
        'Стоимость аренды',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )
    employee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_rentals',
        verbose_name='Сотрудник'
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Выдача'
        verbose_name_plural = 'Выдачи'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(planned_end_date__gte=models.F('start_date')),
                name='rental_end_after_start'
            )
        ]

    def __str__(self):
        return f'Выдача #{self.pk}: {self.unit} → {self.client}'


class ReturnRecord(models.Model):
    rental = models.OneToOneField(
        Rental,
        on_delete=models.CASCADE,
        related_name='return_record',
        verbose_name='Выдача'
    )
    return_date = models.DateField('Дата возврата')
    condition_ok = models.BooleanField('Состояние в норме', default=True)
    damage_description = models.TextField('Описание повреждения', blank=True)
    employee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_returns',
        verbose_name='Сотрудник'
    )

    class Meta:
        verbose_name = 'Возврат'
        verbose_name_plural = 'Возвраты'
        ordering = ['-return_date']

    def __str__(self):
        return f'Возврат по выдаче #{self.rental_id}'


class Deposit(models.Model):
    rental = models.OneToOneField(
        Rental,
        on_delete=models.CASCADE,
        related_name='deposit',
        verbose_name='Выдача'
    )
    amount = models.DecimalField(
        'Сумма залога',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    is_returned = models.BooleanField('Залог возвращён', default=False)
    returned_at = models.DateTimeField('Дата возврата залога', null=True, blank=True)

    class Meta:
        verbose_name = 'Залог'
        verbose_name_plural = 'Залоги'

    def __str__(self):
        return f'Залог {self.amount} ₽ по выдаче #{self.rental_id}'


class ConditionRecord(models.Model):
    CONDITION_GOOD = 'good'
    CONDITION_DAMAGED = 'damaged'
    CONDITION_BROKEN = 'broken'
    CONDITION_CHOICES = [
        (CONDITION_GOOD, 'Хорошее'),
        (CONDITION_DAMAGED, 'Повреждено'),
        (CONDITION_BROKEN, 'Сломано'),
    ]

    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='condition_records',
        verbose_name='Единица'
    )
    check_date = models.DateTimeField('Дата осмотра', auto_now_add=True)
    condition = models.CharField('Состояние', max_length=20, choices=CONDITION_CHOICES)
    description = models.TextField('Описание', blank=True)
    employee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='condition_checks',
        verbose_name='Сотрудник'
    )
    rental = models.ForeignKey(
        Rental,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='condition_records',
        verbose_name='Связанная выдача'
    )

    class Meta:
        verbose_name = 'Запись о состоянии'
        verbose_name_plural = 'Записи о состоянии'
        ordering = ['-check_date']

    def __str__(self):
        return f'{self.unit} — {self.get_condition_display()} ({self.check_date:%d.%m.%Y})'


class Fine(models.Model):
    DAMAGE_MINOR = 'minor'
    DAMAGE_MEDIUM = 'medium'
    DAMAGE_MAJOR = 'major'
    DAMAGE_CHOICES = [
        (DAMAGE_MINOR, 'Незначительное'),
        (DAMAGE_MEDIUM, 'Среднее'),
        (DAMAGE_MAJOR, 'Серьёзное'),
    ]

    # Примерные суммы по категориям повреждения
    DAMAGE_AMOUNTS = {
        DAMAGE_MINOR: Decimal('500.00'),
        DAMAGE_MEDIUM: Decimal('2500.00'),
        DAMAGE_MAJOR: Decimal('8000.00'),
    }

    return_record = models.ForeignKey(
        ReturnRecord,
        on_delete=models.CASCADE,
        related_name='fines',
        verbose_name='Возврат'
    )
    damage_category = models.CharField(
        'Категория повреждения',
        max_length=20,
        choices=DAMAGE_CHOICES
    )
    amount = models.DecimalField(
        'Сумма штрафа',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    is_paid = models.BooleanField('Оплачен', default=False)
    created_at = models.DateTimeField('Начислен', auto_now_add=True)

    class Meta:
        verbose_name = 'Штраф'
        verbose_name_plural = 'Штрафы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Штраф {self.amount} ₽ ({self.get_damage_category_display()})'

    def save(self, *args, **kwargs):
        # Автоматический расчёт суммы по категории, если не задана
        if not self.amount or self.amount == 0:
            self.amount = self.DAMAGE_AMOUNTS.get(self.damage_category, Decimal('0.00'))
        super().save(*args, **kwargs)


class Favorite(models.Model):
    """Промежуточная модель для M2M: избранное клиента."""
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Клиент'
    )
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Инвентарь'
    )
    added_at = models.DateTimeField('Добавлено', auto_now_add=True)

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        unique_together = ('client', 'inventory')
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.client} → {self.inventory}'
