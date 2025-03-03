from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
#
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_manager():
            return redirect('orders:orders')
        elif request.user.is_worker():
            return redirect('orders:worker_orders')
        elif request.user.is_client():
            return redirect('orders:client_orders')
        else:
            messages.warning(request, 'Тип пользователя не определен')
            return redirect('users:login')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.is_manager():
                return redirect('orders:orders')
            elif user.is_worker():
                return redirect('orders:worker_orders')
            elif user.is_client():
                return redirect('orders:client_orders')
            else:
                messages.warning(request, 'Тип пользователя не определен')
                return redirect('users:login')
        else:
            messages.error(request, 'Неправильное имя пользователя или пароль')

    return render(request, 'users/login.html')

#
def logout_view(request):
    logout(request)
    # messages.success(request, 'Вы успешно вышли из системы')
    return redirect('users:login')

