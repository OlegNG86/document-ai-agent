#!/usr/bin/env python3
"""
Скрипт для отладки структуры узлов дерева решений.
"""

import sys
import os

# Добавляем путь к модулям проекта
sys.path.append('/app')

try:
    from ai_agent.utils.decision_tree import DecisionTreeBuilder, QueryType
    
    print("🔍 Отладка структуры узлов дерева решений")
    print("=" * 50)
    
    # Создаем builder
    builder = DecisionTreeBuilder()
    
    # Создаем тестовое дерево
    tree = builder.build_general_query_tree('Тестовый запрос', True)
    
    print(f"📊 Информация о дереве:")
    print(f"   ID дерева: {tree.id}")
    print(f"   Тип запроса: {tree.query_type}")
    
    print(f"\n🌳 Информация о корневом узле:")
    root = tree.root
    print(f"   ID: {root.id}")
    print(f"   Тип объекта: {type(root)}")
    print(f"   Доступные атрибуты: {dir(root)}")
    
    # Проверяем различные возможные названия полей
    possible_labels = ['label', 'name', 'title', 'text', 'description']
    
    print(f"\n🔍 Проверка возможных полей для названия узла:")
    for field in possible_labels:
        if hasattr(root, field):
            value = getattr(root, field)
            print(f"   ✅ {field}: '{value}'")
        else:
            print(f"   ❌ {field}: не найдено")
    
    # Проверяем дочерние узлы
    if root.children:
        print(f"\n👶 Информация о первом дочернем узле:")
        child = root.children[0]
        print(f"   ID: {child.id}")
        print(f"   Тип объекта: {type(child)}")
        
        print(f"\n🔍 Проверка полей дочернего узла:")
        for field in possible_labels:
            if hasattr(child, field):
                value = getattr(child, field)
                print(f"   ✅ {field}: '{value}'")
            else:
                print(f"   ❌ {field}: не найдено")
    else:
        print(f"\n👶 Дочерние узлы отсутствуют")
    
    print(f"\n" + "=" * 50)
    print("✨ Отладка завершена!")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что скрипт запускается из контейнера ai-agent")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()