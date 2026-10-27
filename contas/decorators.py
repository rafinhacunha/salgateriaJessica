from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def proprietaria_required(view):
    """RF02: restringe a view ao perfil Proprietária."""

    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.eh_proprietaria:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper
