# email_utils.py
import random
import logging
import base64
import pickle
import os
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import CodigoVerificacion

logger = logging.getLogger(__name__)


def get_gmail_service():
    """
    Obtiene el servicio de Gmail API usando credenciales desde variables de entorno de Railway
    """
    try:
        # Obtener credenciales desde variables de entorno de Railway
        creds_base64 = os.environ.get('GMAIL_CREDENTIALS_BASE64')
        token_base64 = os.environ.get('GMAIL_TOKEN_BASE64')
        
        if not creds_base64 or not token_base64:
            logger.error("Credenciales de Gmail no encontradas en variables de entorno")
            return None
        
        # Decodificar credenciales
        creds_json = base64.b64decode(creds_base64).decode('utf-8')
        token_data = base64.b64decode(token_base64)
        
        # Cargar credenciales
        creds = pickle.loads(token_data)
        
        # Refrescar si es necesario
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        # Construir servicio
        service = build('gmail', 'v1', credentials=creds)
        logger.info("Servicio Gmail API inicializado correctamente")
        return service
        
    except Exception as e:
        logger.error(f"Error obteniendo servicio Gmail: {e}")
        return None


def generar_codigo_verificacion():
    """Genera un código aleatorio de 6 dígitos"""
    return f"{random.randint(100000, 999999)}"


def obtener_url_sitio():
    """Obtiene la URL base del sitio según el entorno"""
    if settings.DEBUG:
        return 'http://127.0.0.1:8000'
    else:
        return 'https://bibliotecaartdisumsa-production.up.railway.app'


def enviar_codigo_verificacion(usuario):
    """
    Envía un código de verificación usando Gmail API
    """
    try:
        # Eliminar códigos anteriores no usados y expirados
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

        # Obtener servicio Gmail
        service = get_gmail_service()
        if not service:
            logger.error("No se pudo obtener servicio Gmail")
            return None

        sitio_url = obtener_url_sitio()
        nombre_usuario = usuario.first_name or usuario.username or "Usuario"

        asunto = "🔐 Código de verificación - Biblioteca ARTyDIS"
        
        mensaje_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Código de verificación</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 500px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            background: #0F2B3D;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 10px 10px 0 0;
            margin: -20px -20px 20px -20px;
        }}
        .code {{
            font-size: 32px;
            font-weight: bold;
            text-align: center;
            padding: 20px;
            background: #f0f0f0;
            border-radius: 5px;
            letter-spacing: 5px;
        }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: #666;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Biblioteca ARTyDIS</h2>
            <p>Verificación de acceso</p>
        </div>
        <p>¡Hola, {nombre_usuario}! 👋</p>
        <p>Has solicitado acceder a la Biblioteca Digital ARTyDIS.</p>
        <p>Tu código de verificación es:</p>
        <div class="code">{codigo}</div>
        <p>Este código es válido por <strong>10 minutos</strong>.</p>
        <div style="text-align: center;">
            <a href="{sitio_url}" style="background: #0F2B3D; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔐 Ir a la biblioteca</a>
        </div>
        <div class="footer">
            <p>Si no solicitaste este código, ignora este mensaje.</p>
            <p>Biblioteca ARTyDIS - UMSA</p>
        </div>
    </div>
</body>
</html>
        """

        # Crear mensaje
        message = EmailMessage()
        message.set_content(mensaje_html, subtype='html')
        message['To'] = usuario.email
        message['From'] = 'biblioteca.artesdis.umsa@gmail.com'
        message['Subject'] = asunto

        # Codificar mensaje
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Enviar usando Gmail API
        send_message = {
            'raw': encoded_message
        }
        
        service.users().messages().send(
            userId='me',
            body=send_message
        ).execute()

        logger.info(f"Código enviado exitosamente a {usuario.email} via Gmail API")
        return codigo_obj

    except Exception as e:
        logger.error(f"Error al enviar código a {usuario.email}: {str(e)}", exc_info=True)
        return None


def verificar_codigo(usuario, codigo_ingresado):
    """Verifica si el código ingresado es válido"""
    try:
        codigo_obj = CodigoVerificacion.objects.filter(
            usuario=usuario,
            codigo=codigo_ingresado,
            usado=False,
            expira_en__gt=timezone.now()
        ).latest('creado_en')

        codigo_obj.usado = True
        codigo_obj.save()

        logger.info(f"Código verificado exitosamente para {usuario.email}")
        return True

    except CodigoVerificacion.DoesNotExist:
        logger.warning(f"Código inválido o expirado para {usuario.email}")
        return False
    except Exception as e:
        logger.error(f"Error verificando código: {e}")
        return False