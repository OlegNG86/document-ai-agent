# Исправление проблем с визуализацией деревьев решений

## Внесенные изменения

1. **Создан исправленный Dockerfile** (`visualization/Dockerfile.fixed`)

   - Фиксированные версии библиотек для решения проблемы совместимости numpy/pandas
   - Явное указание адреса и порта для Streamlit

2. **Обновлен docker-compose.yml**

   - Использование исправленного Dockerfile
   - Явное указание привязки к 0.0.0.0 для доступа извне
   - Добавлены переменные окружения для Streamlit

3. **Добавлена конфигурация Streamlit** (`visualization/.streamlit/config.toml`)

   - Настройки для доступа извне
   - Отключение CORS и XSRF для упрощения доступа

4. **Созданы вспомогательные скрипты**
   - `restart_visualization.sh` - для перезапуска контейнера визуализации
   - `check_service.sh` - для проверки доступности сервиса

## Инструкции по применению исправлений

1. **Перезапустите контейнер визуализации**:

   ```bash
   ./restart_visualization.sh
   ```

2. **Проверьте доступность сервиса**:

   ```bash
   ./check_service.sh
   ```

3. **Если проблема не решена**, попробуйте перезапустить все контейнеры:

   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Проверьте логи контейнера**:
   ```bash
   docker-compose logs -f decision-tree-viz
   ```

## Доступ к веб-интерфейсу

После успешного запуска веб-интерфейс должен быть доступен по адресу:

- http://10.50.50.10:8501

## Возможные проблемы и их решения

### 1. Контейнер не запускается

Проверьте логи:

```bash
docker-compose logs -f decision-tree-viz
```

Если проблема с зависимостями, отредактируйте `visualization/Dockerfile.fixed` и измените версии библиотек.

### 2. Веб-интерфейс недоступен с JumpHost

Проверьте сетевые настройки:

```bash
# На сервере
netstat -tulpn | grep 8501
```

Убедитесь, что Streamlit слушает на 0.0.0.0, а не только на 127.0.0.1.

### 3. Настройка Nginx (если прямой доступ не работает)

Установите и настройте Nginx как прокси:

```bash
apt-get update && apt-get install -y nginx
```

Создайте файл `/etc/nginx/sites-available/streamlit`:

```nginx
server {
    listen 80;
    server_name 10.50.50.10;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

Активируйте конфигурацию:

```bash
ln -s /etc/nginx/sites-available/streamlit /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

После этого веб-интерфейс должен быть доступен по адресу http://10.50.50.10/
