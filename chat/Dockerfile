# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /code

# Копируем requirements.txt
COPY ./requirements.txt /code/requirements.txt

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Копируем код приложения
COPY . /code

# Открываем порт 8000 для доступа к FastAPI
EXPOSE 8000

# Команда для запуска Uvicorn
CMD ["uvicorn", "chat.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]