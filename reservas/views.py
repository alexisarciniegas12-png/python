from django.shortcuts import render, redirect, get_object_or_404
from .models import  Reserva
from django.contrib import messages

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import get_template
from datetime import date
from xhtml2pdf import pisa
from django.utils import timezone
import json
from django.db.models import Count, Sum
from menu.models import CategoriaMenu, Menu
from ventas.models import Venta
from decimal import Decimal
# --- MÓDULO RESERVAS ---

def listar_reservas(request):
    rol = request.session.get('usuario_rol', '').lower()
    u_id = request.session.get('usuario_id')
    
    # Capturar el filtro de fecha
    fecha_f = request.GET.get('fecha')

    if rol == 'cliente':
        # El cliente ve sus reservas, pero EXCLUIMOS las que están 'CANCELADA'
        # Así, cuando el cliente "elimina" (cambia estado), desaparece de su vista.
        reservas = Reserva.objects.filter(id_cliente=u_id).exclude(estado='CANCELADA')
    else:
        # Administrador/Empleado ve absolutamente todo lo que existe en la DB
        # Incluyendo las que el cliente canceló pero el admin aún no borra.
        reservas = Reserva.objects.all()
        
        # Filtros adicionales solo para staff
        cliente_nom = request.GET.get('cliente')
        estado_f = request.GET.get('estado')
        
        if cliente_nom:
            reservas = reservas.filter(nombre_cliente__icontains=cliente_nom)
        if estado_f:
            reservas = reservas.filter(estado__iexact=estado_f)

    # Filtro de fecha común para ambos
    if fecha_f:
        reservas = reservas.filter(fecha=fecha_f)

    return render(request, 'reservas/listar.html', {
        'reservas': reservas.order_by('-fecha')
    })

def mostrar_registro_reserva(request):
    if 'usuario_id' not in request.session: 
        return redirect('usuarios:login')
    return render(request, 'reservas/registrar.html')

def registrar_reserva(request):
    u_id = request.session.get('usuario_id')
    if not u_id:
        return redirect('login')

    if request.method == 'POST':
        try:
            fecha = request.POST.get('fecha')
            hora = request.POST.get('hora')
            sede = request.POST.get('sede')
            n_personas = int(request.POST.get('n_personas') or 1)
            tipo_reserva = request.POST.get('tipo_reserva')
            
            monto_total = 0
            nombres_platos_str = ""

            if tipo_reserva == 'solo_mesa':
                monto_total = n_personas * 10000
            else:
                id_platos = request.POST.getlist('platos_seleccionados')
                platos_db = Menu.objects.filter(id_menu__in=id_platos)
                suma_platos = sum(p.precio for p in platos_db)
                monto_total = (n_personas * 5000) + suma_platos
                nombres_platos_str = ", ".join([p.nombre_plato for p in platos_db])

            # Validación de Aforo
            ocupacion_actual = Reserva.objects.filter(
                fecha=fecha, hora=hora, sede=sede
            ).aggregate(total=Sum('n_personas'))['total'] or 0

            if ocupacion_actual + n_personas > 50:
                messages.error(request, "No hay cupos suficientes.")
                return redirect('reservas:mostrar_registro_reserva')

            # Guardar Reserva
            Reserva.objects.create(
                nombre_cliente=request.POST.get('nombre_cliente'),
                fecha=fecha,
                hora=hora,
                n_personas=n_personas,
                tipo_reserva=tipo_reserva,
                monto_pago=monto_total,
                pago_confirmado=False,
                platos_seleccionados=nombres_platos_str,
                sede=sede,
                estado='Pendiente',
                id_cliente=u_id
            )

            messages.success(request, f"¡Reserva registrada! Total: ${monto_total:,.0f}")
            return redirect('reservas:listar_reservas')
        
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect('reservas:mostrar_registro_reserva')

    # --- LÓGICA GET (Aquí aplicamos lo de tu listar_menu) ---
    
    # IMPORTANTE: Usamos el filtro 'estado' exactamente como en tu código de menú
    platos_disponibles = Menu.objects.filter(estado__iexact='DISPONIBLE')
    
    ocupacion_queryset = Reserva.objects.filter(
        fecha__gte=date.today()
    ).values('fecha', 'hora', 'sede').annotate(total=Sum('n_personas'))

    ocupacion_data = {
        f"{item['fecha']}_{item['hora'].strftime('%H:%M')}_{item['sede']}": item['total']
        for item in ocupacion_queryset
    }

    return render(request, 'registrar.html', {
        'ocupacion_json': json.dumps(ocupacion_data),
        'platos': platos_disponibles # Ahora sí coincidirá con tu lista de menú
    })

def pre_editar_reserva(request, id_reserva): 
    if 'usuario_id' not in request.session: 
        return redirect('usuarios:login')
    
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    return render(request, 'reservas/editar.html', {'reserva': reserva})

# Agregamos id_reserva aquí para que coincida con la URL y la imagen del error
def editar_reserva(request):
    # 1. Obtención de datos iniciales comunes
    id_reserva = request.POST.get('id_reserva') if request.method == 'POST' else request.GET.get('id')
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    rol_usuario = request.session.get('usuario_rol', '').lower()

    # 2. BLOQUEO DE SEGURIDAD: Si ya pagó, el cliente no puede editar
    if reserva.pago_confirmado and rol_usuario == 'cliente':
        messages.error(request, "Esta reserva ya ha sido pagada y no se permiten más modificaciones.")
        return redirect('reservas:listar_reservas')

    if request.method == 'POST':
        try:
            # Captura de datos básicos y protección de 'hora'
            nueva_hora = request.POST.get('hora')
            reserva.sede = request.POST.get('sede')
            reserva.n_personas = int(request.POST.get('n_personas'))
            reserva.fecha = request.POST.get('fecha')
            reserva.tipo_reserva = request.POST.get('tipo_reserva')
            
            if nueva_hora:
                reserva.hora = nueva_hora

            # Captura de Estado (Solo para Admin/Empleado)
            nuevo_estado = request.POST.get('estado')
            if rol_usuario != 'cliente' and nuevo_estado:
                reserva.estado = nuevo_estado

            # Lógica de Precios (COP)
            PRECIO_SOLO_MESA = Decimal('10000.00')
            PRECIO_BASE_MENU = Decimal('5000.00')

            # Gestión de platos y Cálculo de Monto
            if reserva.tipo_reserva == 'mesa_menu':
                platos_ids = request.POST.getlist('platos_seleccionados')
                platos_queryset = Menu.objects.filter(id_menu__in=platos_ids)
                
                nombres = platos_queryset.values_list('nombre_plato', flat=True)
                reserva.platos_seleccionados = ", ".join(nombres)
                
                total_platos = sum(p.precio for p in platos_queryset)
                reserva.monto_pago = (reserva.n_personas * PRECIO_BASE_MENU) + total_platos
            else:
                reserva.platos_seleccionados = ""
                reserva.monto_pago = reserva.n_personas * PRECIO_SOLO_MESA

            # Guardado final
            reserva.save()

            messages.success(request, f"Reserva #{id_reserva} actualizada correctamente.")
            return redirect('reservas:listar_reservas')

        except Exception as e:
            messages.error(request, f"Error al actualizar: {e}")
            return redirect('reservas:listar_reservas')

    # --- Lógica GET ---
    platos = Menu.objects.all()

    # Ocupación para validación en tiempo real en el frontend
    ocupacion_query = Reserva.objects.values('fecha', 'hora', 'sede').annotate(total=Sum('n_personas'))
    ocupacion_data = {
        f"{reg['fecha']}_{reg['hora'].strftime('%H:%M')}_{reg['sede']}": reg['total'] 
        for reg in ocupacion_query
    }

    context = {
        'reserva': reserva,
        'platos': platos,
        'ocupacion_json': json.dumps(ocupacion_data, default=str)
    }
    return render(request, 'reservas/editar_reserva.html', context)

@transaction.atomic
def eliminar_reserva(request, id_reserva):
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)
    rol = request.session.get('usuario_rol', '').lower()
    
    try:
        from mesas.models import Mesa
        
        # 1. Siempre buscamos y borramos la mesa física asociada
        mesa_a_borrar = Mesa.objects.filter(
            estado='RESERVADA', 
            capacidad=reserva.n_personas
        ).first()

        if mesa_a_borrar:
            mesa_a_borrar.delete()

        # 2. Lógica de eliminación según el rol
        if rol == 'cliente':
            # Si es cliente: NO se elimina de la DB. 
            # Cambia a CANCELADA (así el admin la sigue viendo, pero el cliente no)
            reserva.estado = 'CANCELADA'
            reserva.save()
            messages.success(request, "Has cancelado tu reserva correctamente.")
        
        else:
            # Si es Admin o Empleado: ELIMINACIÓN TOTAL
            # Se borra de la DB, por lo tanto desaparece para ambos
            reserva.delete()
            messages.success(request, "La reserva ha sido eliminada permanentemente del sistema.")
            
    except Exception as e:
        messages.error(request, f"Error al procesar la solicitud: {e}")

    return redirect('reservas:listar_reservas')
def exportar_reservas_pdf(request):
    # 1. Obtener datos de la sesión
    rol_raw = request.session.get('usuario_rol', 'Empleado')
    rol = rol_raw.lower()
    u_id = request.session.get('usuario_id')
    nombre_usuario = request.session.get('usuario_nombre', 'Usuario')
    
    rol_formateado = rol_raw.capitalize()
    
    fecha_f = request.GET.get('fecha')
    cliente_f = request.GET.get('cliente')
    estado_f = request.GET.get('estado')
    
    # 2. Lógica de seguridad y definición de quién genera el reporte
    if rol == 'cliente':
        reservas = Reserva.objects.filter(id_cliente=u_id)
        generado_por = f"Cliente: {nombre_usuario}"
    else:
        reservas = Reserva.objects.all()
        generado_por = f"{rol_formateado}: {nombre_usuario}"
        
        if cliente_f:
            reservas = reservas.filter(nombre_cliente__icontains=cliente_f)
        if estado_f:
            reservas = reservas.filter(estado__iexact=estado_f)

    if fecha_f:
        reservas = reservas.filter(fecha=fecha_f)

    reservas = reservas.order_by('-fecha', '-hora')

    # 3. Capturar fecha y hora exacta de generación
    ahora = timezone.now()

    # 4. Renderizado del PDF
    template = get_template('reservas/pdf_reservas.html')
    context = {
        'reservas': reservas, 
        'fecha': timezone.now(), 
        'generado_por': generado_por
    }
    
    html = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    # El nombre del archivo ahora incluye fecha y hora para evitar duplicados
    timestamp = timezone.now().strftime("%d-%m-%Y")
    response['Content-Disposition'] = f'attachment; filename="reporte_reservas_{timestamp}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar el reporte', status=500)
        
    return response

def analisis_reservas(request):
    # Verificación de seguridad
    if 'usuario_id' not in request.session:
        return redirect('login')

    # 1. KPIs Generales
    total_reservas = Reserva.objects.count()
    total_personas = Reserva.objects.aggregate(Sum('n_personas'))['n_personas__sum'] or 0

    # 2. Distribución por Estado (para gráfico de barras/dona)
    por_estado = Reserva.objects.values('estado').annotate(total=Count('id_reserva'))
    
    labels_estado = [item['estado'] for item in por_estado]
    valores_estado = [item['total'] for item in por_estado]

    # 3. Reservas por Sede (útil si manejas varios locales)
    por_sede = Reserva.objects.values('sede').annotate(total=Count('id_reserva'))
    labels_sede = [item['sede'] for item in por_sede]
    valores_sede = [item['total'] for item in por_sede]

    context = {
        'total_reservas': total_reservas,
        'total_personas': total_personas,
        'labels_estado': json.dumps(labels_estado),
        'valores_estado': json.dumps(valores_estado),
        'labels_sede': json.dumps(labels_sede),
        'valores_sede': json.dumps(valores_sede),
    }

    return render(request, 'reservas/analisis.html', context)

def obtener_disponibilidad(fecha, sede):
    capacidad_total = 50
    # Sumamos las personas de las reservas confirmadas/pendientes para ese día
    ocupacion = Reserva.objects.filter(fecha=fecha, sede=sede).values('hora').annotate(total=Sum('n_personas'))
    # Esto te daría un diccionario de {hora: personas_ocupadas}

@transaction.atomic
def confirmar_pago_final_reserva(request, id_reserva):
    reserva = get_object_or_404(Reserva, id_reserva=id_reserva)

    if request.method == 'POST':
        # 1. Evitar pagos duplicados
        if reserva.pago_confirmado:
            messages.warning(request, "Esta reserva ya ha sido pagada.")
            return redirect('reservas:listar_reservas')

        try:
            # 2. Cálculos
            valor_total = Decimal(str(reserva.monto_pago))
            valor_subtotal = (valor_total / Decimal('1.19')).quantize(Decimal('0.01'))
            valor_iva = (valor_total - valor_subtotal).quantize(Decimal('0.01'))
            metodo = request.POST.get('metodo_pago', 'Tarjeta')
            
            # Obtener ID de empleado de la sesión
            empleado_id = request.session.get('usuario_id')

            # 3. Crear registro en Ventas
            Venta.objects.create(
                categoria_venta='Reserva',
                subtotal=valor_subtotal,
                iva=valor_iva,
                total=valor_total,
                metodo_pago=metodo,
                id_empleado_id=empleado_id
            )

            # 4. Actualizar estado de la Reserva
            reserva.pago_confirmado = True
            # ELIMINADO: reserva.estado = 'Confirmada' 
            # El estado se mantiene como 'Pendiente' o el que tuviera originalmente
            reserva.save()

            messages.success(request, f"¡Pago de ${valor_total} procesado con éxito!")
            return redirect('reservas:listar_reservas')

        except Exception as e:
            messages.error(request, f"Error al procesar el pago: {str(e)}")
            return render(request, 'reservas/pagar_reserva.html', {'reserva': reserva})

    return render(request, 'reservas/pagar_reserva.html', {'reserva': reserva})