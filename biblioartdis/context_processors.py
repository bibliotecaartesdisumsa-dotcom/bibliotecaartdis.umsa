from .models import Usuario

def user_info(request):
    usuario = None
    if request.user.is_authenticated:
        try:
            usuario = Usuario.objects.get(correo=request.user.username)
        except Usuario.DoesNotExist:
            pass
    return {'usuario': usuario}
