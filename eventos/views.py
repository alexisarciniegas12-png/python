from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Evento, InscripcionEvento
from usuarios.models import Usuario 
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa
import json
from django.db.models import Sum, Count, Avg
from django.shortcuts import render

# --- CRUD EVENTOS ---

# 1. LISTAR EVENTOS
def listar_eventos(request):
    if 'usuario_id' not in request.session: 
        return redirect('login')
    
    # 1. Obtener parámetros del primer formulario (Gestión de Eventos)
    q_ev = request.GET.get('q_ev', '')
    fecha_ev = request.GET.get('fecha_ev', '')
    est_ev = request.GET.get('est_ev', '')

    # QuerySet base para eventos
    eventos = Evento.objects.all().order_by('fecha_evento')

    # --- Lógica de Filtrado para Gestión de Eventos ---
    if q_ev:
        eventos = eventos.filter(nombre_evento__icontains=q_ev)
    
    if fecha_ev:
        eventos = eventos.filter(fecha_evento=fecha_ev)
        
    if est_ev:
        eventos = eventos.filter(estado_evento=est_ev)

    # 2. Parámetros del segundo formulario (Control de Usuarios)
    q_ins = request.GET.get('q_ins', '')
    est_pago = request.GET.get('est_pago', '')

    inscripciones_todas = InscripcionEvento.objects.all().order_by('-id_inscripcion')

    # --- Lógica de Filtrado para Control de Inscripciones ---
    if q_ins:
        inscripciones_todas = inscripciones_todas.filter(nombre_cliente__icontains=q_ins)
    
    if est_pago:
        inscripciones_todas = inscripciones_todas.filter(estado_pago=est_pago)

    # 3. Datos para el cliente logueado
    usuario_id = request.session.get('usuario_id')
    inscripciones_usuario = InscripcionEvento.objects.filter(id_cliente=usuario_id)

    return render(request, 'eventos/listar.html', {
        'eventos': eventos,
        'inscripciones_todas': inscripciones_todas,
        'inscripciones': inscripciones_usuario
    })

# 2. MOSTRAR FORMULARIO DE REGISTRO
def mostrar_registro_evento(request):
    if 'usuario_id' not in request.session: return redirect('login')
    return render(request, 'eventos/registrar.html')

# 3. GUARDAR NUEVO EVENTO
def registrar_evento(request):
    if 'usuario_id' not in request.session: return redirect('login')
    
    if request.method == 'POST':
        try:
            Evento.objects.create(
                nombre_evento=request.POST.get('nombre_evento'),
                descripcion=request.POST.get('descripcion'),
                fecha_evento=request.POST.get('fecha_evento'),
                hora_evento=request.POST.get('hora_evento'),
                valor_evento=request.POST.get('valor_evento'),
                cupos_disponibles=request.POST.get('cupos_disponibles'),
                estado_evento=request.POST.get('estado_evento', 'Disponible')
            )
            messages.success(request, "Evento registrado correctamente")
            return redirect('eventos:listar_eventos')
        except Exception as e:
            messages.error(request, f"Error al registrar el evento: {e}")
            return redirect('eventos:mostrar_registro_evento')
            
    return redirect('eventos:listar_eventos')

# 4. PREPARAR EDICIÓN
def pre_editar_evento(request, id_evento):
    if 'usuario_id' not in request.session: return redirect('login')
    evento = get_object_or_404(Evento, id_evento=id_evento)
    return render(request, 'eventos/editar.html', {'evento': evento})

# 5. ACTUALIZAR EVENTO
def editar_evento(request):
    if 'usuario_id' not in request.session: return redirect('login')
    
    if request.method == 'POST':
        id_ev = request.POST.get('id_evento')
        evento = get_object_or_404(Evento, id_evento=id_ev)
        try:
            evento.nombre_evento = request.POST.get('nombre_evento')
            evento.descripcion = request.POST.get('descripcion')
            evento.fecha_evento = request.POST.get('fecha_evento')
            evento.hora_evento = request.POST.get('hora_evento')
            evento.valor_evento = request.POST.get('valor_evento')
            evento.cupos_disponibles = request.POST.get('cupos_disponibles')
            evento.estado_evento = request.POST.get('estado_evento')
            evento.save()
            messages.success(request, "Evento actualizado con éxito")
        except Exception as e:
            messages.error(request, f"Error al guardar: {e}")
        
    return redirect('eventos:listar_eventos')

# 6. ELIMINAR EVENTO
def eliminar_evento(request, id_evento):
    if 'usuario_id' not in request.session: return redirect('login')
    try:
        evento = Evento.objects.get(id_evento=id_evento)
        nombre_aux = evento.nombre_evento
        evento.delete()
        messages.warning(request, f"El evento '{nombre_aux}' ha sido eliminado")
    except Evento.DoesNotExist:
        messages.error(request, "El evento ya no existe.")
        
    return redirect('eventos:listar_eventos')

# --- MÓDULO DE INSCRIPCIONES ---

# 1. LISTAR INSCRIPCIONES
def listar_inscripciones(request):
    if 'usuario_id' not in request.session: 
        return redirect('login')
    
    rol = request.session.get('usuario_rol', '').lower()
    u_id = request.session.get('usuario_id')

    # 1. Capturar los parámetros de filtrado desde la URL
    q_ins = request.GET.get('q_ins', '')
    fecha_filtro = request.GET.get('fecha_filtro', '')
    est_pago = request.GET.get('est_pago', '')

    # 2. Definir el QuerySet base según el rol
    if rol == 'cliente':
        inscripciones = InscripcionEvento.objects.filter(id_cliente=u_id)
    else:
        inscripciones = InscripcionEvento.objects.all()

    # 3. Aplicar los filtros si existen
    if q_ins:
        # Cambio: Ahora filtra por el nombre del evento relacionado
        inscripciones = inscripciones.filter(id_evento__nombre_evento__icontains=q_ins)
    
    if fecha_filtro:
        # Filtramos por la fecha del evento relacionado
        inscripciones = inscripciones.filter(id_evento__fecha_evento=fecha_filtro)
    
    if est_pago:
        inscripciones = inscripciones.filter(estado_pago__iexact=est_pago)

    # 4. Ordenar y renderizar
    inscripciones = inscripciones.order_by('-id_inscripcion')

    return render(request, 'eventos/inscripcion_evento/listar.html', {
        'inscripciones': inscripciones
    })

# 2. MOSTRAR REGISTRO INSCRIPCIÓN
def mostrar_registro_inscripcion(request):
    if 'usuario_id' not in request.session: return redirect('login')
    eventos = Evento.objects.filter(estado_evento='Disponible', cupos_disponibles__gt=0).order_by('fecha_evento')
    return render(request, 'eventos/inscripcion_evento/registrar.html', {'eventos': eventos})

# 3. GUARDAR INSCRIPCIÓN
@transaction.atomic
def registrar_inscripcion(request):
    if 'usuario_id' not in request.session: 
        return redirect('login')
    
    if request.method == 'POST':
        try:
            id_ev = request.POST.get('id_evento')
            metodo_pago = request.POST.get('metodo_pago')
            cantidad = int(request.POST.get('cantidad_personas', 1))
            
            # --- LÓGICA PARA IDENTIFICAR AL CLIENTE ---
            username_seleccionado = request.POST.get('usuario_seleccionado')
            
            if username_seleccionado:
                usuario_cliente = get_object_or_404(Usuario, username=username_seleccionado)
                nombre_final = usuario_cliente.username
            else:
                u_id_sesion = request.session.get('usuario_id')
                usuario_cliente = get_object_or_404(Usuario, id_usuario=u_id_sesion)
                nombre_final = request.session.get('usuario_nombre')

            # --- VALIDACIÓN DE CUPOS ---
            evento_obj = get_object_or_404(Evento, id_evento=id_ev)
            
            if evento_obj.cupos_disponibles >= cantidad:
                evento_obj.cupos_disponibles -= cantidad
                if evento_obj.cupos_disponibles == 0:
                    evento_obj.estado_evento = 'Agotado'
                evento_obj.save()

                # --- CREACIÓN DEL REGISTRO ---
                InscripcionEvento.objects.create(
                    nombre_cliente=nombre_final,
                    id_evento=evento_obj,
                    id_cliente=usuario_cliente, 
                    metodo_pago=metodo_pago,
                    cantidad_personas=cantidad,
                    estado_pago=request.POST.get('estado_pago', 'Pendiente')
                )

                messages.success(request, f"Inscripción registrada con éxito para {nombre_final}.")
                
                # --- REDIRECCIÓN SEGÚN ROL ---
                # Obtenemos el rol de la sesión y lo pasamos a minúsculas para comparar
                rol = request.session.get('usuario_rol', '').lower()

                if rol in ['administrador', 'empleado']:
                    # Admin/Empleado va a la vista general de Gestión de Eventos
                    return redirect('eventos:listar_eventos')
                else:
                    # Cliente va a su lista personal de inscripciones
                    return redirect('eventos:listar_inscripciones')
            
            else:
                messages.warning(request, "No hay cupos suficientes.")
                return redirect('eventos:mostrar_registro_inscripcion')
                
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect('eventos:mostrar_registro_inscripcion')
            
    return redirect('eventos:listar_eventos')

# 4. PREPARAR EDICIÓN INSCRIPCIÓN
def pre_editar_inscripcion(request, id_inscripcion):
    if 'usuario_id' not in request.session: return redirect('login')
    inscripcion = get_object_or_404(InscripcionEvento, id_inscripcion=id_inscripcion)
    eventos = Evento.objects.filter(estado_evento='Disponible')
    return render(request, 'eventos/inscripcion_evento/editar.html', {
        'inscripcion': inscripcion,
        'eventos': eventos
    })

# 5. ACTUALIZAR INSCRIPCIÓN
@transaction.atomic
def editar_inscripcion(request, id_inscripcion):
    if 'usuario_id' not in request.session: return redirect('login')
    
    inscripcion = get_object_or_404(InscripcionEvento, id_inscripcion=id_inscripcion)
    evento_original = inscripcion.id_evento
    cantidad_original = inscripcion.cantidad_personas
    
    if request.method == 'POST':
        try:
            id_ev_nuevo = request.POST.get('id_evento')
            nueva_cantidad = int(request.POST.get('cantidad_personas', 1))
            evento_nuevo = get_object_or_404(Evento, id_evento=id_ev_nuevo)

            if evento_original.id_evento != evento_nuevo.id_evento:
                evento_original.cupos_disponibles += cantidad_original
                evento_original.save()
                
                if evento_nuevo.cupos_disponibles >= nueva_cantidad:
                    evento_nuevo.cupos_disponibles -= nueva_cantidad
                    evento_nuevo.save()
                else:
                    messages.error(request, "Sin cupos en el nuevo evento.")
                    return redirect('eventos:listar_inscripciones')
            else:
                diferencia = nueva_cantidad - cantidad_original
                if evento_nuevo.cupos_disponibles >= diferencia:
                    evento_nuevo.cupos_disponibles -= diferencia
                    evento_nuevo.save()
                else:
                    messages.error(request, "Sin cupos suficientes.")
                    return redirect('eventos:listar_inscripciones')

            inscripcion.id_evento = evento_nuevo
            inscripcion.nombre_cliente = request.POST.get('nombre_cliente')
            inscripcion.metodo_pago = request.POST.get('metodo_pago')
            inscripcion.cantidad_personas = nueva_cantidad
            inscripcion.save()
            
            messages.success(request, "Inscripción actualizada.")
            return redirect('eventos:listar_inscripciones')
        except Exception as e:
            messages.error(request, f"Error: {e}")
            
    return redirect('eventos:listar_inscripciones')

# 6. ELIMINAR INSCRIPCIÓN
@transaction.atomic
def eliminar_inscripcion(request, id_inscripcion):
    if 'usuario_id' not in request.session: return redirect('login')
    inscripcion = get_object_or_404(InscripcionEvento, id_inscripcion=id_inscripcion)
    try:
        evento = inscripcion.id_evento
        evento.cupos_disponibles += inscripcion.cantidad_personas
        if evento.cupos_disponibles > 0:
            evento.estado_evento = 'Disponible'
        evento.save()
        inscripcion.delete()
        messages.success(request, "Inscripción eliminada y cupos restaurados.")
    except Exception as e:
        messages.error(request, f"Error: {e}")
    return redirect('eventos:listar_inscripciones')

# --- VISTAS ADMIN ---

def pre_editar_inscripcion_admin(request, id_inscripcion):
    if 'usuario_id' not in request.session: return redirect('login')
    inscripcion = get_object_or_404(InscripcionEvento, id_inscripcion=id_inscripcion)
    return render(request, 'eventos/editar_in.html', {'inscripcion': inscripcion})

def editar_inscripcion_admin(request, id_inscripcion):
    if 'usuario_id' not in request.session: return redirect('login')
    if request.method == 'POST':
        inscripcion = get_object_or_404(InscripcionEvento, id_inscripcion=id_inscripcion)
        try:
            inscripcion.metodo_pago = request.POST.get('metodo_pago')
            inscripcion.estado_pago = request.POST.get('estado_pago')
            inscripcion.save()
            messages.success(request, "Inscripción actualizada por administrador.")
        except Exception as e:
            messages.error(request, f"Error admin: {e}")
    return redirect('eventos:listar_eventos')

def eliminar_inscripcion_admin(request, id_inscripcion):
    if 'usuario_id' not in request.session: return redirect('login')
    inscripcion = get_object_or_404(InscripcionEvento, id_inscripcion=id_inscripcion)
    try:
        evento = inscripcion.id_evento
        evento.cupos_disponibles += inscripcion.cantidad_personas
        if evento.cupos_disponibles > 0:
            evento.estado_evento = 'Disponible'
        evento.save()
        inscripcion.delete()
        messages.warning(request, "Inscripción eliminada por administrador.")
    except Exception as e:
        messages.error(request, f"Error admin: {e}")
    return redirect('eventos:listar_eventos')

def mostrar_registro_admin(request):
    # 1. Verificación de sesión y permisos
    if 'usuario_id' not in request.session: 
        return redirect('login')
    
    # --- LÓGICA DE FILTROS AÑADIDA ---
    q_ev = request.GET.get('q_ev', '')  # Filtro para nombre de evento
    q_user = request.GET.get('q_user', '')  # Filtro para nombre de usuario/cliente
    # ---------------------------------
    
    # 2. Consultar eventos con cupos y disponibles
    eventos = Evento.objects.filter(
        estado_evento='Disponible', 
        cupos_disponibles__gt=0
    ).order_by('fecha_evento')
    
    # Aplicar filtro de búsqueda a eventos si existe
    if q_ev:
        eventos = eventos.filter(nombre_evento__icontains=q_ev)
    
    # 3. FILTRO POR ROL: Solo traemos usuarios que sean 'Cliente'
    usuarios = Usuario.objects.filter(rol='Cliente').order_by('username')
    
    # Aplicar filtro de búsqueda a usuarios si existe
    if q_user:
        # Busca por nombre_usuario o username según tengas en tu modelo
        usuarios = usuarios.filter(nombre_usuario__icontains=q_user)
    
    # 4. Renderizado a la ruta corregida
    return render(request, 'eventos/registro_inscripcion_admin.html', {
        'eventos': eventos,
        'usuarios': usuarios,
        'q_ev': q_ev,    # Devolvemos el valor para mantenerlo en el input
        'q_user': q_user  # Devolvemos el valor para mantenerlo en el input
    })


def exportar_eventos_pdf(request):
    # 1. Capturar los mismos filtros de la lista para que el PDF sea coherente
    q_ev = request.GET.get('q_ev', '')
    fecha_ev = request.GET.get('fecha_ev', '')
    est_ev = request.GET.get('est_ev', '')

    # 2. Aplicar los filtros al QuerySet
    eventos = Evento.objects.all().order_by('fecha_evento')

    if q_ev:
        eventos = eventos.filter(nombre_evento__icontains=q_ev)
    if fecha_ev:
        eventos = eventos.filter(fecha_evento=fecha_ev)
    if est_ev:
        eventos = eventos.filter(estado_evento=est_ev)

    # 3. Definir quién genera el reporte (Rol + Usuario)
    rol = request.session.get('usuario_rol', 'Empleado').capitalize()
    nombre_user = request.session.get('usuario_nombre', 'Usuario')
    generado_por = f"{rol}: {nombre_user}"

    # 4. Preparar el contexto para el template
    data = {
        'eventos': eventos,
        'fecha_generacion': timezone.now(),
        'generado_por': generado_por,
    }

    # 5. Renderizar el template y generar el PDF
    template = get_template('eventos/pdf_eventos.html')
    html = template.render(data)
    
    response = HttpResponse(content_type='application/pdf')
    
    # Nombre de archivo dinámico con fecha actual
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    response['Content-Disposition'] = f'attachment; filename="reporte_eventos_{fecha_str}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Ocurrió un error al generar el PDF', status=500)
    
    return response


def exportar_reporte_general_eventos(request):
    # 1. Capturar los filtros de la SEGUNDA tabla (Inscritos)
    q_ins = request.GET.get('q_ins', '')
    est_pago = request.GET.get('est_pago', '')

    # 2. CAMBIO CLAVE: Consultar Inscripciones en lugar de Eventos
    # Usamos select_related para traer el nombre del evento y el cliente
    query = InscripcionEvento.objects.all().select_related('id_evento', 'id_cliente').order_by('-id_inscripcion')

    if q_ins:
        query = query.filter(id_cliente__nombre_usuario__icontains=q_ins)
    if est_pago:
        query = query.filter(estado_pago__iexact=est_pago)

    inscripciones = query

    # 3. Definir quién genera el reporte
    rol = request.session.get('usuario_rol', 'Empleado').capitalize()
    nombre_user = request.session.get('usuario_nombre', 'Usuario')
    generado_por = f"{rol}: {nombre_user}"

    # 4. Preparar el contexto enviando 'inscripciones'
    template = get_template('eventos/reporte_general_eventos.html')
    context = {
        'inscripciones': inscripciones, # Enviamos la lista de inscritos
        'fecha': timezone.now(),
        'generado_por': generado_por,
    }

    # 5. Renderizar a PDF
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    response['Content-Disposition'] = f'attachment; filename="reporte_inscripciones_{fecha_str}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)

    return response


def generar_pdf_inscripciones_filtradas(request):
    if 'usuario_id' not in request.session:
        return redirect('login')

    # 1. Capturar los mismos filtros del listado
    q_ins = request.GET.get('q_ins', '')
    fecha_filtro = request.GET.get('fecha_filtro', '')
    est_pago = request.GET.get('est_pago', '')
    
    rol = request.session.get('usuario_rol', '').lower()
    u_id = request.session.get('usuario_id')
    nombre_usuario = request.session.get('usuario_nombre', 'Usuario')

    # 2. QuerySet base con restricción de seguridad por rol
    if rol == 'cliente':
        inscripciones = InscripcionEvento.objects.filter(id_cliente=u_id)
    elif rol in ['administrador', 'empleado']:
        inscripciones = InscripcionEvento.objects.all()
    else:
        inscripciones = InscripcionEvento.objects.none()

    # 3. Aplicar filtros
    if q_ins:
        inscripciones = inscripciones.filter(id_evento__nombre_evento__icontains=q_ins)
    if fecha_filtro:
        inscripciones = inscripciones.filter(id_evento__fecha_evento=fecha_filtro)
    if est_pago:
        inscripciones = inscripciones.filter(estado_pago__iexact=est_pago)

    inscripciones = inscripciones.order_by('-id_inscripcion')

    # 4. Configuración del PDF
    template = get_template('eventos/inscripcion_evento/pdf_filtrado.html')
    
    # Formateamos el string para que diga "Nombre (Rol)"
    usuario_completo = f"{nombre_usuario} ({rol.capitalize()})"

    context = {
        'inscripciones': inscripciones,
        'fecha_actual': timezone.now(),
        'generado_por': usuario_completo,
        'filtros': {
            'evento': q_ins,
            'fecha': fecha_filtro,
            'estado': est_pago
        }
    }
    
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_inscripciones_{timezone.now().strftime("%Y%m%d")}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el reporte', status=500)
    return response

def analisis_eventos(request):
    if 'usuario_id' not in request.session:
        return redirect('login')

    eventos = Evento.objects.all()
    total_eventos = eventos.count()
    
    # 1. KPIs Financieros y de Capacidad
    valor_proyectado = eventos.aggregate(Sum('valor_evento'))['valor_evento__sum'] or 0
    promedio_cupos = eventos.aggregate(Avg('cupos_disponibles'))['cupos_disponibles__avg'] or 0
    
    # 2. Eventos por Estado (Disponible, Finalizado, Cancelado)
    estados_query = eventos.values('estado_evento').annotate(count=Count('id_evento'))
    labels_est = [item['estado_evento'].upper() for item in estados_query]
    valores_est = [item['count'] for item in estados_query]

    # 3. Comparativa de Valor por Evento (Top 5 más costosos/importantes)
    top_eventos = eventos.order_by('-valor_evento')[:5]
    labels_val = [e.nombre_evento for e in top_eventos]
    valores_val = [float(e.valor_evento) for e in top_eventos]

    context = {
        'total_eventos': total_eventos,
        'valor_proyectado': float(valor_proyectado),
        'promedio_cupos': round(promedio_cupos, 1),
        'labels_est': json.dumps(labels_est),
        'valores_est': json.dumps(valores_est),
        'labels_val': json.dumps(labels_val),
        'valores_val': json.dumps(valores_val),
    }

    return render(request, 'eventos/analisis_eventos.html', context)

def analisis_inscripciones(request):
    # --- KPIs ---
    total_inscritos = InscripcionEvento.objects.count()
    
    # Sumamos el valor del evento solo para las inscripciones con estado 'Pagado'
    ingresos_reales = InscripcionEvento.objects.filter(estado_pago='Pagado').aggregate(
        total=Sum('id_evento__valor_evento')
    )['total'] or 0
    
    # Nuevo KPI: Conteo de cuántas inscripciones están marcadas como 'Pagado'
    total_pagados = InscripcionEvento.objects.filter(estado_pago='Pagado').count()

    # --- Gráfica 1: Top 5 Eventos con más personas (Asistencia) ---
    top_eventos = InscripcionEvento.objects.values('id_evento__nombre_evento').annotate(
        total_p=Sum('cantidad_personas')
    ).order_by('-total_p')[:5]
    
    labels_inv = [item['id_evento__nombre_evento'] for item in top_eventos]
    valores_inv = [item['total_p'] for item in top_eventos]

    # --- Gráfica 2: Distribución por Método de Pago ---
    pagos_dist = InscripcionEvento.objects.values('metodo_pago').annotate(
        count=Count('id_inscripcion')
    )
    labels_pago = [item['metodo_pago'] for item in pagos_dist]
    valores_pago = [item['count'] for item in pagos_dist]

    # --- Gráfica 3: Estado de Pago (Nueva) ---
    estados_dist = InscripcionEvento.objects.values('estado_pago').annotate(
        count=Count('id_inscripcion')
    )
    labels_estado = [item['estado_pago'] for item in estados_dist]
    valores_estado = [item['count'] for item in estados_dist]

    context = {
        'total_inscritos': total_inscritos,
        'ingresos_reales': ingresos_reales,
        'total_pagados': total_pagados,
        # Datos para Chart.js
        'labels_inv': json.dumps(labels_inv),
        'valores_inv': json.dumps(valores_inv),
        'labels_pago': json.dumps(labels_pago),
        'valores_pago': json.dumps(valores_pago),
        'labels_estado': json.dumps(labels_estado),
        'valores_estado': json.dumps(valores_estado),
    }
    
    return render(request, 'eventos/analisis_inscripciones.html', context)