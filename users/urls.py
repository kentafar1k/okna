from django.urls import path
from .views import custom_login_view

app_name = 'users'

# class CustomLoginView(LoginView):
#     template_name = 'users/login.html'
#     authentication_form = UserLoginForm
#
#     def get_success_url(self):
#         return '/dashboard/'

urlpatterns = [
    path('', custom_login_view, name='login'),
]