#!/usr/bin/env python3
"""Скрипт для создания тестовых деревьев решений для веб-визуализации."""

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

def create_test_trees():
    """Создает несколько тестовых деревьев для демонстрации."""
    
    logger.info("🌳 Создание тестовых деревьев решений...")
    
    try:
        # Создаем компоненты
        tree_builder = DecisionTreeBuilder()
        tree_exporter = DecisionTreeExporter()
        
        # Тестовые запросы разных типов
        test_cases = [
            {
                "query": "Какие требования к поставщикам в государственных закупках?",
                "type": "general_question",
                "context": True
            },
            {
                "query": "Как проверить документы на соответствие 44-ФЗ?",
                "type": "compliance_check", 
                "context": True
            },
            {
                "query": "Какие штрафы предусмотрены за нарушения в закупках?",
                "type": "general_question",
                "context": True
            },
            {
                "query": "Процедура обжалования результатов закупки",
                "type": "general_question",
                "context": False
            },
            {
                "query": "Требования к техническому заданию",
                "type": "compliance_check",
                "context": True
            }
        ]
        
        created_trees = []
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n--- Создание дерева {i}/5: {test_case['query'][:50]}... ---")
            
            # Создаем дерево в зависимости от типа
            if test_case['type'] == 'compliance_check':
                tree = tree_builder.build_compliance_check_tree(
                    has_reference_docs=test_case['context'],
                    query_context=test_case['query']
                )
            else:
                tree = tree_builder.build_general_query_tree(
                    query=test_case['query'],
                    context_available=test_case['context']
                )
            
            logger.info(f"✅ Дерево создано с ID: {tree.id}")
            
            # Экспортируем дерево
            tree_path = tree_exporter.export_tree(
                tree=tree,
                query_type=test_case['type'],
                query_text=test_case['query']
            )
            
            if tree_path:
                logger.info(f"📁 Экспортировано в: {tree_path}")
                
                # Получаем URL
                viz_url = tree_exporter.get_visualization_url(tree_path)
                logger.info(f"🔗 URL: {viz_url}")
                
                created_trees.append({
                    'query': test_case['query'],
                    'type': test_case['type'],
                    'path': tree_path,
                    'url': viz_url
                })
            else:
                logger.error(f"❌ Ошибка экспорта для: {test_case['query']}")
        
        # Итоговая статистика
        logger.info(f"\n📊 === ИТОГИ ===")
        logger.info(f"✅ Создано деревьев: {len(created_trees)}")
        logger.info(f"🌐 Веб-визуализация: http://localhost:8501")
        
        # Проверяем общее количество файлов
        export_dir = "./visualization/data/decision_trees"
        if os.path.exists(export_dir):
            files = [f for f in os.listdir(export_dir) if f.endswith('.json')]
            logger.info(f"📁 Всего файлов в директории: {len(files)}")
            
            # Показываем последние созданные файлы
            logger.info(f"\n📋 Последние созданные деревья:")
            for tree in created_trees:
                filename = os.path.basename(tree['path'])
                file_size = os.path.getsize(tree['path'])
                logger.info(f"  • {filename} ({file_size} байт)")
                logger.info(f"    Запрос: {tree['query'][:60]}...")
        
        logger.info(f"\n🎉 Тестовые деревья созданы! Откройте http://localhost:8501 для просмотра.")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании тестовых деревьев: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    create_test_trees()