from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q
from datetime import date
from decimal import Decimal
from .models import Venta
from eventos.models import InscripcionEvento 
from pedidos.models import Pedido
from datetime import datetime, time
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from .utils import obtener_conversion_dinamica
import json
from django.db.models import Sum, Avg, Count
from django.shortcuts import render
def listar_ventas(request):
    if 'usuario_id' not in request.session:
        return redirect('login')

    # 1. Capturar filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    categoria = request.GET.get('categoria')
    metodo = request.GET.get('metodo')
    moneda_seleccionada = request.GET.get('moneda', 'USD')

    ventas_qs = Venta.objects.all().select_related(
        'id_pedido__id_mesa', 
        'id_evento'
    )

    # 2. Aplicación de filtros de fecha
    try:
        if fecha_inicio and fecha_fin:
            inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            ventas_qs = ventas_qs.filter(
                fecha_venta__range=(
                    datetime.combine(inicio_obj, time.min),
                    datetime.combine(fin_obj, time.max)
                )
            )
        elif fecha_inicio:
            dia_especifico = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            ventas_qs = ventas_qs.filter(
                fecha_venta__range=(
                    datetime.combine(dia_especifico, time.min),
                    datetime.combine(dia_especifico, time.max)
                )
            )
    except ValueError:
        pass

    # 3. Otros filtros
    if categoria:
        ventas_qs = ventas_qs.filter(categoria_venta=categoria)
        
    if metodo:
        ventas_qs = ventas_qs.filter(metodo_pago=metodo)

    ventas_qs = ventas_qs.order_by('-id_venta')

    # 4. Totales por Categoría (COP)
    total_restaurante = ventas_qs.filter(categoria_venta='Restaurante').aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    total_eventos = ventas_qs.filter(categoria_venta='Evento').aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    
    # NUEVO: Sumar la categoría Reserva
    total_reservas = ventas_qs.filter(categoria_venta='Reserva').aggregate(Sum('total'))['total__sum'] or Decimal('0.00')

    # 5. Total General (Suma de todas las categorías filtradas)
    # Es mejor sumar el total de ventas_qs directamente para que el total general 
    # siempre coincida con lo que se ve en la tabla inferior del Dashboard.
    total_general = ventas_qs.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')

    # --- CONSUMO DE API DINÁMICO ---
    tasa = obtener_conversion_dinamica(moneda_seleccionada)
    total_convertido = None
    
    if tasa:
        total_convertido = float(total_general) * tasa

    return render(request, 'ventas/listar.html', {
        'ventas': ventas_qs,
        'total_restaurante': total_restaurante,
        'total_eventos': total_eventos,
        'total_reservas': total_reservas, # Pasar a la plantilla
        'total_general': total_general,
        'total_convertido': total_convertido,
        'moneda_actual': moneda_seleccionada,
    })

def eliminar_venta(request, id_venta):
    # get_object_or_404 es lo que lanza ese error 404 si el ID no existe
    venta = get_object_or_404(Venta, id_venta=id_venta)
    venta.delete()
    return redirect('ventas:listar_ventas')
from django.utils import timezone # 1. Importante: Importar timezone

def pagar_inscripcion(request, id_inscripcion):
    inscripcion = get_object_or_404(InscripcionEvento, id_inscripcion=id_inscripcion)
    
    valor_unitario = Decimal(str(inscripcion.id_evento.valor_evento))
    cantidad = Decimal(str(inscripcion.cantidad_personas))
    
    total_pago = valor_unitario * cantidad
    subtotal = total_pago / Decimal('1.19')
    iva = total_pago - subtotal

    if request.method == 'POST':
        try:
            with transaction.atomic():
                Venta.objects.create(
                    # CAMBIO AQUÍ: Cambia date.today() por timezone.now()
                    fecha_venta=timezone.now(), 
                    categoria_venta='Evento',
                    subtotal=subtotal.quantize(Decimal('0.01')),
                    iva=iva.quantize(Decimal('0.01')),
                    descuento=Decimal('0.00'),
                    total=total_pago,
                    metodo_pago=inscripcion.metodo_pago,
                    id_cliente=inscripcion.id_cliente,
                    id_evento=inscripcion.id_evento,
                )
                
                inscripcion.estado_pago = 'Pagado'
                inscripcion.save()
                
                messages.success(request, f"¡Pago de {inscripcion.id_evento.nombre_evento} procesado con éxito!")
                return redirect('eventos:listar_inscripciones')
                
        except Exception as e:
            messages.error(request, f"Error al procesar el pago: {str(e)}")
            return redirect('eventos:listar_inscripciones')

    return render(request, 'eventos/inscripcion_evento/pagar_inscripcion.html', {
        'inscripcion': inscripcion,
        'total': total_pago
    })



def exportar_ventas_pdf(request):
    # 1. Seguridad: Solo usuarios logueados
    if 'usuario_id' not in request.session:
        return redirect('login')

    # 2. Capturar datos reales de quién genera el reporte
    rol_session = request.session.get('usuario_rol', 'Empleado').capitalize()
    nombre_session = request.session.get('usuario_nombre', 'Usuario')
    generado_por = f"{rol_session}: {nombre_session}"

    # 3. Aplicar los mismos filtros que en la lista y capturar Moneda
    fecha = request.GET.get('fecha')
    categoria = request.GET.get('categoria')
    metodo = request.GET.get('metodo')
    # Capturamos la moneda seleccionada (por defecto USD)
    moneda_seleccionada = request.GET.get('moneda', 'USD')

    ventas = Venta.objects.all().select_related('id_pedido__id_mesa', 'id_evento')

    if fecha:
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            ventas = ventas.filter(
                fecha_venta__range=(
                    datetime.combine(fecha_obj, time.min),
                    datetime.combine(fecha_obj, time.max)
                )
            )
        except ValueError:
            pass
            
    if categoria:
        ventas = ventas.filter(categoria_venta=categoria)
    if metodo:
        ventas = ventas.filter(metodo_pago=metodo)

    # 4. Totales y Consumo de API Dinámico
    total_general = ventas.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    
    # --- Lógica de API Dinámica para el PDF ---
    tasa = obtener_conversion_dinamica(moneda_seleccionada)
    total_convertido = None
    if tasa:
        # Convertimos el total general de COP a la moneda elegida (USD, EUR, MXN, etc.)
        total_convertido = float(total_general) * tasa
    # ---------------------------------

    data = {
        'ventas': ventas.order_by('-id_venta'),
        'total_general': total_general,
        'total_convertido': total_convertido, # Variable actualizada
        'moneda_actual': moneda_seleccionada, # Enviamos el nombre de la moneda
        'fecha': timezone.now(),
        'generado_por': generado_por,
        'empresa': 'Parrilla Express',
        'filtros': {'fecha': fecha, 'cat': categoria, 'met': metodo}
    }
    
    # 5. Renderizar el HTML
    template = get_template('ventas/pdf_reporte.html')
    html = template.render(data)
    
    # 6. Crear la respuesta del PDF
    response = HttpResponse(content_type='application/pdf')
    
    # Nombre de archivo dinámico incluyendo la moneda
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    filename = f"reporte_ventas_{moneda_seleccionada}_{fecha_str}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Ocurrió un error al generar el PDF de ventas', status=500)
        
    return response

def analisis_ventas(request):
    # --- KPIs Principales ---
    # El total general ya suma todas las categorías automáticamente
    total_recaudado = Venta.objects.aggregate(Sum('total'))['total__sum'] or 0
    
    # Ingresos desglosados por área de negocio
    ventas_restaurante = Venta.objects.filter(categoria_venta='Restaurante').aggregate(
        total=Sum('total')
    )['total'] or 0
    
    ventas_evento = Venta.objects.filter(categoria_venta='Evento').aggregate(
        total=Sum('total')
    )['total'] or 0

    # SE AGREGA: Cálculo para la nueva categoría de Reservas
    ventas_reserva = Venta.objects.filter(categoria_venta='Reserva').aggregate(
        total=Sum('total')
    )['total'] or 0

    # --- Gráfica 1: Comparativa de Ingresos (Barras) ---
    # Se añade 'Reservas' a las etiquetas y valores para que la gráfica se actualice
    labels_ingresos = ['Restaurante', 'Eventos', 'Reservas']
    valores_ingresos = [
        float(ventas_restaurante), 
        float(ventas_evento), 
        float(ventas_reserva)
    ]

    # --- Gráfica 2: Métodos de Pago (Dona) ---
    # Este conteo agrupa automáticamente por los métodos (Efectivo, Tarjeta, Transferencia)
    pagos_dist = Venta.objects.values('metodo_pago').annotate(
        count=Count('id_venta')
    )
    labels_pago = [item['metodo_pago'] for item in pagos_dist]
    valores_pago = [item['count'] for item in pagos_dist]

    context = {
        'total_recaudado': total_recaudado,
        'ventas_restaurante': ventas_restaurante,
        'ventas_evento': ventas_evento,
        'ventas_reserva': ventas_reserva, # Nueva variable para el cuadro verde
        
        # Datos formateados para Chart.js
        'labels_ingresos': json.dumps(labels_ingresos),
        'valores_ingresos': json.dumps(valores_ingresos),
        'labels_pago': json.dumps(labels_pago),
        'valores_pago': json.dumps(valores_pago),
    }
    
    return render(request, 'ventas/analisis_ventas.html', context)