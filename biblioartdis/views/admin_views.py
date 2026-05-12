# views/admin_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db.models.signals import post_save
import logging
import random
import string
import re

from ..decorators import admin_required
from ..models import (
    Usuario, Sugerencia, Categoria, Autor, VisitaLibro, Libro, Revista, Imagen,
    create_or_update_user_profile
)
from ..forms import VisitaFilterForm, UsuarioForm, AutorForm

logger = logging.getLogger(__name__)


def generar_username_unico(correo, ci):
    """Genera un username único para el usuario de Django"""
    # Limpiar correo (solo parte antes del @)
    correo_limpio = correo.split('@')[0]
    # Eliminar caracteres especiales
    correo_limpio = re.sub(r'[^a-zA-Z0-9_]', '', correo_limpio)
    base = f"{ci}_{correo_limpio}"
    # Limpiar caracteres especiales
    base = re.sub(r'[^a-zA-Z0-9_]', '', base)
    # Acortar si es muy largo
    if len(base) > 140:
        base = base[:140]
    return base


# ==================== Gestión de Usuarios ====================
@login_required
@admin_required
def lista_usuarios(request):
    usuarios = Usuario.objects.all().order_by('-usuario_id')
    paginator = Paginator(usuarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'lista_usuarios.html', {'page_obj': page_obj})


@login_required
@admin_required
def agregar_usuario(request):
    if request.method == 'GET':
        fecha_baja_default = timezone.now() + timedelta(days=5*365)
        return render(request, 'agregar_usuario.html', {'fecha_baja_default': fecha_baja_default})

    if request.method == 'POST':
        try:
            nombres = request.POST.get('nombres', '').strip()
            apepat = request.POST.get('apepat', '').strip()
            apemat = request.POST.get('apemat', '').strip()
            ci = request.POST.get('ci', '').strip()
            correo = request.POST.get('correo', '').strip().lower()
            extension = request.POST.get('extension', 'LP')
            complemento = request.POST.get('complemento', '').strip()
            tipo_usuario = request.POST.get('tipo_usuario', 'Externo')
            ru = request.POST.get('ru', '').strip()
            nro_celular = request.POST.get('nro_celular', '').strip()
            fecha_baja = request.POST.get('fecha_baja', '')

            # Validaciones básicas
            if not nombres:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'El nombre es obligatorio.'}, status=400)
                return render(request, 'agregar_usuario.html', {'mensaje': 'El nombre es obligatorio.'})
            
            if not ci or len(ci) < 5:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'El CI debe tener al menos 5 dígitos.'}, status=400)
                return render(request, 'agregar_usuario.html', {'mensaje': 'El CI debe tener al menos 5 dígitos.'})
            
            if not nro_celular or len(nro_celular) != 8:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'El número de celular debe tener 8 dígitos.'}, status=400)
                return render(request, 'agregar_usuario.html', {'mensaje': 'El número de celular debe tener 8 dígitos.'})

            if tipo_usuario == 'Estudiante' and (not ru or len(ru) < 5):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Para estudiantes, el RU es obligatorio y debe tener al menos 5 dígitos.'}, status=400)
                return render(request, 'agregar_usuario.html', {'mensaje': 'Para estudiantes, el RU es obligatorio y debe tener al menos 5 dígitos.'})

            # Validar formato de email
            if '@' not in correo:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Ingrese un correo electrónico válido.'}, status=400)
                return render(request, 'agregar_usuario.html', {'mensaje': 'Ingrese un correo electrónico válido.'})

            # Verificar CI único
            if Usuario.objects.filter(ci=ci).exists():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': f'El CI {ci} ya está registrado.'}, status=400)
                return render(request, 'agregar_usuario.html', {'mensaje': f'El CI {ci} ya está registrado.'})
            
            # Verificar RU único (solo para estudiantes)
            if ru and Usuario.objects.filter(ru=ru).exists():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'El RU ya está registrado.'}, status=400)
                return render(request, 'agregar_usuario.html', {'mensaje': 'El RU ya está registrado.'})

            logger.info(f"Creando usuario: {nombres}, CI: {ci}, Correo: {correo}, Tipo: {tipo_usuario}")

            try:
                # Desconectar señal temporalmente
                post_save.disconnect(create_or_update_user_profile, sender=User)
                
                with transaction.atomic():
                    # Generar username único
                    username_unico = generar_username_unico(correo, ci)
                    
                    # Crear usuario de Django con contraseña = CI (no se usará porque el login es por código)
                    django_user = User.objects.create_user(
                        username=username_unico,
                        email=correo,
                        password=ci
                    )
                    
                    # Crear perfil Usuario
                    usuario = Usuario.objects.create(
                        user=django_user,
                        nombres=nombres,
                        apepat=apepat,
                        apemat=apemat,
                        ci=ci,
                        correo=correo,
                        extension=extension,
                        complemento=complemento,
                        tipo_usuario=tipo_usuario,
                        ru=ru if tipo_usuario == 'Estudiante' else '',
                        nro_celular=nro_celular,
                        fecha_baja=fecha_baja if fecha_baja else timezone.now() + timedelta(days=5*365),
                        esta_activo=True
                    )
                    
                logger.info(f"Usuario creado exitosamente: ID {usuario.usuario_id}")
                
                # Respuesta exitosa
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success', 
                        'message': f'Usuario {nombres} creado exitosamente'
                    })
                else:
                    return render(request, 'aviso.html', {
                        'cabeza': 'Agregación de Usuario',
                        'cuerpo': f"Se ha agregado el usuario: {nombres} ({tipo_usuario}). El acceso es con su correo institucional y código de verificación."
                    })
                    
            except Exception as e:
                logger.error(f"Error al crear usuario: {str(e)}")
                if 'django_user' in locals():
                    try:
                        django_user.delete()
                    except:
                        pass
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': f'Error al crear: {str(e)}'}, status=500)
                return render(request, 'agregar_usuario.html', {'mensaje': f'Error al crear: {str(e)}'})
            finally:
                # Reconectar señal
                post_save.connect(create_or_update_user_profile, sender=User)
                
        except Exception as e:
            logger.error(f"Error general en agregar_usuario: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status=500)
            return render(request, 'agregar_usuario.html', {'mensaje': f'Error: {str(e)}'})

    return render(request, 'agregar_usuario.html')


@login_required
@admin_required
def modificar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, usuario_id=usuario_id)
    if request.method == 'POST':
        try:
            form = UsuarioForm(request.POST, instance=usuario)
            if form.is_valid():
                with transaction.atomic():
                    usuario = form.save(commit=False)
                    nuevo_correo = form.cleaned_data['correo']
                    if usuario.user:
                        usuario.user.email = nuevo_correo
                        usuario.user.username = nuevo_correo
                        usuario.user.save()
                    usuario.correo = nuevo_correo
                    usuario.save()
                return JsonResponse({
                    'status': 'success',
                    'message': f'Usuario {usuario.nombres} actualizado',
                    'redirect_url': reverse('lista_usuarios')
                })
            else:
                errores = [f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()]
                return JsonResponse({'status': 'error', 'message': '; '.join(errores)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    context = {
        'form': UsuarioForm(instance=usuario),
        'usuario': usuario,
        'opciones_usuarios': Usuario.opciones_usuarios,
        'opciones_extensiones': Usuario.opciones_extensiones,
        'titulo': f'Modificar Usuario: {usuario.nombres}'
    }
    return render(request, 'modificar_usuario.html', context)


@login_required
def eliminar_usuario(request, usuario_id):
    if request.method == 'POST':
        usuario = get_object_or_404(Usuario, usuario_id=usuario_id)
        nombre = usuario.nombres
        usuario.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': f'Usuario {nombre} eliminado'})
        return redirect('lista_usuarios')
    return redirect('lista_usuarios')


# ==================== Panel Principal / Dashboard ====================
@login_required
@admin_required
def principal(request):
    form = VisitaFilterForm()
    visitas_agrupadas_nivel = {}
    visitas_agrupadas_unitarias = {}
    vista_opcion = None

    if request.method == 'POST':
        form = VisitaFilterForm(request.POST)
        if form.is_valid():
            mes = form.cleaned_data['mes']
            año = form.cleaned_data['año']
            vista_opcion = form.cleaned_data['vista_opcion']
            visitas = VisitaLibro.objects.filter(fecha_consulta__year=año, fecha_consulta__month=mes)
            if visitas.exists():
                visitas_unitarias = visitas.values('libro_visitado__titulo').annotate(total=Count('id')).order_by('-total')
                for v in visitas_unitarias:
                    visitas_agrupadas_unitarias[v['libro_visitado__titulo']] = v['total']
                visitas_nivel = visitas.values('libro_visitado__categoria').annotate(total=Count('id')).order_by('-total')
                for v in visitas_nivel:
                    visitas_agrupadas_nivel[v['libro_visitado__categoria']] = v['total']
            else:
                messages.info(request, f'No se encontraron visitas para {mes}/{año}.')
        else:
            messages.error(request, 'El formulario contiene errores.')

    total_usuarios = Usuario.objects.count()
    total_sugerencias = Sugerencia.objects.count()
    from ..models import Libro, Revista, Imagen
    total_libros = Libro.objects.count()
    total_revistas = Revista.objects.count()
    total_imagenes = Imagen.objects.count()

    datos = {
        'total_usuarios': total_usuarios,
        'total_sugerencias': total_sugerencias,
        'total_libros': total_libros,
        'total_revistas': total_revistas,
        'total_imagenes': total_imagenes,
        'form': form,
        'visitas_agrupadas_nivel': visitas_agrupadas_nivel,
        'visitas_agrupadas_unitarias': visitas_agrupadas_unitarias,
        'vista_opcion': vista_opcion,
        'usuario': request.user.usuario
    }

    # Estadísticas adicionales
    estadisticas = {
        'usuarios_activos': Usuario.objects.filter(esta_activo=True).count(),
        'usuarios_nuevos_mes': Usuario.objects.filter(
            fecha_alta__month=datetime.now().month,
            fecha_alta__year=datetime.now().year
        ).count(),
        'libros_por_categoria': Categoria.objects.annotate(num_libros=Count('libro')).values('nom_cat', 'num_libros'),
        'imagenes_por_categoria': Categoria.objects.annotate(num_imagenes=Count('imagen')).values('nom_cat', 'num_imagenes'),
        'total_visitas_mes': VisitaLibro.objects.filter(
            fecha_visualizacion__month=datetime.now().month,
            fecha_visualizacion__year=datetime.now().year
        ).count(),
    }

    estado_sistema = {
        'libros': {
            'total': Libro.objects.count(),
            'archivos': {
                'pdfs': Libro.objects.exclude(pdf='').count(),
                'portadas': Libro.objects.exclude(img_portada='').count(),
                'autorizaciones': Libro.objects.exclude(archivo_autorizacion='').count()
            },
            'espacio': {
                'pdfs': sum(l.pdf.size for l in Libro.objects.all() if l.pdf and hasattr(l.pdf, 'size')),
                'portadas': sum(l.img_portada.size for l in Libro.objects.all() if l.img_portada and hasattr(l.img_portada, 'size')),
                'autorizaciones': sum(l.archivo_autorizacion.size for l in Libro.objects.all() if l.archivo_autorizacion and hasattr(l.archivo_autorizacion, 'size'))
            },
            'por_categoria': Libro.objects.values('categoria').annotate(total=Count('id_libro')),
            'por_tipo': Libro.objects.values('tipo').annotate(total=Count('id_libro'))
        },
        'revistas': {
            'total': Revista.objects.count(),
            'archivos': {'pdfs': Revista.objects.exclude(pdf='').count(), 'portadas': Revista.objects.exclude(img_portada='').count()},
            'espacio': {
                'pdfs': sum(r.pdf.size for r in Revista.objects.all() if r.pdf and hasattr(r.pdf, 'size')),
                'portadas': sum(r.img_portada.size for r in Revista.objects.all() if r.img_portada and hasattr(r.img_portada, 'size'))
            },
            'por_coleccion': Revista.objects.values('coleccion__nomb_colecc').annotate(total=Count('id_revista'))
        },
        'imagenes': {
            'total': Imagen.objects.count(),
            'archivos': {'imagenes': Imagen.objects.exclude(img_portada='').count(), 'pdfs': Imagen.objects.exclude(pdf='').count(), 'marcas_agua': Imagen.objects.exclude(marca_agua='').count()},
            'espacio': {
                'imagenes': sum(i.img_portada.size for i in Imagen.objects.all() if i.img_portada and hasattr(i.img_portada, 'size')),
                'pdfs': sum(i.pdf.size for i in Imagen.objects.all() if i.pdf and hasattr(i.pdf, 'size')),
                'marcas_agua': sum(i.marca_agua.size for i in Imagen.objects.all() if i.marca_agua and hasattr(i.marca_agua, 'size'))
            }
        },
        'totales': {
            'archivos_totales': {
                'pdfs': Libro.objects.exclude(pdf='').count() + Revista.objects.exclude(pdf='').count() + Imagen.objects.exclude(pdf='').count(),
                'imagenes': Libro.objects.exclude(img_portada='').count() + Revista.objects.exclude(img_portada='').count() + Imagen.objects.exclude(img_portada='').count()
            },
            'espacio_total': {'pdfs': 0, 'imagenes': 0, 'total': 0}
        }
    }
    estado_sistema['totales']['espacio_total']['pdfs'] = (
        estado_sistema['libros']['espacio']['pdfs'] +
        estado_sistema['revistas']['espacio']['pdfs'] +
        estado_sistema['imagenes']['espacio']['pdfs']
    )
    estado_sistema['totales']['espacio_total']['imagenes'] = (
        estado_sistema['libros']['espacio']['portadas'] +
        estado_sistema['revistas']['espacio']['portadas'] +
        estado_sistema['imagenes']['espacio']['imagenes'] +
        estado_sistema['imagenes']['espacio']['marcas_agua']
    )
    estado_sistema['totales']['espacio_total']['total'] = (
        estado_sistema['totales']['espacio_total']['pdfs'] +
        estado_sistema['totales']['espacio_total']['imagenes']
    )

    datos.update({'estadisticas': estadisticas, 'estado_sistema': estado_sistema})
    return render(request, 'principal.html', datos)


# ==================== Categorías ====================
@login_required
@admin_required
def agregar_categoria(request):
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre_categoria')
            if not nombre:
                raise ValueError('El nombre es requerido')
            categoria = Categoria.objects.create(nom_cat=nombre)
            return JsonResponse({'success': True, 'id_categoria': categoria.id_categoria, 'nombre': categoria.nom_cat})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def editar_categoria(request, id_categoria):
    try:
        categoria = get_object_or_404(Categoria, id_categoria=id_categoria)
        if request.method == 'POST':
            nombre = request.POST.get('nombre_categoria')
            if not nombre:
                raise ValueError('El nombre es requerido')
            categoria.nom_cat = nombre
            categoria.save()
            return JsonResponse({'success': True, 'id_categoria': categoria.id_categoria, 'nombre': categoria.nom_cat})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def eliminar_categoria(request, id_categoria):
    try:
        categoria = get_object_or_404(Categoria, id_categoria=id_categoria)
        nombre = categoria.nom_cat
        categoria.delete()
        return JsonResponse({'success': True, 'message': f'Categoría "{nombre}" eliminada'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ==================== Autores ====================
@login_required
def agregar_autor(request):
    if request.method == 'POST':
        form = AutorForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            if Autor.objects.filter(nombre=nombre).exists():
                return JsonResponse({'error': 'El autor ya existe.'})
            nuevo_autor = form.save()
            return JsonResponse({'id_autor': nuevo_autor.id_autor, 'nombre': str(nuevo_autor), 'success': True})
        return JsonResponse({'error': 'Formulario inválido.'})
    form = AutorForm()
    return render(request, 'agregar_autor.html', {'form': form})


@login_required
def editar_autor(request, id_autor):
    autor = get_object_or_404(Autor, id_autor=id_autor)
    if request.method == 'POST':
        form = AutorForm(request.POST, instance=autor)
        if form.is_valid():
            autor = form.save()
            return JsonResponse({'success': True, 'id_autor': autor.id_autor, 'nombre': autor.nombre})
        return JsonResponse({'success': False, 'errors': form.errors})


@login_required
def eliminar_autor(request, id_autor):
    autor = get_object_or_404(Autor, id_autor=id_autor)
    if request.method == 'POST':
        autor.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


# ==================== Sugerencias (Admin) ====================
@login_required
@admin_required
def listar_sugerencias(request):
    sugerencias = Sugerencia.objects.all().order_by('-fecha_sugerencia')
    paginator = Paginator(sugerencias, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'listar_sugerencias.html', {'sugerencias': page_obj})


@login_required
@admin_required
def aprobar_sugerencia(request, sugerencia_id):
    if request.method == 'POST':
        sugerencia = get_object_or_404(Sugerencia, pk=sugerencia_id)
        sugerencia.estado_respuesta = 'Aprobado'
        sugerencia.save()
        return redirect('listar_sugerencias')


# ==================== Monitoreo de Usuarios Activos ====================
@login_required
@admin_required
def usuarios_activos(request):
    """Vista para monitorear usuarios activos y sus lecturas"""
    from datetime import date, timedelta
    from django.db.models import Count
    from ..models import Libro  # ✅ Importación local
    
    # Obtener todos los usuarios con sus visitas recientes
    usuarios = Usuario.objects.filter(esta_activo=True).prefetch_related('visitalibro_set')
    
    # Datos para el dashboard
    stats = {
        'total_usuarios': Usuario.objects.count(),
        'usuarios_activos': Usuario.objects.filter(esta_activo=True).count(),
        'total_visitas_hoy': VisitaLibro.objects.filter(fecha_consulta=date.today()).count(),
        'total_visitas_semana': VisitaLibro.objects.filter(
            fecha_consulta__gte=date.today() - timedelta(days=7)
        ).count(),
        'libros_mas_leidos': Libro.objects.annotate(
            visitas_count=Count('visitalibro')
        ).order_by('-visitas_count')[:10],
        'usuarios_mas_activos': Usuario.objects.annotate(
            visitas_count=Count('visitalibro')
        ).order_by('-visitas_count')[:10]
    }
    
    # Últimas visitas (últimas 50)
    ultimas_visitas = VisitaLibro.objects.select_related(
        'visitante', 'libro_visitado'
    ).order_by('-fecha_visualizacion')[:50]
    
    context = {
        'usuarios': usuarios,
        'stats': stats,
        'ultimas_visitas': ultimas_visitas,
    }
    
    return render(request, 'usuarios_activos.html', context)


@login_required
@admin_required
def ver_historial_usuario(request, usuario_id):
    """Ver el historial completo de un usuario específico"""
    from django.core.paginator import Paginator
    from ..models import Libro  # ✅ Importación local
    
    usuario = get_object_or_404(Usuario, usuario_id=usuario_id)
    
    # Obtener visitas del usuario con información del libro
    visitas = VisitaLibro.objects.filter(
        visitante=usuario
    ).select_related('libro_visitado').order_by('-fecha_visualizacion')
    
    # Estadísticas del usuario
    stats = {
        'total_visitas': visitas.count(),
        'libros_distintos': visitas.values('libro_visitado').distinct().count(),
        'ultima_visita': visitas.first().fecha_visualizacion if visitas.exists() else None,
        'ultimo_libro': visitas.first().libro_visitado.titulo if visitas.exists() else 'Ninguno',
    }
    
    # Paginación
    paginator = Paginator(visitas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'usuario': usuario,
        'visitas': page_obj,
        'stats': stats,
    }
    
    return render(request, 'historial_usuario.html', context)