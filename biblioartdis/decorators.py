 # biblioartdis/decorators.py
from django.contrib.auth.decorators import user_passes_test

def is_admin(user):
    """Retorna True si el usuario es administrador (campo tipo_usuario del perfil Usuario)."""
    return hasattr(user, 'usuario') and user.usuario.tipo_usuario == 'Administrador'

# Decorador para restringir vistas solo a administradores
admin_required = user_passes_test(is_admin, login_url='inicio')