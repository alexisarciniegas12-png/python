from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin


app_name = 'ventas'
urlpatterns = [
# MÓDULO DE VENTAS (Reportes y Control)
    path('', views.listar_ventas, name='listar_ventas'),
    path('eliminar/<int:id_venta>/', views.eliminar_venta, name='eliminar_venta'),
    path('inscripciones/pagar/<int:id_inscripcion>/', views.pagar_inscripcion, name='pagar_inscripcion'),
    path('reporte/pdf/', views.exportar_ventas_pdf, name='exportar_pdf'),
    path('analisis/', views.analisis_ventas, name='analisis_ventas'),
]