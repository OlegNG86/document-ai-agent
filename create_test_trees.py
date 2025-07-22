#!/usr/bin/env python3
"""
Скрипт для создания тестовых деревьев решений для проверки уникальности.
"""

import sys
import os
import json
from datetime import datetime

# Добавляем путь к модулям проекта
sys.path.append('/app')

try:
    from ai_agent.utils.decision_tree import DecisionTreeBuilder, QueryType
    from ai_agent.utils.tree_exporter import DecisionTreeExporter
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что скрипт запускается из контейнера ai-agent")
    sys.exit(1)

def create_test_trees():
    """Создание тестовых деревьев решений."""
    print("🌳 Создание тестовых деревьев решений...")
    
    # Инициализация компонентов
    builder = DecisionTreeBuilder()
    exporter = DecisionTreeExporter('/tmp/decision_trees_analysis')
    
    # Тестовые запросы
    test_queries = [
        ("Проверить соответствие договора поставки требованиям закона о госзакупках", "compliance_check"),
        ("Проверить соответствие трудового договора нормам трудового кодекса", "compliance_check"),
        ("Найти информацию о требованиях к оформлению документов", "general_question"),
        ("Какие документы нужны для регистрации ООО?", "general_question"),
        ("Сравнить два договора на предмет различий", "general_question")
    ]
    
    created_files = []
    
    for i, (query, query_type) in enumerate(test_queries, 1):
        print(f"\n📝 Создание дерева {i}/5: {query[:50]}...")
        
        try:
            # Создание дерева в зависимости от типа
            if query_type == "compliance_check":
                tree = builder.build_compliance_check_tree(
                    has_reference_docs=True, 
                    query_context=query
                )
                qt = QueryType.COMPLIANCE_CHECK
            else:
                tree = builder.build_general_query_tree(query, context_available=True)
                qt = QueryType.GENERAL_QUESTION
            
            # Экспорт дерева
            file_path = exporter.export_tree(tree, qt.value, query)
            
            if file_path:
                created_files.append(file_path)
                print(f"✅ Создан файл: {os.path.basename(file_path)}")
            else:
                print(f"❌ Ошибка создания файла для запроса {i}")
                
        except Exception as e:
            print(f"❌ Ошибка при создании дерева {i}: {e}")
    
    return created_files

def analyze_uniqueness(files):
    """Анализ уникальности созданных файлов."""
    print(f"\n🔍 Анализ уникальности {len(files)} файлов...")
    
    if not files:
        print("❌ Нет файлов для анализа")
        return
    
    # Проверка содержимого файлов
    file_contents = {}
    unique_fields = set()
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                file_contents[file_path] = content
                
                # Собираем уникальные поля для проверки
                unique_key = (
                    content.get('id', ''),
                    content.get('timestamp', ''),
                    content.get('query_text', ''),
                    content.get('root', {}).get('label', ''),
                    content.get('root', {}).get('description', '')
                )
                unique_fields.add(unique_key)
                
        except Exception as e:
            print(f"❌ Ошибка чтения файла {os.path.basename(file_path)}: {e}")
    
    # Результаты анализа
    print(f"\n📊 Результаты анализа:")
    print(f"   Всего файлов: {len(files)}")
    print(f"   Уникальных по содержимому: {len(unique_fields)}")
    
    if len(unique_fields) == len(files):
        print("✅ Все файлы уникальны!")
    else:
        print("❌ Найдены дублирующиеся файлы")
    
    # Показать ключевые поля каждого файла
    print(f"\n📋 Ключевые поля файлов:")
    for file_path in files:
        if file_path in file_contents:
            content = file_contents[file_path]
            filename = os.path.basename(file_path)
            print(f"\n🔸 {filename}:")
            print(f"   ID: {content.get('id', 'N/A')[:8]}...")
            print(f"   Timestamp: {content.get('timestamp', 'N/A')}")
            print(f"   Query: {content.get('query_text', 'N/A')[:50]}...")
            print(f"   Root Label: {content.get('root', {}).get('label', 'N/A')}")

def main():
    """Главная функция."""
    print("🚀 Тестирование уникальности деревьев решений")
    print("=" * 60)
    
    # Создание тестовых деревьев
    created_files = create_test_trees()
    
    # Анализ уникальности
    analyze_uniqueness(created_files)
    
    print("\n" + "=" * 60)
    print("✨ Тестирование завершено!")
    print(f"📁 Файлы сохранены в: /tmp/decision_trees_analysis/")
    print(f"🌐 Визуализация доступна: http://localhost:8501")

if __name__ == "__main__":
    main()