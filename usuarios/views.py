from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from datetime import date
from django.db.models import Sum, Q
from decimal import Decimal
from django.contrib.auth import authenticate
# IMPORTACIONES CRÍTICAS
from .models import Usuario
from eventos.models import InscripcionEvento 
from mesas.models import Mesa
from reservas.models import Reserva
from eventos.models import Evento
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import pandas as pd
from django.db.models import Count
import json
from ventas.models import Venta
from pedidos.models import Pedido

def registro(request):
    if request.method == 'POST':
        # 1. Capturar datos del formulario
        nombre = request.POST.get('first_name')
        apellido = request.POST.get('last_name')
        correo = request.POST.get('email')
        usuario_slug = request.POST.get('username')
        clave = request.POST.get('password')
        confirmar = request.POST.get('confirm_password')

        # 2. Validaciones básicas
        if clave != confirmar:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'usuarios/registro.html')

        if User.objects.filter(username=usuario_slug).exists():
            messages.error(request, "El nombre de usuario ya existe.")
            return render(request, 'usuarios/registro.html')

        try:
            # USAR TRANSACCIONES: Si falla uno, no se guarda ninguno
            with transaction.atomic():
                # 3. Guardar en la tabla de Django (auth_user)
                nuevo_user_django = User.objects.create_user(
                    username=usuario_slug,
                    email=correo,
                    password=clave,
                    first_name=nombre,
                    last_name=apellido
                )

                # 4. Guardar en TU tabla personalizada (Usuario)
                Usuario.objects.create(
                    username=usuario_slug,  # Se mapea a la columna 'Usuario'
                    password=clave,           # Se mapea a la columna 'contraseña'
                    rol='cliente'             # Se mapea a la columna 'rol'
                )

                messages.success(request, f"¡Bienvenido {nombre}! Cuenta creada correctamente.")
                return redirect('login')

        except Exception as e:
            messages.error(request, f"Error al registrar: {e}")
            # CORREGIDO: Apunta a la nueva ubicación tras mover el archivo
            return render(request, 'usuarios/registro.html')

    # CORREGIDO: Apunta a la nueva ubicación para cuando se carga la página por primera vez (GET)
    return render(request, 'usuarios/registro.html')
def inicio(request):

    eventos = Evento.objects.all() 
    return render(request, 'usuarios/inicio.html', {'eventos': eventos})

def menu(request):
    return render(request, 'usuarios/menu.html')
# --- LOGIN ---
def iniciar_sesion(request):
    if request.method == 'POST':
        nombre_usu = request.POST.get('username')
        clave = request.POST.get('password')
        
        # Django compara el hash de la BD con la clave que escribe el usuario
        user = authenticate(request, username=nombre_usu, password=clave)
        
        if user is not None:
            login(request, user) # Esto crea la sesión de forma segura
            
            # Guardamos el rol en la sesión si es necesario para tu lógica
            request.session['usuario_rol'] = user.rol 
            
            return redirect('dashboard')
        else:
            messages.error(request, "Usuario o contraseña incorrectos")
            
    return render(request, 'usuarios/login.html')
# --- DASHBOARD (EL TABLERO) ---


def dashboard(request):
    if 'usuario_id' not in request.session:
        return redirect('login')

    # --- 1. KPIs PRINCIPALES (TARJETAS) ---
    total_usuarios = Usuario.objects.count()
    total_recaudado = Venta.objects.aggregate(Sum('total'))['total__sum'] or 0
    
    hoy = timezone.now().date()
    # Corrección: Usamos fecha_venta según image_91c627.png
    total_ventas_hoy = Venta.objects.filter(fecha_venta=hoy).aggregate(total=Sum('total'))['total'] or 0
    
    # Ticket Promedio (Ingresos / Total Pedidos)
    total_pedidos_count = Pedido.objects.count()
    ticket_promedio = total_recaudado / total_pedidos_count if total_pedidos_count > 0 else 0
    
    reservas_activas = Reserva.objects.filter(estado='pendiente').count()
    mesas_disponibles = Mesa.objects.filter(estado='disponible').count()

    # --- 2. DISTRIBUCIÓN DE USUARIOS POR ROL (userChart) ---
    # Corrección: Usamos 'rol' según image_873f11.png
    usuarios_por_rol = Usuario.objects.values('rol').annotate(total=Count('id_usuario'))
    labels_user = [item['rol'].capitalize() for item in usuarios_por_rol]
    valores_user = [item['total'] for item in usuarios_por_rol]

    # --- 3. ESTADO DE PEDIDOS (chartEstados) ---
    # Corrección: Usamos 'estado_pedido' según image_91bf23.png
    pedidos_est = Pedido.objects.values('estado_pedido').annotate(cantidad=Count('id_pedido'))
    labels_est = [item['estado_pedido'].upper() for item in pedidos_est]
    valores_est = [item['cantidad'] for item in pedidos_est]

    # --- 4. TOP 5 PLATOS MÁS VENDIDOS (chartPlatos) ---
    platos_top = Pedido.objects.values('id_plato__nombre_plato').annotate(
        total_unidades=Sum('cantidad')
    ).order_by('-total_unidades')[:5]
    
    labels_platos = [item['id_plato__nombre_plato'] for item in platos_top]
    valores_platos = [item['total_unidades'] for item in platos_top]

    context = {
        'total_usuarios': total_usuarios,
        'total_recaudado': float(total_recaudado),
        'total_ventas_hoy': float(total_ventas_hoy),
        'ticket_promedio': float(ticket_promedio),
        'reservas_activas': reservas_activas,
        'mesas_disponibles': mesas_disponibles,
        
        # Datos JSON para los scripts
        'labels_json': json.dumps(labels_user),
        'valores_json': json.dumps(valores_user),
        'labels_est': json.dumps(labels_est),
        'valores_est': json.dumps(valores_est),
        'labels_platos': json.dumps(labels_platos),
        'valores_platos': json.dumps(valores_platos),
    }

    return render(request, 'usuarios/dashboard.html', context)

def cerrar_sesion(request):
    request.session.flush()
    return redirect('login')





# --- MÓDULO USUARIOS ---
def listar_usuarios(request):
    # 1. Verificación de seguridad
    if 'usuario_id' not in request.session:
        return redirect('login')

    # 2. Obtener todos los usuarios inicialmente
    usuarios = Usuario.objects.all()

    # 3. Capturar criterios de búsqueda desde el GET (los "name" del HTML)
    q = request.GET.get('q', '')      # Nombre de usuario
    rol = request.GET.get('rol', '')  # Rol seleccionado

    # 4. Aplicar filtros si existen
    if q:
        # Filtra si el username contiene el texto (sin importar mayúsculas)
        usuarios = usuarios.filter(username__icontains=q)
    
    if rol:
        # Filtra exactamente por el rol seleccionado
        usuarios = usuarios.filter(rol__iexact=rol)

    # 5. Ordenar por ID para que los nuevos salgan arriba
    usuarios = usuarios.order_by('-id_usuario')

    # 6. Enviar datos al template
    data = {
        'usuarios': usuarios,
        'query_q': q,     # Opcional: para mantener el texto en el buscador
        'query_rol': rol  # Opcional: para mantener la selección del rol
    }
    
    return render(request, 'usuarios/listar.html', data)

def mostrar_registro_usuario(request):
    if 'usuario_id' not in request.session: 
        return redirect('login')
    return render(request, 'usuarios/registrar.html')

def registrar_usuario(request):
    if request.method == 'POST':
        nombre_usu = request.POST['usuario']
        clave = request.POST['contraseña']
        rol_usu = request.POST.get('rol') # <--- AGREGADO: Captura el rol del select
        
        # Inserción directa en MariaDB
        Usuario.objects.create(
            username=nombre_usu,
            password=clave, # Sin encriptar por requerimiento del usuario
            rol=rol_usu     # <--- AGREGADO: Se guarda el rol en la DB
        )
        return redirect('listar_usuarios')
    return redirect('mostrar_registro_usuario')

def pre_editar_usuario(request, id_usuario): 
    if 'usuario_id' not in request.session: 
        return redirect('login')
    
    usuario = Usuario.objects.get(id_usuario=id_usuario)
    data = {'usuario': usuario}
    return render(request, 'usuarios/editar.html', data)

def editar_usuario(request):
    if request.method == 'POST':
        id = request.POST['id_usuario']
        nombre_usu = request.POST['usuario']
        clave = request.POST['contraseña']
        rol = request.POST['rol']
        
        usuario = Usuario.objects.get(id_usuario=id)
        usuario.username = nombre_usu
        usuario.password = clave
        usuario.rol = rol
        usuario.save() # Guarda los cambios en MariaDB
        
    return redirect('listar_usuarios')

def eliminar_usuario(request, id_usuario):
    if 'usuario_id' not in request.session: 
        return redirect('login')
        
    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    
    # PASO MANUAL: Borramos primero todas las reservas de este usuario
    # Esto evita el error de IntegrityError 1451 en MariaDB
    Reserva.objects.filter(id_cliente=id_usuario).delete()
    
    # Ahora que no tiene reservas asociadas, podemos borrar al usuario
    usuario.delete()
    
    return redirect('listar_usuarios')


def exportar_usuarios_pdf(request):
    # 1. Seguridad: Solo usuarios logueados
    if 'usuario_id' not in request.session:
        return redirect('login')

    # 2. Capturar datos reales de quién genera el reporte
    rol_session = request.session.get('usuario_rol', 'Empleado').capitalize()
    nombre_session = request.session.get('usuario_nombre', 'Usuario')
    generado_por = f"{rol_session}: {nombre_session}"

    # 3. Aplicar los mismos filtros que en la lista
    usuarios = Usuario.objects.all()
    q = request.GET.get('q')
    rol_f = request.GET.get('rol')

    if q:
        usuarios = usuarios.filter(username__icontains=q)
    if rol_f:
        usuarios = usuarios.filter(rol__iexact=rol_f)

    # 4. Preparamos el contexto para el template (ahora con generado_por)
    data = {
        'usuarios': usuarios,
        'fecha': timezone.now(),
        'generado_por': generado_por, # <--- Se pasa el nombre real
        'empresa': 'Parrilla Express'
    }
    
    # 5. Renderizar el HTML
    template = get_template('usuarios/pdf_usuarios.html')
    html = template.render(data)
    
    # 6. Crear la respuesta del PDF con descarga automática
    response = HttpResponse(content_type='application/pdf')
    
    # Nombre de archivo dinámico con fecha
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    response['Content-Disposition'] = f'attachment; filename="reporte_usuarios_{fecha_str}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Ocurrió un error al generar el PDF', status=500)
        
    return response

def carga_masiva_usuarios(request):
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        archivo = request.FILES['archivo_excel']
        try:
            df = pd.read_excel(archivo)
            usuarios_nuevos = []
            
            for index, row in df.iterrows():
                usuarios_nuevos.append(Usuario(
                    username=row['usuario'], # Se mapea a db_column='Usuario'
                    password=row['password'], # Se mapea a db_column='contraseña'
                    rol=row['rol'].lower()
                ))
            
            Usuario.objects.bulk_create(usuarios_nuevos)
            messages.success(request, f"¡Se cargaron {len(usuarios_nuevos)} usuarios correctamente!")
            return redirect('listar_usuarios')
            
        except Exception as e:
            messages.error(request, f"Error al procesar el archivo: {e}")
            
    return render(request, 'usuarios/carga_masiva_usuarios.html')

def analisis_usuarios(request):
    # Verificación de sesión igual a tu vista de referencia
    if 'usuario_id' not in request.session:
        return redirect('login')

    # Consulta: Contar usuarios por rol
    conteo = Usuario.objects.values('rol').annotate(total=Count('id_usuario')).order_by('-total')

    # Preparamos los datos como listas simples
    labels = [item['rol'].capitalize() for item in conteo]
    valores = [item['total'] for item in conteo]

    data = {
        'labels_json': json.dumps(labels), # Convertimos a JSON para evitar errores en JS
        'valores_json': json.dumps(valores),
        'total_usuarios': Usuario.objects.count(),
        'roles_detalle': conteo # Para mostrar una tabla informativa
    }
    
    return render(request, 'usuarios/estadisticas.html', data)