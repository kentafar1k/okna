from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm

def custom_login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                # print(f"Authenticated user role: {user.role}")
                login(request, user)
                # Редирект в зависимости от роли
                if hasattr(user, 'role'):  # Проверяем наличие атрибута role
                    if user.role == 'admin':
                        return redirect('/admin/')
                    elif user.role == 'manager':
                        return redirect('/manager-dashboard/')
                    elif user.role == 'employee':
                        return redirect('/employee-dashboard/')
                return redirect('/default-dashboard/')
        return render(request, 'users/login.html', {'form': form, 'error': 'Invalid credentials'})
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

# from django.contrib.auth.views import LoginView
# from .models import CustomUser
# from django.http import HttpRequest, HttpResponse
#
# def some_view(request: HttpRequest) -> HttpResponse:
#     user: CustomUser = request.user  # Аннотация типа
#     print(user.role)
#     return HttpResponse("User role is: " + user.role)
#
# class CustomLoginView(LoginView):
#     def get_success_url(self):
#         # Проверяем роль пользователя
#         user: CustomUser = self.request.user
#         if user.role == 'admin':
#             return '/admin-dashboard/'
#         elif user.role == 'manager':
#             return '/manager-dashboard/'
#         elif user.role == 'employee':
#             return '/employee-dashboard/'
#         return '/default-dashboard/'  # Редирект по умолчанию

