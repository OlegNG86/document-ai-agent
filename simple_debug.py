#!/usr/bin/env python3
"""
Простой скрипт для отладки структуры узлов дерева решений.
"""

import sys
import os
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Копируем необходимые классы напрямую
class QueryType(Enum):
    """Types of queries for decision tree categorization."""
    GENERAL_QUESTION = "general_question"
    COMPLIANCE_CHECK = "compliance_check"

@dataclass
class DecisionNode:
    """Represents a node in the decision tree."""
    id: str
    label: str
    probability: float
    description: str = ""
    children: List['DecisionNode'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_child(self, child: 'DecisionNode') -> None:
        """Add a child node."""
        self.children.append(child)

@dataclass
class DecisionTree:
    """Represents a complete decision tree."""
    id: str
    root: DecisionNode
    query_type: QueryType
    metadata: Dict[str, Any] = field(default_factory=dict)

def create_test_tree():
    """Создает тестовое дерево для отладки."""
    print("🔍 Создание тестового дерева решений")
    print("=" * 50)
    
    # Создаем корневой узел
    root_node = DecisionNode(
        id=str(uuid.uuid4()),
        label="Тестовый корневой узел",
        probability=1.0,
        description="Описание корневого узла"
    )
    
    # Создаем дочерние узлы
    child1 = DecisionNode(
        id=str(uuid.uuid4()),
        label="Первый дочерний узел",
        probability=0.7,
        description="Описание первого дочернего узла"
    )
    
    child2 = DecisionNode(
        id=str(uuid.uuid4()),
        label="Второй дочерний узел", 
        probability=0.3,
        description="Описание второго дочернего узла"
    )
    
    root_node.add_child(child1)
    root_node.add_child(child2)
    
    # Создаем дерево
    tree = DecisionTree(
        id=str(uuid.uuid4()),
        root=root_node,
        query_type=QueryType.GENERAL_QUESTION
    )
    
    return tree

def debug_tree_structure(tree):
    """Отладка структуры дерева."""
    print(f"📊 Информация о дереве:")
    print(f"   ID дерева: {tree.id}")
    print(f"   Тип запроса: {tree.query_type}")
    
    print(f"\n🌳 Информация о корневом узле:")
    root = tree.root
    print(f"   ID: {root.id}")
    print(f"   Label: '{root.label}'")
    print(f"   Description: '{root.description}'")
    print(f"   Probability: {root.probability}")
    print(f"   Количество детей: {len(root.children)}")
    
    # Проверяем дочерние узлы
    for i, child in enumerate(root.children):
        print(f"\n👶 Дочерний узел {i+1}:")
        print(f"   ID: {child.id}")
        print(f"   Label: '{child.label}'")
        print(f"   Description: '{child.description}'")
        print(f"   Probability: {child.probability}")

def test_exporter_conversion(tree):
    """Тестируем конвертацию как в экспортере."""
    print(f"\n🔧 Тестирование конвертации экспортера:")
    
    def convert_node(node):
        """Имитируем логику экспортера."""
        node_json = {
            'id': getattr(node, 'id', str(uuid.uuid4())),
            'label': getattr(node, 'label', ''),
            'description': getattr(node, 'description', ''),
            'probability': getattr(node, 'probability', 1.0),
        }
        
        children = []
        for child in getattr(node, 'children', []):
            children.append(convert_node(child))
        
        if children:
            node_json['children'] = children
        
        return node_json
    
    # Конвертируем корневой узел
    root_json = convert_node(tree.root)
    
    print(f"   Корневой узел JSON:")
    print(f"     ID: {root_json['id']}")
    print(f"     Label: '{root_json['label']}'")
    print(f"     Description: '{root_json['description']}'")
    print(f"     Probability: {root_json['probability']}")
    
    if 'children' in root_json:
        for i, child_json in enumerate(root_json['children']):
            print(f"   Дочерний узел {i+1} JSON:")
            print(f"     ID: {child_json['id']}")
            print(f"     Label: '{child_json['label']}'")
            print(f"     Description: '{child_json['description']}'")
            print(f"     Probability: {child_json['probability']}")

def main():
    """Главная функция."""
    try:
        print("🚀 Отладка структуры деревьев решений")
        print("=" * 60)
        
        # Создаем тестовое дерево
        tree = create_test_tree()
        
        # Отлаживаем структуру
        debug_tree_structure(tree)
        
        # Тестируем конвертацию
        test_exporter_conversion(tree)
        
        print(f"\n" + "=" * 60)
        print("✨ Отладка завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()