# search.py

from .models import Libro

# Función para buscar libros en la base de datos
def buscar_libros_por_atributos(atributos):
    query = Libro.objects.all()
    
    if 'titulo' in atributos:
        query = query.filter(titulo__icontains=atributos['titulo'])
    
    if 'autor' in atributos:
        query = query.filter(autores__icontains=atributos['autor'])
    
    if 'palabra_clave' in atributos:
        query = query.filter(palabra_clave__icontains=atributos['palabra_clave'])

    return query
