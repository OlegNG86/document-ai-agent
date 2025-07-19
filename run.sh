#!/bin/bash

# Скрипт для удобного запуска команд AI Agent в Docker контейнере

if [ $# -eq 0 ]; then
    echo "🤖 Document AI Agent - Помощник по работе с контейнером"
    echo ""
    echo "Использование: ./run.sh [команда]"
    echo ""
    echo "Доступные команды:"
    echo "  status      - Проверить статус системы"
    echo "  upload      - Загрузить документ (требует путь к файлу)"
    echo "  query       - Интерактивный режим вопросов"
    echo "  docs        - Управление документами"
    echo "  session     - Управление сессиями"
    echo "  shell       - Войти в контейнер"
    echo "  help        - Показать справку AI Agent"
    echo ""
    echo "Примеры:"
    echo "  ./run.sh status"
    echo "  ./run.sh upload /path/to/document.pdf"
    echo "  ./run.sh query"
    echo "  ./run.sh docs --list"
    echo "  ./run.sh shell"
    exit 0
fi

# Проверка запущен ли контейнер
if ! docker-compose ps | grep -q "ai-agent-app.*Up"; then
    echo "❌ Контейнер ai-agent-app не запущен"
    echo "Запустите: docker-compose up -d"
    exit 1
fi

case "$1" in
    "shell")
        echo "🐚 Вход в контейнер..."
        docker-compose exec ai-agent bash
        ;;
    "status"|"upload"|"query"|"docs"|"session")
        echo "🤖 Выполнение команды: $@"
        docker-compose exec ai-agent poetry run python -m ai_agent.main "$@"
        ;;
    "help")
        echo "📖 Справка AI Agent:"
        docker-compose exec ai-agent poetry run python -m ai_agent.main --help
        ;;
    *)
        echo "🤖 Выполнение команды: $@"
        docker-compose exec ai-agent poetry run python -m ai_agent.main "$@"
        ;;
esac
