from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import Pedido
from datetime import date
from decimal import Decimal
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.db.models import Sum, Count
import json

# --- IMPORTACIONES DE OTRAS APPS ---
# Asegúrate de que estos nombres de app coincidan con tu proyecto
from mesas.models import Mesa
from menu.models import Menu, CategoriaMenu
from usuarios.models import Usuario
from ventas.models import Venta


# --- MÓDULO PEDIDOS ---

def listar_pedidos(request):
    if 'usuario_id' not in request.session:
        return redirect('login')
    
    # 1. Datos de sesión y auditoría
    rol = request.session.get('usuario_rol', '').lower()
    u_id = request.session.get('usuario_id')
    nombre_session = request.session.get('usuario_nombre', 'Usuario')
    generado_por = f"{rol.capitalize()}: {nombre_session}"

    # 2. Capturar parámetros de filtrado desde el GET
    q = request.GET.get('q')
    estado_f = request.GET.get('estado')

    # 3. Consulta base con optimización de relaciones
    query = Pedido.objects.all().select_related('id_plato', 'id_mesa')

    # 4. Filtro por Rol (Seguridad)
    if rol == 'cliente':
        query = query.filter(id_usuario=u_id)

    # 5. Aplicar Filtros de Búsqueda
    if q:
        # Filtramos por el número de la mesa relacionada
        query = query.filter(id_mesa__numero_mesa__icontains=q)
    
    if estado_f:
        query = query.filter(estado_pedido__iexact=estado_f)

    # 6. Ordenar (Agrupamos por mesa y luego por ID más reciente)
    pedidos = query.order_by('id_mesa__numero_mesa', '-id_pedido')
        
    context = {
        'pedidos': pedidos,
        'generado_por': generado_por
    }
    
    return render(request, 'pedido/listar.html', context)


def factura_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id_mesa=mesa_id)
    
    # Filtramos solo lo que ya se entregó al cliente
    pedidos = Pedido.objects.filter(
        id_mesa=mesa_id, 
        estado_pedido__iexact='ENTREGADO'
    )
    
    if not pedidos.exists():
        messages.warning(request, "Esta mesa no tiene pedidos entregados para facturar.")
        return redirect('pedidos:listar_pedidos')

    subtotal = sum(p.total for p in pedidos)
    iva = (subtotal * Decimal('0.19')).quantize(Decimal('0.01'))
    total = subtotal + iva

    context = {
        'mesa': mesa,
        'pedidos': pedidos,
        'subtotal': subtotal,
        'iva': iva,
        'total': total,
        'mesa_id': mesa_id
    }
    return render(request, 'pedido/confirmar_pago.html', context)


@transaction.atomic
def confirmar_pago_final(request, mesa_id):
    if request.method == 'POST':
        pedidos = Pedido.objects.filter(id_mesa=mesa_id, estado_pedido__iexact='Entregado')

        if not pedidos.exists():
            messages.warning(request, "No hay pedidos listos para cobrar en esta mesa.")
            return redirect('pedidos:listar_pedidos')

        # Cálculos económicos
        valor_subtotal = sum(p.total for p in pedidos)
        valor_iva = (valor_subtotal * Decimal('0.19')).quantize(Decimal('0.01'))
        valor_total = valor_subtotal + valor_iva
        metodo = request.POST.get('metodo_pago', 'Efectivo')

        try:
            # --- REGISTRO EN VENTAS ---
            # Usando los nombres exactos de tu modelo 'Venta'
            Venta.objects.create(
                categoria_venta='Restaurante',
                subtotal=valor_subtotal,
                iva=valor_iva,
                total=valor_total,
                metodo_pago=metodo,
                # Opcional: podrías asociar el ID del empleado desde la sesión
                id_empleado_id=request.session.get('usuario_id') 
            )

            # Actualizar pedidos a pagado
            pedidos.update(estado_pedido='pagado')
            
            # Liberar la mesa
            Mesa.objects.filter(id_mesa=mesa_id).update(estado='disponible')

            messages.success(request, f"¡Pago de ${valor_total} procesado y mesa liberada!")
            return redirect('pedidos:listar_pedidos')

        except Exception as e:
            messages.error(request, f"Error al registrar la venta: {e}")
            return redirect('pedidos:factura_mesa', mesa_id=mesa_id)

    return redirect('pedidos:listar_pedidos')


def mostrar_registro_pedido(request):
    if 'usuario_id' not in request.session:
        return redirect('usuarios:login')
    
    return render(request, 'pedido/registrar.html', {
        'mesas': Mesa.objects.all().order_by('numero_mesa'),
        'platos': Menu.objects.all(),
        'categorias': CategoriaMenu.objects.all()
    })


def guardar_pedido(request):
    if request.method == 'POST':
        u_id = request.session.get('usuario_id')
        mesa_id = request.POST.get('id_mesa')
        platos_ids = request.POST.getlist('platos[]')
        cantidades = request.POST.getlist('cantidades[]')

        if not platos_ids:
            messages.error(request, "No puedes guardar un pedido vacío")
            return redirect('pedidos:mostrar_registro_pedido')

        try:
            with transaction.atomic():
                usuario = Usuario.objects.get(id_usuario=u_id)
                mesa = Mesa.objects.get(id_mesa=mesa_id)
                hora_actual = timezone.now().strftime('%H:%M:%S')

                for i in range(len(platos_ids)):
                    plato = Menu.objects.get(id_plato=platos_ids[i])
                    cant = int(cantidades[i])
                    
                    Pedido.objects.create(
                        fecha_pedido=date.today(),
                        hora_pedido=hora_actual,
                        id_mesa=mesa,
                        id_usuario=usuario,
                        id_plato=plato,
                        cantidad=cant,
                        total=plato.precio * cant,
                        estado_pedido='Pendiente'
                    )

                # --- CAMBIO CLAVE AQUÍ ---
                # Usamos 'estado' en lugar de 'estado_mesa'
                # Lo ponemos en mayúsculas 'OCUPADA' para que coincida con tus badges
                mesa.estado = 'OCUPADA' 
                mesa.save()

            messages.success(request, f"Pedido guardado y Mesa {mesa_id} marcada como ocupada.")
            return redirect('pedidos:listar_pedidos')

        except Exception as e:
            messages.error(request, f"Error al guardar: {e}")
            return redirect('pedidos:mostrar_registro_pedido')


def pre_editar_pedido(request, id_pedido):
    if 'usuario_id' not in request.session:
        return redirect('usuarios:login')
    
    pedido = get_object_or_404(Pedido, id_pedido=id_pedido)
    return render(request, 'pedido/editar.html', {
        'pedido': pedido,
        'mesas': Mesa.objects.all().order_by('numero_mesa'),
        'platos': Menu.objects.all(),
        'categorias': CategoriaMenu.objects.all()
    })


def editar_pedido(request, id_pedido):
    if request.method == 'POST':
        pedido = get_object_or_404(Pedido, id_pedido=id_pedido)
        try:
            plato = Menu.objects.get(id_plato=request.POST.get('id_plato'))
            cantidad = int(request.POST.get('cantidad'))
            
            pedido.id_plato = plato
            pedido.id_mesa = Mesa.objects.get(id_mesa=request.POST.get('id_mesa'))
            pedido.cantidad = cantidad
            pedido.total = plato.precio * cantidad
            pedido.estado_pedido = request.POST.get('estado_pedido')
            pedido.save()
            
            messages.success(request, "Pedido actualizado correctamente.")
        except Exception as e:
            messages.error(request, f"Error al actualizar: {e}")
            
    return redirect('pedidos:listar_pedidos')


def eliminar_pedido(request, id_pedido):
    pedido = get_object_or_404(Pedido, id_pedido=id_pedido) 
    pedido.delete()
    messages.success(request, "Pedido eliminado.")
    return redirect('pedidos:listar_pedidos')


def exportar_pedidos_pdf(request):
    # 1. Capturar los mismos filtros que en la lista
    q = request.GET.get('q')
    estado_f = request.GET.get('estado')
    
    # 2. Obtener datos filtrados con relaciones optimizadas
    query = Pedido.objects.all().select_related('id_plato', 'id_mesa')
    
    if q:
        query = query.filter(id_mesa__numero_mesa__icontains=q)
    if estado_f:
        query = query.filter(estado_pedido__iexact=estado_f)

    # Ordenamos por mesa para que el agrupado en el PDF funcione igual que en la web
    pedidos = query.order_by('id_mesa__numero_mesa', '-id_pedido')

    # 3. Definir quién genera el reporte
    rol = request.session.get('usuario_rol', 'Empleado').capitalize()
    nombre_user = request.session.get('usuario_nombre', 'Usuario')
    generado_por = f"{rol}: {nombre_user}"

    # 4. Preparar el contexto para el template
    template = get_template('pedido/pdf_pedidos.html')
    context = {
        'pedidos': pedidos,
        'fecha': timezone.now(),
        'generado_por': generado_por,
    }
    
    # 5. Renderizar HTML a PDF
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    
    # Configuramos el nombre del archivo con la fecha actual
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    response['Content-Disposition'] = f'attachment; filename="reporte_pedidos_{fecha_str}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)
        
    return response

def analisis_pedidos(request):
    # Verificación de sesión
    if 'usuario_id' not in request.session:
        return redirect('login')

    # 1. KPIs Generales
    pedidos = Pedido.objects.all()
    total_pedidos = pedidos.count()
    # Sumamos el campo 'total' de todos los registros para obtener el ingreso real
    ingresos_totales = pedidos.aggregate(Sum('total'))['total__sum'] or 0
    # Promedio de gasto por cada ticket generado
    ticket_promedio = ingresos_totales / total_pedidos if total_pedidos > 0 else 0

    # 2. Distribución por Estado de Pedido (Dona)
    estados_query = pedidos.values('estado_pedido').annotate(cantidad=Count('id_pedido'))
    labels_est = [item['estado_pedido'].upper() for item in estados_query]
    valores_est = [item['cantidad'] for item in estados_query]

    # 3. Platos más Pedidos (Barras Horizontales)
    # IMPORTANTE: Ahora usamos Sum('cantidad') para capturar si un pedido incluyó varias unidades
    platos_top = pedidos.values('id_plato__nombre_plato').annotate(
        total_unidades=Sum('cantidad')
    ).order_by('-total_unidades')[:5]
    
    labels_platos = [item['id_plato__nombre_plato'] for item in platos_top]
    # Usamos total_unidades para que la gráfica refleje el volumen real de la cocina
    valores_platos = [item['total_unidades'] for item in platos_top]

    context = {
        'total_pedidos': total_pedidos,
        'ingresos_totales': float(ingresos_totales),
        'ticket_promedio': float(ticket_promedio),
        
        # Datos para Gráficas
        'labels_est': json.dumps(labels_est),
        'valores_est': json.dumps(valores_est),
        'labels_platos': json.dumps(labels_platos),
        'valores_platos': json.dumps(valores_platos),
    }
    
    # Asegúrate de que la ruta 'pedido/analisis_pedidos.html' coincida con tu estructura de carpetas
    return render(request, 'pedido/analisis_pedidos.html', context)