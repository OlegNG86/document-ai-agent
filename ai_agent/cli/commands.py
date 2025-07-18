"""CLI commands for the AI agent."""

import os
import sys
import click
from pathlib import Path
from typing import Optional
import logging

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown

from ..core.document_manager import DocumentManager, DocumentManagerError
from ..core.session_manager import SessionManager, SessionManagerError
from ..core.query_processor import QueryProcessor, QueryProcessorError
from ..core.ollama_client import OllamaClient, OllamaConnectionError


console = Console()
logger = logging.getLogger(__name__)


class AIAgentCLI:
    """CLI interface for the AI agent."""
    
    def __init__(self):
        """Initialize CLI with core components."""
        self.document_manager = None
        self.session_manager = None
        self.query_processor = None
        self.ollama_client = None
        self.current_session_id = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all core components."""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Инициализация компонентов...", total=None)
                
                # Initialize Ollama client
                self.ollama_client = OllamaClient()
                
                # Check Ollama connection
                if not self.ollama_client.health_check():
                    console.print("[red]❌ Ошибка: Не удается подключиться к Ollama сервису")
                    console.print("Убедитесь, что Ollama запущен (ollama serve)")
                    sys.exit(1)
                
                # Initialize document manager
                self.document_manager = DocumentManager()
                
                # Initialize session manager
                self.session_manager = SessionManager()
                
                # Initialize query processor
                self.query_processor = QueryProcessor(
                    document_manager=self.document_manager,
                    session_manager=self.session_manager,
                    ollama_client=self.ollama_client
                )
                
                progress.update(task, description="Компоненты инициализированы ✅")
                
        except Exception as e:
            console.print(f"[red]❌ Ошибка инициализации: {e}")
            sys.exit(1)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Включить подробный вывод')
@click.pass_context
def cli(ctx, verbose):
    """Локальный AI агент для работы с нормативной документацией."""
    ctx.ensure_object(dict)
    
    # Setup logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
    
    # Initialize CLI
    ctx.obj['cli'] = AIAgentCLI()


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--title', '-t', help='Заголовок документа')
@click.option('--metadata', '-m', multiple=True, help='Метаданные в формате key=value')
@click.pass_context
def upload(ctx, file_path, title, metadata):
    """Загрузить документ в базу знаний."""
    cli_instance = ctx.obj['cli']
    
    try:
        # Parse metadata
        metadata_dict = {}
        for item in metadata:
            if '=' in item:
                key, value = item.split('=', 1)
                metadata_dict[key] = value
        
        if title:
            metadata_dict['title'] = title
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Загрузка документа...", total=None)
            
            doc_id = cli_instance.document_manager.upload_document(
                file_path=file_path,
                metadata=metadata_dict
            )
            
            progress.update(task, description="Документ загружен ✅")
        
        console.print(Panel(
            f"[green]✅ Документ успешно загружен\n\n"
            f"ID документа: [bold]{doc_id}[/bold]\n"
            f"Файл: [blue]{file_path}[/blue]",
            title="Успех"
        ))
        
    except DocumentManagerError as e:
        console.print(f"[red]❌ Ошибка загрузки: {e}")
        sys.exit(1)


@cli.command()
@click.option('--session-id', '-s', help='ID сессии (создается автоматически если не указан)')
@click.pass_context
def query(ctx, session_id):
    """Задать вопрос AI агенту."""
    cli_instance = ctx.obj['cli']
    
    # Create or use existing session
    if session_id is None:
        session_id = cli_instance.session_manager.create_session()
        console.print(f"[blue]📝 Создана новая сессия: {session_id}")
    
    cli_instance.current_session_id = session_id
    
    try:
        # Interactive query loop
        console.print(Panel(
            "[bold green]AI Агент готов к работе[/bold green]\n\n"
            "Введите ваш вопрос или команду:\n"
            "• [cyan]/help[/cyan] - показать помощь\n"
            "• [cyan]/history[/cyan] - показать историю сессии\n"
            "• [cyan]/check[/cyan] - проверить документ на соответствие\n"
            "• [cyan]/exit[/cyan] - выйти из режима запросов",
            title="Интерактивный режим"
        ))
        
        while True:
            user_input = Prompt.ask("\n[bold blue]Ваш вопрос")
            
            if user_input.lower() in ['/exit', '/quit', 'exit', 'quit']:
                break
            elif user_input.lower() == '/help':
                _show_help()
                continue
            elif user_input.lower() == '/history':
                _show_session_history(cli_instance, session_id)
                continue
            elif user_input.lower() == '/check':
                _document_check_mode(cli_instance, session_id)
                continue
            elif not user_input.strip():
                continue
            
            # Process query
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Обработка запроса...", total=None)
                
                try:
                    response = cli_instance.query_processor.process_general_query(
                        query=user_input,
                        session_id=session_id
                    )
                    
                    progress.update(task, description="Ответ получен ✅")
                    
                except QueryProcessorError as e:
                    progress.update(task, description="Ошибка обработки ❌")
                    console.print(f"[red]❌ Ошибка: {e}")
                    continue
            
            # Display response
            _display_response(response)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 До свидания!")
    except Exception as e:
        console.print(f"[red]❌ Ошибка: {e}")


@cli.command()
@click.option('--list', '-l', 'list_sessions', is_flag=True, help='Показать список сессий')
@click.option('--history', '-h', help='Показать историю сессии')
@click.option('--clear', '-c', help='Очистить сессию')
@click.option('--delete', '-d', help='Удалить сессию')
@click.pass_context
def session(ctx, list_sessions, history, clear, delete):
    """Управление сессиями."""
    cli_instance = ctx.obj['cli']
    
    try:
        if list_sessions:
            _list_sessions(cli_instance)
        elif history:
            _show_session_history(cli_instance, history)
        elif clear:
            if cli_instance.session_manager.clear_session(clear):
                console.print(f"[green]✅ Сессия {clear} очищена")
            else:
                console.print(f"[red]❌ Сессия {clear} не найдена")
        elif delete:
            if Confirm.ask(f"Удалить сессию {delete}?"):
                if cli_instance.session_manager.delete_session(delete):
                    console.print(f"[green]✅ Сессия {delete} удалена")
                else:
                    console.print(f"[red]❌ Сессия {delete} не найдена")
        else:
            console.print("[yellow]Используйте одну из опций: --list, --history, --clear, --delete")
            
    except SessionManagerError as e:
        console.print(f"[red]❌ Ошибка управления сессиями: {e}")


@cli.command()
@click.option('--list', '-l', 'list_docs', is_flag=True, help='Показать список документов')
@click.option('--info', '-i', help='Показать информацию о документе')
@click.option('--delete', '-d', help='Удалить документ')
@click.option('--stats', is_flag=True, help='Показать статистику коллекции')
@click.pass_context
def docs(ctx, list_docs, info, delete, stats):
    """Управление документами."""
    cli_instance = ctx.obj['cli']
    
    try:
        if list_docs:
            _list_documents(cli_instance)
        elif info:
            _show_document_info(cli_instance, info)
        elif delete:
            if Confirm.ask(f"Удалить документ {delete}?"):
                if cli_instance.document_manager.delete_document(delete):
                    console.print(f"[green]✅ Документ {delete} удален")
                else:
                    console.print(f"[red]❌ Документ {delete} не найден")
        elif stats:
            _show_collection_stats(cli_instance)
        else:
            console.print("[yellow]Используйте одну из опций: --list, --info, --delete, --stats")
            
    except DocumentManagerError as e:
        console.print(f"[red]❌ Ошибка управления документами: {e}")


@cli.command()
@click.pass_context
def status(ctx):
    """Показать статус системы."""
    cli_instance = ctx.obj['cli']
    
    # Check Ollama connection
    ollama_status = "🟢 Подключен" if cli_instance.ollama_client.health_check() else "🔴 Недоступен"
    
    # Get available models
    try:
        models = cli_instance.ollama_client.list_available_models()
        models_text = f"{len(models)} моделей: {', '.join(models[:3])}" + ("..." if len(models) > 3 else "")
    except:
        models_text = "Недоступно"
    
    # Get document stats
    doc_stats = cli_instance.document_manager.get_collection_stats()
    
    # Get session stats
    session_stats = cli_instance.session_manager.get_session_stats()
    
    status_panel = Panel(
        f"[bold]Статус AI Агента[/bold]\n\n"
        f"🤖 Ollama: {ollama_status}\n"
        f"📚 Модели: {models_text}\n"
        f"📄 Документы: {doc_stats.get('total_documents', 0)} ({doc_stats.get('total_chunks', 0)} чанков)\n"
        f"💬 Сессии: {session_stats.get('active_sessions', 0)} активных / {session_stats.get('total_sessions', 0)} всего\n"
        f"💭 Сообщения: {session_stats.get('total_messages', 0)} всего",
        title="Системная информация"
    )
    
    console.print(status_panel)


def _show_help():
    """Show help information."""
    help_text = """
[bold]Доступные команды:[/bold]

• [cyan]/help[/cyan] - показать эту справку
• [cyan]/history[/cyan] - показать историю текущей сессии
• [cyan]/check[/cyan] - перейти в режим проверки документов
• [cyan]/exit[/cyan] - выйти из интерактивного режима

[bold]Примеры вопросов:[/bold]

• "Какие требования к документации по закупкам?"
• "Что нужно указать в договоре с поставщиком?"
• "Какие документы нужны для участия в тендере?"
"""
    console.print(Panel(help_text, title="Справка"))


def _show_session_history(cli_instance, session_id):
    """Show session history."""
    try:
        messages = cli_instance.session_manager.get_session_history(session_id, limit=10)
        
        if not messages:
            console.print("[yellow]История сессии пуста")
            return
        
        table = Table(title=f"История сессии {session_id}")
        table.add_column("Время", style="cyan")
        table.add_column("Роль", style="magenta")
        table.add_column("Сообщение", style="white", max_width=60)
        
        for message in messages[-10:]:  # Last 10 messages
            role = "👤 Пользователь" if message.is_user_message() else "🤖 Ассистент"
            content = message.content[:100] + "..." if len(message.content) > 100 else message.content
            time_str = message.created_at.strftime("%H:%M:%S")
            
            table.add_row(time_str, role, content)
        
        console.print(table)
        
    except SessionManagerError as e:
        console.print(f"[red]❌ Ошибка получения истории: {e}")


def _document_check_mode(cli_instance, session_id):
    """Document compliance check mode."""
    console.print(Panel(
        "[bold yellow]Режим проверки документов[/bold yellow]\n\n"
        "Введите путь к файлу для проверки или вставьте текст документа.\n"
        "Для выхода введите 'exit'.",
        title="Проверка соответствия"
    ))
    
    while True:
        user_input = Prompt.ask("\n[bold blue]Файл или текст документа")
        
        if user_input.lower() in ['exit', 'quit']:
            break
        
        # Check if it's a file path
        if Path(user_input).exists():
            try:
                with open(user_input, 'r', encoding='utf-8') as f:
                    document_content = f.read()
            except Exception as e:
                console.print(f"[red]❌ Ошибка чтения файла: {e}")
                continue
        else:
            document_content = user_input
        
        if not document_content.strip():
            console.print("[yellow]Пустой документ")
            continue
        
        # Process document check
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Проверка соответствия...", total=None)
            
            try:
                response = cli_instance.query_processor.process_document_check(
                    document_content=document_content,
                    session_id=session_id
                )
                
                progress.update(task, description="Проверка завершена ✅")
                
            except QueryProcessorError as e:
                progress.update(task, description="Ошибка проверки ❌")
                console.print(f"[red]❌ Ошибка: {e}")
                continue
        
        # Display response
        _display_response(response)


def _display_response(response):
    """Display query response."""
    # Format response text as markdown
    response_md = Markdown(response.response)
    
    # Create panel with response
    panel_content = f"{response_md}"
    
    # Add metadata if available
    metadata_parts = []
    if response.confidence_score:
        confidence_percent = int(response.confidence_score * 100)
        metadata_parts.append(f"Уверенность: {confidence_percent}%")
    
    if response.processing_time:
        metadata_parts.append(f"Время: {response.processing_time:.2f}с")
    
    if response.relevant_documents:
        metadata_parts.append(f"Источники: {len(response.relevant_documents)} док.")
    
    if metadata_parts:
        panel_content += f"\n\n[dim]ℹ️ {' | '.join(metadata_parts)}[/dim]"
    
    console.print(Panel(panel_content, title="🤖 Ответ", border_style="blue"))


def _list_sessions(cli_instance):
    """List all sessions."""
    sessions = cli_instance.session_manager.list_sessions()
    
    if not sessions:
        console.print("[yellow]Нет активных сессий")
        return
    
    table = Table(title="Список сессий")
    table.add_column("ID", style="cyan")
    table.add_column("Создана", style="magenta")
    table.add_column("Обновлена", style="yellow")
    table.add_column("Сообщений", style="green")
    table.add_column("Статус", style="white")
    
    for session in sessions:
        created = session['created_at'][:19].replace('T', ' ')
        updated = session['updated_at'][:19].replace('T', ' ')
        status = "🟢 Активна" if session['is_active'] else "🔴 Неактивна"
        
        table.add_row(
            session['id'][:8] + "...",
            created,
            updated,
            str(session['message_count']),
            status
        )
    
    console.print(table)


def _list_documents(cli_instance):
    """List all documents."""
    documents = cli_instance.document_manager.list_documents()
    
    if not documents:
        console.print("[yellow]Нет загруженных документов")
        return
    
    table = Table(title="Список документов")
    table.add_column("ID", style="cyan")
    table.add_column("Название", style="white")
    table.add_column("Тип", style="magenta")
    table.add_column("Чанков", style="green")
    table.add_column("Загружен", style="yellow")
    
    for doc in documents:
        upload_date = doc['upload_date'][:19].replace('T', ' ') if doc['upload_date'] else "Неизвестно"
        
        table.add_row(
            doc['id'][:8] + "...",
            doc['title'][:30] + ("..." if len(doc['title']) > 30 else ""),
            doc['file_type'],
            str(doc['chunk_count']),
            upload_date
        )
    
    console.print(table)


def _show_document_info(cli_instance, doc_id):
    """Show document information."""
    doc_info = cli_instance.document_manager.get_document_info(doc_id)
    
    if not doc_info:
        console.print(f"[red]❌ Документ {doc_id} не найден")
        return
    
    info_text = f"""
[bold]ID:[/bold] {doc_info['id']}
[bold]Название:[/bold] {doc_info['title']}
[bold]Тип файла:[/bold] {doc_info['file_type']}
[bold]Количество чанков:[/bold] {doc_info['chunk_count']}
[bold]Дата загрузки:[/bold] {doc_info['upload_date']}
"""
    
    if doc_info.get('metadata'):
        info_text += f"\n[bold]Метаданные:[/bold]\n"
        for key, value in doc_info['metadata'].items():
            info_text += f"  {key}: {value}\n"
    
    console.print(Panel(info_text, title="Информация о документе"))


def _show_collection_stats(cli_instance):
    """Show collection statistics."""
    stats = cli_instance.document_manager.get_collection_stats()
    
    stats_text = f"""
[bold]Всего документов:[/bold] {stats.get('total_documents', 0)}
[bold]Всего чанков:[/bold] {stats.get('total_chunks', 0)}
[bold]Среднее чанков на документ:[/bold] {stats.get('average_chunks_per_document', 0):.1f}
"""
    
    console.print(Panel(stats_text, title="Статистика коллекции"))