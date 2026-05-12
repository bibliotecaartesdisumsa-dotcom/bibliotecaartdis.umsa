# suggestions.py

from .models import Libro

# Generar sugerencias cuando no hay coincidencias exactas
def generar_sugerencias(atributos):
    # Busca libros por categorías similares, palabras clave, autores, etc.
    sugerencias = Libro.objects.all()
    
    if 'categoria' in atributos:
        sugerencias = sugerencias.filter(categoria__icontains=atributos['categoria'])
    
    if 'autor' in atributos:
        sugerencias = sugerencias.filter(autores__icontains=atributos['autor'])
    
    return sugerencias[:5]  # Devuelve las primeras 5 sugerencias
