"""
Модуль для экспорта деревьев решений в JSON формат для визуализации.
"""

import os
import json
import uuid
import logging
from datetime import datetime
import pytz
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
            'query_text': self._clean_text(query_text or ''),
            'root': self._clean_node_data(root_node),
            'statistics': stats
        }
        
        return tree_json
    
    def _clean_text(self, text: str) -> str:
        """Clean text from problematic Unicode characters.
        
        Args:
            text: Text to clean.
            
        Returns:
            Cleaned text.
        """
        if not text:
            return ""
        
        try:
            # Remove surrogate characters and other problematic Unicode
            clean_text = text.encode('utf-8', errors='ignore').decode('utf-8')
            return clean_text
        except (UnicodeEncodeError, UnicodeDecodeError):
            # Fallback: replace problematic characters
            return ''.join(char for char in text if ord(char) < 0x110000 and not (0xD800 <= ord(char) <= 0xDFFF))
    
    def _clean_node_data(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively clean node data from problematic Unicode characters.
        
        Args:
            node_data: Node data to clean.
            
        Returns:
            Cleaned node data.
        """
        if not isinstance(node_data, dict):
            return node_data
        
        cleaned = {}
        for key, value in node_data.items():
            if isinstance(value, str):
                cleaned[key] = self._clean_text(value)
            elif isinstance(value, list):
                cleaned[key] = [self._clean_node_data(item) if isinstance(item, dict) else 
                              self._clean_text(item) if isinstance(item, str) else item 
                              for item in value]
            elif isinstance(value, dict):
                cleaned[key] = self._clean_node_data(value)
            else:
                cleaned[key] = value
        
        return cleaned
    
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
    
    def export_tree(self, tree: Any, query_type: str, query_text: str = None, document_filename: str = None) -> Optional[str]:
        """
        Экспортирует дерево решений в JSON файл.
        
        Args:
            tree: Объект дерева решений.
            query_type: Тип запроса.
            query_text: Текст запроса пользователя для уникальности.
            document_filename: Имя файла документа для включения в имя файла дерева.
            
        Returns:
            Optional[str]: Путь к сохраненному файлу или None в случае ошибки.
        """
        try:
            # Конвертируем дерево в JSON
            tree_json = self.convert_tree_to_json(tree, query_type, query_text)
            
            # Получаем московское время
            moscow_tz = pytz.timezone('Europe/Moscow')
            moscow_time = datetime.now(moscow_tz)
            
            # Генерируем имя файла в новом формате
            if query_type == 'compliance_check' and document_filename:
                # Извлекаем имя файла без расширения
                doc_name = os.path.splitext(os.path.basename(document_filename))[0]
                timestamp = moscow_time.strftime('%Y%m%d_%H-%M')
                filename = f"c_check_{timestamp}_{doc_name}.json"
            else:
                # Для других типов запросов используем старый формат
                timestamp = moscow_time.strftime('%Y%m%d_%H%M%S')
                microseconds = moscow_time.microsecond
                filename = f"{query_type}_{timestamp}_{microseconds}_{tree_json['id'][:8]}.json"
            
            filepath = os.path.join(self.export_path, filename)
            
            # Сохраняем в файл
            with open(filepath, 'w', encoding='utf-8') as f:
                try:
                    json.dump(tree_json, f, ensure_ascii=False, indent=2)
                except UnicodeEncodeError:
                    # Fallback: use ASCII encoding
                    json.dump(tree_json, f, ensure_ascii=True, indent=2)
            
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