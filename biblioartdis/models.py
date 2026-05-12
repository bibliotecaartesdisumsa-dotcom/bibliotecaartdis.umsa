from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from django.db import models
import io
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

def get_fecha_baja_default():
    return timezone.now() + timedelta(days=5*365)

class Usuario(models.Model):
    opciones_usuarios = (
        ('Estudiante', 'Estudiante'),
        ('Administrador', 'Administrador'),
        ('Docente', 'Docente'),
        ('Externo', 'Externo'),
    )
    opciones_extensiones = (
        ('LP', 'LP'),
        ('CH', 'CH'),
        ('CB', 'CB'),
        ('OR', 'OR'),
        ('PT', 'PT'),
        ('TJ', 'TJ'),
        ('SC', 'SC'),
        ('BE', 'BE'),
        ('PD', 'PD'),
    )
    usuario_id = models.AutoField(primary_key=True)  
    nombres = models.CharField(max_length=50)
    apepat = models.CharField(max_length=30)
    apemat = models.CharField(max_length=30)
    ci = models.CharField(max_length=20)
    correo = models.EmailField()
    extension = models.CharField(max_length=5, choices=opciones_extensiones)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    tipo_usuario = models.CharField(max_length=50, choices=opciones_usuarios)
    ru = models.CharField(max_length=20, blank=True, null=True)
    nro_celular = models.CharField(max_length=20)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    fecha_alta = models.DateTimeField(default=timezone.now)
    fecha_baja = models.DateTimeField(null=True, blank=True,
        default=get_fecha_baja_default
    )
    esta_activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_alta']  # Ordenar por fecha de alta descendente

    def __str__(self):
        return f"ID: {self.usuario_id} Usuario: {self.nombres}, Tipo: {self.tipo_usuario}"

    def save(self, *args, **kwargs):
        if not self.pk:  # Si es una nueva instancia
            self.fecha_baja = get_fecha_baja_default()
        super().save(*args, **kwargs)

    # Métodos útiles para reportes
    @property
    def dias_restantes(self):
        """Retorna los días restantes hasta la fecha de baja"""
        if self.fecha_baja:
            delta = self.fecha_baja - timezone.now()
            return max(0, delta.days)
        return 0

    @property
    def estado(self):
        """Retorna el estado actual del usuario"""
        if not self.esta_activo:
            return "Inactivo"
        if self.dias_restantes <= 0:
            return "Expirado"
        return "Activo"

    @classmethod
    def get_usuarios_por_vencer(cls, dias=30):
        """Retorna usuarios que vencerán en los próximos X días"""
        fecha_limite = timezone.now() + timedelta(days=dias)
        return cls.objects.filter(
            esta_activo=True,
            fecha_baja__lte=fecha_limite,
            fecha_baja__gt=timezone.now()
        )

    @classmethod
    def get_estadisticas(cls):
        """Retorna estadísticas básicas de usuarios"""
        total = cls.objects.count()
        activos = cls.objects.filter(esta_activo=True).count()
        por_tipo = cls.objects.filter(esta_activo=True).values(
            'tipo_usuario'
        ).annotate(total=Count('tipo_usuario'))
        
        return {
            'total_usuarios': total,
            'usuarios_activos': activos,
            'por_tipo': por_tipo
        }

# Señal para crear o actualizar el perfil de usuario
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # Crear un Usuario por defecto cuando se crea un User
        try:
            Usuario.objects.create(
                user=instance,
                nombres=instance.username,  # Usar el username como nombre por defecto
                apepat='-',  # Campos obligatorios con valores por defecto
                apemat='-',
                ci='SIN CI',
                correo=instance.email or f'{instance.username}@example.com',
                extension='LP',  # Valor por defecto
                tipo_usuario='Externo',  # Valor por defecto
                nro_celular='00000000'
            )
        except Exception as e:
            print(f"Error al crear Usuario: {e}")
    # Eliminamos la actualización automática del correo aquí para evitar conflictos

class Autor(models.Model):
    id_autor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre} "
 
class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nom_cat = models.CharField(max_length=100)
    def __str__(self):
        return self.nom_cat   
class Libro(models.Model):
    opciones_categ = (
        ('NIVEL 1', 'NIVEL 1'),
        ('NIVEL 2', 'NIVEL 2'),
        ('NIVEL 3', 'NIVEL 3'),
        ('NIVEL 4', 'NIVEL 4'),
        ('OTRO', 'OTRO'),
    ) 

    opciones_tipo = (
        ('LIBRO', 'Libro'),
        ('ARTICULO', 'Artículo'),
        ('REVISTA', 'Revista'),
        ('TESIS', 'Tesis'),
        ('DICCIONARIO', 'Diccionario'),
        ('MONOGRAFIA', 'Monografía'),
        ('FOLLETO', 'Folleto'),
        ('INFORME', 'Informe'),
        ('OTRO', 'Otro'),
    )
    
    id_libro = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=15, choices=opciones_tipo)
    titulo = models.CharField(max_length=255)
    edicion = models.CharField(max_length=50, blank=True, null=True)  
    categoria = models.CharField(max_length=15, choices=opciones_categ)
    img_portada = models.ImageField(upload_to='portadas/')
    pdf = models.FileField(upload_to='pdfs/')
    archivo_autorizacion = models.FileField(upload_to='autorizaciones/', blank=True, null=True)
    autores = models.ManyToManyField('Autor')
    fecha_publicacion = models.DateField(default=date.today)
    descripcion = models.TextField(blank=True, null=True)
    palabra_clave = models.TextField(blank=True, null=True)
    descarga_autorizada = models.BooleanField(default=True)
    pdf_url = models.URLField(max_length=500, blank=True, null=True)
    categorias = models.ManyToManyField(Categoria, blank=True)


    def agregar_palabras_claves(self, palabras):
        palabras_claves_actuales = self.palabra_clave.split(', ') if self.palabra_clave else []
        nuevas_palabras = [palabra.strip() for palabra in palabras.split(',')]
        palabras_claves_actuales.extend(nuevas_palabras)
        self.palabra_clave = ', '.join(palabras_claves_actuales)
        self.save()  # Guardar los cambios en la base de datos

    def __str__(self):
        return self.titulo


class Sugerencia(models.Model):
    id_sugerencia = models.AutoField(primary_key=True)
    solicitante = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    autor_sugerencia = models.CharField(max_length=50)
    titulo_sugerencia = models.CharField(max_length=80)
    fecha_sugerencia = models.DateField(auto_now_add=True)
    edicion = models.CharField(max_length=50)
    estado_respuesta = models.CharField(max_length=20, default='Pendiente')
    descripcion = models.TextField()
    respondido_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='sugerencias_respondidas')
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Sugerencia #{self.id_sugerencia}: {self.titulo_sugerencia} ({self.autor_sugerencia})"


class Coleccion(models.Model):
    id_coleccion = models.AutoField(primary_key=True)
    nomb_colecc = models.CharField(max_length=100)
    orden = models.PositiveIntegerField(default=0)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return self.nomb_colecc

class Revista(models.Model):
    id_revista = models.AutoField(primary_key=True)
    nro_revista = models.IntegerField(null=True, blank=True)
    coleccion = models.ForeignKey(Coleccion, on_delete=models.CASCADE)
    img_portada = models.ImageField(upload_to='portadasRev/')
    pdf = models.FileField(upload_to='pdfsRev/', null=True, blank=True)
    url = models.URLField(max_length=200, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        coleccion_nombre = self.coleccion.nomb_colecc if self.coleccion else "Sin colección"
        numero = f"#{self.nro_revista}" if self.nro_revista else "s/n"
        return f"Revista {numero} de la colección {coleccion_nombre}"


class VisitaLibro(models.Model):
    fecha_visualizacion = models.DateTimeField(auto_now=True)
    fecha_consulta = models.DateField(default=date.today)
    visitante = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    libro_visitado = models.ForeignKey('Libro', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.visitante} visitó {self.libro_visitado} el {self.fecha_visualizacion}"

    @classmethod
    def obtUltimaVisitaLibro(cls, usuario, libro, fecha):
        try:
            return cls.objects.filter(
                visitante=usuario,
                libro_visitado=libro,
                fecha_consulta__year=fecha.year,
                fecha_consulta__month=fecha.month
            ).latest('fecha_visualizacion')
        except cls.DoesNotExist:
            return None

class Imagen(models.Model):
    id_Imagen = models.AutoField(primary_key=True)
    titulo = models.CharField(max_length=255)
    autorImg = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    img_portada = models.ImageField(upload_to='imagenes/', max_length=255)
    pdf = models.FileField(upload_to='pdfs/', null=True, blank=True, max_length=255)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    marca_agua = models.ImageField(upload_to='marcas_agua/', max_length=255, blank=True, null=True)
    categorias = models.ManyToManyField(Categoria, blank=True)

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        # Almacena la imagen previa si existe y se actualiza `img_portada`
        if self.pk:
            old_img = Imagen.objects.get(pk=self.pk).img_portada
            if old_img and old_img != self.img_portada:
                old_img.delete(save=False)  # Elimina la imagen antigua
        super().save(*args, **kwargs)
    
class HistorialBusqueda(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    termino_busqueda = models.CharField(max_length=255)
    fecha_busqueda = models.DateTimeField(auto_now_add=True)
   
    class Meta:
       ordering = ['-fecha_busqueda']
    
# models.py - Agregar después de la clase HistorialBusqueda y antes de auditlog

class CodigoVerificacion(models.Model):
    id_codigo = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=6)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    usado = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Código de verificación"
        verbose_name_plural = "Códigos de verificación"
        ordering = ['-creado_en']
    
    def __str__(self):
        return f"Código para {self.usuario.email} - Expira: {self.expira_en}"
    
    def es_valido(self):
        """Verifica si el código aún es válido (no usado y no expirado)"""
        from django.utils import timezone
        return not self.usado and timezone.now() < self.expira_en
        
from auditlog.registry import auditlog
auditlog.register(Usuario)
auditlog.register(Autor)
auditlog.register(Categoria)
auditlog.register(Libro)
auditlog.register(Sugerencia)
auditlog.register(Imagen)
auditlog.register(Revista)
auditlog.register(Coleccion)
