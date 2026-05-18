# biblioartdis/drive_utils.py
import os
import io
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import logging

logger = logging.getLogger(__name__)


def get_drive_service():
    """Obtiene el servicio de Google Drive autenticado con OAuth"""
    try:
        creds_json = os.environ.get('GOOGLE_DRIVE_OAUTH_CREDENTIALS')
        
        if not creds_json:
            logger.error("GOOGLE_DRIVE_OAUTH_CREDENTIALS no encontrada")
            return None
        
        creds_info = json.loads(creds_json)
        
        credentials = Credentials(
            token=creds_info.get('token'),
            refresh_token=creds_info.get('refresh_token'),
            token_uri=creds_info.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=creds_info.get('client_id'),
            client_secret=creds_info.get('client_secret'),
            scopes=creds_info.get('scopes', ['https://www.googleapis.com/auth/drive.file'])
        )
        
        service = build('drive', 'v3', credentials=credentials)
        logger.info("✅ Servicio Google Drive inicializado correctamente")
        return service
        
    except Exception as e:
        logger.error(f"❌ Error inicializando Drive: {str(e)}")
        return None


def subir_pdf_a_drive(archivo_pdf, nombre_archivo=None, folder_id=None):
    """Sube un PDF a Google Drive usando OAuth"""
    try:
        service = get_drive_service()
        if not service:
            return None
        
        folder_id = folder_id or os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        
        if not folder_id:
            logger.error("GOOGLE_DRIVE_FOLDER_ID no configurada")
            return None
        
        if not nombre_archivo:
            nombre_archivo = archivo_pdf.name
        
        contenido = archivo_pdf.read()
        archivo_pdf.seek(0)
        
        media = MediaIoBaseUpload(
            io.BytesIO(contenido),
            mimetype='application/pdf',
            resumable=True
        )
        
        file_metadata = {
            'name': nombre_archivo,
            'parents': [folder_id]
        }
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        
        preview_url = f"https://drive.google.com/file/d/{file_id}/preview"
        
        logger.info(f"✅ PDF subido a Google Drive: {preview_url}")
        return preview_url
        
    except Exception as e:
        logger.error(f"❌ Error subiendo PDF: {str(e)}")
        return None