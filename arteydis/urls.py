from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

# Importar desde cada módulo de vistas
from biblioartdis.views import auth_views, libro_views, admin_views, usuario_views

urlpatterns = [
    # ==================== PÁGINA PRINCIPAL Y AUTENTICACIÓN ====================
    path('admin/', admin.site.urls),
    path('', auth_views.home, name='home'),
    path('accounts/login/', auth_views.home, name='login'),
    path('inicio/', auth_views.home, name='inicio'),
    
    # Principal - Usando home temporalmente (evita error 404)
    path('principal/', auth_views.home, name='principal'),
    
    path('accounts/logout/', auth_views.logout_view, name='logout'),
    
    # ==================== VERIFICACIÓN DE DOS FACTORES (2FA) ====================
    path('verificar-codigo/', auth_views.verificar_codigo_view, name='verificar_codigo'),
    path('reenviar-codigo/', auth_views.reenviar_codigo, name='reenviar_codigo'),
    
    # ==================== PERFIL Y USUARIOS ====================
    path('perfil/', usuario_views.perfil, name='perfil'),
    path('agregar_usuario/', usuario_views.agregar_usuario, name='agregar_usuario'),
    path('modificar_usuario/<int:usuario_id>/', usuario_views.modificar_usuario, name='modificar_usuario'),
    path('eliminar_usuario/<int:usuario_id>/', usuario_views.eliminar_usuario, name='eliminar_usuario'),
    path('lista_usuarios/', usuario_views.lista_usuarios, name='lista_usuarios'),
    path('restablecer_password/', usuario_views.restablecer_password, name='restablecer_password'),
    path('cambiar-password/', usuario_views.cambiar_password, name='cambiar_password'),

    # ==================== GESTIÓN DE LIBROS (CRÍTICO PARA DESCARGAS) ====================
    path('listar_libros/', libro_views.listar_libros, name='listar_libros'),
    path('ver_pdf/<int:libro_id>/', libro_views.ver_descargar_libro, name='ver_pdf'),
    path('libro/ver_descargar/<int:libro_id>/', libro_views.ver_descargar_libro, name='ver_descargar_libro'),
    path('libro/<int:libro_id>/editar/', libro_views.editar_libro, name='editar_libro'),
    path('libros/<int:libro_id>/eliminar/', libro_views.eliminar_libro, name='eliminar_libro'),
    path('libros/agregar/', libro_views.agregar_libro, name='agregar_libro'),
    path('libros/nivel/<int:id_nivel>/', libro_views.libros_nivel, name='libros_nivel'),
    path('novedades_libros/', libro_views.novedades_libros, name='novedades_libros'),
    path('registrar_visita/', libro_views.registrar_visita_libro, name='registrar_visita_libro'),
    path('historial_visitas/', libro_views.historial_visitas, name='historial_visitas'),
    path('eliminar_autorizacion/<int:libro_id>/', libro_views.eliminar_autorizacion, name='eliminar_autorizacion'),
    # ⭐ ESTA ES LA MÁS IMPORTANTE PARA RESTRINGIR/AUTORIZAR
    path('libro/<int:libro_id>/cambiar_estado_descarga/', libro_views.cambiar_estado_descarga, name='cambiar_estado_descarga'),

    # ==================== GESTIÓN DE SUGERENCIAS ====================
    path('sugerencias/', usuario_views.listar_sugerencias, name='listar_sugerencias'),
    path('sugerencias/descartar/<int:sugerencia_id>/', usuario_views.descartar_sugerencia, name='descartar_sugerencia'),
    path('sugerencias/aprobar/<int:sugerencia_id>/', usuario_views.aprobar_sugerencia, name='aprobar_sugerencia'), 
    path('sugerir_libro/', usuario_views.sugerir_libro, name='sugerir_libro'),
    path('listar_sugerencias_usuario/', usuario_views.listar_sugerencias_usuario, name='listar_sugerencias_usuario'),
    
    # ==================== GESTIÓN DE CATEGORÍAS ====================
    path('agregar_categoria/', admin_views.agregar_categoria, name='agregar_categoria'),
    path('editar_categoria/<int:id_categoria>/', admin_views.editar_categoria, name='editar_categoria'),
    path('eliminar_categoria/<int:id_categoria>/', admin_views.eliminar_categoria, name='eliminar_categoria'),
    
    # ==================== GESTIÓN DE AUTORES ====================
    path('agregar-autor/', admin_views.agregar_autor, name='agregar_autor'),
    path('editar_autor/<int:id_autor>/', admin_views.editar_autor, name='editar_autor'),
    path('eliminar_autor/<int:id_autor>/', admin_views.eliminar_autor, name='eliminar_autor'),

    # ==================== GESTIÓN DE REVISTAS Y COLECCIONES ====================
    path('agregar_revista/', admin_views.agregar_revista, name='agregar_revista'),
    path('listar_revistas/', admin_views.listar_revistas, name='listar_revistas'),
    path('eliminar_revista/<int:id_revista>/', admin_views.eliminar_revista, name='eliminar_revista'),
    path('modificar_revista/<int:id_revista>/', admin_views.modificar_revista, name='modificar_revista'),
    
    path('agregar_coleccion/', admin_views.agregar_coleccion, name='agregar_coleccion'),
    path('eliminar_coleccion/<int:id_coleccion>/', admin_views.eliminar_coleccion, name='eliminar_coleccion'),
    path('modificar_coleccion/<int:id_coleccion>/', admin_views.modificar_coleccion, name='modificar_coleccion'),
    path('actualizar-orden/', admin_views.actualizar_orden_colecciones, name='actualizar_orden_colecciones'),

    # ==================== GESTIÓN DE LA GALERÍA DE IMÁGENES ====================
    path('galeria_artistica/', admin_views.galeria_artistica, name='galeria_artistica'),
    path('lista_imagenes/', admin_views.listar_imagenes, name='lista_imagenes'),
    path('agregar/', admin_views.agregar_imagen, name='agregar_imagen'),
    path('editar_imagen/<int:id_imagen>/', admin_views.editar_imagen, name='editar_imagen'),
    path('editar_marca/<int:id_imagen>/', admin_views.editar_marca, name='editar_marca'),
    path('eliminar/<int:pk>/', admin_views.eliminar_imagen, name='eliminar_imagen'),
    path('ver_imagen/<int:id>/', admin_views.ver_imagen, name='ver_imagen'),
    
    # ==================== MONITOREO DE USUARIOS ACTIVOS ====================
    path('usuarios-activos/', usuario_views.usuarios_activos, name='usuarios_activos'),
    path('ver-historial/<int:usuario_id>/', usuario_views.ver_historial_usuario, name='ver_historial_usuario'),
]

# Archivos de medios
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)