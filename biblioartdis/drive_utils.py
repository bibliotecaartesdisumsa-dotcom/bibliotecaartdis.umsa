# biblioartdis/drive_utils.py
import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_drive_service():
    """Obtiene el servicio de Google Drive autenticado"""
    try:
        # Obtener credenciales desde variables de entorno
        creds_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_JSON')
        
        if not creds_json:
            logger.error("GOOGLE_DRIVE_CREDENTIALS_JSON no encontrada en variables de entorno")
            return None
        
        # Decodificar credenciales
        creds_info = json.loads(creds_json)
        
        # Crear credenciales
        credentials = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        # Construir servicio
        service = build('drive', 'v3', credentials=credentials)
        logger.info("✅ Servicio Google Drive inicializado correctamente")
        return service
        
    except Exception as e:
        logger.error(f"❌ Error inicializando Google Drive: {str(e)}")
        return None


def subir_pdf_a_drive(archivo_pdf, nombre_archivo=None, folder_id=None):
    """
    Sube un PDF a Google Drive y retorna la URL de vista previa
    
    Args:
        archivo_pdf: Archivo subido desde Django (request.FILES)
        nombre_archivo: Nombre personalizado (opcional)
        folder_id: ID de la carpeta en Drive (opcional)
    
    Returns:
        str: URL de vista previa del PDF en Drive
    """
    try:
        service = get_drive_service()
        if not service:
            return None
        
        # Preparar nombre del archivo
        if not nombre_archivo:
            nombre_archivo = archivo_pdf.name
        
        # Leer contenido del archivo
        contenido = archivo_pdf.read()
        
        # Volver a posicionar el puntero del archivo (por si se necesita después)
        archivo_pdf.seek(0)
        
        # Crear media para subir
        media = MediaIoBaseUpload(
            io.BytesIO(contenido),
            mimetype='application/pdf',
            resumable=True
        )
        
        # Metadata del archivo
        file_metadata = {
            'name': nombre_archivo,
        }
        
        # Especificar carpeta si se proporcionó
        folder_id = folder_id or os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        # Subir archivo
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        
        # Configurar permisos para que sea público (cualquier persona puede ver)
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        # Generar URL de vista previa
        preview_url = f"https://drive.google.com/file/d/{file_id}/preview"
        
        logger.info(f"✅ PDF subido a Google Drive: {preview_url}")
        return preview_url
        
    except Exception as e:
        logger.error(f"❌ Error subiendo PDF a Google Drive: {str(e)}")
        return None


def eliminar_pdf_de_drive(file_id):
    """
    Elimina un archivo de Google Drive por su ID
    """
    try:
        service = get_drive_service()
        if not service:
            return False
        
        service.files().delete(fileId=file_id).execute()
        logger.info(f"✅ Archivo eliminado de Google Drive: {file_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error eliminando archivo de Drive: {str(e)}")
        return False


def obtener_id_drive_desde_url(url):
    """
    Extrae el ID del archivo desde una URL de Google Drive
    """
    import re
    pattern = r'/file/d/([a-zA-Z0-9_-]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None