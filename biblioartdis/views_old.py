from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.db.models.signals import post_save
from django.db.models.functions import TruncMonth
from .models import (
    Usuario, Libro, Autor, Categoria, Sugerencia, 
    Coleccion, Revista, VisitaLibro, Imagen, create_or_update_user_profile,
    HistorialBusqueda
)
from .forms import (
    LoginForm, VisitaFilterForm, AutorForm, UsuarioForm,
    ImagenForm, ColeccionForm, RevistaForm, CambiarPasswordForm
)
from biblioartdis.utils.text_cleaner import limpiar_texto, limpiar_busqueda
from biblioartdis.utils.chat_responses import ChatResponses
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test, login_required
import random
import logging
import json
import re
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from difflib import get_close_matches
import spacy
from django.contrib.auth.hashers import make_password, check_password

nlp = spacy.load("es_core_news_sm")
logger = logging.getLogger(__name__)

def is_admin(user):
    return hasattr(user, 'usuario') and user.usuario.tipo_usuario == 'Administrador'

admin_required = user_passes_test(is_admin, login_url='inicio')
#historial de consulta de libros del usuario dela sesion actual
@login_required
def historial_visitas(request):
    try:
        usuario = request.user.usuario
        visitas = VisitaLibro.objects.filter(visitante=usuario).order_by('-fecha_visualizacion')
        return render(request, 'historial_visitas.html', {'visitas': visitas})
    except Usuario.DoesNotExist:
        messages.error(request, "Tu cuenta de usuario no está correctamente configurada. Por favor contacta al administrador.")
        return redirect('inicio')

#registrar las viositas cada vs qu haga click ver pdf del libro
@login_required
def registrar_visita_libro(request):
    if request.method == 'POST':
        try:
            libro_id = request.POST.get('libro_id')
            usuario = request.user.usuario  # Get usuario directly from request.user

            # Get or create the visit record
            visita, created = VisitaLibro.objects.get_or_create(
                visitante=usuario,
                libro_visitado_id=libro_id,
                fecha_consulta=date.today(),
                defaults={'fecha_visualizacion': timezone.now()}
            )

            if not created:
                # Update visualization time if record already exists
                visita.fecha_visualizacion = timezone.now()
                visita.save()

            return JsonResponse({'mensaje': 'Visita registrada correctamente'})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


#LISTAR LOS 10 ULTIMOS LIBROS REGISTRADOS
@login_required
def novedades_libros(request):
    # Base queryset for all books and images
    libros_base = Libro.objects.all().prefetch_related('autores', 'categorias')
    imagenes_base = Imagen.objects.prefetch_related('categorias').all()
    
    # Get filter parameters
    filtros = {
        'categoria': request.GET.get('categoria'),
        'tipo': request.GET.get('tipo'),
        'autor': request.GET.get('autor'),
        'descarga': request.GET.get('descarga')
    }
    
    # Apply filters to get filtered queryset
    libros_filtered = libros_base
    imagenes_filtered = imagenes_base
    
    if filtros['categoria']:
        libros_filtered = libros_filtered.filter(categorias__id_categoria=filtros['categoria'])
        imagenes_filtered = imagenes_filtered.filter(categorias__id_categoria=filtros['categoria'])
    
    if filtros['tipo']:
        libros_filtered = libros_filtered.filter(tipo=filtros['tipo'])
    
    if filtros['autor']:
        libros_filtered = libros_filtered.filter(autores__id_autor=filtros['autor'])
    
    if filtros['descarga'] is not None:
        libros_filtered = libros_filtered.filter(descarga_autorizada=filtros['descarga'] == '1')
    
    # Get all categories with their counts from base queryset
    categorias = Categoria.objects.all()
    categoria_counts = {
        str(cat.id_categoria): {
            'libros': libros_base.filter(categorias__id_categoria=cat.id_categoria, tipo='LIBRO').distinct().count(),
            'imagenes': imagenes_base.filter(categorias__id_categoria=cat.id_categoria).distinct().count()
        } for cat in categorias
    }
    
    # Get all authors with their book counts
    autores = Autor.objects.all()
    autor_counts = {
        str(autor.id_autor): libros_base.filter(autores__id_autor=autor.id_autor, tipo='LIBRO').distinct().count()
        for autor in autores
    }
    
    # Get counts for each document type
    tipos = []
    for tipo_choice in Libro._meta.get_field('tipo').choices:
        count = libros_base.filter(tipo=tipo_choice[0])
        if filtros['categoria']:
            count = count.filter(categorias__id_categoria=filtros['categoria'])
        if filtros['autor']:
            count = count.filter(autores__id_autor=filtros['autor'])
        tipos.append((tipo_choice[0], tipo_choice[1], count.distinct().count()))
    
    # Get download status counts (only for books)
    descarga_counts = {
        'autorizada': libros_base.filter(descarga_autorizada=True, tipo='LIBRO').distinct().count(),
        'no_autorizada': libros_base.filter(descarga_autorizada=False, tipo='LIBRO').distinct().count()
    }
    
    context = {
        'libros': libros_filtered.distinct(),
        'imagenes': imagenes_filtered.distinct(),
        'categorias': categorias,
        'categoria_counts': categoria_counts,
        'autores': autores,
        'autor_counts': autor_counts,
        'tipos': tipos,
        'descarga_counts': descarga_counts,
        'filtros_activos': filtros,
        'total_libros': libros_base.distinct().count(),
        'total_imagenes': imagenes_base.distinct().count()
    }
    
    return render(request, 'novedades_libros.html', context)

#MOSTRAR LIBROS POR NIVEL
@login_required
def libros_nivel(request, id_nivel):
    niveles = {
        1: 'NIVEL 1',
        2: 'NIVEL 2',
        3: 'NIVEL 3',
        4: 'NIVEL 4'
    }
    nomb_nivel={
        1:"PRIMER AÑO",
        2:"SEGUNDO AÑO",
        3:"TERCERO AÑO",
        4:"CUARTO AÑO",
        5:"OTRAS SECCIONES",
    }
    categoria = niveles.get(id_nivel, 'OTRO')
    libros = Libro.objects.filter(categoria=categoria)
    return render(request, 'nivel.html', {'libros': libros, 'nivel': categoria,'nomb_nivel':nomb_nivel.get(id_nivel, 'OTRO')})

#catalogo de revistas por cada coleccion

def catalogo(request):
    colecciones = Coleccion.objects.prefetch_related('revista_set').all()
    return render(request, 'catalogo.html', {'colecciones': colecciones})

from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@admin_required
def actualizar_orden_colecciones(request):
    if request.method == 'POST':
        coleccion_ids = request.POST.getlist('coleccion_ids[]')
        for index, coleccion_id in enumerate(coleccion_ids):
            Coleccion.objects.filter(id_coleccion=coleccion_id).update(orden=index)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
@admin_required
def modificar_coleccion(request, id_coleccion):
    coleccion = get_object_or_404(Coleccion, id_coleccion=id_coleccion)
    
    if request.method == 'POST':
        form = ColeccionForm(request.POST, instance=coleccion)
        if form.is_valid():
            form.save()
            # Si es una petición AJAX, devolver respuesta JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Colección actualizada correctamente'
                })
            return redirect('listar_revistas')
        else:
            # Si hay errores y es AJAX, devolver los errores
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Error en el formulario',
                    'errors': form.errors
                })
    else:
        form = ColeccionForm(instance=coleccion)
    
    return render(request, 'modificar_coleccion.html', {
        'form': form,
        'coleccion': coleccion
    })
@login_required
@admin_required
def listar_revistas(request):
    revistas = Revista.objects.all()
    colecciones = Coleccion.objects.all()
    return render(request, 'listar_revistas.html', {'revistas': revistas, 'colecciones': colecciones})

@login_required
@admin_required
def eliminar_revista(request, id_revista):
    if request.method == 'POST':
        revista = get_object_or_404(Revista, id_revista=id_revista)
        revista.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@login_required
@admin_required
def eliminar_coleccion(request, id_coleccion):
    if request.method == 'POST':
        coleccion = get_object_or_404(Coleccion, id_coleccion=id_coleccion)
        coleccion.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@login_required
@admin_required
def agregar_revista(request):
    if request.method == 'POST':
        try:
            # Validación básica
            if not request.POST.get('coleccion'):
                raise ValueError('La colección es requerida')
            
            coleccion = Coleccion.objects.get(id_coleccion=request.POST['coleccion'])
            
            # Manejar el número de revista
            nro_revista = request.POST.get('nro_revista')
            nro_revista = int(nro_revista) if nro_revista else None
            
            # Validar archivos requeridos
            if not request.FILES.get('img_portada'):
                raise ValueError('La imagen de portada es requerida')
            
            # Crear la revista con todos los campos
            revista = Revista(
                nro_revista=nro_revista,
                coleccion=coleccion,
                descripcion=request.POST.get('descripcion', '').strip(),
                img_portada=request.FILES.get('img_portada'),
                pdf=request.FILES.get('pdf'),
                url=request.POST.get('url', '').strip()
            )
            
            revista.save()
            
            # Respuesta para peticiones AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Revista agregada correctamente',
                    'id': revista.id_revista,
                    'titulo': f'Revista #{revista.nro_revista}' if revista.nro_revista else 'Nueva Revista'
                })
            
            messages.success(request, 'Revista agregada correctamente')
            return redirect('listar_revistas')
            
        except ValueError as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=400)
            messages.error(request, str(e))
            return redirect('agregar_revista')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Error inesperado: {str(e)}'
                }, status=500)
            messages.error(request, f'Error inesperado: {str(e)}')
            return redirect('agregar_revista')
    
    # GET request
    colecciones = Coleccion.objects.all().order_by('nomb_colecc')
    return render(request, 'agregar_revista.html', {
        'colecciones': colecciones,
        'max_upload_size_mb': {
            'imagen': 5,
            'pdf': 10
        }
    })

@login_required
@admin_required
def modificar_revista(request, id_revista):
    revista = get_object_or_404(Revista, id_revista=id_revista)
    
    if request.method == 'POST':
        form = RevistaForm(request.POST, request.FILES, instance=revista)
        if form.is_valid():
            try:
                revista = form.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Revista actualizada correctamente',
                    'data': {
                        'id': revista.id_revista,
                        'nro_revista': revista.nro_revista,
                        'descripcion': revista.descripcion,
                        'coleccion': revista.coleccion.nomb_colecc,
                        'tiene_pdf': bool(revista.pdf),
                        'tiene_url': bool(revista.url)
                    }
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error al guardar la revista: {str(e)}'
                }, status=500)
        else:
            # Formatear errores del formulario para una mejor presentación
            errores = {}
            for field, errors in form.errors.items():
                errores[field] = [str(error) for error in errors]
            
            return JsonResponse({
                'success': False,
                'message': 'Por favor corrija los errores en el formulario',
                'errors': errores
            }, status=400)
    else:
        form = RevistaForm(instance=revista)
    
    return render(request, 'modificar_revista.html', {
        'form': form,
        'revista': revista,
        'max_upload_size_mb': {
            'imagen': 5,
            'pdf': 10
        }
    })
@login_required
@admin_required
def agregar_coleccion(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            nombre_coleccion = request.POST.get('nomb_colecc')
            descripcion = request.POST.get('descripcion')
            nueva_coleccion = Coleccion.objects.create(
                nomb_colecc=nombre_coleccion,
                descripcion=descripcion
            )
            
            return JsonResponse({
                'success': True,
                'id_coleccion': nueva_coleccion.id_coleccion,
                'nomb_colecc': nueva_coleccion.nomb_colecc,
                'descripcion': nueva_coleccion.descripcion
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@login_required
def listar_sugerencias_usuario(request):
    try:
        # Obtener el usuario existente
        usuario = get_object_or_404(Usuario, user=request.user)
        
        sugerencias = Sugerencia.objects.filter(solicitante=usuario)
        return render(request, 'listar_sugerencias_usuario.html', {'sugerencias': sugerencias})
    except Exception as e:
        messages.error(request, "Hubo un problema al acceder a su perfil de usuario. Por favor, contacte al administrador.")
        print(f"Error en listar_sugerencias_usuario: {e}")
        return redirect('inicio')

@login_required
def sugerir_libro(request):
    if request.method == 'POST':
        autor_sugerencia = request.POST.get('autor_sugerencia')
        titulo_sugerencia = request.POST.get('titulo_sugerencia')
        edicion = request.POST.get('edicion')
        descripcion = request.POST.get('descripcion')
        
        # Obtener la instancia del modelo Usuario correspondiente al usuario autenticado

        nueva_sugerencia = Sugerencia(
            solicitante=request.user.usuario,
            autor_sugerencia=autor_sugerencia,
            titulo_sugerencia=titulo_sugerencia,
            edicion=edicion,
            estado_respuesta='Pendiente',
            descripcion=descripcion 
        )
        nueva_sugerencia.save()
        
        return redirect('listar_sugerencias_usuario')  
    return render(request, 'sugerir_libro.html')

@login_required
def descartar_sugerencia(request, sugerencia_id):
    sugerencia = get_object_or_404(Sugerencia, pk=sugerencia_id)
    sugerencia.estado_respuesta = 'Descartado'
    sugerencia.save()
    return redirect('listar_sugerencias')

@login_required
@admin_required
def aprobar_sugerencia(request, sugerencia_id):  
    if request.method == 'POST':
        sugerencia = get_object_or_404(Sugerencia, pk=sugerencia_id)
        sugerencia.estado_respuesta = 'Aprobado'
        sugerencia.save()
        return redirect('listar_sugerencias')

@login_required
@admin_required
def listar_sugerencias(request):
    sugerencias = Sugerencia.objects.all().order_by('-fecha_sugerencia')  # Ordenar por fecha, por ejemplo
    
    # Configuración de paginación
    paginator = Paginator(sugerencias, 10)  # Muestra 10 sugerencias por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'listar_sugerencias.html', {'sugerencias': page_obj})

@login_required
@admin_required
def agregar_categoria(request):
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre_categoria')
            if not nombre:
                raise ValueError('El nombre de la categoría es requerido')
                
            categoria = Categoria.objects.create(nom_cat=nombre)
            return JsonResponse({
                'success': True,
                'message': 'Categoría agregada exitosamente',
                'id_categoria': categoria.id_categoria,
                'nombre': categoria.nom_cat
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

@login_required
def editar_categoria(request, id_categoria):
    try:
        categoria = get_object_or_404(Categoria, id_categoria=id_categoria)
        if request.method == 'POST':
            nombre = request.POST.get('nombre_categoria')
            if not nombre:
                raise ValueError('El nombre de la categoría es requerido')
                
            categoria.nom_cat = nombre
            categoria.save()
            return JsonResponse({
                'success': True,
                'message': 'Categoría actualizada exitosamente',
                'id_categoria': categoria.id_categoria,
                'nombre': categoria.nom_cat
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def eliminar_categoria(request, id_categoria):
    try:
        categoria = get_object_or_404(Categoria, id_categoria=id_categoria)
        nombre = categoria.nom_cat
        categoria.delete()
        return JsonResponse({
            'success': True,
            'message': f'Categoría "{nombre}" eliminada exitosamente'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@admin_required
def agregar_libro(request):
    autores = Autor.objects.all()
    categorias = Categoria.objects.all()
    
    if request.method == 'POST':
        try:
            titulo = request.POST.get('titulo')
            edicion = request.POST.get('edicion')
            tipo = request.POST.get('tipo')
            categoria = request.POST.get('categoria')
            descripcion = request.POST.get('descripcion', '').strip()  # Obtener descripción
            autores_seleccionados = request.POST.getlist('autores')
            palabras_claves = request.POST.get('palabras_claves', '').split(',')
            pdf_url = request.POST.get('pdf_url')
            categorias_seleccionadas = request.POST.getlist('categorias')
            
            # Crear nuevo libro
            nuevo_libro = Libro(
                titulo=titulo,
                edicion=edicion,
                tipo=tipo,
                categoria=categoria,
                descripcion=descripcion,  # Añadir descripción
                pdf_url=pdf_url
            )

            # Manejar archivos
            if 'portada' in request.FILES:
                nuevo_libro.img_portada = request.FILES['portada']
            if 'pdf' in request.FILES:
                nuevo_libro.pdf = request.FILES['pdf']
            if 'autorizacion' in request.FILES:
                nuevo_libro.archivo_autorizacion = request.FILES['autorizacion']

            nuevo_libro.save()

            # Procesar el nuevo autor si existe
            nuevo_autor_nombre = request.POST.get('nombre_autor')
            if nuevo_autor_nombre and nuevo_autor_nombre.strip():
                # Verificar si el autor ya existe
                autor_existente = Autor.objects.filter(nombre=nuevo_autor_nombre).first()
                if autor_existente:
                    nuevo_libro.autores.add(autor_existente)
                else:
                    nuevo_autor = Autor(nombre=nuevo_autor_nombre)
                    nuevo_autor.save()
                    nuevo_libro.autores.add(nuevo_autor)

            # Agregar autores existentes seleccionados
            for autor_id in autores_seleccionados:
                try:
                    autor = Autor.objects.get(pk=autor_id)
                    nuevo_libro.autores.add(autor)
                except (Autor.DoesNotExist, ValueError):
                    continue

            # Agregar categorías
            for categoria_id in categorias_seleccionadas:
                try:
                    categoria = Categoria.objects.get(pk=categoria_id)
                    nuevo_libro.categorias.add(categoria)
                except Categoria.DoesNotExist:
                    print(f'Categoría con ID {categoria_id} no encontrada.')
            
            # Guardar palabras clave
            for palabra in palabras_claves:
                if palabra.strip():
                    nuevo_libro.agregar_palabras_claves(palabra.strip())

            return JsonResponse({
                'success': True,
                'message': 'Libro agregado exitosamente',
                'libro_id': nuevo_libro.id_libro,
                'titulo': nuevo_libro.titulo,
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al agregar el libro: {str(e)}'
            })

    context = {
        'autores': autores,
        'categorias': categorias,
    }
    return render(request, 'agregar_libro.html', context)
    
@login_required
def eliminar_libro(request, libro_id):
    libro = get_object_or_404(Libro, pk=libro_id)
    if request.method == 'POST':
        libro.delete()
        return redirect('listar_libros')
    
@login_required
def eliminar_autorizacion(request, libro_id):
    libro = get_object_or_404(Libro, id_libro=libro_id)
    
    if request.method == 'POST':
        # Verificar si hay un archivo de autorización
        if libro.archivo_autorizacion:
            libro.archivo_autorizacion.delete(save=False)  # Eliminar el archivo del sistema de archivos
            libro.archivo_autorizacion = None  # Limpiar el campo en el modelo
            libro.save()  # Guardar los cambios en la base de datos
            
            return JsonResponse({'success': True, 'message': 'Autorización eliminada exitosamente.'})
        else:
            return JsonResponse({'success': False, 'message': 'No hay autorización para eliminar.'})
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

@login_required
@admin_required
def editar_libro(request, libro_id):
    libro = get_object_or_404(Libro, id_libro=libro_id)
    
    if request.method == 'POST':
        try:
            # Validación básica
            if not request.POST.get('titulo'):
                return JsonResponse({
                    'success': False,
                    'error': 'El título es requerido'
                }, status=400)

            # Actualizar campos básicos
            libro.titulo = request.POST.get('titulo').strip()
            libro.edicion = request.POST.get('edicion', '').strip()
            libro.tipo = request.POST.get('tipo')
            libro.descripcion = request.POST.get('descripcion', '').strip()
            libro.categoria = request.POST.get('categoria')  # Añadido para manejar el nivel
            libro.categorias.set(request.POST.getlist('categorias'))  # Añadido para manejar las categorías
            
            # Manejar PDF y URL
            if 'pdf' in request.FILES:
                libro.pdf = request.FILES['pdf']
                libro.pdf_url = ''  # Limpiar URL si hay archivo
            else:
                pdf_url = request.POST.get('pdf_url', '').strip()
                libro.pdf_url = pdf_url

            # Manejar otros archivos
            if 'portada' in request.FILES:
                libro.img_portada = request.FILES['portada']
            if 'autorizacion' in request.FILES:
                libro.archivo_autorizacion = request.FILES['autorizacion']

            # Actualizar relaciones
            if 'autores' in request.POST:
                autores = request.POST.getlist('autores')
                if autores:
                    libro.autores.set(autores)
                else:
                    libro.autores.clear()

            # Actualizar palabras clave
            palabras_claves = request.POST.get('palabras_claves', '')
            if palabras_claves:
                libro.palabra_clave = palabras_claves

            libro.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Libro actualizado exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

    # Contexto para GET
    context = {
        'libro': libro,
        'autores': Autor.objects.all(),
        'categorias': Categoria.objects.all(),
        'palabras_claves': libro.palabra_clave.split(',') if libro.palabra_clave else []
    }
    
    return render(request, 'editar_libro.html', context)

def cambiar_estado_descarga(request, libro_id):
    libro = get_object_or_404(Libro, id_libro=libro_id)
    
    # Cambiar el estado de descarga autorizada
    libro.descarga_autorizada = not libro.descarga_autorizada
    libro.save()
    
    return redirect('listar_libros') 
@login_required
#verpdf d un libro
def ver_pdf(request, libro_id):
    libro = get_object_or_404(Libro, id_libro=libro_id)
    # Devuelve el PDF como respuesta
    response = HttpResponse(libro.pdf, content_type='application/pdf')
    return response

from django.core.paginator import Paginator
@login_required
@admin_required
def listar_libros(request):
    # Obtener todos los libros
    libros = Libro.objects.all()

    # Ordenar los libros
    if request.GET.get('ordenar') == 'fecha_asc':
        libros = libros.order_by('fecha_publicacion')
    elif request.GET.get('ordenar') == 'fecha_desc':
        libros = libros.order_by('-fecha_publicacion')
    else:
        # Cambiamos a id_libro que es el nombre correcto del campo
        libros = libros.order_by('-id_libro')

    # Configuración de paginación
    paginator = Paginator(libros, 10)  # Muestra 10 libros por página
    page_number = request.GET.get('page')  # Obtener el número de página de la URL
    page_obj = paginator.get_page(page_number)
    
    # Pasar el usuario al contexto
    return render(request, 'listar_libros.html', {
        'libros': page_obj,
        'usuario': request.user  # Asegúrate de que esto esté correcto
    })
#primero que se visualiza, login

from django.contrib.auth.views import LoginView

class CustomLoginView(LoginView):
    template_name = 'login.html'

def home(request):
    if request.method == 'POST':
        correo = request.POST.get('correo')
        password = request.POST.get('password')
        
        if not correo:
            messages.error(request, '⚠️ Por favor ingresa tu correo electrónico')
            return render(request, 'login.html')
        
        if not password:
            messages.error(request, '🔒 Por favor ingresa tu contraseña')
            return render(request, 'login.html')
            
        user = authenticate(request, username=correo, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'¡Bienvenido/a {user.first_name}! 👋')
            return redirect('principal')  # Redirect to principal page after successful login
        else:
            messages.error(request, '❌ Credenciales inválidas. Por favor, intenta nuevamente.')
            return render(request, 'login.html')
    
    return render(request, 'login.html')

@login_required
def logout_view(request):
    if request.method == 'GET' or request.method == 'POST':
        logout(request)
        messages.success(request, '¡Has cerrado sesión exitosamente!')
        return redirect('home')
    return HttpResponse('Método no permitido', status=405)

@require_http_methods(["POST"])
@login_required
def cambiar_password(request):
    try:
        data = json.loads(request.body)
        password_actual = data.get('password_actual')
        password_nuevo = data.get('password_nuevo')
        
        # Verificar si la contraseña actual es correcta
        if request.user.check_password(password_actual):
            request.user.set_password(password_nuevo)
            request.user.save()
            
            # Actualizar la sesión para que el usuario no sea desconectado
            update_session_auth_hash(request, request.user)
            
            return JsonResponse({'success': True})
        else:
            return JsonResponse({
                'success': False, 
                'error': 'La contraseña actual es incorrecta'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        })
 
@require_http_methods(["POST"])
@login_required
@admin_required
def restablecer_password(request):
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Método no permitido'
        }, status=405)

    try:
        # Verificar si el usuario actual es administrador
        if request.user.usuario.tipo_usuario != 'Administrador':
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para realizar esta acción'
            }, status=403)

        # Obtener y validar datos
        data = json.loads(request.body)
        usuario_id = data.get('usuario_id')
        ci = data.get('ci')
        
        if not usuario_id or not ci:
            return JsonResponse({
                'success': False,
                'error': 'Faltan datos requeridos'
            }, status=400)

        # Obtener el usuario y restablecer su contraseña
        try:
            usuario = Usuario.objects.get(usuario_id=usuario_id)
        except Usuario.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuario no encontrado'
            }, status=404)

        if not usuario.user:
            return JsonResponse({
                'success': False,
                'error': 'Usuario no tiene cuenta de acceso asociada'
            }, status=400)

        # Restablecer la contraseña
        usuario.user.set_password(ci)
        usuario.user.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Contraseña restablecida correctamente'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos JSON inválidos'
        }, status=400)
    except Exception as e:
        logger.error(f"Error al restablecer contraseña: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)
@admin_required 
def lista_usuarios(request):
    usuarios = Usuario.objects.all().order_by('-usuario_id')
    # Configuración de paginación
    paginator = Paginator(usuarios, 10)  # Muestra 10 usuarios por página
    page_number = request.GET.get('page')                         
    page_obj = paginator.get_page(page_number)

    return render(request, 'lista_usuarios.html', {'page_obj': page_obj})


@login_required
@admin_required
def agregar_usuario(request):
    if request.method == 'GET':
        fecha_baja_default = timezone.now() + timedelta(days=5*365)
        return render(request, 'agregar_usuario.html', {
            'fecha_baja_default': fecha_baja_default
        })

    if request.method == 'POST':
        try:
            # Obtener y validar datos
            nombres = request.POST['nombres'].strip()
            apepat = request.POST['apepat'].strip()
            apemat = request.POST['apemat'].strip()
            ci = request.POST['ci'].strip()
            correo = request.POST['correo'].strip().lower()
            extension = request.POST['extension']
            complemento = request.POST.get('complemento', '').strip()
            tipo_usuario = request.POST['tipo_usuario']
            ru = request.POST.get('ru', '').strip()
            nro_celular = request.POST['nro_celular'].strip()
            fecha_baja = request.POST.get('fecha_baja')

            # Validaciones básicas
            if len(ci) < 5:
                return render(request, 'agregar_usuario.html', {'mensaje': 'El CI debe tener al menos 5 dígitos.'})
            
            if len(nro_celular) != 8:
                return render(request, 'agregar_usuario.html', {'mensaje': 'El número de celular debe tener 8 dígitos.'})

            if tipo_usuario == 'Estudiante' and (not ru or len(ru) < 5):
                return render(request, 'agregar_usuario.html', {'mensaje': 'Para estudiantes, el RU es obligatorio y debe tener al menos 5 dígitos.'})

            # Verificar correo existente
            if User.objects.filter(Q(email=correo) | Q(username=correo)).exists():
                return render(request, 'agregar_usuario.html', {'mensaje': 'El correo ya está registrado.'})

            # Verificar CI
            if Usuario.objects.filter(ci=ci).exists():
                return render(request, 'agregar_usuario.html', {'mensaje': 'El CI ya está registrado.'})
            
            # Verificar RU solo si es estudiante y tiene RU
            if ru and Usuario.objects.filter(ru=ru).exists():
                return render(request, 'agregar_usuario.html', {'mensaje': 'El RU ya está registrado.'})

            try:
                # Desconectar temporalmente la señal
                post_save.disconnect(create_or_update_user_profile, sender=User)
                
                with transaction.atomic():
                    # 1. Crear el usuario de Django y guardarlo
                    django_user = User.objects.create_user(
                        username=correo,
                        email=correo,
                        password=ci
                    )

                    # 2. Crear el usuario personalizado
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
                        fecha_baja=fecha_baja if fecha_baja else timezone.now() + timedelta(days=5*365)
                    )

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return HttpResponse('success')
                else:
                    return render(request, 'aviso.html', {
                        'cabeza': 'Agregación de Usuario', 
                        'cuerpo': f"Se ha agregado el usuario: {nombres} satisfactoriamente. La contraseña inicial es su CI."
                    })

            except IntegrityError as e:
                # Si hay un error de integridad, eliminar el usuario de Django si fue creado
                if 'django_user' in locals():
                    django_user.delete()
                return render(request, 'agregar_usuario.html', {'mensaje': f'Error de integridad al crear el usuario: {str(e)}'})
            except Exception as e:
                # Si hay cualquier otro error, eliminar el usuario de Django si fue creado
                if 'django_user' in locals():
                    django_user.delete()
                return render(request, 'agregar_usuario.html', {'mensaje': f'Error al crear el usuario: {str(e)}'})
            finally:
                # Reconectar la señal sin importar lo que pase
                post_save.connect(create_or_update_user_profile, sender=User)

        except Exception as e:
            # Si algo sale mal, eliminar el usuario de Django si fue creado
            if 'django_user' in locals():
                try:
                    with transaction.atomic():
                        Usuario.objects.filter(user=django_user).delete()
                        django_user.delete()
                except Exception as delete_error:
                    print(f"Error al eliminar usuario: {delete_error}")
            
            error_message = f'Error al crear el usuario: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return render(request, 'agregar_usuario.html', {'mensaje': error_message})
            else:
                return render(request, 'agregar_usuario.html', {'mensaje': error_message})

    return render(request, 'agregar_usuario.html')

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
@login_required
@admin_required
def principal(request):
    form = VisitaFilterForm()
    visitas_agrupadas_nivel = {}  # Datos para la tabla o gráfica por categoría
    visitas_agrupadas_unitarias = {}  # Datos para la tabla o gráfica por título
    vista_opcion = None  # Inicializa vista_opcion con un valor por defecto

    if request.method == 'POST':
        form = VisitaFilterForm(request.POST)
        if form.is_valid():
            mes = form.cleaned_data['mes']
            año = form.cleaned_data['año']
            vista_opcion = form.cleaned_data['vista_opcion']

            # Consulta genérica
            visitas = VisitaLibro.objects.filter(
                fecha_consulta__year=año,
                fecha_consulta__month=mes
            )

            # Agrupamos siempre por título y por categoría
            if visitas.exists():
                visitas_unitarias = visitas.values('libro_visitado__titulo').annotate(total=Count('id')).order_by('-total')
                for visita in visitas_unitarias:
                    titulo = visita['libro_visitado__titulo']
                    visitas_agrupadas_unitarias[titulo] = visita['total']

                visitas_nivel = visitas.values('libro_visitado__categoria').annotate(total=Count('id')).order_by('-total')
                for visita in visitas_nivel:
                    categoria = visita['libro_visitado__categoria']
                    visitas_agrupadas_nivel[categoria] = visita['total']
            else:
                messages.info(request, f'No se encontraron visitas para {mes}/{año}.')
        else:
            messages.error(request, 'El formulario contiene errores.')

    # Contadores generales
    total_usuarios = Usuario.objects.count()
    total_sugerencias = Sugerencia.objects.count()
    total_libros = Libro.objects.count()
    total_revistas = Revista.objects.count()
    total_imagenes = Imagen.objects.count()

    # Datos que serán renderizados en el template
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
        'usuario': request.user.usuario  # Para saber qué opción fue seleccionada
    }

    # Estadísticas adicionales
    estadisticas = {
        # Usuarios
        'usuarios_activos': Usuario.objects.filter(esta_activo=True).count(),
        'usuarios_nuevos_mes': Usuario.objects.filter(
            fecha_alta__month=datetime.now().month,
            fecha_alta__year=datetime.now().year
        ).count(),
        
        
        # Estadísticas por tipo de contenido
        'libros_por_categoria': Categoria.objects.annotate(
            num_libros=Count('libro')
        ).values('nom_cat', 'num_libros'),
        
        'imagenes_por_categoria': Categoria.objects.annotate(
            num_imagenes=Count('imagen')
        ).values('nom_cat', 'num_imagenes'),
        
        # Métricas de uso
        'total_visitas_mes': VisitaLibro.objects.filter(
            fecha_visualizacion__month=datetime.now().month,
            fecha_visualizacion__year=datetime.now().year
        ).count(),
    }
    
    # Estado del sistema
    estado_sistema = {
        # Desglose por tipo de contenido
        'libros': {
            'total': Libro.objects.count(),
            'archivos': {
                'pdfs': Libro.objects.exclude(pdf='').count(),
                'portadas': Libro.objects.exclude(img_portada='').count(),
                'autorizaciones': Libro.objects.exclude(archivo_autorizacion='').count()
            },
            'espacio': {
                'pdfs': sum(libro.pdf.size for libro in Libro.objects.all() if libro.pdf and hasattr(libro.pdf, 'size')),
                'portadas': sum(libro.img_portada.size for libro in Libro.objects.all() if libro.img_portada and hasattr(libro.img_portada, 'size')),
                'autorizaciones': sum(libro.archivo_autorizacion.size for libro in Libro.objects.all() if libro.archivo_autorizacion and hasattr(libro.archivo_autorizacion, 'size'))
            },
            'por_categoria': Libro.objects.values('categoria').annotate(total=Count('id_libro')),
            'por_tipo': Libro.objects.values('tipo').annotate(total=Count('id_libro'))
        },
        
        'revistas': {
            'total': Revista.objects.count(),
            'archivos': {
                'pdfs': Revista.objects.exclude(pdf='').count(),
                'portadas': Revista.objects.exclude(img_portada='').count()
            },
            'espacio': {
                'pdfs': sum(revista.pdf.size for revista in Revista.objects.all() if revista.pdf and hasattr(revista.pdf, 'size')),
                'portadas': sum(revista.img_portada.size for revista in Revista.objects.all() if revista.img_portada and hasattr(revista.img_portada, 'size'))
            },
            'por_coleccion': Revista.objects.values('coleccion__nomb_colecc').annotate(total=Count('id_revista'))
        },
        
        'imagenes': {
            'total': Imagen.objects.count(),
            'archivos': {
                'imagenes': Imagen.objects.exclude(img_portada='').count(),
                'pdfs': Imagen.objects.exclude(pdf='').count(),
                'marcas_agua': Imagen.objects.exclude(marca_agua='').count()
            },
            'espacio': {
                'imagenes': sum(imagen.img_portada.size for imagen in Imagen.objects.all() if imagen.img_portada and hasattr(imagen.img_portada, 'size')),
                'pdfs': sum(imagen.pdf.size for imagen in Imagen.objects.all() if imagen.pdf and hasattr(imagen.pdf, 'size')),
                'marcas_agua': sum(imagen.marca_agua.size for imagen in Imagen.objects.all() if imagen.marca_agua and hasattr(imagen.marca_agua, 'size'))
            }
        },
        
        # Totales generales
        'totales': {
            'archivos_totales': {
                'pdfs': (
                    Libro.objects.exclude(pdf='').count() +
                    Revista.objects.exclude(pdf='').count() +
                    Imagen.objects.exclude(pdf='').count()
                ),
                'imagenes': (
                    Libro.objects.exclude(img_portada='').count() +
                    Revista.objects.exclude(img_portada='').count() +
                    Imagen.objects.exclude(img_portada='').count()
                )
            },
            'espacio_total': {
                'pdfs': 0,  # Se calculará abajo
                'imagenes': 0,  # Se calculará abajo
                'total': 0  # Se calculará abajo
            }
        }
    }
    
    # Calcular totales de espacio
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

    datos.update({
        'estadisticas': estadisticas,
        'estado_sistema': estado_sistema,
    })

    return render(request, 'principal.html', datos)

@login_required
def inicio(request):
    # Consulta base optimizada
    libros = Libro.objects.prefetch_related('autores', 'categorias')
    
    # Obtener parámetros de búsqueda y filtros
    buscar_por = request.GET.get('q', '')
    filtro = request.GET.get('filtro', '')
    categoria = request.GET.get('categoria', '')
    
    # Aplicar búsqueda
    if buscar_por:
        libros = libros.filter(
            Q(titulo__icontains=buscar_por) |
            Q(autores__nombre__icontains=buscar_por) |
            Q(palabra_clave__icontains=buscar_por)
        ).distinct()

    # Aplicar filtros
    if categoria:
        libros = libros.filter(categorias__id_categoria=categoria)
        
    # Aplicar ordenamiento por defecto o según filtro
    if filtro == 'populares':
        libros = libros.annotate(
            visitas_count=Count('visitalibro')
        ).order_by('-visitas_count')
    else:
        # Ordenamiento por defecto para evitar la advertencia de paginación
        libros = libros.order_by('-fecha_publicacion')
    
    # Paginación
    paginator = Paginator(libros, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'libros': page_obj,
        'buscar_por': buscar_por,
        'filtro_actual': filtro,
        'categoria_id': categoria,
    }
    return render(request, 'inicio.html', context)

#perfil de l usuario actual
@login_required
def perfil(request):
    try:
        usuario = request.user.usuario
        # Verificar si el usuario está usando su CI como contraseña
        usando_ci_como_password = check_password(usuario.ci, usuario.user.password)
        
        context = {
            'usuario': usuario,
            'usando_ci_como_password': usando_ci_como_password
        }
        return render(request, 'perfil.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, "Tu cuenta de usuario no está correctamente configurada. Por favor contacta al administrador.")
        return redirect('inicio')

#......................
@login_required
def agregar_autor(request):
    if request.method == 'POST':
        form = AutorForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            if Autor.objects.filter(nombre=nombre).exists():
                return JsonResponse({'error': 'El autor ya existe.'})
            else:
                nuevo_autor = form.save()
                return JsonResponse({'id_autor': nuevo_autor.id_autor, 'nombre': str(nuevo_autor), 'success': True})
        else:
            return JsonResponse({'error': 'Formulario inválido.'})
    else:
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

@login_required
def eliminar_usuario(request, usuario_id):
    if request.method == 'POST':
        try:
            usuario = get_object_or_404(Usuario, usuario_id=usuario_id)
            nombre = usuario.nombres
            usuario.delete()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f'El usuario {nombre} ha sido eliminado exitosamente'
                })
            return redirect('lista_usuarios')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=500)
            raise e
    return redirect('lista_usuarios')
#---------------------------------------------------------------
def galeria_artistica(request):
    imagenes = Imagen.objects.all()
    categorias = Categoria.objects.all()  # Obtiene todas las categorías
    
    context = {
        'imagenes': imagenes,
        'categorias': categorias,  # Pasa las categorías al contexto
    }
    return render(request, 'galeria_artistica.html', context)

@login_required
@admin_required
def lista_imagenes(request):
    # Asegúrate de ordenar las imágenes por 'id_Imagen' o cualquier otro campo
    imagenes = Imagen.objects.all().order_by('-id_Imagen')  # Usar 'id_Imagen' como campo de ordenación

    # Configuración de paginación
    paginator = Paginator(imagenes, 10)  # Muestra 10 imágenes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'lista_imagenes.html', {'page_obj': page_obj})
@admin_required
def agregar_imagen(request):
    categorias = Categoria.objects.all()
    
    if request.method == 'POST':
        try:
            titulo = request.POST.get('titulo')
            descripcion = request.POST.get('descripcion', '')
            autorImg = request.POST.get('autorImg')
            img_portada = request.FILES['img_portada']
            pdf = request.FILES.get('pdf', None)
            marca_agua = request.POST.get('marca_agua', '')

            fs = FileSystemStorage()
            img_portada_name = fs.save(img_portada.name, img_portada)
            pdf_name = fs.save(pdf.name, pdf) if pdf else None

            nueva_imagen = Imagen(
                titulo=titulo,
                descripcion=descripcion,
                autorImg=autorImg,
                img_portada=img_portada_name,
                pdf=pdf_name,
                marca_agua=marca_agua
            )
            nueva_imagen.save()
            
            # Agregar manejo de categorías
            categorias_seleccionadas = request.POST.getlist('categorias')
            for categoria_id in categorias_seleccionadas:
                try:
                    categoria = Categoria.objects.get(pk=categoria_id)
                    nueva_imagen.categorias.add(categoria)
                except Categoria.DoesNotExist:
                    messages.warning(request, f'Categoría con ID {categoria_id} no encontrada.')
            
            return redirect('lista_imagenes')
        except Exception as e:
            messages.error(request, f'Error al agregar la imagen: {str(e)}')
            return render(request, 'agregar_imagen.html', {
                'categorias': categorias,
                'error': str(e)
            })

    return render(request, 'agregar_imagen.html', {
        'categorias': categorias,
    })
from django.urls import reverse
from django.http import JsonResponse
from django.db import IntegrityError
@admin_required
def modificar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, usuario_id=usuario_id)
    if request.method == 'POST':
        try:
            form = UsuarioForm(request.POST, instance=usuario)
            if form.is_valid():
                with transaction.atomic():
                    # Guardar usuario
                    usuario = form.save(commit=False)
                    nuevo_correo = form.cleaned_data['correo']
                    
                    # Actualizar usuario relacionado si existe
                    if usuario.user:
                        usuario.user.email = nuevo_correo
                        usuario.user.username = nuevo_correo
                        usuario.user.save()
                    
                    # Guardar el usuario con el nuevo correo
                    usuario.correo = nuevo_correo
                    usuario.save()
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'Usuario {usuario.nombres} actualizado exitosamente',
                    'redirect_url': reverse('lista_usuarios')
                })
            else:
                errores = []
                for field, errors in form.errors.items():
                    errores.append(f"{field}: {', '.join(errors)}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Por favor corrija los siguientes errores: ' + '; '.join(errores)
                })
                
        except IntegrityError as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Error de integridad: Este registro ya existe'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error inesperado: {str(e)}'
            })

    context = {
        'form': UsuarioForm(instance=usuario),
        'usuario': usuario,
        'opciones_usuarios': Usuario.opciones_usuarios,
        'opciones_extensiones': Usuario.opciones_extensiones,
        'titulo': f'Modificar Usuario: {usuario.nombres}'
    }
    return render(request, 'modificar_usuario.html', context)

@admin_required
def eliminar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, usuario_id=usuario_id)
    if request.method == 'POST':
        usuario.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': f'El usuario {usuario.nombres} ha sido eliminado exitosamente'
            })
        return redirect('lista_usuarios')
    return render(request, 'eliminar_usuario.html', {'usuario': usuario})
@admin_required
def eliminar_imagen(request, pk):
    imagen = get_object_or_404(Imagen, pk=pk)
    if request.method == 'POST':
        imagen.delete()
        messages.success(request, "Imagen eliminada con éxito.")
        return redirect('lista_imagenes')
    return render(request, 'lista_imagenes', {'imagen': imagen})

def ver_imagen(request, id):
    imagen = get_object_or_404(Imagen, id=id)
    return render(request, 'ver_imagen.html', {'imagen': imagen})

@login_required
@admin_required
def editar_imagen(request, id_imagen):
    imagen = get_object_or_404(Imagen, pk=id_imagen)
    categorias = Categoria.objects.all()

    if request.method == 'POST':
        try:
            titulo = request.POST.get('titulo')
            descripcion = request.POST.get('descripcion', '')
            autorImg = request.POST.get('autorImg')
            marca_agua = request.POST.get('marca_agua', '')
            categorias_seleccionadas = request.POST.getlist('categorias')

            imagen.titulo = titulo
            imagen.descripcion = descripcion
            imagen.autorImg = autorImg
            imagen.marca_agua = marca_agua

            # Manejar la imagen de portada
            if 'img_portada' in request.FILES:
                if imagen.img_portada:
                    try:
                        imagen.img_portada.delete()
                    except Exception:
                        pass
                imagen.img_portada = request.FILES['img_portada']

            # Manejar el PDF
            if 'pdf' in request.FILES:
                if imagen.pdf:
                    try:
                        imagen.pdf.delete()
                    except Exception:
                        pass
                imagen.pdf = request.FILES['pdf']

            # Guardar la imagen
            imagen.save()

            # Actualizar categorías
            imagen.categorias.set(categorias_seleccionadas)

            messages.success(request, "La imagen se ha actualizado correctamente.")
            return redirect('lista_imagenes')

        except Exception as e:
            messages.error(request, f"Error al editar la imagen: {str(e)}")
            return render(request, 'editar_imagen.html', {
                'imagen': imagen,
                'categorias': categorias,
                'error': str(e)
            })

    return render(request, 'editar_imagen.html', {
        'imagen': imagen,
        'categorias': categorias
    })

from django.shortcuts import render, get_object_or_404, redirect
from PIL import Image as PILImage
import io
from django.core.files.base import ContentFile
from django.conf import settings
@login_required

def editar_marca(request, id_imagen):
    imagen = get_object_or_404(Imagen, pk=id_imagen)
    
    if request.method == 'POST':
        if 'img_portada' in request.FILES:
            imagen.img_portada = request.FILES['img_portada']
        
        if 'marca_agua' in request.FILES:
            # Cargar la imagen de la marca de agua directamente desde el archivo subido
            marca_agua_file = request.FILES['marca_agua']
            marca_agua = PILImage.open(marca_agua_file)
            img_portada = PILImage.open(imagen.img_portada)  # Cargar la imagen de portada
            
            # Aplicar la marca de agua
            # Aquí puedes ajustar la posicin y transparencia como necesites
            transparencia = 0.5  # Cambia según el control de transparencia que uses
            marca_agua.putalpha(int(255 * transparencia))  # Ajustar transparencia
            img_portada.paste(marca_agua, (0, 0), marca_agua)  # Ajustar posición según sea necesario
            
            # Guardar la imagen resultante en un objeto BytesIO
            img_io = io.BytesIO()
            img_portada.save(img_io, format='PNG')
            img_file = ContentFile(img_io.getvalue(), 'imagen_con_marca_agua.png')
            
            # Guardar el archivo en el modelo, si es necesario
            imagen.img_portada = img_file  # Actualiza la imagen de portada con la nueva imagen procesada
            
        imagen.save()  # Guardar cambios en la base de datos
        return redirect('lista_imagenes')
    
    return render(request, 'editar_marca.html', {'imagen': imagen})



def obtener_recomendaciones_personalizadas(usuario):
    historial = HistorialBusqueda.objects.filter(usuario=usuario).order_by('-fecha_busqueda')[:5]
    
    # Suponiendo que quieres recomendar libros relacionados con los términos de búsqueda recientes
    terminos_busqueda = [busqueda.termino_busqueda for busqueda in historial]
    
    # Buscar libros que coincidan con los términos de búsqueda
    libros_recomendados = Libro.objects.filter(
        Q(titulo__icontains=' '.join(terminos_busqueda)) |
        Q(descripcion__icontains=' '.join(terminos_busqueda)) |
        Q(palabra_clave__icontains=' '.join(terminos_busqueda))
    ).distinct()[:5]  # Limitar a 5 recomendaciones

    # Construir la respuesta
    recomendaciones = []
    for libro in libros_recomendados:
        recomendaciones.append({
            'titulo': libro.titulo,
            'autores': ', '.join([autor.nombre for autor in libro.autores.all()]) or 'Autor desconocido',
            'img_portada': libro.img_portada.url if libro.img_portada else '',
            'descripcion': libro.descripcion or 'No hay descripción disponible',
            'pdf': libro.pdf.url if libro.pdf else '',
            'pdf_url': libro.pdf_url if libro.pdf_url else '',
            'descarga_autorizada': libro.descarga_autorizada if hasattr(libro, 'descarga_autorizada') else False,
            'palabra_clave': libro.palabra_clave or '',
            'categoria': libro.categoria or '',
            'categorias': [cat.nom_cat for cat in libro.categorias.all()],
            'edicion': libro.edicion or '',
        })
    
    return recomendaciones

import spacy
nlp = spacy.load("es_core_news_sm")
def buscar_libros(request):
    query = request.GET.get('q', '').strip()
    
    try:
        if not query:
            if request.user.is_authenticated:
                return JsonResponse(obtener_recomendaciones_personalizadas(request.user), safe=False)
            return JsonResponse([{'mensaje': "Por favor, introduce un término de búsqueda."}], safe=False)

        # Guardar la búsqueda en el historial
        if request.user.is_authenticated:
            try:
                HistorialBusqueda.objects.create(
                    usuario=request.user,
                    termino_busqueda=query
                )
            except:
                pass  

        # Verificar si es una búsqueda por tipo
        if query.startswith('tipo:'):
            try:
                tipo = query.split(':', 1)[1].upper()
                if tipo == 'TODOS':
                    libros = Libro.objects.all()
                else:
                    libros = Libro.objects.filter(tipo__iexact=tipo)

                if libros.exists():
                    respuesta = []
                    tipo_plural = 'documentos' if tipo == 'TODOS' else tipo.lower() + ('s' if tipo != 'TESIS' else '')
                    respuesta.append({'mensaje': f"Aquí tienes los {tipo_plural} disponibles:"})

                    for libro in libros:
                        respuesta.append({
                            'titulo': libro.titulo,
                            'autores': ', '.join([autor.nombre for autor in libro.autores.all()]) or 'Autor desconocido',
                            'img_portada': libro.img_portada.url if libro.img_portada else '',
                            'descripcion': libro.descripcion or 'No hay descripción disponible',
                            'pdf': libro.pdf.url if libro.pdf else '',
                            'pdf_url': libro.pdf_url if libro.pdf_url else '',
                            'descarga_autorizada': libro.descarga_autorizada if hasattr(libro, 'descarga_autorizada') else False,
                            'palabra_clave': libro.palabra_clave or '',
                            'tipo': libro.tipo,
                            'categoria': libro.categoria or '',
                            'categorias': [cat.nom_cat for cat in libro.categorias.all()],
                            'edicion': libro.edicion or '',
                        })
                    return JsonResponse(respuesta, safe=False)
                else:
                    tipo_plural = 'documentos' if tipo == 'TODOS' else tipo.lower() + ('s' if tipo != 'TESIS' else '')
                    return JsonResponse([{
                        'mensaje': f"No encontré {tipo_plural} disponibles en este momento.",
                        'tipo': 'info'
                    }], safe=False)
            except Exception as e:
                return JsonResponse([{
                    'mensaje': "Hubo un problema al buscar por tipo. Por favor, intenta con una búsqueda normal.",
                    'tipo': 'error'
                }], safe=False)

        # Procesar posibles mensajes conversacionales
        if query:
            respuesta_chat = ChatResponses.procesar_mensaje(query)
            if respuesta_chat.get("mensaje"):  # Solo si hay un mensaje de chat específico
                # Si es una solicitud de novedades
                if respuesta_chat.get("accion") == "novedades":
                    try:
                        # Obtener los últimos 10 libros
                        ultimos_libros = Libro.objects.prefetch_related('autores', 'categorias').order_by('-fecha_registro')[:10]
                        if ultimos_libros:
                            resultados = [
                                {
                                    'titulo': libro.titulo,
                                    'autores': ', '.join([autor.nombre for autor in libro.autores.all()]) or 'Autor desconocido',
                                    'tipo': libro.tipo,
                                    'fecha': libro.fecha_registro.strftime('%d/%m/%Y'),
                                    'img_portada': libro.img_portada.url if libro.img_portada else '',
                                    'descripcion': libro.descripcion or 'No hay descripción disponible',
                                    'pdf': libro.pdf.url if libro.pdf else '',
                                    'pdf_url': libro.pdf_url if libro.pdf_url else '',
                                    'descarga_autorizada': libro.descarga_autorizada if hasattr(libro, 'descarga_autorizada') else False,
                                    'categorias': [cat.nom_cat for cat in libro.categorias.all()],
                                    'edicion': libro.edicion or '',
                                } for libro in ultimos_libros
                            ]
                            return JsonResponse(resultados, safe=False)
                        else:
                            return JsonResponse([{
                                'mensaje': "No hay novedades disponibles en este momento 🦝",
                                'tipo': 'info'
                            }], safe=False)
                    except Exception as e:
                        return JsonResponse([{
                            'mensaje': "Hubo un problema al obtener las novedades. Por favor, intenta más tarde.",
                            'tipo': 'error'
                        }], safe=False)
                else:
                    return JsonResponse([respuesta_chat], safe=False)

        # Si no hay respuesta de chat o es una búsqueda, continuar con la búsqueda normal
        query = query.lower().strip()
        
        # Limpiar y normalizar la consulta
        query_limpia = limpiar_busqueda(query)
        
        # Detectar si es búsqueda por autor
        es_busqueda_autor = 'autor' in query.lower() or 'del autor' in query.lower()
        
        try:
            # Si es búsqueda por autor
            if es_busqueda_autor:
                # Extraer el nombre del autor
                nombre_autor = query_limpia.replace('autor', '').replace('del', '').strip()
                if not nombre_autor:
                    return JsonResponse([{
                        'mensaje': "¿Podrías decirme el nombre del autor que estás buscando?",
                        'tipo': 'info',
                        'sugerencia': "Por ejemplo: 'libros del autor Ken Hultgren'"
                    }], safe=False)
                    
                libros = Libro.objects.filter(
                    autores__nombre__icontains=nombre_autor
                ).distinct()
            else:
                # Búsqueda general
                if not query_limpia:
                    return JsonResponse([{
                        'mensaje': ChatResponses.get_saludo(),
                        'sugerencias': [
                            "- Buscar por autor: 'libros del autor Ken Hultgren'",
                            "- Buscar por tema: 'libros sobre dibujo'",
                            "- Buscar por tipo: 'tipo:LIBRO'",
                            "- Ver todos: 'tipo:TODOS'",
                        ],
                        'tipo': 'ayuda'
                    }], safe=False)

                # Dividir términos para búsqueda individual
                terminos = query_limpia.split()
                
                # Construir consulta inicial con título y descripción (más peso)
                q_titulo_desc = Q()
                q_otros = Q()
                
                # Buscar términos consecutivos en título y descripción
                q_titulo_desc |= (
                    Q(titulo__icontains=query_limpia) |
                    Q(descripcion__icontains=query_limpia)
                )
                
                # Buscar términos individuales
                for termino in terminos:
                    if len(termino) > 2:  # Ignorar términos muy cortos
                        q_titulo_desc |= (
                            Q(titulo__icontains=termino) |
                            Q(descripcion__icontains=termino)
                        )
                        q_otros |= (
                            Q(palabra_clave__icontains=termino) |
                            Q(autores__nombre__icontains=termino) |
                            Q(categoria__icontains=termino) |
                            Q(categorias__nom_cat__icontains=termino)
                        )

                # Combinar resultados, dando prioridad a coincidencias en título/descripción
                libros_titulo_desc = Libro.objects.filter(q_titulo_desc)
                libros_otros = Libro.objects.filter(q_otros)
                
                # Unir resultados manteniendo el orden de prioridad
                libros = (libros_titulo_desc | libros_otros).distinct()

            if libros.exists():
                respuesta = []
                if es_busqueda_autor:
                    mensaje_inicial = f"¡Excelente! Encontré estos libros del autor {nombre_autor}:"
                else:
                    mensaje_inicial = f"¡Perfecto! Encontré estos documentos relacionados con '{query}'"

                respuesta.append({
                    'mensaje': mensaje_inicial,
                    'tipo': 'success'
                })

                for libro in libros:
                    respuesta.append({
                        'titulo': libro.titulo,
                        'autores': ', '.join([autor.nombre for autor in libro.autores.all()]) or 'Autor desconocido',
                        'img_portada': libro.img_portada.url if libro.img_portada else '',
                        'descripcion': libro.descripcion or 'No hay descripción disponible',
                        'pdf': libro.pdf.url if libro.pdf else '',
                        'pdf_url': libro.pdf_url if libro.pdf_url else '',
                        'descarga_autorizada': libro.descarga_autorizada if hasattr(libro, 'descarga_autorizada') else False,
                        'palabra_clave': libro.palabra_clave or '',
                        'tipo': libro.tipo,
                        'categoria': libro.categoria or '',
                        'categorias': [cat.nom_cat for cat in libro.categorias.all()],
                        'edicion': libro.edicion or '',
                    })
                
                # Agregar sugerencia aleatoria de vez en cuando
                if random.random() < 0.3:  # 30% de probabilidad
                    respuesta.append({
                        'sugerencia': ChatResponses.get_sugerencia_busqueda(),
                        'tipo': 'tip'
                    })
                    
                return JsonResponse(respuesta, safe=False)
            else:
                if es_busqueda_autor:
                    mensaje = ChatResponses.get_disculpa()
                    submensaje = f"No encontré libros del autor {nombre_autor}."
                else:
                    mensaje = ChatResponses.get_disculpa()
                    submensaje = f"No encontré resultados para '{query}'."
                
                return JsonResponse([{
                    'mensaje': mensaje,
                    'submensaje': submensaje,
                    'tipo': 'info',
                    'sugerencias': [
                        "- Intenta con términos más generales",
                        "- Verifica la ortografía",
                        "- Prueba buscar por tipo: 'tipo:LIBRO'",
                        "- Ver todos los documentos: 'tipo:TODOS'"
                    ]
                }], safe=False)

        except Exception as e:
            return JsonResponse([{
                'mensaje': "Ups, parece que hubo un problema al realizar la búsqueda.",
                'submensaje': "¿Podrías intentarlo de nuevo?",
                'tipo': 'error',
                'sugerencia': ChatResponses.get_sugerencia_busqueda()
            }], safe=False)

    except Exception as e:
        return JsonResponse([{
            'mensaje': "Lo siento, ha ocurrido un error inesperado.",
            'submensaje': "Por favor, inténtalo de nuevo en unos momentos.",
            'tipo': 'error',
            'sugerencia': "Si el problema persiste, no dudes en contactar con soporte técnico."
        }], safe=False)

def chatbot_view(request):
    return render(request, 'chatbot.html')

@login_required
def obtener_novedades(request):
    try:
        # Obtener solo los últimos 3 libros agregados
        ultimos_libros = Libro.objects.all().order_by('-fecha_publicacion')[:3]
        
        # Preparar la respuesta
        novedades = []
        for libro in ultimos_libros:
            try:
                libro_data = {
                    'titulo': libro.titulo,
                    'autores': ', '.join([autor.nombre for autor in libro.autores.all()]) or 'Autor desconocido',
                    'categoria': libro.categoria.nombre if hasattr(libro.categoria, 'nombre') else libro.categoria if libro.categoria else None,
                    'descripcion': libro.descripcion if hasattr(libro, 'descripcion') else None,
                    'pdf': libro.pdf.url if libro.pdf else '',
                    'descarga_autorizada': libro.descarga_autorizada if hasattr(libro, 'descarga_autorizada') else False,
                    'img_portada': libro.img_portada.url if libro.img_portada else None,
                    'pdf_url': libro.pdf_url,
                    'archivo_autorizacion': libro.archivo_autorizacion.url if libro.archivo_autorizacion else None,
                    'edicion': libro.edicion,
                    'palabra_clave': libro.palabra_clave
                }
                novedades.append(libro_data)
            except Exception as libro_error:
                print(f"Error procesando libro {libro.titulo}: {str(libro_error)}")
                continue
        
        return JsonResponse({
            'status': 'success',
            'mensaje': '📚 Últimos libros añadidos a la biblioteca:',
            'libros': novedades
        })
    except Exception as e:
        print(f"Error en obtener_novedades: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al obtener las novedades: {str(e)}'
        })