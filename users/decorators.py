from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib import messages
from functools import wraps

def client_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Пожалуйста, войдите в систему')
            return redirect('users:login')
        if not request.user.is_client():
            messages.error(request, 'Доступ разрешен только для клиентов')
            return redirect('users:login')
        return view_func(request, *args, **kwargs)
    return wrapper

def manager_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Пожалуйста, войдите в систему')
            return redirect('users:login')
        if not request.user.is_manager():
            messages.error(request, 'Доступ разрешен только для менеджеров')
            return redirect('users:login')
        return view_func(request, *args, **kwargs)
    return wrapper

def worker_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Пожалуйста, войдите в систему')
            return redirect('users:login')
        if not request.user.is_worker():
            messages.error(request, 'Доступ разрешен только для работников')
            return redirect('users:login')
        return view_func(request, *args, **kwargs)
    return wrapper 