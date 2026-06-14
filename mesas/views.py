from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import  Mesa
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import json

# --- CRUD MESAS ---

def listar_mesas(request):
    if 'usuario_id' not in request.session: 
        return redirect('login')
    
    # 1. Capturar datos del usuario para el encabezado
    rol_session = request.session.get('usuario_rol', 'Empleado').capitalize()
    nombre_session = request.session.get('usuario_nombre', 'Usuario')
    generado_por = f"{rol_session}: {nombre_session}"
    
    # 2. Obtener parámetros de filtrado desde el request.GET
    q = request.GET.get('q')
    estado_f = request.GET.get('estado')
    
    # 3. Consulta base
    mesas = Mesa.objects.all()
    
    # 4. Aplicar filtros si existen
    if q:
        mesas = mesas.filter(numero_mesa__icontains=q)
    if estado_f:
        mesas = mesas.filter(estado__iexact=estado_f)
        
    # 5. Ordenar resultados
    mesas = mesas.order_by('numero_mesa')
    
    # 6. Enviamos todo al context
    context = {
        'mesas': mesas,
        'generado_por': generado_por
    }
    
    return render(request, 'mesas/listar.html', context)
# 2. MOSTRAR FORMULARIO DE REGISTRO
def mostrar_registro_mesa(request):
    if 'usuario_id' not in request.session: return redirect('login')
    return render(request, 'mesas/registrar.html')

# 3. GUARDAR NUEVA MESA
def registrar_mesa(request):
    if 'usuario_id' not in request.session: return redirect('login')
    
    if request.method == 'POST':
        try:
            # Creamos la mesa usando los campos de tu tabla SQL
            Mesa.objects.create(
                numero_mesa=request.POST.get('numero_mesa'),
                capacidad=request.POST.get('capacidad'),
                # El ENUM de MySQL recibirá: 'Disponible', 'Ocupada' o 'Reservada'
                estado=request.POST.get('estado', 'Disponible')
            )
            
            return redirect('listar_mesas')
        except Exception as e:
            
            return redirect('mostrar_registro_mesa')
            
    return redirect('listar_mesas')

# 4. PREPARAR EDICIÓN (Cargar datos)
def pre_editar_mesa(request, id_mesa):
    if 'usuario_id' not in request.session: return redirect('login')
    
    mesa = get_object_or_404(Mesa, id_mesa=id_mesa)
    return render(request, 'mesas/editar.html', {'mesa': mesa})

# 5. ACTUALIZAR MESA
def editar_mesa(request):
    if 'usuario_id' not in request.session: return redirect('login')
    
    if request.method == 'POST':
        id_m = request.POST.get('id_mesa')
        mesa = get_object_or_404(Mesa, id_mesa=id_m)
        
        # Actualizamos los campos según el formulario
        mesa.numero_mesa = request.POST.get('numero_mesa')
        mesa.capacidad = request.POST.get('capacidad')
        mesa.estado = request.POST.get('estado')
        
        mesa.save()
        
        
    return redirect('listar_mesas')


def eliminar_mesa(request, id_mesa):
    if 'usuario_id' not in request.session: return redirect('login')
    
    mesa = get_object_or_404(Mesa, id_mesa=id_mesa)
    numero_aux = mesa.numero_mesa
    mesa.delete()
    
    messages.warning(request, f"La Mesa {numero_aux} ha sido eliminada del sistema")
    return redirect('listar_mesas')


def exportar_mesas_pdf(request):
    # 1. Capturar los mismos filtros que en la lista
    q = request.GET.get('q')
    estado_f = request.GET.get('estado')
    
    # 2. Obtener datos filtrados
    mesas = Mesa.objects.all()
    
    if q:
        mesas = mesas.filter(numero_mesa__icontains=q)
    if estado_f:
        mesas = mesas.filter(estado__iexact=estado_f)

    # Ordenamos por número de mesa
    mesas = mesas.order_by('numero_mesa')

    # 3. Definir quién genera el reporte
    rol = request.session.get('usuario_rol', 'Empleado').capitalize()
    nombre_user = request.session.get('usuario_nombre', 'Usuario')
    generado_por = f"{rol}: {nombre_user}"

    # 4. Preparar el contexto para el template
    template = get_template('mesas/pdf_mesas.html')
    context = {
        'mesas': mesas,
        'fecha': timezone.now(), 
        'generado_por': generado_por,
    }
    
    # 5. Renderizar HTML a PDF
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    
    # Configuramos el nombre del archivo con la fecha actual
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    response['Content-Disposition'] = f'attachment; filename="reporte_mesas_{fecha_str}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)
        
    return response

def analisis_mesas(request):
    # Verificación de sesión
    if 'usuario_id' not in request.session:
        return redirect('login')

    # KPIs Generales
    mesas = Mesa.objects.all()
    total_mesas = mesas.count()
    capacidad_total = sum(m.capacidad for m in mesas)
    mesa_mas_grande = mesas.order_by('-capacidad').first().capacidad if mesas else 0
    
    # --- Solución: Distribución por Estado ---
    # Normalizamos el texto: 'Disponible' en lugar de 'Libre'
    # Eliminamos 'Mantenimiento'
    estados = ['Disponible', 'Ocupada', 'Reservada']
    
    # Mapeamos los colores exactos para cada estado
    # Verde (Disponible), Rojo (Ocupada), Amarillo (Reservada)
    colores_estados = ['#198754', '#dc3545', '#ffc107']

    # Contamos basándonos en la lista 'estados'
    # Usamos .filter().count() para precisión
    valores_est = [mesas.filter(estado=est).count() for est in estados]
    
    # Preparamos las etiquetas limpias (Ej: DISPONIBLE, OCUPADA...)
    labels_estado_limpias = [est.upper() for est in estados]

    # --- Distribución por Capacidad (Sin cambios) ---
    capacidades = sorted(list(set(m.capacidad for m in mesas)))
    labels_capacidad = [f"Capacidad {c}" for c in capacidades]
    valores_cap = [mesas.filter(capacidad=c).count() for c in capacidades]

    # Contexto con datos JSON seguros para JS
    context = {
        'total_mesas': total_mesas,
        'capacidad_total': capacidad_total,
        'mesa_mas_grande': mesa_mas_grande,
        
        # Datos para Gráfica de Estados (CORREGIDO)
        'labels_est': json.dumps(labels_estado_limpias), # ['DISPONIBLE', 'OCUPADA'...]
        'valores_est': json.dumps(valores_est),          # [3, 1, 3]
        'colores_est': json.dumps(colores_estados),       # ['#1987...', '#dc35...']
        
        # Datos para Gráfica de Capacidad
        'labels_cap': json.dumps(labels_capacidad),
        'valores_cap': json.dumps(valores_cap),
    }
    
    return render(request, 'mesas/analisis_mesas.html', context)