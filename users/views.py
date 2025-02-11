from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm, UserUpdateForm
from django.contrib import messages

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

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна!')
            return redirect('users:login')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('users:profile')
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'users/profile.html', {'form': form})

@login_required
def home(request):
    if request.user.is_manager():
        return redirect('orders:orders')
    elif request.user.is_worker():
        return redirect('orders:worker_orders')
    else:  # клиент
        return redirect('orders:client_orders')

def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('users:login')

