#!/bin/bash

# Скрипт запуска Document AI Agent
# Проверяет доступность Ollama на хосте и запускает Docker Compose

echo "🚀 Запуск Document AI Agent..."

# Проверка доступности Ollama на хосте
echo "🔍 Проверка доступности Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama доступна на localhost:11434"
else
    echo "❌ Ollama недоступна на localhost:11434"
    echo "Убедитесь, что Ollama запущена:"
    echo "  sudo systemctl start ollama"
    echo "  или"
    echo "  ollama serve"
    exit 1
fi

# Проверка наличия необходимых моделей
echo "🔍 Проверка доступных моделей..."
MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | cut -d'"' -f4)

if echo "$MODELS" | grep -q "qwen2.5vl:latest"; then
    echo "✅ Модель qwen2.5vl:latest найдена"
else
    echo "⚠️  Модель qwen2.5vl:latest не найдена"
fi

if echo "$MODELS" | grep -q "nomic-embed-text:latest"; then
    echo "✅ Модель nomic-embed-text:latest найдена"
else
    echo "⚠️  Модель nomic-embed-text:latest не найдена"
fi

# Создание необходимых директорий
echo "📁 Создание директорий..."
mkdir -p data/documents data/chroma_db logs

# Создание .env файла если его нет
if [ ! -f .env ]; then
    echo "📝 Создание .env файла..."
    cp .env.example .env
    echo "✅ Файл .env создан из .env.example"
    echo "💡 Отредактируйте .env файл при необходимости"
fi

# Запуск Docker Compose
echo "🐳 Запуск Docker Compose..."
docker-compose up -d

echo ""
echo "🎉 Document AI Agent запущен!"
echo ""
echo "📋 Полезные команды:"
echo "  docker-compose logs -f ai-agent     # Просмотр логов"
echo "  docker-compose exec ai-agent bash  # Вход в контейнер"
echo "  docker-compose down                 # Остановка сервисов"
echo ""
echo "🔧 Для работы с агентом:"
echo "  docker-compose exec ai-agent poetry run python -m ai_agent.main --help"
echo "  docker-compose exec ai-agent poetry run python -m ai_agent.main status"
echo "  docker-compose exec ai-agent poetry run python -m ai_agent.main query"
