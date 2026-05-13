from django.apps import AppConfig
import os

class BiblioartdisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'biblioartdis'
    path = os.path.dirname(os.path.abspath(__file__))
