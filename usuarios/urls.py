from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('login/', views.iniciar_sesion, name='login'),
    path('registro/', views.registro, name='registro'),
    path('Menu/', views.menu, name='menu'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.cerrar_sesion, name='logout'),
    
    # Usuarios
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/registrar/', views.mostrar_registro_usuario, name='mostrar_registro_usuario'),
    path('usuarios/guardar/', views.registrar_usuario, name='registrar_usuario'),
    path('usuarios/editar/<int:id_usuario>/', views.pre_editar_usuario, name='pre_editar_usuario'),
    path('usuarios/actualizar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:id_usuario>/', views.eliminar_usuario, name='eliminar_usuario'),
    path('usuarios/exportar-pdf/', views.exportar_usuarios_pdf, name='exportar_usuarios_pdf'),
    path('usuarios/carga-masiva/', views.carga_masiva_usuarios, name='carga_masiva_usuarios'),
    path('analisis/', views.analisis_usuarios, name='analisis_usuarios'),

    path('reservas/', include('reservas.urls')),
    path('pedidos/', include('pedidos.urls')),
    path('mesas/', include('mesas.urls')),
    path('menu/', include('menu.urls')),
    path('eventos/', include('eventos.urls')),
    path('ventas/', include('ventas.urls', namespace='ventas')),
    
    
    

    

   

    

    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)