# email_utils.py
import random
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import CodigoVerificacion

logger = logging.getLogger(__name__)

def generar_codigo_verificacion():
    """Genera un código aleatorio de 6 dígitos"""
    return f"{random.randint(100000, 999999)}"

def obtener_url_sitio():
    """
    Obtiene la URL base del sitio según el entorno
    """
    if settings.DEBUG:
        return 'http://127.0.0.1:8000'
    else:
        # Para producción en Railway
        if 'bibliotecaartdisumsa-production.up.railway.app' in settings.ALLOWED_HOSTS:
            return 'https://bibliotecaartdisumsa-production.up.railway.app'
        elif settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS[0] not in ['*', 'localhost', '127.0.0.1']:
            return f"https://{settings.ALLOWED_HOSTS[0]}"
        else:
            return 'https://bibliotecaartdisumsa-production.up.railway.app'

def enviar_codigo_verificacion(usuario):
    """
    Envía un código de verificación al email del usuario
    Retorna el objeto CodigoVerificacion creado o None si hay error
    """
    try:
        # Eliminar códigos anteriores no usados y expirados del mismo usuario
        CodigoVerificacion.objects.filter(
            usuario=usuario, 
            usado=False,
            expira_en__lt=timezone.now()
        ).delete()
        
        # Generar nuevo código
        codigo = generar_codigo_verificacion()
        expiracion = timezone.now() + timedelta(minutes=10)
        
        # Guardar en base de datos
        codigo_obj = CodigoVerificacion.objects.create(
            usuario=usuario,
            codigo=codigo,
            expira_en=expiracion
        )
        
        # Obtener URL dinámica del sitio
        sitio_url = obtener_url_sitio()
        
        # Construir mensaje de email
        asunto = "🔐 Código de verificación - Biblioteca ARTyDIS"
        
        # Versión texto plano (fallback)
        mensaje_texto = f"""
Hola {usuario.first_name or usuario.username},

Has solicitado acceder a la Biblioteca Digital ARTyDIS.

Tu código de verificación es: {codigo}

Este código es válido por 10 minutos.

Accede a: {sitio_url}

Si no solicitaste este código, puedes ignorar este mensaje.

---
Biblioteca ARTyDIS - Carrera de Artes y Diseño Gráfico
Universidad Mayor de San Andrés
"""
        
        # Versión HTML (tu mismo código HTML, lo omito por brevedad pero déjalo igual)
        mensaje_html = f"""... (tu HTML existente) ..."""
        
        # Enviar email con manejo de errores y timeout
        try:
            send_mail(
                asunto,
                mensaje_texto,
                settings.DEFAULT_FROM_EMAIL,
                [usuario.email],
                fail_silently=False,
                html_message=mensaje_html,
                timeout=getattr(settings, 'EMAIL_TIMEOUT', 10)  # Timeout configurable
            )
            logger.info(f"Código de verificación enviado exitosamente a {usuario.email}")
            return codigo_obj
        except Exception as email_error:
            # Si falla el email, igual retornamos el código (se puede reenviar después)
            logger.error(f"Error enviando email a {usuario.email}: {str(email_error)}")
            return codigo_obj  # Retornar el código aunque falle el email
        
    except Exception as e:
        logger.error(f"Error al enviar código de verificación a {usuario.email}: {str(e)}", exc_info=True)
        return None

def verificar_codigo(usuario, codigo_ingresado):
    """
    Verifica si el código ingresado es válido
    Retorna True si es válido, False en caso contrario
    """
    try:
        codigo_obj = CodigoVerificacion.objects.filter(
            usuario=usuario,
            codigo=codigo_ingresado,
            usado=False,
            expira_en__gt=timezone.now()
        ).latest('creado_en')
        
        # Marcar como usado
        codigo_obj.usado = True
        codigo_obj.save()
        
        logger.info(f"Código verificado exitosamente para {usuario.email}")
        return True
        
    except CodigoVerificacion.DoesNotExist:
        logger.warning(f"Código de verificación inválido o expirado para {usuario.email}")
        return False
    except Exception as e:
        logger.error(f"Error al verificar código para {usuario.email}: {str(e)}")
        return False