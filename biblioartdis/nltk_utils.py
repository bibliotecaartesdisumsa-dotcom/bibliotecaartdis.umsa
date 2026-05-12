# nltk_utils.py

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Inicialización de NLTK (tokenizer, lematización, etc.)
def inicializar_nltk():
    nltk.download('punkt')
    nltk.download('wordnet')
    nltk.download('stopwords')
    lemmatizer = WordNetLemmatizer()
    stop_words_en = set(stopwords.words('english'))
    stop_words_es = set(stopwords.words('spanish'))
    stop_words = stop_words_en.union(stop_words_es)
    return lemmatizer, stop_words

# Procesar el texto y devolver tokens útiles
def procesar_texto(texto, lemmatizer, stop_words):
    # Convertir a minúsculas
    texto = texto.lower()
    
    # Tokenización
    tokens = word_tokenize(texto)
    
    # Filtrar tokens y lematizar
    tokens_filtrados = []
    for token in tokens:
        if token.isalnum() and token not in stop_words:  # Solo tokens alfanuméricos
            token_lemmatizado = lemmatizer.lemmatize(token)
            tokens_filtrados.append(token_lemmatizado)
    
    return tokens_filtrados

def contiene_palabras(texto, lista_palabras):
    """Verifica si el texto contiene alguna de las palabras de la lista"""
    texto = texto.lower()
    return any(palabra in texto for palabra in lista_palabras)
