from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

app_name = 'reservas'
urlpatterns = [

# Reservas
    path('', views.listar_reservas, name='listar_reservas'),
    path('registrar/', views.mostrar_registro_reserva, name='mostrar_registro_reserva'),
    path('guardar/', views.registrar_reserva, name='registrar_reserva'), 
    path('editar/<int:id_reserva>/', views.pre_editar_reserva, name='pre_editar_reserva'),
    path('actualizar/', views.editar_reserva, name='editar_reserva'),
    path('eliminar/<int:id_reserva>/', views.eliminar_reserva, name='eliminar_reserva'),
    path('reporte-pdf/', views.exportar_reservas_pdf, name='exportar_reservas_pdf'),
    path('analisis/', views.analisis_reservas, name='analisis_reservas'),
    path('confirmar-pago-final/<int:id_reserva>/', views.confirmar_pago_final_reserva, name='confirmar_pago_final_reserva'),
]