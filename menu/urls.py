from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

app_name = 'menu'
urlpatterns = [

    # Menú
    path('', views.listar_menu, name='listar_menu'),
    path('registrar/', views.mostrar_registro_menu, name='mostrar_registro_menu'),
    path('guardar/', views.registrar_menu, name='registrar_menu'),
    path('editar/<int:id_plato>/', views.pre_editar_menu, name='pre_editar_menu'),
    path('actualizar/', views.editar_menu, name='editar_menu'),
    path('eliminar/<int:id_plato>/', views.eliminar_menu, name='eliminar_menu'),
    path('reporte-pdf/', views.exportar_menu_pdf, name='exportar_menu_pdf'),
    path('carga-masiva/', views.carga_masiva_menu, name='carga_masiva_menu'), 
    path('analisis/', views.analisis_menu, name='analisis_menu'),
]