# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
# from users.decorators import manager_required
# from .models import Client
# from .forms import ClientCreateForm, ClientUpdateForm
#
# @manager_required
# def client_list(request):
#     """Базовое представление списка клиентов"""
#     clients = Client.objects.all().order_by('full_name')
#     search_query = request.GET.get('search', '')
#     if search_query:
#         clients = clients.filter(full_name__icontains=search_query)
#     return render(request, 'clients/client_list.html', {'clients': clients})
#
# @manager_required
# def client_detail(request, client_id):
#     """Детальная информация о клиенте"""
#     client = get_object_or_404(Client, id=client_id)
#     return render(request, 'clients/client_detail.html', {'client': client})
#
# @manager_required
# def client_create(request):
#     """Создание клиента"""
#     if request.method == 'POST':
#         form = ClientCreateForm(request.POST)
#         if form.is_valid():
#             client = form.save()
#             return redirect('clients:client_detail', client_id=client.id)
#     else:
#         form = ClientCreateForm()
#     return render(request, 'clients/client_form.html', {'form': form})
#
# @login_required
# def client_update(request, client_id):
#     client = Client.objects.get(id=client_id)
#     if request.method == 'POST':
#         form = ClientUpdateForm(request.POST, instance=client)
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'Данные клиента обновлены')
#             return redirect('clients:client_detail', client_id=client.id)
#     else:
#         form = ClientUpdateForm(instance=client)
#     return render(request, 'clients/client_form.html', {'form': form})
