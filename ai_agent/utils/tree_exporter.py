"""
Модуль для экспорта деревьев решений в JSON формат для визуализации.
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)

class DecisionTreeExporter:
    """
    Класс для экспорта деревьев решений в JSON формат для визуализации.
    """
    
    def __init__(self, export_path: str = None):
        """
        Инициализация экспортера деревьев решений.
        
        Args:
            export_path: Путь для сохранения JSON файлов деревьев решений.
                         Если не указан, используется переменная окружения DECISION_TREE_EXPORT_PATH
                         или './visualization/data/decision_trees' по умолчанию.
        """
        self.export_path = export_path or os.environ.get(
            'DECISION_TREE_EXPORT_PATH', 
            './visualization/data/decision_trees'
        )
        
        # Создаем директорию, если она не существует
        os.makedirs(self.export_path, exist_ok=True)
        
        logger.info(f"Инициализирован экспортер деревьев решений. Путь экспорта: {self.export_path}")
    
    def convert_tree_to_json(self, tree: Any, query_type: str, query_text: str = None) -> Dict[str, Any]:
        """
        Конвертирует дерево решений в JSON формат для визуализации.
        
        Args:
            tree: Объект дерева решений.
            query_type: Тип запроса (например, 'general_question', 'compliance_check').
            query_text: Текст запроса пользователя для уникальности.
            
        Returns:
            Dict[str, Any]: JSON-совместимый словарь с данными дерева.
        """
        tree_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Получаем корневой узел и статистику
        root_node = self._convert_node(tree.root) if hasattr(tree, 'root') else {}
        
        # Добавляем информацию о запросе в корневой узел для уникальности
        if root_node and query_text:
            root_node['query_text'] = query_text
            root_node['description'] = f"{root_node.get('description', '')} | Запрос: {query_text[:100]}..."
        
        # Собираем статистику
        stats = {
            'total_nodes': getattr(tree, 'total_nodes', 0),
            'total_paths': getattr(tree, 'total_paths', 0),
            'max_depth': getattr(tree, 'max_depth', 0),
            'generation_time': getattr(tree, 'generation_time', 0.0)
        }
        
        # Формируем итоговый JSON
        tree_json = {
            'id': tree_id,
            'query_type': query_type,
            'timestamp': timestamp,
            'query_text': query_text or '',
            'root': root_node,
            'statistics': stats
        }
        
        return tree_json
    
    def _convert_node(self, node: Any) -> Dict[str, Any]:
        """
        Рекурсивно конвертирует узел дерева в JSON формат.
        
        Args:
            node: Узел дерева решений.
            
        Returns:
            Dict[str, Any]: JSON-совместимый словарь с данными узла.
        """
        if node is None:
            return {}
        
        # Базовые атрибуты узла
        node_json = {
            'id': getattr(node, 'id', str(uuid.uuid4())),
            'label': getattr(node, 'label', ''),
            'description': getattr(node, 'description', ''),
            'probability': getattr(node, 'probability', 1.0),
        }
        
        # Рекурсивно обрабатываем дочерние узлы
        children = []
        for child in getattr(node, 'children', []):
            children.append(self._convert_node(child))
        
        if children:
            node_json['children'] = children
        
        return node_json
    
    def export_tree(self, tree: Any, query_type: str, query_text: str = None) -> Optional[str]:
        """
        Экспортирует дерево решений в JSON файл.
        
        Args:
            tree: Объект дерева решений.
            query_type: Тип запроса.
            query_text: Текст запроса пользователя для уникальности.
            
        Returns:
            Optional[str]: Путь к сохраненному файлу или None в случае ошибки.
        """
        try:
            # Конвертируем дерево в JSON
            tree_json = self.convert_tree_to_json(tree, query_type, query_text)
            
            # Генерируем имя файла с дополнительной уникальностью
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            microseconds = datetime.now().microsecond
            filename = f"{query_type}_{timestamp}_{microseconds}_{tree_json['id'][:8]}.json"
            filepath = os.path.join(self.export_path, filename)
            
            # Сохраняем в файл
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(tree_json, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Дерево решений успешно экспортировано: {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Ошибка при экспорте дерева решений: {str(e)}")
            return None
    
    def get_visualization_url(self, tree_path: Optional[str] = None) -> str:
        """
        Возвращает URL для доступа к визуализации дерева решений.
        
        Args:
            tree_path: Путь к файлу дерева решений (опционально).
            
        Returns:
            str: URL для доступа к визуализации.
        """
        base_url = os.environ.get('VISUALIZATION_URL', 'http://localhost:8501')
        
        if tree_path:
            # Извлекаем только имя файла из пути
            filename = os.path.basename(tree_path)
            # В будущем можно добавить параметры для прямого перехода к конкретному дереву
            return f"{base_url}?tree={filename}"
        
        return base_url