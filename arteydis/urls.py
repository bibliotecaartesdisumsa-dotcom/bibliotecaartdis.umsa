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
    path('inicio/', usuario_views.inicio, name='inicio'),  # ← Usar usuario_views.inicio
    path('principal/', admin_views.principal, name='principal'),  # ← Usar admin_views.principal
    path('accounts/logout/', auth_views.logout_view, name='logout'),
    
    # ==================== VERIFICACIÓN 2FA ====================
    path('verificar-codigo/', auth_views.verificar_codigo_view, name='verificar_codigo'),
    path('reenviar-codigo/', auth_views.reenviar_codigo, name='reenviar_codigo'),
    
    # ==================== PERFIL Y USUARIOS (usuario_views) ====================
    path('perfil/', usuario_views.perfil, name='perfil'),
    path('cambiar-password/', auth_views.cambiar_password, name='cambiar_password'),  # ← auth_views
    
    # ==================== GESTIÓN DE USUARIOS (admin_views) ====================
    path('agregar_usuario/', admin_views.agregar_usuario, name='agregar_usuario'),
    path('modificar_usuario/<int:usuario_id>/', admin_views.modificar_usuario, name='modificar_usuario'),
    path('eliminar_usuario/<int:usuario_id>/', admin_views.eliminar_usuario, name='eliminar_usuario'),
    path('lista_usuarios/', admin_views.lista_usuarios, name='lista_usuarios'),
    path('restablecer_password/', admin_views.restablecer_password, name='restablecer_password'),
    
    # ==================== GESTIÓN DE LIBROS (libro_views) ====================
    path('listar_libros/', libro_views.listar_libros, name='listar_libros'),
    path('ver_pdf/<int:libro_id>/', libro_views.ver_descargar_libro, name='ver_pdf'),
    path('libro/ver_descargar/<int:libro_id>/', libro_views.ver_descargar_libro, name='ver_descargar_libro'),
    path('libro/<int:libro_id>/editar/', libro_views.editar_libro, name='editar_libro'),
    path('libros/<int:libro_id>/eliminar/', libro_views.eliminar_libro, name='eliminar_libro'),
    path('libros/agregar/', libro_views.agregar_libro, name='agregar_libro'),
    path('libros/nivel/<int:id_nivel>/', usuario_views.libros_nivel, name='libros_nivel'),  # ← usuario_views
    path('novedades_libros/', usuario_views.novedades_libros, name='novedades_libros'),  # ← usuario_views
    path('registrar_visita/', usuario_views.registrar_visita_libro, name='registrar_visita_libro'),
    path('historial_visitas/', usuario_views.historial_visitas, name='historial_visitas'),
    path('eliminar_autorizacion/<int:libro_id>/', libro_views.eliminar_autorizacion, name='eliminar_autorizacion'),
    path('libro/<int:libro_id>/cambiar_estado_descarga/', libro_views.cambiar_estado_descarga, name='cambiar_estado_descarga'),

    # ==================== GESTIÓN DE SUGERENCIAS ====================
    path('sugerencias/', admin_views.listar_sugerencias, name='listar_sugerencias'),  # ← admin_views
    path('sugerencias/descartar/<int:sugerencia_id>/', usuario_views.descartar_sugerencia, name='descartar_sugerencia'),
    path('sugerencias/aprobar/<int:sugerencia_id>/', admin_views.aprobar_sugerencia, name='aprobar_sugerencia'),  # ← admin_views
    path('sugerir_libro/', usuario_views.sugerir_libro, name='sugerir_libro'),
    path('listar_sugerencias_usuario/', usuario_views.listar_sugerencias_usuario, name='listar_sugerencias_usuario'),
    
    # ==================== GESTIÓN DE CATEGORÍAS (admin_views) ====================
    path('agregar_categoria/', admin_views.agregar_categoria, name='agregar_categoria'),
    path('editar_categoria/<int:id_categoria>/', admin_views.editar_categoria, name='editar_categoria'),
    path('eliminar_categoria/<int:id_categoria>/', admin_views.eliminar_categoria, name='eliminar_categoria'),
    
    # ==================== GESTIÓN DE AUTORES (admin_views) ====================
    path('agregar-autor/', admin_views.agregar_autor, name='agregar_autor'),
    path('editar_autor/<int:id_autor>/', admin_views.editar_autor, name='editar_autor'),
    path('eliminar_autor/<int:id_autor>/', admin_views.eliminar_autor, name='eliminar_autor'),

    # ==================== GESTIÓN DE REVISTAS Y COLECCIONES (admin_views) ====================
    path('agregar_revista/', admin_views.agregar_revista, name='agregar_revista'),
    path('listar_revistas/', admin_views.listar_revistas, name='listar_revistas'),
    path('eliminar_revista/<int:id_revista>/', admin_views.eliminar_revista, name='eliminar_revista'),
    path('modificar_revista/<int:id_revista>/', admin_views.modificar_revista, name='modificar_revista'),
    path('agregar_coleccion/', admin_views.agregar_coleccion, name='agregar_coleccion'),
    path('eliminar_coleccion/<int:id_coleccion>/', admin_views.eliminar_coleccion, name='eliminar_coleccion'),
    path('modificar_coleccion/<int:id_coleccion>/', admin_views.modificar_coleccion, name='modificar_coleccion'),
    path('actualizar-orden/', admin_views.actualizar_orden_colecciones, name='actualizar_orden_colecciones'),

    # ==================== GESTIÓN DE IMÁGENES (admin_views) ====================
    path('galeria_artistica/', usuario_views.galeria_artistica, name='galeria_artistica'),
    path('lista_imagenes/', admin_views.listar_imagenes, name='lista_imagenes'),
    path('agregar/', admin_views.agregar_imagen, name='agregar_imagen'),
    path('editar_imagen/<int:id_imagen>/', admin_views.editar_imagen, name='editar_imagen'),
    path('editar_marca/<int:id_imagen>/', admin_views.editar_marca, name='editar_marca'),
    path('eliminar/<int:pk>/', admin_views.eliminar_imagen, name='eliminar_imagen'),
    path('ver_imagen/<int:id>/', usuario_views.ver_imagen, name='ver_imagen'),
    
    # ==================== CATÁLOGO Y BÚSQUEDA ====================
    path('catalogo/', usuario_views.catalogo, name='catalogo'),
    path('buscar_libros/', usuario_views.buscar_libros, name='buscar_libros'),
    path('obtener_novedades/', usuario_views.obtener_novedades, name='obtener_novedades'),
    
    # ==================== MONITOREO DE USUARIOS ACTIVOS (admin_views) ====================
    path('usuarios-activos/', admin_views.usuarios_activos, name='usuarios_activos'),
    path('ver-historial/<int:usuario_id>/', admin_views.ver_historial_usuario, name='ver_historial_usuario'),
    
    # ==================== CHAT ====================
    path('chatbot/', usuario_views.chatbot_view, name='chatbot'),
    path('chat-gemini/', usuario_views.chat_con_gemini, name='chat_gemini'),
]

# Archivos de medios
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)