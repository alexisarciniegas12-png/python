from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

urlpatterns = [
     # Mesas 
    path('', views.listar_mesas, name='listar_mesas'),
    path('registrar/', views.mostrar_registro_mesa, name='mostrar_registro_mesa'),
    path('guardar/', views.registrar_mesa, name='registrar_mesa'),
    path('editar/<int:id_mesa>/', views.pre_editar_mesa, name='pre_editar_mesa'),
    path('actualizar/', views.editar_mesa, name='editar_mesa'),
    path('eliminar/<int:id_mesa>/', views.eliminar_mesa, name='eliminar_mesa'),
    path('mesas/reporte/pdf/', views.exportar_mesas_pdf, name='exportar_mesas_pdf'),
    path('mesas/analisis/', views.analisis_mesas, name='analisis_mesas'),

]