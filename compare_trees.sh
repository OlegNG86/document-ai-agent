#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Сравнение деревьев решений ===${NC}"

TREE_DIR="/tmp/decision_trees_analysis"

if [ ! -d "$TREE_DIR" ]; then
    echo -e "${RED}Директория $TREE_DIR не найдена${NC}"
    exit 1
fi

# Найти все JSON файлы
json_files=($(find "$TREE_DIR" -name "*.json" | sort))
file_count=${#json_files[@]}

if [ $file_count -eq 0 ]; then
    echo -e "${RED}JSON файлы не найдены в $TREE_DIR${NC}"
    exit 1
fi

echo -e "${YELLOW}Найдено файлов: $file_count${NC}"

# Функция для извлечения ключевых полей из JSON
extract_key_fields() {
    local file="$1"
    echo "=== $(basename "$file") ==="
    echo -n "ID: "
    jq -r '.id // "N/A"' "$file" 2>/dev/null || echo "N/A"
    echo -n "Timestamp: "
    jq -r '.timestamp // "N/A"' "$file" 2>/dev/null || echo "N/A"
    echo -n "Query Type: "
    jq -r '.query_type // "N/A"' "$file" 2>/dev/null || echo "N/A"
    echo -n "Query Text: "
    jq -r '.query_text // "N/A"' "$file" 2>/dev/null || echo "N/A"
    echo -n "Root Label: "
    jq -r '.root.label // "N/A"' "$file" 2>/dev/null || echo "N/A"
    echo -n "Root Description: "
    jq -r '.root.description // "N/A"' "$file" 2>/dev/null | head -c 100
    echo "..."
    echo ""
}

# Показать ключевые поля каждого файла
echo -e "${YELLOW}Ключевые поля каждого файла:${NC}"
for file in "${json_files[@]}"; do
    extract_key_fields "$file"
done

# Проверить уникальность по MD5
echo -e "${YELLOW}Проверка уникальности содержимого:${NC}"
declare -A md5_map
duplicates=0

for file in "${json_files[@]}"; do
    md5=$(md5sum "$file" | cut -d' ' -f1)
    if [[ -n "${md5_map[$md5]}" ]]; then
        echo -e "${RED}Дубликат найден:${NC}"
        echo "  $(basename "${md5_map[$md5]}")"
        echo "  $(basename "$file")"
        duplicates=$((duplicates + 1))
    else
        md5_map[$md5]="$file"
    fi
done

if [ $duplicates -eq 0 ]; then
    echo -e "${GREEN}✓ Все файлы уникальны по содержимому${NC}"
else
    echo -e "${RED}✗ Найдено $duplicates дубликатов${NC}"
fi

# Показать размеры файлов
echo -e "${YELLOW}Размеры файлов:${NC}"
ls -lh "$TREE_DIR"/*.json | awk '{print $9 " - " $5}'

echo -e "\n${GREEN}=== Сравнение завершено ===${NC}"