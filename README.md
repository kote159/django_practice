# Прокат спортивного инвентаря (вариант 15)

Учебный Django-проект.

## Запуск

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install django pillow
cd prokat_project
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Открой http://127.0.0.1:8000/

Админка: http://127.0.0.1:8000/admin/

## Что реализовано

- Модели: Category, Inventory, Unit, Client, Rental, ReturnRecord, Deposit, ConditionRecord, Fine, Favorite
- Регистрация / вход / выход
- Каталог с поиском, фильтрами, сортировкой, пагинацией (20)
- Карточка инвентаря + список единиц
- Заявка на аренду клиентом (проверка пересечения дат + transaction)
- Личный кабинет клиента
- Оформление выдачи сотрудником
- Возврат: фиксация состояния, авто-штраф по категории, перевод единицы в «ремонт»
- Дашборд со сводными показателями
- JSON API для доступных единиц
- Адаптивная базовая вёрстка

## Роли

- Гость — каталог
- Клиент — заявка, кабинет
- Сотрудник (is_staff) — выдачи, возвраты, дашборд
- Админ — полный доступ + /admin/
