from django.shortcuts import render, redirect, get_object_or_404
from .models import   Menu, CategoriaMenu
from xhtml2pdf import pisa
from django.http import HttpResponse
from .models import Menu, CategoriaMenu
from datetime import date
from django.template.loader import get_template
from django.utils import timezone
import pandas as pd
from django.contrib import messages
import json
from django.db.models import Count, Avg, Max, Min


    # --- CRUD MENÚ (PLATOS Y CATEGORÍAS) ---

def listar_menu(request):
    if 'usuario_id' not in request.session: 
        return redirect('login')
    
    nombre_f = request.GET.get('nombre')
    categoria_f = request.GET.get('categoria')
    estado_f = request.GET.get('estado')

    platos = Menu.objects.all()

    if nombre_f:
        platos = platos.filter(nombre_plato__icontains=nombre_f)
    
    if categoria_f:
        platos = platos.filter(id_categoria=categoria_f)
        
    if estado_f:
        # Aquí aplicamos el filtro exacto: DISPONIBLE o NO DISPONIBLE
        platos = platos.filter(estado__iexact=estado_f)

    categorias = CategoriaMenu.objects.all()

    return render(request, 'menu/listar.html', {
        'platos': platos, 
        'categorias': categorias
    })

def mostrar_registro_menu(request):
    if 'usuario_id' not in request.session: return redirect('login')
    categorias = CategoriaMenu.objects.all()
    return render(request, 'menu/registrar.html', {'categorias': categorias})

def registrar_menu(request):
    if request.method == 'POST':
        id_cat = request.POST.get('id_categoria')
        # Buscamos la categoría usando el ID que viene del formulario
        categoria = get_object_or_404(CategoriaMenu, id_categoria=id_cat)
        
        # --- LIMPIEZA DEL PRECIO ---
        # Obtenemos el precio del formulario (ej: "45.000")
        precio_raw = request.POST.get('precio', '0')
        # Eliminamos puntos y comas para que se guarde como un número puro (ej: "45000")
        precio_limpio = precio_raw.replace('.', '').replace(',', '')
        
        # Corregimos los nombres de los campos para que coincidan con la DB
        Menu.objects.create(
            nombre_plato=request.POST.get('nombre_plato'), 
            descripcion=request.POST.get('descripcion'),
            precio=precio_limpio, # Usamos el valor ya sin puntos
            # CAMBIO CLAVE: Usamos 'estado' en lugar de 'disponibilidad'
            estado=request.POST.get('estado', 'Disponible'), 
            id_categoria=categoria,
            imagen=request.FILES.get('imagen') 
        )
        
        
        return redirect('menu:listar_menu')
        
    return redirect('mostrar_registro_menu')

def pre_editar_menu(request, id_plato):
    if 'usuario_id' not in request.session: return redirect('login')
    plato = get_object_or_404(Menu, id_plato=id_plato)
    categorias = CategoriaMenu.objects.all()
    return render(request, 'menu/editar.html', {'plato': plato, 'categorias': categorias})

def editar_menu(request):
    if request.method == 'POST':
        id_p = request.POST.get('id_plato')
        plato = get_object_or_404(Menu, id_plato=id_p)
        
        # Corregimos el nombre del campo para evitar el IntegrityError
        plato.nombre_plato = request.POST.get('nombre_plato') 
        plato.descripcion = request.POST.get('descripcion')
        
        # Procesamos el precio para asegurar los 3 ceros (Pesos Colombianos)
        precio_base = request.POST.get('precio')
        if precio_base:
            # Si el usuario ingresa 53, guardamos 53000
            plato.precio = int(precio_base)
        
        # Categoría y Estado
        id_cat = request.POST.get('id_categoria')
        plato.id_categoria = get_object_or_404(CategoriaMenu, id_categoria=id_cat)
        plato.estado = request.POST.get('estado')

        if 'imagen' in request.FILES:
            plato.imagen = request.FILES['imagen']
            
        plato.save()
        
        
    return redirect('menu:listar_menu')
def eliminar_menu(request, id_plato):
    plato = get_object_or_404(Menu, id_plato=id_plato)
    plato.delete()
    return redirect('menu:listar_menu')

def exportar_menu_pdf(request):
    # 1. Capturar los mismos filtros que en la lista
    nombre_f = request.GET.get('nombre')
    categoria_f = request.GET.get('categoria')
    estado_f = request.GET.get('estado')
    
    # 2. Obtener datos filtrados
    platos = Menu.objects.all()
    
    if nombre_f:
        platos = platos.filter(nombre_plato__icontains=nombre_f)
    if categoria_f:
        platos = platos.filter(id_categoria=categoria_f)
    if estado_f:
        # Filtra exactamente por DISPONIBLE o NO DISPONIBLE
        platos = platos.filter(estado__iexact=estado_f)

    # 3. Definir quién genera el reporte
    rol = request.session.get('usuario_rol', 'Empleado').capitalize()
    nombre_user = request.session.get('usuario_nombre', 'Usuario')
    generado_por = f"{rol}: {nombre_user}"

    # 4. Preparar el contexto para el template
    template = get_template('menu/pdf_menu.html')
    context = {
        'platos': platos,
        'fecha': timezone.now(),
        'generado_por': generado_por,
    }
    
    # 5. Renderizar HTML a PDF
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    
    # Configuramos el nombre del archivo con la fecha actual
    fecha_str = timezone.now().strftime("%d-%m-%Y")
    # CAMBIO: 'attachment' fuerza la descarga directa
    response['Content-Disposition'] = f'attachment; filename="reporte_menu_{fecha_str}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)
        
    return response


def carga_masiva_menu(request):
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        archivo = request.FILES['archivo_excel']
        try:
            # Leemos el Excel
            df = pd.read_excel(archivo)
            
            platos_nuevos = []
            for index, row in df.iterrows():
                # Buscamos la categoría en la DB usando el ID del Excel
                categoria = CategoriaMenu.objects.get(id_categoria=int(row['id_categoria']))
                
                # Creamos el objeto usando los nombres exactos de tu modelo
                nuevo_plato = Menu(
                    nombre_plato=row['nombre_plato'],
                    descripcion=row['descripcion'],
                    precio=row['precio'],
                    id_categoria=categoria, # Pasamos el objeto categoría
                    estado='Disponible'    # Estado por defecto
                )
                platos_nuevos.append(nuevo_plato)
            
            # Inserción masiva eficiente
            Menu.objects.bulk_create(platos_nuevos)
            messages.success(request, "¡Platos cargados exitosamente!")
            return redirect('menu:listar_menu')
            
        except CategoriaMenu.DoesNotExist:
            messages.error(request, "Error: Uno de los ID de categoría no existe en la base de datos.")
        except Exception as e:
            messages.error(request, f"Error al leer el archivo: {e}")
            
    return render(request, 'menu/carga_masiva.html')

def analisis_menu(request):
    if 'usuario_id' not in request.session:
        return redirect('login')

    # KPIs Generales
    total_platos = Menu.objects.count()
    precio_promedio = Menu.objects.aggregate(Avg('precio'))['precio__avg'] or 0
    plato_mas_caro = Menu.objects.aggregate(Max('precio'))['precio__max'] or 0

    # 1. Distribución por Categoría
    # Consultamos la relación con CategoriaMenu
    por_categoria = Menu.objects.values('id_categoria__nombre_categoria').annotate(total=Count('id_plato'))
    
    labels_cat = [item['id_categoria__nombre_categoria'] for item in por_categoria]
    valores_cat = [item['total'] for item in por_categoria]

    # 2. Platos Disponibles vs No Disponibles
    por_estado = Menu.objects.values('estado').annotate(total=Count('id_plato'))
    labels_est = [item['estado'] for item in por_estado]
    valores_est = [item['total'] for item in por_estado]

    context = {
        'total_platos': total_platos,
        'precio_promedio': int(precio_promedio),
        'plato_mas_caro': int(plato_mas_caro),
        'labels_cat': json.dumps(labels_cat),
        'valores_cat': json.dumps(valores_cat),
        'labels_est': json.dumps(labels_est),
        'valores_est': json.dumps(valores_est),
    }
    return render(request, 'menu/analisis_menu.html', context)