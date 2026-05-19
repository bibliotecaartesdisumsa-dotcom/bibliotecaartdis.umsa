# views/libro_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
import logging
import io
import tempfile
import os
import re

from ..decorators import admin_required
from ..models import Libro, Autor, Categoria, Revista, Coleccion, Imagen
from ..forms import RevistaForm, ColeccionForm, ImagenForm
from ..drive_utils import subir_pdf_a_drive

logger = logging.getLogger(__name__)


# ==================== CRUD Libros ====================

@login_required
@admin_required
def listar_libros(request):
    """Lista todos los libros con paginación y filtros"""
    libros = Libro.objects.all()
    
    # Aplicar ordenamiento
    ordenar = request.GET.get('ordenar')
    if ordenar == 'fecha_asc':
        libros = libros.order_by('fecha_publicacion')
    elif ordenar == 'fecha_desc':
        libros = libros.order_by('-fecha_publicacion')
    else:
        libros = libros.order_by('-id_libro')
    
    # Paginación
    paginator = Paginator(libros, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'listar_libros.html', {
        'libros': page_obj, 
        'usuario': request.user,
        'ordenar': ordenar
    })


@login_required
@admin_required
def agregar_libro(request):
    """Agrega un nuevo libro al sistema"""
    autores = Autor.objects.all()
    categorias = Categoria.objects.all()
    
    if request.method == 'POST':
        try:
            # Datos básicos del libro
            titulo = request.POST.get('titulo')
            edicion = request.POST.get('edicion')
            tipo = request.POST.get('tipo')
            categoria = request.POST.get('categoria')
            descripcion = request.POST.get('descripcion', '').strip()
            autores_seleccionados = request.POST.getlist('autores')
            palabras_claves = request.POST.get('palabras_claves', '').split(',')
            pdf_url = request.POST.get('pdf_url')
            google_drive_url = request.POST.get('google_drive_url')
            categorias_seleccionadas = request.POST.getlist('categorias')
            
            # Crear el libro (por defecto descarga restringida)
            nuevo_libro = Libro(
                titulo=titulo, 
                edicion=edicion, 
                tipo=tipo, 
                categoria=categoria,
                descripcion=descripcion, 
                pdf_url=pdf_url,
                google_drive_url=google_drive_url,
                descarga_autorizada=False  # Por defecto restringido
            )
            
            # Manejo de portada
            if 'portada' in request.FILES:
                nuevo_libro.img_portada = request.FILES['portada']
                logger.info(f"Portada agregada: {request.FILES['portada'].name}")
            
            # Manejo de PDF - Subida a Drive si es grande
            if 'pdf' in request.FILES:
                pdf_original = request.FILES['pdf']
                tamaño_mb = pdf_original.size / (1024 * 1024)
                
                if tamaño_mb > 10:
                    logger.info(f"📄 PDF grande: {tamaño_mb:.1f}MB. Subiendo a Drive...")
                    try:
                        drive_url = subir_pdf_a_drive(pdf_original, titulo)
                        if drive_url:
                            nuevo_libro.google_drive_url = drive_url
                            nuevo_libro.pdf = None
                            messages.success(request, "✅ PDF subido a Google Drive")
                        else:
                            nuevo_libro.pdf = pdf_original
                            messages.warning(request, "No se pudo subir a Drive")
                    except Exception as e:
                        logger.error(f"Error subiendo a Drive: {e}")
                        nuevo_libro.pdf = pdf_original
                else:
                    nuevo_libro.pdf = pdf_original
            
            # Archivo de autorización
            if 'autorizacion' in request.FILES:
                nuevo_libro.archivo_autorizacion = request.FILES['autorizacion']
                logger.info(f"Autorización agregada: {request.FILES['autorizacion'].name}")
            
            nuevo_libro.save()

            # Agregar nuevo autor si se proporcionó
            nuevo_autor_nombre = request.POST.get('nombre_autor')
            if nuevo_autor_nombre and nuevo_autor_nombre.strip():
                autor_existente = Autor.objects.filter(nombre=nuevo_autor_nombre).first()
                if autor_existente:
                    nuevo_libro.autores.add(autor_existente)
                else:
                    nuevo_autor = Autor.objects.create(nombre=nuevo_autor_nombre)
                    nuevo_libro.autores.add(nuevo_autor)

            # Agregar autores seleccionados
            for autor_id in autores_seleccionados:
                try:
                    autor = Autor.objects.get(pk=autor_id)
                    nuevo_libro.autores.add(autor)
                except:
                    pass
            
            # Agregar categorías seleccionadas
            for categoria_id in categorias_seleccionadas:
                try:
                    cat = Categoria.objects.get(pk=categoria_id)
                    nuevo_libro.categorias.add(cat)
                except:
                    pass
            
            # Agregar palabras clave
            for palabra in palabras_claves:
                if palabra.strip():
                    nuevo_libro.agregar_palabras_claves(palabra.strip())
            
            logger.info(f"Libro '{titulo}' creado por {request.user.username}")
            messages.success(request, f'Libro "{titulo}" agregado correctamente')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Libro agregado', 'libro_id': nuevo_libro.id_libro})
            return redirect('listar_libros')
            
        except Exception as e:
            logger.error(f"Error agregando libro: {str(e)}", exc_info=True)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            messages.error(request, f'Error: {str(e)}')
            return render(request, 'agregar_libro.html', {'autores': autores, 'categorias': categorias})
    
    return render(request, 'agregar_libro.html', {'autores': autores, 'categorias': categorias})


@login_required
@admin_required
def editar_libro(request, libro_id):
    """Edita un libro existente"""
    libro = get_object_or_404(Libro, id_libro=libro_id)
    categorias = Categoria.objects.all()
    
    if request.method == 'POST':
        try:
            libro.titulo = request.POST.get('titulo').strip()
            libro.edicion = request.POST.get('edicion', '').strip()
            libro.tipo = request.POST.get('tipo')
            libro.descripcion = request.POST.get('descripcion', '').strip()
            libro.categoria = request.POST.get('categoria')
            
            # Actualizar categorías
            libro.categorias.set(request.POST.getlist('categorias'))
            
            # Actualizar URLs
            libro.pdf_url = request.POST.get('pdf_url', '').strip()
            libro.google_drive_url = request.POST.get('google_drive_url', '').strip()
            
            # Manejo de PDF en edición
            if 'pdf' in request.FILES and not libro.google_drive_url:
                pdf_original = request.FILES['pdf']
                tamaño_mb = pdf_original.size / (1024 * 1024)
                
                if tamaño_mb > 10:
                    try:
                        drive_url = subir_pdf_a_drive(pdf_original, libro.titulo)
                        if drive_url:
                            libro.google_drive_url = drive_url
                            libro.pdf = None
                            messages.success(request, "PDF subido a Google Drive")
                        else:
                            libro.pdf = pdf_original
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        libro.pdf = pdf_original
                else:
                    libro.pdf = pdf_original
            
            # Manejo de portada
            if 'portada' in request.FILES:
                libro.img_portada = request.FILES['portada']
            
            # Archivo de autorización
            if 'autorizacion' in request.FILES:
                libro.archivo_autorizacion = request.FILES['autorizacion']
            
            # Actualizar autores
            if 'autores' in request.POST:
                libro.autores.set(request.POST.getlist('autores'))
            
            # Palabras clave
            libro.palabra_clave = request.POST.get('palabras_claves', '')
            
            libro.save()
            
            logger.info(f"Libro '{libro.titulo}' actualizado por {request.user.username}")
            messages.success(request, f'Libro "{libro.titulo}" actualizado')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Libro actualizado'})
            return redirect('listar_libros')
            
        except Exception as e:
            logger.error(f"Error editando libro: {str(e)}", exc_info=True)
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'editar_libro.html', {
        'libro': libro,
        'autores': Autor.objects.all(),
        'categorias': categorias,
        'palabras_claves': libro.palabra_clave.split(',') if libro.palabra_clave else []
    })


@login_required
@admin_required
def eliminar_libro(request, libro_id):
    """Elimina un libro del sistema"""
    libro = get_object_or_404(Libro, pk=libro_id)
    if request.method == 'POST':
        titulo = libro.titulo
        libro.delete()
        logger.info(f"Libro '{titulo}' eliminado por {request.user.username}")
        messages.success(request, f'Libro "{titulo}" eliminado')
        return redirect('listar_libros')
    return redirect('listar_libros')


@login_required
@admin_required
def cambiar_estado_descarga(request, libro_id):
    """Cambia el estado de autorización de descarga del libro"""
    libro = get_object_or_404(Libro, id_libro=libro_id)
    
    libro.descarga_autorizada = not libro.descarga_autorizada
    libro.save()
    
    estado = "AUTORIZADA" if libro.descarga_autorizada else "RESTRINGIDA"
    logger.info(f"Descarga {estado} para '{libro.titulo}' por {request.user.username}")
    messages.success(request, f'Descarga {estado.lower()} para "{libro.titulo}"')
    
    return redirect('listar_libros')


@login_required
def ver_descargar_libro(request, libro_id):
    libro = get_object_or_404(Libro, id_libro=libro_id)
    
    es_admin = hasattr(request.user, 'usuario') and request.user.usuario.tipo_usuario == 'Administrador'
    es_modo_embed = request.GET.get('embed') == 'true'
    
    # Verificar permisos
    if not libro.descarga_autorizada and not es_admin:
        if es_modo_embed:
            # Mostrar visor embebido con mensaje de restricción
            return render(request, 'ver_libro_embed.html', {
                'libro': libro,
                'archivo_url': None,
                'permitir_descarga': False,
                'mensaje': 'Este libro solo está disponible para lectura dentro del sistema.'
            })
        else:
            return render(request, 'acceso_restringido.html', {
                'libro': libro,
                'mensaje': 'Este libro tiene restringida su descarga.'
            })
    
    # Obtener URL del archivo
    archivo_url = libro.get_pdf_display_url()
    
    if not archivo_url:
        return render(request, 'error_recurso.html', {'mensaje': 'No hay archivo disponible.'}, status=404)
    
    # Modo embebido - mostrar visor
    if es_modo_embed:
        # Verificar si es URL de Google Drive para formatear correctamente
        if 'drive.google.com' in archivo_url:
            file_id = None
            if '/file/d/' in archivo_url:
                file_id = archivo_url.split('/file/d/')[1].split('/')[0]
            elif 'id=' in archivo_url:
                file_id = archivo_url.split('id=')[1].split('&')[0]
            if file_id:
                archivo_url = f'https://drive.google.com/file/d/{file_id}/preview'
        
        return render(request, 'ver_libro_embed.html', {
            'libro': libro,
            'archivo_url': archivo_url,
            'permitir_descarga': libro.descarga_autorizada or es_admin
        })
    
    # Modo normal - redirigir al archivo
    return redirect(archivo_url)


@login_required
@admin_required
def eliminar_autorizacion(request, libro_id):
    """Elimina el archivo de autorización de un libro"""
    libro = get_object_or_404(Libro, id_libro=libro_id)
    
    if request.method == 'POST':
        if libro.archivo_autorizacion:
            libro.archivo_autorizacion.delete(save=False)
            libro.archivo_autorizacion = None
            libro.save()
            logger.info(f"Autorización eliminada para '{libro.titulo}'")
            messages.success(request, f'Autorización eliminada')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
    
    return redirect('listar_libros')


# ==================== CRUD Revistas ====================

@login_required
@admin_required
def listar_revistas(request):
    """Lista todas las revistas"""
    revistas = Revista.objects.all()
    colecciones = Coleccion.objects.all()
    return render(request, 'listar_revistas.html', {
        'revistas': revistas, 
        'colecciones': colecciones
    })


@login_required
@admin_required
def agregar_revista(request):
    """Agrega una nueva revista"""
    if request.method == 'POST':
        try:
            if not request.POST.get('coleccion'):
                raise ValueError('La colección es requerida')
            
            coleccion = Coleccion.objects.get(id_coleccion=request.POST['coleccion'])
            nro_revista = request.POST.get('nro_revista')
            nro_revista = int(nro_revista) if nro_revista else None
            
            if not request.FILES.get('img_portada'):
                raise ValueError('La imagen de portada es requerida')
            
            revista = Revista(
                nro_revista=nro_revista,
                coleccion=coleccion,
                descripcion=request.POST.get('descripcion', '').strip(),
                img_portada=request.FILES.get('img_portada'),
                pdf=request.FILES.get('pdf'),
                url=request.POST.get('url', '').strip(),
                google_drive_url=request.POST.get('google_drive_url', '').strip()
            )
            revista.save()
            
            messages.success(request, 'Revista agregada correctamente')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'id': revista.id_revista})
            return redirect('listar_revistas')
            
        except Exception as e:
            logger.error(f"Error agregando revista: {str(e)}")
            messages.error(request, str(e))
    
    colecciones = Coleccion.objects.all().order_by('nomb_colecc')
    return render(request, 'agregar_revista.html', {
        'colecciones': colecciones,
        'max_upload_size_mb': {'imagen': 5, 'pdf': 10}
    })


@login_required
@admin_required
def modificar_revista(request, id_revista):
    """Modifica una revista existente"""
    revista = get_object_or_404(Revista, id_revista=id_revista)
    
    if request.method == 'POST':
        form = RevistaForm(request.POST, request.FILES, instance=revista)
        if form.is_valid():
            form.save()
            messages.success(request, 'Revista actualizada')
            return redirect('listar_revistas')
    else:
        form = RevistaForm(instance=revista)
    
    return render(request, 'modificar_revista.html', {
        'form': form,
        'revista': revista,
        'max_upload_size_mb': {'imagen': 5, 'pdf': 10}
    })


@login_required
@admin_required
def eliminar_revista(request, id_revista):
    """Elimina una revista"""
    if request.method == 'POST':
        revista = get_object_or_404(Revista, id_revista=id_revista)
        revista.delete()
        messages.success(request, 'Revista eliminada')
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
@admin_required
def agregar_coleccion(request):
    """Agrega una nueva colección"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            coleccion = Coleccion.objects.create(
                nomb_colecc=request.POST.get('nomb_colecc'),
                descripcion=request.POST.get('descripcion')
            )
            return JsonResponse({
                'success': True,
                'id_coleccion': coleccion.id_coleccion,
                'nomb_colecc': coleccion.nomb_colecc
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


@login_required
@admin_required
def modificar_coleccion(request, id_coleccion):
    """Modifica una colección"""
    coleccion = get_object_or_404(Coleccion, id_coleccion=id_coleccion)
    
    if request.method == 'POST':
        form = ColeccionForm(request.POST, instance=coleccion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Colección actualizada')
            return redirect('listar_revistas')
    else:
        form = ColeccionForm(instance=coleccion)
    
    return render(request, 'modificar_coleccion.html', {'form': form, 'coleccion': coleccion})


@login_required
@admin_required
def eliminar_coleccion(request, id_coleccion):
    """Elimina una colección"""
    if request.method == 'POST':
        coleccion = get_object_or_404(Coleccion, id_coleccion=id_coleccion)
        coleccion.delete()
        messages.success(request, 'Colección eliminada')
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@csrf_exempt
@admin_required
def actualizar_orden_colecciones(request):
    """Actualiza el orden de las colecciones"""
    if request.method == 'POST':
        coleccion_ids = request.POST.getlist('coleccion_ids[]')
        for index, coleccion_id in enumerate(coleccion_ids):
            Coleccion.objects.filter(id_coleccion=coleccion_id).update(orden=index)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


# ==================== CRUD Imágenes ====================

@login_required
@admin_required
def listar_imagenes(request):
    """Lista todas las imágenes"""
    imagenes = Imagen.objects.all().order_by('-id_Imagen')
    paginator = Paginator(imagenes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'lista_imagenes.html', {'page_obj': page_obj})


@login_required
@admin_required
def agregar_imagen(request):
    """Agrega una nueva imagen"""
    categorias = Categoria.objects.all()
    
    if request.method == 'POST':
        try:
            imagen = Imagen(
                titulo=request.POST.get('titulo'),
                descripcion=request.POST.get('descripcion', ''),
                autorImg=request.POST.get('autorImg')
            )
            
            if 'img_portada' in request.FILES:
                imagen.img_portada = request.FILES['img_portada']
            if 'pdf' in request.FILES:
                imagen.pdf = request.FILES['pdf']
            
            imagen.save()
            imagen.categorias.set(request.POST.getlist('categorias'))
            
            messages.success(request, 'Imagen agregada correctamente')
            return redirect('lista_imagenes')
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'agregar_imagen.html', {'categorias': categorias})


@login_required
@admin_required
def editar_imagen(request, id_imagen):
    """Edita una imagen existente"""
    imagen = get_object_or_404(Imagen, pk=id_imagen)
    categorias = Categoria.objects.all()
    
    if request.method == 'POST':
        try:
            imagen.titulo = request.POST.get('titulo')
            imagen.descripcion = request.POST.get('descripcion', '')
            imagen.autorImg = request.POST.get('autorImg')
            
            if 'img_portada' in request.FILES:
                imagen.img_portada = request.FILES['img_portada']
            if 'pdf' in request.FILES:
                imagen.pdf = request.FILES['pdf']
            
            imagen.save()
            imagen.categorias.set(request.POST.getlist('categorias'))
            
            messages.success(request, 'Imagen actualizada')
            return redirect('lista_imagenes')
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'editar_imagen.html', {'imagen': imagen, 'categorias': categorias})


@login_required
@admin_required
def eliminar_imagen(request, pk):
    """Elimina una imagen"""
    if request.method == 'POST':
        imagen = get_object_or_404(Imagen, pk=pk)
        imagen.delete()
        messages.success(request, 'Imagen eliminada')
        return redirect('lista_imagenes')
    return redirect('lista_imagenes')


@login_required
def editar_marca(request, id_imagen):
    """Aplica marca de agua a una imagen"""
    from PIL import Image as PILImage
    import io
    from django.core.files.base import ContentFile
    
    imagen = get_object_or_404(Imagen, pk=id_imagen)
    
    if request.method == 'POST':
        try:
            if 'img_portada' in request.FILES:
                imagen.img_portada = request.FILES['img_portada']
            
            if 'marca_agua' in request.FILES:
                marca_agua = PILImage.open(request.FILES['marca_agua'])
                img_portada = PILImage.open(imagen.img_portada)
                
                transparencia = 0.5
                marca_agua.putalpha(int(255 * transparencia))
                img_portada.paste(marca_agua, (0, 0), marca_agua)
                
                img_io = io.BytesIO()
                img_portada.save(img_io, format='PNG')
                img_file = ContentFile(img_io.getvalue(), 'imagen_con_marca_agua.png')
                imagen.img_portada = img_file
            
            imagen.save()
            messages.success(request, 'Marca de agua aplicada')
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('lista_imagenes')
    
    return render(request, 'editar_marca.html', {'imagen': imagen})