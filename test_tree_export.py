#!/usr/bin/env python3
"""Тестовый скрипт для проверки экспорта деревьев решений."""

import os
import sys
import logging
import json
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from ai_agent.utils.decision_tree import DecisionTreeBuilder, QueryType
from ai_agent.utils.tree_exporter import DecisionTreeExporter

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_tree_export():
    """Тестирует экспорт дерева решений."""
    
    # Устанавливаем переменную окружения
    os.environ['VISUALIZATION_ENABLED'] = 'true'
    
    logger.info("Начинаем тест экспорта дерева решений...")
    
    try:
        # Создаем компоненты
        tree_builder = DecisionTreeBuilder()
        tree_exporter = DecisionTreeExporter()
        
        logger.info("Создаем тестовое дерево решений...")
        
        # Создаем тестовое дерево
        tree = tree_builder.build_general_query_tree(
            query="Какие требования к поставщикам?",
            context_available=True
        )
        
        logger.info(f"Дерево создано: {tree}")
        
        # Экспортируем дерево
        logger.info("Экспортируем дерево...")
        tree_path = tree_exporter.export_tree(
            tree=tree,
            query_type="general_question",
            query_text="Какие требования к поставщикам?"
        )
        
        if tree_path:
            logger.info(f"Дерево успешно экспортировано в: {tree_path}")
            
            # Проверяем, что файл существует
            if os.path.exists(tree_path):
                logger.info(f"Файл существует: {tree_path}")
                
                # Читаем содержимое файла
                with open(tree_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f"Содержимое файла (первые 200 символов): {content[:200]}...")
                    
                # Получаем URL для визуализации
                viz_url = tree_exporter.get_visualization_url(tree_path)
                logger.info(f"URL для визуализации: {viz_url}")
                
            else:
                logger.error(f"Файл не найден: {tree_path}")
        else:
            logger.error("Экспорт дерева вернул None")
            
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_tree_export()