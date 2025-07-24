#!/bin/bash

# Скрипт для тестирования MCP сервера

MCP_URL="http://localhost:3000"

echo "🧪 Тестирование ChromaDB MCP Server"
echo "=================================="

# Проверка здоровья сервера
echo "1. Проверка health endpoint..."
curl -s "$MCP_URL/health" | jq '.' || echo "❌ Health check failed"
echo ""

# Получение списка инструментов
echo "2. Получение списка MCP инструментов..."
curl -s "$MCP_URL/mcp/tools" | jq '.' || echo "❌ Tools list failed"
echo ""

# Тестовый вызов инструмента поиска
echo "3. Тестовый вызов chromadb_search..."
curl -s -X POST "$MCP_URL/mcp/tools/chromadb_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test query",
    "collection": "documents",
    "n_results": 3
  }' | jq '.' || echo "❌ Search tool failed"
echo ""

echo "✅ Тестирование завершено"