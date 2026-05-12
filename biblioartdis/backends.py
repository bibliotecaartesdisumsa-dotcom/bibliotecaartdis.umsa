# backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from .models import Usuario

class CIAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            usuario = Usuario.objects.get(ci=username)
            if usuario.ci == password:
                user, created = User.objects.get_or_create(username=usuario.correo)
                if created:
                    user.set_password(password)
                    user.save()
                return user
        except Usuario.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
