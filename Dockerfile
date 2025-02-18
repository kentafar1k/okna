FROM python:3.11.9-slim

WORKDIR /okna

# копируем директорию зависимостей
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# копируем все остальные директории(они чаще меняются чем requirements)
COPY . .

CMD [ "python", "main.py" ]