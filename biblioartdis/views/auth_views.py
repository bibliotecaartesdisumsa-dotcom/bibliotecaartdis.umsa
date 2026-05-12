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

from ..decorators import admin_required
from ..email_utils import enviar_codigo_verificacion, verificar_codigo

logger = logging.getLogger(__name__)

# Diccionario temporal para almacenar intentos de login
intentos_fallidos = {}


def home(request):
    """PASO 1: Solicitar email (acepta @umsa.bo y @gmail.com para desarrollo)"""
    if request.method == 'POST':
        email = request.POST.get('correo', '').strip().lower()
        
        # Validar formato de email
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, '❌ Por favor ingresa un correo electrónico válido.')
            return render(request, 'login.html')
        
        # ✅ Para desarrollo: permitir @gmail.com también
        if not (email.endswith('@umsa.bo') or email.endswith('@gmail.com')):
            messages.error(request, '❌ Solo se permiten correos @umsa.bo (o @gmail.com para pruebas)')
            return render(request, 'login.html')
        
        # Verificar intentos fallidos (seguridad)
        ip = request.META.get('REMOTE_ADDR')
        if ip in intentos_fallidos and intentos_fallidos[ip] >= 5:
            messages.error(request, '❌ Demasiados intentos. Espera 5 minutos.')
            return render(request, 'login.html')
        
        # Buscar usuario por email
        try:
            user = User.objects.get(email=email)
            
            # Verificar si el usuario está activo
            if not user.is_active:
                messages.error(request, '❌ Tu cuenta está desactivada. Contacta al administrador.')
                return render(request, 'login.html')
            
            # Verificar si tiene perfil de Usuario
            if not hasattr(user, 'usuario'):
                messages.error(request, '❌ Tu perfil no está completo. Contacta al administrador.')
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
            
        except User.DoesNotExist:
            # Registrar intento fallido
            intentos_fallidos[ip] = intentos_fallidos.get(ip, 0) + 1
            
            messages.error(request, '❌ No existe una cuenta con este correo. Contacta al administrador para registrarte.')
            return render(request, 'login.html')
    
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
                # Código correcto - iniciar sesión
                # Especificar el backend de autenticación
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