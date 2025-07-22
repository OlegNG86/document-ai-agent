FROM python:3.9-slim

# Установка системных зависимостей для pygraphviz
RUN apt-get update && apt-get install -y \
    graphviz \
    graphviz-dev \
    pkg-config \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Обновление pip и установка совместимых версий библиотек
RUN pip install --upgrade pip

# Установка numpy и pandas в правильном порядке
RUN pip install --no-cache-dir \
    numpy==1.23.5 \
    pandas==1.5.3

# Копирование и установка остальных зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание директорий для данных
RUN mkdir -p /app/data/decision_trees

# Открытие порта для Streamlit
EXPOSE 8501

# Запуск приложения
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]