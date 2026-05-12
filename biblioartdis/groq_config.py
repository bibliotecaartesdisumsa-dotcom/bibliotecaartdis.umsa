# biblioartdis/groq_config.py

import os
import logging

from groq import Groq
from django.db.models import Q
from dotenv import load_dotenv

from biblioartdis.models import Libro, Autor

# Cargar variables .env
load_dotenv()

logger = logging.getLogger(__name__)

# Obtener API Key desde variables de entorno
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Validar existencia de API KEY
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY no encontrada en variables de entorno")
    cliente = None
else:
    cliente = Groq(api_key=GROQ_API_KEY)


def buscar_libros_en_bd(prompt):
    """
    Busca libros en la base de datos según la consulta del usuario.
    """

    prompt_lower = prompt.lower()

    # Extraer palabras clave
    palabras_clave = [
        p for p in prompt_lower.split()
        if len(p) > 2
    ]

    if not palabras_clave:
        return []

    # Construir consulta dinámica
    q = Q()

    for palabra in palabras_clave:
        q |= Q(titulo__icontains=palabra)
        q |= Q(descripcion__icontains=palabra)
        q |= Q(palabra_clave__icontains=palabra)
        q |= Q(autores__nombre__icontains=palabra)

    libros = Libro.objects.filter(q).distinct()[:5]

    resultados = []

    for libro in libros:
        resultados.append({
            "titulo": libro.titulo,
            "autor": ", ".join(
                [a.nombre for a in libro.autores.all()]
            ) or "Autor no especificado",

            "descripcion": (
                libro.descripcion[:150]
                if libro.descripcion
                else "Sin descripción"
            ),

            "tipo": libro.get_tipo_display(),
            "id": libro.id_libro
        })

    return resultados


def get_ai_response(prompt):
    """
    Obtiene una respuesta de Groq API.
    Primero busca libros en la base de datos.
    """

    try:

        # Buscar libros primero
        libros_encontrados = buscar_libros_en_bd(prompt)

        if libros_encontrados:

            respuesta = (
                "📚 Encontré estos libros en nuestra biblioteca:\n\n"
            )

            for libro in libros_encontrados:

                respuesta += f"• {libro['titulo']}\n"
                respuesta += f"  ✍️ Autor: {libro['autor']}\n"

                if libro["descripcion"] != "Sin descripción":
                    respuesta += (
                        f"  📝 {libro['descripcion']}...\n"
                    )

                respuesta += (
                    f"  🏷️ Tipo: {libro['tipo']}\n\n"
                )

            respuesta += (
                "¿Te gustaría más detalles de algún libro?"
            )

            return respuesta

        # Validar cliente Groq
        if not cliente:
            return (
                "El asistente IA no está configurado correctamente."
            )

        # Prompt del sistema
        system_prompt = """
Eres un asistente virtual de una biblioteca digital llamada Biblioteca ARTyDIS.

Tus respuestas deben:
- Ser en español
- Ser amables y útiles
- Ser concisas
- Tener máximo 3 o 4 oraciones

Si el libro no existe:
- Sugiere palabras clave alternativas
- Recomienda temas similares
"""

        respuesta = cliente.chat.completions.create(
            model="llama-3.3-70b-versatile",

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.7,
            max_tokens=500,
        )

        return respuesta.choices[0].message.content

    except Exception as e:

        logger.error(f"Error en Groq API: {str(e)}")

        return (
            "Lo siento, el asistente no está disponible "
            "en este momento. Intenta más tarde."
        )


def probar_conexion():
    """
    Prueba conexión con Groq API
    """

    print("Probando conexión con Groq API...")

    try:

        respuesta = get_ai_response(
            "Hola, ¿cómo estás?"
        )

        print("✅ Conexión exitosa!")
        print(f"Respuesta: {respuesta[:200]}...")

        return respuesta

    except Exception as e:

        print(f"❌ Error: {e}")

        return None