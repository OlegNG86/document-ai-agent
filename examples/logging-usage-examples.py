#!/usr/bin/env python3
"""
Примеры использования улучшенной системы логирования и обработки ошибок AI Agent.

Этот файл демонстрирует различные возможности новой системы:
- Централизованное логирование
- Обработка ошибок с retry механизмами
- Мониторинг производительности
- Интеграция всех компонентов
"""

import os
import time
import logging
from pathlib import Path

# Настройка окружения для демонстрации
os.environ.update({
    'LOG_LEVEL': 'DEBUG',
    'ENABLE_FILE_LOGGING': 'true',
    'LOG_DIR': 'logs/examples',
    'MAX_LOG_SIZE_MB': '1',
    'LOG_BACKUP_COUNT': '2',
    'SLOW_OPERATION_THRESHOLD': '1.0',
    'MEMORY_USAGE_THRESHOLD': '100'
})

# Импорты системы логирования
from ai_agent.utils.logging_config import get_logger, logging_manager
from ai_agent.utils.error_handling import (
    with_retry, RetryConfig, handle_error, create_error,
    ErrorCategory, ErrorSeverity, NETWORK_RETRY_CONFIG
)
from ai_agent.utils.performance_monitor import (
    performance_tracker, monitor_performance, performance_monitor
)


def example_basic_logging():
    """Пример базового логирования с контекстом."""
    print("\n=== Пример 1: Базовое логирование ===")
    
    logger = get_logger("example.basic")
    
    # Обычные сообщения
    logger.debug("Отладочная информация")
    logger.info("Информационное сообщение")
    logger.warning("Предупреждение о потенциальной проблеме")
    
    # Логирование с дополнительным контекстом
    logger.info(
        "Операция выполнена успешно",
        extra={
            'operation': 'example_operation',
            'processing_time': 1.23,
            'document_id': 'doc-123',
            'session_id': 'session-456'
        }
    )
    
    print("✅ Базовое логирование завершено")


def example_error_handling():
    """Пример обработки ошибок с классификацией."""
    print("\n=== Пример 2: Обработка ошибок ===")
    
    logger = get_logger("example.errors")
    
    try:
        # Симуляция ошибки
        raise ValueError("Пример ошибки валидации")
    except ValueError as e:
        # Обработка ошибки с классификацией
        ai_error = handle_error(
            error=e,
            error_code="EXAMPLE_VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            details={
                'input_value': 'invalid_data',
                'expected_format': 'valid_format'
            },
            suggestions=[
                "Проверьте формат входных данных",
                "Убедитесь, что все обязательные поля заполнены",
                "Обратитесь к документации API"
            ],
            context={'operation': 'example_validation', 'user_id': 'user-123'}
        )
        
        logger.info(f"Ошибка обработана: {ai_error.error_info.error_code}")
    
    # Создание пользовательской ошибки
    custom_error = create_error(
        error_code="EXAMPLE_CUSTOM_ERROR",
        message="Пример пользовательской ошибки",
        category=ErrorCategory.PROCESSING,
        severity=ErrorSeverity.LOW,
        details={'component': 'example_module'},
        suggestions=["Попробуйте перезапустить операцию"]
    )
    
    logger.info(f"Создана пользовательская ошибка: {custom_error.error_info.message}")
    print("✅ Обработка ошибок завершена")


def example_retry_mechanisms():
    """Пример использования retry механизмов."""
    print("\n=== Пример 3: Retry механизмы ===")
    
    logger = get_logger("example.retry")
    call_count = 0
    
    @with_retry(
        RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            exponential_base=2.0,
            jitter=False
        ),
        exceptions=(ConnectionError, TimeoutError),
        logger=logger
    )
    def unreliable_network_operation():
        """Симуляция нестабильной сетевой операции."""
        nonlocal call_count
        call_count += 1
        
        logger.info(f"Попытка подключения #{call_count}")
        
        if call_count < 3:
            raise ConnectionError(f"Сетевая ошибка на попытке {call_count}")
        
        return "Подключение успешно установлено"
    
    try:
        result = unreliable_network_operation()
        logger.info(f"Результат: {result}")
        print(f"✅ Операция успешна после {call_count} попыток")
    except Exception as e:
        logger.error(f"Операция не удалась: {e}")
        print(f"❌ Операция не удалась после {call_count} попыток")


def example_performance_monitoring():
    """Пример мониторинга производительности."""
    print("\n=== Пример 4: Мониторинг производительности ===")
    
    logger = get_logger("example.performance")
    
    # Использование context manager
    with performance_tracker("example_operation", component="demo") as metrics:
        logger.info("Начало длительной операции")
        time.sleep(0.5)  # Симуляция работы
        logger.info("Операция в процессе...")
        time.sleep(0.3)  # Еще немного работы
        logger.info("Операция завершена")
    
    # Использование декоратора
    @monitor_performance("decorated_operation", category="example")
    def slow_operation(duration: float):
        """Симуляция медленной операции."""
        logger.info(f"Выполнение операции в течение {duration}с")
        time.sleep(duration)
        return f"Операция завершена за {duration}с"
    
    # Быстрая операция
    result1 = slow_operation(0.2)
    logger.info(f"Быстрая операция: {result1}")
    
    # Медленная операция (превысит порог)
    result2 = slow_operation(1.2)
    logger.info(f"Медленная операция: {result2}")
    
    # Получение статистики
    stats = performance_monitor.get_operation_stats()
    print(f"✅ Выполнено операций: {sum(s.get('count', 0) for s in stats.values())}")
    
    # Медленные операции
    slow_ops = performance_monitor.get_slow_operations()
    if slow_ops:
        print(f"⚠️ Обнаружено медленных операций: {len(slow_ops)}")


def example_integrated_workflow():
    """Пример интегрированного рабочего процесса."""
    print("\n=== Пример 5: Интегрированный рабочий процесс ===")
    
    logger = get_logger("example.workflow")
    
    @monitor_performance("document_processing_workflow")
    @with_retry(NETWORK_RETRY_CONFIG, logger=logger)
    def process_document_workflow(doc_id: str):
        """Симуляция обработки документа с полным циклом логирования."""
        
        # Создаем operation logger с контекстом
        op_logger = logging_manager.create_operation_logger(
            logger, 
            document_id=doc_id,
            operation="document_processing"
        )
        
        try:
            op_logger.info("Начало обработки документа")
            
            # Этап 1: Валидация
            op_logger.info("Валидация документа", step="validation")
            time.sleep(0.1)
            
            # Этап 2: Обработка (с возможной ошибкой)
            op_logger.info("Обработка содержимого", step="processing")
            time.sleep(0.2)
            
            # Симуляция случайной ошибки
            import random
            if random.random() < 0.3:  # 30% вероятность ошибки
                raise ConnectionError("Временная ошибка сети")
            
            # Этап 3: Сохранение
            op_logger.info("Сохранение результатов", step="saving")
            time.sleep(0.1)
            
            op_logger.info("Документ успешно обработан")
            return f"Документ {doc_id} обработан успешно"
            
        except Exception as e:
            # Обработка ошибки с полным контекстом
            error = handle_error(
                error=e,
                error_code="DOCUMENT_PROCESSING_ERROR",
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                details={'document_id': doc_id, 'step': 'processing'},
                suggestions=[
                    "Проверьте сетевое подключение",
                    "Убедитесь, что документ доступен",
                    "Попробуйте повторить операцию"
                ],
                context={'document_id': doc_id, 'operation': 'document_processing'}
            )
            raise error
    
    # Обработка нескольких документов
    documents = ["doc-001", "doc-002", "doc-003"]
    
    for doc_id in documents:
        try:
            result = process_document_workflow(doc_id)
            logger.info(f"✅ {result}")
        except Exception as e:
            logger.error(f"❌ Ошибка обработки {doc_id}: {e}")
    
    print("✅ Интегрированный рабочий процесс завершен")


def show_performance_summary():
    """Показать сводку по производительности."""
    print("\n=== Сводка по производительности ===")
    
    stats = performance_monitor.get_operation_stats()
    
    if not stats:
        print("Нет данных о производительности")
        return
    
    print(f"Всего операций: {sum(s.get('count', 0) for s in stats.values())}")
    print("\nДетальная статистика:")
    
    for operation, data in stats.items():
        print(f"  {operation}:")
        print(f"    Выполнений: {data.get('count', 0)}")
        print(f"    Успешных: {data.get('success_count', 0)}")
        print(f"    Ошибок: {data.get('error_count', 0)}")
        print(f"    Среднее время: {data.get('avg_duration', 0):.3f}с")
        print(f"    Макс. время: {data.get('max_duration', 0):.3f}с")
    
    # Медленные операции
    slow_ops = performance_monitor.get_slow_operations()
    if slow_ops:
        print(f"\nМедленные операции ({len(slow_ops)}):")
        for op in slow_ops[-5:]:  # Последние 5
            print(f"  {op.operation}: {op.duration:.3f}с")


def main():
    """Главная функция с примерами."""
    print("🚀 Демонстрация системы логирования AI Agent")
    print("=" * 60)
    
    # Создаем директорию для логов
    Path("logs/examples").mkdir(parents=True, exist_ok=True)
    
    try:
        # Запуск всех примеров
        example_basic_logging()
        example_error_handling()
        example_retry_mechanisms()
        example_performance_monitoring()
        example_integrated_workflow()
        
        # Показать сводку
        show_performance_summary()
        
        print("\n" + "=" * 60)
        print("✅ Все примеры выполнены успешно!")
        print(f"📁 Логи сохранены в: logs/examples/")
        print("📊 Проверьте файлы логов для детальной информации")
        
    except Exception as e:
        print(f"\n❌ Ошибка выполнения примеров: {e}")
        raise


if __name__ == "__main__":
    main()