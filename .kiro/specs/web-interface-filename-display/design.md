# Design Document

## Overview

Модификация веб-интерфейса визуализации деревьев решений для отображения имен JSON файлов в выпадающем списке вместо описательных названий. Изменения затронут функцию `load_decision_trees()` в файле `visualization/app.py`.

## Architecture

### Current Architecture

```
visualization/app.py
├── load_decision_trees() - загружает файлы и создает описательные названия
├── Streamlit UI - отображает список с описательными названиями
└── load_tree_data() - загружает данные выбранного файла
```

### Modified Architecture

```
visualization/app.py
├── load_decision_trees() - загружает файлы и возвращает имена файлов
├── Streamlit UI - отображает список с именами файлов
└── load_tree_data() - загружает данные выбранного файла (без изменений)
```

## Components and Interfaces

### Modified Function: load_decision_trees()

**Current Implementation:**

```python
def load_decision_trees():
    trees = []
    for file in os.listdir(DATA_PATH):
        if file.endswith('.json'):
            # ... load data ...
            trees.append({
                'filename': file,
                'display_name': f"{query_type} - {query_text[:50]}..." if len(query_text) > 50 else f"{query_type} - {query_text}"
            })
    return sorted(trees, key=lambda x: x.get('created_at', ''), reverse=True)
```

**New Implementation:**

```python
def load_decision_trees():
    trees = []
    for file in os.listdir(DATA_PATH):
        if file.endswith('.json'):
            # ... load data ...
            trees.append({
                'filename': file,
                'display_name': file,  # Use filename as display name
                'created_at': created_at,
                'query_type': query_type,
                'query_text': query_text
            })
    return sorted(trees, key=lambda x: x.get('created_at', ''), reverse=True)
```

### Modified UI Component: Tree Selection

**Current Implementation:**

```python
tree_options = {tree['display_name']: tree['filename'] for tree in filtered_trees}
selected_tree_name = st.sidebar.selectbox(
    "Выберите дерево решений",
    list(tree_options.keys())
)
```

**New Implementation:**

```python
tree_options = {tree['display_name']: tree['filename'] for tree in filtered_trees}
selected_tree_name = st.sidebar.selectbox(
    "Выберите дерево решений",
    list(tree_options.keys())
)
```

## Data Models

### Tree Data Structure

```python
{
    'filename': str,           # Имя JSON файла
    'display_name': str,       # Имя для отображения (теперь = filename)
    'created_at': str,         # Время создания
    'query_type': str,         # Тип запроса для фильтрации
    'query_text': str          # Текст запроса (сохраняется для совместимости)
}
```

## Error Handling

### File Loading Errors

- Сохранить существующую обработку ошибок при загрузке JSON файлов
- Продолжить показ ошибок через `st.error()` для проблемных файлов

### Empty File List

- Сохранить существующее предупреждение когда файлы не найдены
- Показать путь к данным для диагностики

## Testing Strategy

### Manual Testing

1. **Filename Display Test**

   - Создать несколько файлов с разными именами
   - Проверить, что в списке отображаются точные имена файлов
   - Убедиться, что файлы с новым форматом (`c_check_*`) отображаются корректно

2. **Filtering Test**

   - Проверить фильтрацию по типу запроса
   - Убедиться, что фильтр "Все" показывает все файлы
   - Проверить, что фильтрация работает с именами файлов

3. **Sorting Test**

   - Создать файлы в разное время
   - Проверить, что новые файлы отображаются сверху
   - Убедиться в корректной сортировке

4. **Functionality Test**
   - Выбрать файл из списка
   - Проверить, что дерево загружается и отображается корректно
   - Убедиться, что все функции визуализации работают

### Edge Cases

- Файлы с длинными именами
- Файлы с специальными символами в именах
- Файлы без метаданных timestamp
- Пустая директория с файлами

## Implementation Notes

### Backward Compatibility

- Сохранить структуру данных для совместимости
- Не изменять логику загрузки файлов
- Сохранить все существующие функции

### Performance Considerations

- Изменения не влияют на производительность
- Загрузка файлов остается такой же
- UI рендеринг не изменяется значительно

### User Experience

- Пользователи смогут быстро находить файлы по именам
- Особенно полезно для файлов с новым форматом именования
- Сохраняется привычный интерфейс
