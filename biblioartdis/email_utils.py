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
        
        # Versión HTML con diseño moderno
        mensaje_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Código de verificación</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Poppins', Arial, sans-serif;
            background-color: #F0F4F8;
            margin: 0;
            padding: 20px;
        }}
        
        .email-container {{
            max-width: 550px;
            margin: 0 auto;
            background: #FFFFFF;
            border-radius: 24px;
            overflow: hidden;
            box-shadow: 0 20px 35px -10px rgba(0, 0, 0, 0.1);
        }}
        
        /* Header */
        .email-header {{
            background: linear-gradient(135deg, #0F2B3D 0%, #1A3A4F 100%);
            padding: 30px 20px;
            text-align: center;
            border-bottom: 3px solid #F59E0B;
        }}
        
        .logo {{
            margin-bottom: 15px;
        }}
        
        .logo-icon {{
            width: 60px;
            height: 60px;
            background: rgba(245, 158, 11, 0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto;
        }}
        
        .logo-icon span {{
            font-size: 30px;
        }}
        
        .email-header h1 {{
            color: #FFFFFF;
            font-size: 24px;
            font-weight: 700;
            margin: 0;
        }}
        
        .email-header p {{
            color: rgba(255, 255, 255, 0.8);
            font-size: 14px;
            margin: 8px 0 0;
        }}
        
        /* Body */
        .email-body {{
            padding: 30px;
        }}
        
        .greeting {{
            font-size: 18px;
            font-weight: 600;
            color: #1F2937;
            margin-bottom: 20px;
        }}
        
        .message {{
            font-size: 14px;
            color: #6B7280;
            line-height: 1.6;
            margin-bottom: 25px;
        }}
        
        /* Código destacado */
        .code-container {{
            background: linear-gradient(135deg, #F8FAFC 0%, #F0F4F8 100%);
            border-radius: 16px;
            padding: 25px;
            text-align: center;
            margin: 20px 0;
            border: 1px solid #E5E7EB;
        }}
        
        .code-label {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: #F59E0B;
            margin-bottom: 10px;
        }}
        
        .code-value {{
            font-size: 42px;
            font-weight: 800;
            letter-spacing: 8px;
            color: #0F2B3D;
            background: white;
            padding: 15px 20px;
            border-radius: 12px;
            display: inline-block;
            font-family: monospace;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }}
        
        /* Info de expiración */
        .expiry-info {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin: 20px 0;
            padding: 12px;
            background: #FEF3C7;
            border-radius: 12px;
        }}
        
        .expiry-icon {{
            font-size: 18px;
        }}
        
        .expiry-text {{
            font-size: 13px;
            color: #D97706;
            font-weight: 500;
        }}
        
        /* Botón */
        .btn {{
            display: inline-block;
            background: linear-gradient(135deg, #0F2B3D 0%, #1A3A4F 100%);
            color: white;
            padding: 12px 28px;
            border-radius: 40px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            margin: 15px 0;
            transition: transform 0.2s ease;
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
        }}
        
        /* Footer */
        .email-footer {{
            background: #F8FAFC;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #E5E7EB;
        }}
        
        .email-footer p {{
            font-size: 11px;
            color: #9CA3AF;
            margin: 5px 0;
        }}
        
        .footer-links {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 10px;
        }}
        
        .footer-links a {{
            color: #6B7280;
            text-decoration: none;
            font-size: 11px;
        }}
        
        .footer-links a:hover {{
            color: #F59E0B;
        }}
        
        @media (max-width: 480px) {{
            .code-value {{
                font-size: 28px;
                letter-spacing: 4px;
            }}
            .email-body {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <!-- Header -->
        <div class="email-header">
            <div class="logo">
                <div class="logo-icon">
                    <span>📚</span>
                </div>
            </div>
            <h1>Biblioteca ARTyDIS</h1>
            <p>Verificación de acceso</p>
        </div>
        
        <!-- Body -->
        <div class="email-body">
            <div class="greeting">
                ¡Hola, {usuario.first_name or usuario.username}! 👋
            </div>
            
            <div class="message">
                Has solicitado acceder a la Biblioteca Digital ARTyDIS. 
                Para completar tu ingreso, utiliza el siguiente código de verificación:
            </div>
            
            <!-- Código -->
            <div class="code-container">
                <div class="code-label">TU CÓDIGO DE ACCESO</div>
                <div class="code-value">{codigo}</div>
            </div>
            
            <!-- Información de expiración -->
            <div class="expiry-info">
                <span class="expiry-icon">⏰</span>
                <span class="expiry-text">Este código es válido por <strong>10 minutos</strong></span>
            </div>
            
            <div class="message" style="text-align: center; font-size: 13px;">
                Si no solicitaste este código, puedes ignorar este mensaje.<br>
                Por tu seguridad, no compartas este código con nadie.
            </div>
            
            <div style="text-align: center;">
                <a href="{sitio_url}" class="btn">
                    🔐 Ir a la biblioteca
                </a>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="email-footer">
            <p>Biblioteca Digital ARTyDIS - Carrera de Artes y Diseño Gráfico</p>
            <p>Universidad Mayor de San Andrés</p>
            <div class="footer-links">
                <a href="{sitio_url}">Inicio</a>
                <a href="{sitio_url}/contacto">Contacto</a>
                <a href="{sitio_url}/ayuda">Ayuda</a>
            </div>
            <p style="margin-top: 15px;">© 2025 - Todos los derechos reservados</p>
        </div>
    </div>
</body>
</html>
"""
        
        # ✅ CORREGIDO: Enviar email SIN el argumento 'timeout'
        send_mail(
            asunto,
            mensaje_texto,
            settings.DEFAULT_FROM_EMAIL,
            [usuario.email],
            fail_silently=False,
            html_message=mensaje_html
        )
        
        logger.info(f"Código de verificación enviado exitosamente a {usuario.email}")
        return codigo_obj
        
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