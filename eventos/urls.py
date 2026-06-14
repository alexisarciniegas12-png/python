from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin


app_name = 'eventos'
urlpatterns = [

# --- MÓDULO DE EVENTOS 
    path('', views.listar_eventos, name='listar_eventos'),
    path('registrar/', views.mostrar_registro_evento, name='mostrar_registro_evento'),
    path('guardar/', views.registrar_evento, name='registrar_evento'),
    path('editar/<int:id_evento>/', views.pre_editar_evento, name='pre_editar_evento'),
    path('actualizar/', views.editar_evento, name='editar_evento'),
    path('eliminar/<int:id_evento>/', views.eliminar_evento, name='eliminar_evento'),    

    # --- MÓDULO DE INSCRIPCIONES 
    path('inscripciones/', views.listar_inscripciones, name='listar_inscripciones'),
    path('inscripciones/registrar/', views.mostrar_registro_inscripcion, name='mostrar_registro_inscripcion'),
    path('inscripciones/guardar/', views.registrar_inscripcion, name='registrar_inscripcion'),
    path('inscripciones/editar/<int:id_inscripcion>/', views.pre_editar_inscripcion, name='pre_editar_inscripcion'),
    path('inscripciones/actualizar/<int:id_inscripcion>/', views.editar_inscripcion, name='editar_inscripcion'),
    path('inscripciones/eliminar/<int:id_inscripcion>/', views.eliminar_inscripcion, name='eliminar_inscripcion'),

    path('gestion/inscripcion/editar/<int:id_inscripcion>/', views.pre_editar_inscripcion_admin, name='pre_editar_inscripcion_admin'),
    
    path('gestion/inscripcion/actualizar/<int:id_inscripcion>/', views.editar_inscripcion_admin, name='editar_inscripcion_admin'),
    path('eliminar-inscripcion-admin/<int:id_inscripcion>/', views.eliminar_inscripcion_admin, name='eliminar_inscripcion_admin'),

    path('inscripciones/registrar-admin/', views.mostrar_registro_admin, name='mostrar_registro_admin'),
    path('exportar_eventos_pdf/', views.exportar_eventos_pdf, name='exportar_eventos_pdf'),
    path('reporte-general-eventos/', views.exportar_reporte_general_eventos, name='url_reporte_general_eventos'),
    path('inscripciones/reporte-pdf/', views.generar_pdf_inscripciones_filtradas, name='pdf_inscripciones_busqueda'),
    path('analisis/', views.analisis_eventos, name='analisis_eventos'),
    path('analisis-inscripciones/', views.analisis_inscripciones, name='analisis_inscripciones'),
    

]