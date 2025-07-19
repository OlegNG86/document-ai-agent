"""CLI commands for the AI agent."""

import os
import sys
import click
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

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
@click.argument('path', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True, help='Рекурсивный поиск файлов в подпапках')
@click.option('--pattern', '-p', default='*.txt,*.md,*.docx', help='Шаблон файлов для загрузки (по умолчанию: *.txt,*.md,*.docx)')
@click.option('--metadata', '-m', multiple=True, help='Общие метаданные для всех файлов в формате key=value')
@click.option('--skip-errors', is_flag=True, help='Продолжить загрузку при ошибках в отдельных файлах')
@click.option('--dry-run', is_flag=True, help='Показать список файлов без загрузки')
@click.pass_context
def batch_upload(ctx, path, recursive, pattern, metadata, skip_errors, dry_run):
    """Загрузить несколько документов одновременно из папки или по списку файлов."""
    cli_instance = ctx.obj['cli']
    
    try:
        # Parse common metadata
        metadata_dict = {}
        for item in metadata:
            if '=' in item:
                key, value = item.split('=', 1)
                metadata_dict[key] = value
        
        # Find files to upload
        files_to_upload = _find_files_for_batch_upload(path, pattern, recursive)
        
        if not files_to_upload:
            console.print("[yellow]⚠️ Не найдено файлов для загрузки")
            return
        
        # Show files that will be uploaded
        console.print(f"[blue]📁 Найдено файлов для загрузки: {len(files_to_upload)}")
        
        if dry_run:
            _show_batch_upload_preview(files_to_upload)
            return
        
        # Confirm batch upload
        if not Confirm.ask(f"Загрузить {len(files_to_upload)} файлов?"):
            console.print("[yellow]Загрузка отменена")
            return
        
        # Perform batch upload
        results = _perform_batch_upload(cli_instance, files_to_upload, metadata_dict, skip_errors)
        
        # Show results
        _show_batch_upload_results(results)
        
    except Exception as e:
        console.print(f"[red]❌ Ошибка batch загрузки: {e}")
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
                file_path = Path(user_input)
                if file_path.suffix.lower() == '.docx':
                    if DocxDocument is None:
                        console.print("[red]❌ Библиотека python-docx не установлена")
                        continue
                    doc = DocxDocument(file_path)
                    document_content = '\n'.join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
                else:
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
    # Create markdown content
    response_md = Markdown(response.response)
    
    # Add metadata if available
    metadata_parts = []
    if response.confidence_score:
        confidence_percent = int(response.confidence_score * 100)
        metadata_parts.append(f"Уверенность: {confidence_percent}%")
    
    if response.processing_time:
        metadata_parts.append(f"Время: {response.processing_time:.2f}с")
    
    if response.relevant_documents:
        metadata_parts.append(f"Источники: {len(response.relevant_documents)} док.")
    
    # Display response with proper markdown rendering
    console.print(Panel(response_md, title="🤖 Ответ", border_style="blue"))
    
    # Display metadata separately if available
    if metadata_parts:
        console.print(f"[dim]ℹ️ {' | '.join(metadata_parts)}[/dim]")


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


def _find_files_for_batch_upload(path: str, pattern: str, recursive: bool) -> List[Path]:
    """Find files for batch upload based on pattern and recursion settings.
    
    Args:
        path: Path to search (file or directory).
        pattern: File patterns to match (comma-separated).
        recursive: Whether to search recursively.
        
    Returns:
        List of file paths to upload.
    """
    path_obj = Path(path)
    files_to_upload = []
    
    # Parse patterns
    patterns = [p.strip() for p in pattern.split(',')]
    
    if path_obj.is_file():
        # Single file provided
        files_to_upload.append(path_obj)
    elif path_obj.is_dir():
        # Directory provided - find matching files
        for pattern_str in patterns:
            if recursive:
                files_to_upload.extend(path_obj.rglob(pattern_str))
            else:
                files_to_upload.extend(path_obj.glob(pattern_str))
    
    # Remove duplicates and sort
    files_to_upload = sorted(list(set(files_to_upload)))
    
    # Filter out non-files (in case glob matched directories)
    files_to_upload = [f for f in files_to_upload if f.is_file()]
    
    return files_to_upload


def _show_batch_upload_preview(files: List[Path]) -> None:
    """Show preview of files that will be uploaded.
    
    Args:
        files: List of file paths.
    """
    table = Table(title="Предварительный просмотр загрузки")
    table.add_column("№", style="cyan", width=4)
    table.add_column("Файл", style="white")
    table.add_column("Размер", style="green", width=10)
    table.add_column("Тип", style="magenta", width=8)
    
    for i, file_path in enumerate(files, 1):
        try:
            size = file_path.stat().st_size
            size_str = _format_file_size(size)
        except:
            size_str = "Неизвестно"
        
        table.add_row(
            str(i),
            str(file_path),
            size_str,
            file_path.suffix[1:] if file_path.suffix else "unknown"
        )
    
    console.print(table)


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format.
    
    Args:
        size_bytes: Size in bytes.
        
    Returns:
        Formatted size string.
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _perform_batch_upload(
    cli_instance, 
    files: List[Path], 
    common_metadata: Dict[str, str], 
    skip_errors: bool
) -> Dict[str, Any]:
    """Perform batch upload of files with progress tracking.
    
    Args:
        cli_instance: CLI instance with document manager.
        files: List of files to upload.
        common_metadata: Common metadata for all files.
        skip_errors: Whether to continue on individual file errors.
        
    Returns:
        Results dictionary with success/failure counts and details.
    """
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    
    results = {
        'total_files': len(files),
        'successful': [],
        'failed': [],
        'skipped': []
    }
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        upload_task = progress.add_task(
            "Загрузка файлов...", 
            total=len(files)
        )
        
        for i, file_path in enumerate(files):
            progress.update(
                upload_task, 
                description=f"Загрузка: {file_path.name}",
                completed=i
            )
            
            try:
                # Prepare metadata for this file
                file_metadata = common_metadata.copy()
                file_metadata['original_path'] = str(file_path)
                file_metadata['batch_upload'] = 'true'
                
                # Upload document
                doc_id = cli_instance.document_manager.upload_document(
                    file_path=str(file_path),
                    metadata=file_metadata
                )
                
                results['successful'].append({
                    'file': str(file_path),
                    'doc_id': doc_id,
                    'size': file_path.stat().st_size
                })
                
            except Exception as e:
                error_info = {
                    'file': str(file_path),
                    'error': str(e)
                }
                
                if skip_errors:
                    results['failed'].append(error_info)
                    logger.warning(f"Failed to upload {file_path}: {e}")
                else:
                    results['failed'].append(error_info)
                    progress.update(upload_task, description=f"Ошибка: {file_path.name}")
                    break
        
        progress.update(
            upload_task, 
            completed=len(files),
            description="Загрузка завершена"
        )
    
    return results


def _show_batch_upload_results(results: Dict[str, Any]) -> None:
    """Show results of batch upload operation.
    
    Args:
        results: Results dictionary from batch upload.
    """
    total = results['total_files']
    successful = len(results['successful'])
    failed = len(results['failed'])
    
    # Summary panel
    if failed == 0:
        status_color = "green"
        status_icon = "✅"
        status_text = "Все файлы загружены успешно"
    elif successful == 0:
        status_color = "red"
        status_icon = "❌"
        status_text = "Не удалось загрузить ни одного файла"
    else:
        status_color = "yellow"
        status_icon = "⚠️"
        status_text = "Загрузка завершена с ошибками"
    
    summary_text = f"""
[bold]Всего файлов:[/bold] {total}
[bold green]Успешно:[/bold green] {successful}
[bold red]Ошибки:[/bold red] {failed}
"""
    
    console.print(Panel(
        summary_text,
        title=f"{status_icon} {status_text}",
        border_style=status_color
    ))
    
    # Show successful uploads
    if results['successful']:
        success_table = Table(title="Успешно загруженные файлы")
        success_table.add_column("Файл", style="white")
        success_table.add_column("ID документа", style="cyan")
        success_table.add_column("Размер", style="green")
        
        for item in results['successful']:
            success_table.add_row(
                Path(item['file']).name,
                item['doc_id'][:8] + "...",
                _format_file_size(item['size'])
            )
        
        console.print(success_table)
    
    # Show failed uploads
    if results['failed']:
        error_table = Table(title="Ошибки загрузки")
        error_table.add_column("Файл", style="white")
        error_table.add_column("Ошибка", style="red")
        
        for item in results['failed']:
            error_table.add_row(
                Path(item['file']).name,
                item['error'][:50] + ("..." if len(item['error']) > 50 else "")
            )
        
        console.print(error_table)