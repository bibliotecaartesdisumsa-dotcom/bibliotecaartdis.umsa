# views/auth_views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
import json
import logging
import re

from ..decorators import admin_required
from ..email_utils import enviar_codigo_verificacion, verificar_codigo

logger = logging.getLogger(__name__)

# Diccionario temporal para almacenar intentos de login
intentos_fallidos = {}


def home(request):
    """PASO 1: Solicitar email - Acepta @umsa.bo y el correo especial vc3070934@gmail.com"""
    if request.method == 'POST':
        email = request.POST.get('correo', '').strip().lower()
        
        # Validar formato de email
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, '❌ Por favor ingresa un correo electrónico válido.')
            return render(request, 'login.html')
        
        # ✅ Validación especial: permite @umsa.bo o el correo específico @gmail.com
        CORREO_ESPECIAL = 'vc3070934@gmail.com'
        
        if not (email.endswith('@umsa.bo') or email == CORREO_ESPECIAL):
            messages.error(request, '❌ Solo se permiten correos institucionales @umsa.bo')
            return render(request, 'login.html')
        
        # Verificar intentos fallidos (seguridad)
        ip = request.META.get('REMOTE_ADDR')
        if ip in intentos_fallidos and intentos_fallidos[ip] >= 5:
            messages.error(request, '❌ Demasiados intentos. Espera 5 minutos.')
            return render(request, 'login.html')
        
        # ========== CREAR USUARIO AUTOMÁTICAMENTE SI NO EXISTE ==========
        try:
            # Buscar si el usuario ya existe
            user = User.objects.get(email=email)
            logger.info(f"Usuario existente: {email}")
            
        except User.DoesNotExist:
            # 🔥 CREAR USUARIO AUTOMÁTICAMENTE (no requiere registro previo)
            try:
                # Crear username a partir del email
                username_base = re.sub(r'[^a-zA-Z0-9_]', '', email.split('@')[0])
                if not username_base:
                    username_base = f"user_{email.split('@')[0]}"
                
                # Asegurar username único
                final_username = username_base
                counter = 1
                while User.objects.filter(username=final_username).exists():
                    final_username = f"{username_base}{counter}"
                    counter += 1
                
                # Crear el usuario de Django
                user = User.objects.create_user(
                    username=final_username,
                    email=email,
                    password=None  # Sin contraseña porque usamos 2FA
                )
                user.set_unusable_password()  # Deshabilitar contraseña normal
                user.first_name = email.split('@')[0].capitalize()
                user.save()
                
                # Crear el perfil de Usuario automáticamente
                from ..models import Usuario
                from datetime import timedelta
                
                # Determinar tipo de usuario (Administrador para el correo especial)
                tipo_usuario = 'Administrador' if email == CORREO_ESPECIAL else 'Externo'
                
                usuario_perfil = Usuario.objects.create(
                    user=user,
                    nombres=email.split('@')[0].capitalize(),
                    apepat='',
                    apemat='',
                    ci='PENDIENTE',  # Se actualizará después
                    correo=email,
                    extension='LP',
                    complemento='',
                    tipo_usuario=tipo_usuario,
                    ru='',
                    nro_celular='',
                    fecha_baja=timezone.now() + timedelta(days=365*5),  # 5 años
                    esta_activo=True
                )
                logger.info(f"✅ Usuario creado automáticamente: {email} (Tipo: {tipo_usuario})")
                
                if email == CORREO_ESPECIAL:
                    messages.success(request, f'✨ ¡Bienvenido Administrador! Se ha creado tu cuenta automáticamente.')
                else:
                    messages.info(request, f'📝 Se ha creado tu cuenta automáticamente. ¡Bienvenido a la biblioteca!')
                
            except Exception as e:
                logger.error(f"❌ Error al crear usuario automático {email}: {str(e)}")
                messages.error(request, 'Error al crear tu cuenta. Contacta al administrador.')
                return render(request, 'login.html')
        
        # Verificar si el usuario está activo
        if not user.is_active:
            messages.error(request, '❌ Tu cuenta está desactivada. Contacta al administrador.')
            return render(request, 'login.html')
        
        # Verificar si tiene perfil de Usuario (si no, crearlo)
        if not hasattr(user, 'usuario'):
            from ..models import Usuario
            from datetime import timedelta
            
            try:
                tipo_usuario = 'Administrador' if email == CORREO_ESPECIAL else 'Externo'
                
                usuario_perfil = Usuario.objects.create(
                    user=user,
                    nombres=email.split('@')[0].capitalize(),
                    apepat='',
                    apemat='',
                    ci='PENDIENTE',
                    correo=email,
                    extension='LP',
                    complemento='',
                    tipo_usuario=tipo_usuario,
                    ru='',
                    nro_celular='',
                    fecha_baja=timezone.now() + timedelta(days=365*5),
                    esta_activo=True
                )
                logger.info(f"✅ Perfil creado para usuario existente: {email}")
            except Exception as e:
                logger.error(f"❌ Error al crear perfil: {str(e)}")
                messages.error(request, 'Error al configurar tu perfil.')
                return render(request, 'login.html')
        
        # Verificar si el usuario está activo (fecha_baja)
        if user.usuario.fecha_baja and user.usuario.fecha_baja < timezone.now():
            messages.error(request, '❌ Tu cuenta ha expirado. Contacta al administrador para renovarla.')
            return render(request, 'login.html')
        
        # Enviar código de verificación
        try:
            enviar_codigo_verificacion(user)
        except Exception as e:
            logger.error(f"Error enviando código a {email}: {e}")
            messages.error(request, '❌ Error al enviar el código. Intenta nuevamente.')
            return render(request, 'login.html')
        
        # Guardar en sesión que el usuario está en proceso de verificación
        request.session['verificacion_email'] = email
        request.session['verificacion_timestamp'] = str(timezone.now())
        
        # Redirigir al formulario de código
        return redirect('verificar_codigo')
    
    return render(request, 'login.html')


def verificar_codigo_view(request):
    """PASO 2: Ingresar código de verificación"""
    # Verificar que hay un email en sesión
    email = request.session.get('verificacion_email')
    if not email:
        messages.error(request, '❌ Por favor inicia el proceso de login nuevamente.')
        return redirect('home')
    
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        
        if not codigo or len(codigo) != 6 or not codigo.isdigit():
            messages.error(request, '❌ Por favor ingresa el código de 6 dígitos.')
            return render(request, 'verificar_codigo.html', {'email': email})
        
        try:
            user = User.objects.get(email=email)
            
            if verificar_codigo(user, codigo):
                # ✅ Especificar el backend de autenticación
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                
                # Limpiar datos de sesión
                if 'verificacion_email' in request.session:
                    del request.session['verificacion_email']
                if 'verificacion_timestamp' in request.session:
                    del request.session['verificacion_timestamp']
                
                messages.success(request, f'¡Bienvenido/a {user.first_name or user.username}! 👋')
                
                # Redirigir según el tipo de usuario
                if hasattr(user, 'usuario') and user.usuario.tipo_usuario == 'Administrador':
                    return redirect('principal')
                else:
                    return redirect('inicio')
            else:
                messages.error(request, '❌ Código incorrecto o expirado. Solicita un nuevo código.')
                return render(request, 'verificar_codigo.html', {'email': email})
                
        except User.DoesNotExist:
            messages.error(request, '❌ Usuario no encontrado.')
            return redirect('home')
    
    return render(request, 'verificar_codigo.html', {'email': email})


def reenviar_codigo(request):
    """Reenviar código de verificación vía AJAX"""
    if request.method == 'POST':
        email = request.session.get('verificacion_email')
        if not email:
            return JsonResponse({'success': False, 'error': 'Sesión inválida'})
        
        try:
            user = User.objects.get(email=email)
            enviar_codigo_verificacion(user)
            return JsonResponse({'success': True, 'message': 'Código reenviado a tu correo'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Usuario no encontrado'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


class CustomLoginView(LoginView):
    template_name = 'login.html'


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
        
        if request.user.check_password(password_actual):
            request.user.set_password(password_nuevo)
            request.user.save()
            update_session_auth_hash(request, request.user)
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'La contraseña actual es incorrecta'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
@login_required
@admin_required
def restablecer_password(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    try:
        if request.user.usuario.tipo_usuario != 'Administrador':
            return JsonResponse({'success': False, 'error': 'No tienes permisos'}, status=403)

        data = json.loads(request.body)
        usuario_id = data.get('usuario_id')
        ci = data.get('ci')
        
        if not usuario_id or not ci:
            return JsonResponse({'success': False, 'error': 'Faltan datos'}, status=400)

        from ..models import Usuario
        usuario = Usuario.objects.get(usuario_id=usuario_id)
        if not usuario.user:
            return JsonResponse({'success': False, 'error': 'Usuario sin cuenta asociada'}, status=400)

        usuario.user.set_password(ci)
        usuario.user.save()
        return JsonResponse({'success': True, 'message': 'Contraseña restablecida correctamente'})
        
    except Exception as e:
        logger.error(f"Error al restablecer contraseña: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Error interno'}, status=500)