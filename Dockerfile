FROM python:3.12.8

WORKDIR /okna

# копируем директорию зависимостей
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# копируем все остальные директории(они чаще меняются чем requirements)
COPY . .


#CMD ["gunicorn", "crm.wsgi:application", "--bind", "0.0.0.0:8000"]

#CMD [ "python", "manage.py", "runserver", "0.0.0.0:8000"]

CMD [ "python", "main.py"]