#!/usr/bin/env python3
"""Простой скрипт для отладки экспорта деревьев решений."""

import os
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

# Устанавливаем переменную окружения
os.environ['VISUALIZATION_ENABLED'] = 'true'

from ai_agent.utils.decision_tree import DecisionTreeBuilder, QueryType
from ai_agent.utils.tree_exporter import DecisionTreeExporter

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Основная функция для тестирования."""
    
    logger.info("=== Тест экспорта деревьев решений ===")
    
    try:
        # Создаем компоненты
        tree_builder = DecisionTreeBuilder()
        tree_exporter = DecisionTreeExporter()
        
        # Создаем несколько тестовых деревьев
        queries = [
            "Какие требования к поставщикам?",
            "Как проверить документы на соответствие?",
            "Какие штрафы за нарушения?"
        ]
        
        for i, query in enumerate(queries, 1):
            logger.info(f"\n--- Тест {i}: {query} ---")
            
            # Создаем дерево
            tree = tree_builder.build_general_query_tree(
                query=query,
                context_available=True
            )
            
            logger.info(f"Дерево создано с ID: {tree.id}")
            
            # Экспортируем дерево
            tree_path = tree_exporter.export_tree(
                tree=tree,
                query_type="general_question",
                query_text=query
            )
            
            if tree_path:
                logger.info(f"✅ Дерево экспортировано: {tree_path}")
                
                # Получаем URL
                viz_url = tree_exporter.get_visualization_url(tree_path)
                logger.info(f"🔗 URL визуализации: {viz_url}")
                
                # Проверяем размер файла
                file_size = os.path.getsize(tree_path)
                logger.info(f"📁 Размер файла: {file_size} байт")
                
            else:
                logger.error(f"❌ Ошибка экспорта дерева для запроса: {query}")
        
        # Проверяем общее количество файлов
        export_dir = "./visualization/data/decision_trees"
        files = [f for f in os.listdir(export_dir) if f.endswith('.json')]
        logger.info(f"\n📊 Всего файлов деревьев: {len(files)}")
        
        for file in files[-5:]:  # Показываем последние 5 файлов
            file_path = os.path.join(export_dir, file)
            file_size = os.path.getsize(file_path)
            logger.info(f"  - {file} ({file_size} байт)")
            
        logger.info("\n✅ Тест завершен успешно!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()