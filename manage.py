#!/usr/bin/env python
"""
Carrera de Artes Plásticas y Diseño Gráfico - Sistema web de Biblioteca con asistente virtual
Desarrollado por: Lex Carita
Copyright (c) 2024. Todos los derechos reservados.

Este archivo es parte del sistema BiblioArtdis y está protegido por
las leyes de derechos de autor y tratados internacionales.
La reproducción o distribución no autorizada de este archivo,
o cualquier parte del mismo, puede resultar en sanciones severas.

Django's command-line utility for administrative tasks.
"""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arteydis.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
