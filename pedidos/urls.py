from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

app_name = 'pedidos'
urlpatterns = [
# Pedidos 
    path('', views.listar_pedidos, name='listar_pedidos'),
    path('registrar/', views.mostrar_registro_pedido, name='mostrar_registro_pedido'),
    path('guardar/', views.guardar_pedido, name='guardar_pedido'),
    path('editar/<int:id_pedido>/', views.pre_editar_pedido, name='pre_editar_pedido'),
    path('actualizar/<int:id_pedido>/', views.editar_pedido, name='editar_pedido'),
    path('eliminar/<int:id_pedido>/', views.eliminar_pedido, name='eliminar_pedido'),
    path('factura/<int:mesa_id>/', views.factura_mesa, name='factura_mesa'),

    # Ruta para PROCESAR el pago (el botón de confirmar)
    path('confirmar-pago/<int:mesa_id>/', views.confirmar_pago_final, name='confirmar_pago_final'),
    path('reporte/pdf/', views.exportar_pedidos_pdf, name='exportar_pedidos_pdf'),
    path('analisis/', views.analisis_pedidos, name='analisis_pedidos'),
]