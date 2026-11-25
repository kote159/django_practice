from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('catalog/<int:pk>/', views.inventory_detail, name='inventory_detail'),
    path('register/', views.register, name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('cabinet/', views.cabinet, name='cabinet'),
    path('rentals/request/<int:unit_id>/', views.request_rental, name='request_rental'),
    path('staff/rentals/', views.staff_rentals, name='staff_rentals'),
    path('staff/rentals/create/', views.staff_create_rental, name='staff_create_rental'),
    path('staff/returns/<int:rental_id>/', views.staff_return, name='staff_return'),
    path('staff/dashboard/', views.dashboard, name='dashboard'),
    path('api/units/<int:inventory_id>/', views.units_availability_api, name='units_api'),
]
