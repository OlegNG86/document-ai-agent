import streamlit as st
import networkx as nx
import json
import os
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import io

# Настройка страницы
st.set_page_config(
    page_title="Визуализация деревьев решений AI агента",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Путь к данным деревьев решений
DATA_PATH = os.environ.get("DECISION_TREE_DATA_PATH", "./data/decision_trees")

# Если запускаем из корневой директории проекта, корректируем путь
if not os.path.exists(DATA_PATH) and os.path.exists("./visualization/data/decision_trees"):
    DATA_PATH = "./visualization/data/decision_trees"

# Функции для работы с деревьями решений
def load_decision_trees():
    """Загрузка доступных деревьев решений"""
    trees = []
    if os.path.exists(DATA_PATH):
        for file in os.listdir(DATA_PATH):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(DATA_PATH, file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        created_at = data.get('timestamp', 'Неизвестно')
                        query_type = data.get('query_type', 'Неизвестно')
                        query_text = data.get('query_text', 'Неизвестно')
                        trees.append({
                            'filename': file,
                            'created_at': created_at,
                            'query_type': query_type,
                            'query_text': query_text,
                            'display_name': f"{query_type} - {query_text[:50]}..." if len(query_text) > 50 else f"{query_type} - {query_text}"
                        })
                except Exception as e:
                    st.error(f"Ошибка при загрузке {file}: {str(e)}")
    
    # Сортировка по времени создания (новые сверху)
    return sorted(trees, key=lambda x: x.get('created_at', ''), reverse=True)

def load_tree_data(filename):
    """Загрузка данных дерева решений из JSON"""
    try:
        with open(os.path.join(DATA_PATH, filename), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Ошибка при загрузке дерева: {str(e)}")
        return None

def build_graph(tree_data):
    """Построение графа NetworkX из данных дерева решений"""
    G = nx.DiGraph()
    
    def add_node_recursive(node_data, parent_id=None):
        if not node_data:
            return
        
        node_id = node_data.get('id', 'unknown')
        label = node_data.get('label', 'Без названия')
        probability = node_data.get('probability', 1.0)
        description = node_data.get('description', '')
        
        G.add_node(node_id, 
                  label=label, 
                  probability=probability, 
                  description=description)
        
        if parent_id:
            G.add_edge(parent_id, node_id)
        
        # Рекурсивно добавляем дочерние узлы
        children = node_data.get('children', [])
        for child in children:
            add_node_recursive(child, node_id)
    
    root = tree_data.get('root', {})
    add_node_recursive(root)
    
    return G

def get_node_color(probability):
    """Получение цвета узла в зависимости от вероятности"""
    if probability >= 0.8:
        return '#2E8B57'  # Зеленый
    elif probability >= 0.6:
        return '#FFD700'  # Желтый
    elif probability >= 0.4:
        return '#FF8C00'  # Оранжевый
    else:
        return '#DC143C'  # Красный

def visualize_tree_plotly(G, color_scheme='default', show_probabilities=True, layout_type='hierarchical'):
    """Создание интерактивной визуализации дерева с помощью Plotly"""
    if not G or len(G.nodes()) == 0:
        return None
    
    try:
        # Выбор алгоритма расположения узлов
        if layout_type == 'hierarchical':
            try:
                pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
            except Exception:
                pos = nx.spring_layout(G, k=3, iterations=50)
        elif layout_type == 'circular':
            pos = nx.circular_layout(G)
        elif layout_type == 'spring':
            pos = nx.spring_layout(G, k=3, iterations=50)
        else:
            pos = nx.spring_layout(G, k=3, iterations=50)
    except Exception:
        pos = nx.spring_layout(G, k=3, iterations=50)
    
    # Подготовка данных для узлов
    node_x = []
    node_y = []
    node_text = []
    node_colors = []
    node_sizes = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        node_data = G.nodes[node]
        label = node_data.get('label', 'Без названия')
        probability = node_data.get('probability', 1.0)
        description = node_data.get('description', '')
        
        # Текст для отображения
        if show_probabilities:
            display_text = f"{label}<br>P: {probability:.3f}"
        else:
            display_text = label
            
        node_text.append(f"{display_text}<br>{description}")
        
        # Цвет узла
        if color_scheme == 'probability':
            node_colors.append(probability)
        else:
            node_colors.append(get_node_color(probability))
        
        # Размер узла
        node_sizes.append(15 + probability * 20)
    
    # Подготовка данных для рёбер
    edge_x = []
    edge_y = []
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    # Создание графика
    fig = go.Figure()
    
    # Добавление рёбер
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='none',
        mode='lines',
        showlegend=False
    ))
    
    # Добавление узлов
    if color_scheme == 'probability':
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=[G.nodes[node].get('label', '') for node in G.nodes()],
            textposition="middle center",
            hovertext=node_text,
            marker=dict(
                size=node_sizes,
                color=node_colors,
                colorscale='RdYlGn',
                cmin=0,
                cmax=1,
                colorbar=dict(title="Вероятность"),
                line=dict(width=2, color='black')
            ),
            showlegend=False
        ))
    else:
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=[G.nodes[node].get('label', '') for node in G.nodes()],
            textposition="middle center",
            hovertext=node_text,
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=2, color='black')
            ),
            showlegend=False
        ))
    
    # Настройка макета
    fig.update_layout(
        title="Дерево решений",
        titlefont_size=16,
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20,l=5,r=5,t=40),
        annotations=[ dict(
            text="",
            showarrow=False,
            xref="paper", yref="paper",
            x=0.005, y=-0.002 ) ],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white'
    )
    
    return fig

def calculate_paths(G):
    """Расчет всех путей от корня до листьев"""
    if not G or len(G.nodes()) == 0:
        return []
    
    # Находим корневой узел (узел без входящих рёбер)
    root_nodes = [n for n in G.nodes() if G.in_degree(n) == 0]
    if not root_nodes:
        return []
    
    root_node = root_nodes[0]
    
    # Находим листовые узлы (узлы без исходящих рёбер)
    leaf_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]
    if not leaf_nodes:
        return []
    
    # Находим все пути от корня до листьев
    all_paths = []
    for leaf in leaf_nodes:
        try:
            for path in nx.all_simple_paths(G, source=root_node, target=leaf):
                path_info = {
                    "nodes": path,
                    "labels": [G.nodes[n].get('label', '') for n in path],
                    "probabilities": [G.nodes[n].get('probability', 1.0) for n in path],
                    "total_probability": 1.0
                }
                
                # Расчет общей вероятности пути
                for prob in path_info["probabilities"]:
                    path_info["total_probability"] *= prob
                
                all_paths.append(path_info)
        except nx.NetworkXNoPath:
            continue
    
    # Сортировка путей по вероятности (от высокой к низкой)
    return sorted(all_paths, key=lambda x: x["total_probability"], reverse=True)

def compare_trees(tree1_data, tree2_data):
    """Сравнение двух деревьев решений"""
    comparison = {
        'basic_stats': {},
        'structural_differences': {},
        'common_paths': [],
        'unique_paths_tree1': [],
        'unique_paths_tree2': []
    }
    
    # Базовая статистика
    stats1 = tree1_data.get('statistics', {})
    stats2 = tree2_data.get('statistics', {})
    
    comparison['basic_stats'] = {
        'tree1': {
            'nodes': stats1.get('total_nodes', 0),
            'paths': stats1.get('total_paths', 0),
            'depth': stats1.get('max_depth', 0),
            'query_type': tree1_data.get('query_type', 'unknown')
        },
        'tree2': {
            'nodes': stats2.get('total_nodes', 0),
            'paths': stats2.get('total_paths', 0),
            'depth': stats2.get('max_depth', 0),
            'query_type': tree2_data.get('query_type', 'unknown')
        }
    }
    
    # Построение графов для анализа путей
    G1 = build_graph(tree1_data)
    G2 = build_graph(tree2_data)
    
    paths1 = calculate_paths(G1)
    paths2 = calculate_paths(G2)
    
    # Сравнение путей (упрощенное - по меткам узлов)
    paths1_labels = [" → ".join(path["labels"]) for path in paths1]
    paths2_labels = [" → ".join(path["labels"]) for path in paths2]
    
    common_paths = list(set(paths1_labels) & set(paths2_labels))
    unique_paths_tree1 = list(set(paths1_labels) - set(paths2_labels))
    unique_paths_tree2 = list(set(paths2_labels) - set(paths1_labels))
    
    comparison['common_paths'] = common_paths
    comparison['unique_paths_tree1'] = unique_paths_tree1
    comparison['unique_paths_tree2'] = unique_paths_tree2
    
    return comparison

def export_graph_to_image(G, format='png', dpi=300):
    """Экспорт графа в изображение"""
    plt.figure(figsize=(12, 8), dpi=dpi)
    
    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    except Exception:
        pos = nx.spring_layout(G)
    
    # Рисуем узлы с цветами в зависимости от вероятности
    node_colors = [get_node_color(G.nodes[n].get('probability', 0)) for n in G.nodes()]
    node_sizes = [300 + G.nodes[n].get('probability', 0) * 500 for n in G.nodes()]
    
    nx.draw(G, pos, with_labels=True, node_color=node_colors, 
            node_size=node_sizes, font_size=8, font_weight='bold',
            edge_color='gray', arrows=True)
    
    # Добавляем заголовок
    plt.title("Дерево решений", fontsize=16)
    
    # Сохраняем в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format=format, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

# Основной интерфейс
st.title("🌳 Визуализация деревьев решений AI агента")
st.write("Интерактивный просмотр и анализ деревьев принятия решений")

# Создаем вкладки
tab1, tab2, tab3 = st.tabs(["📊 Просмотр дерева", "🔄 Сравнение деревьев", "⚙️ Настройки"])

# Загрузка списка деревьев
trees = load_decision_trees()

if not trees:
    st.warning("Деревья решений не найдены. Проверьте путь к данным или создайте новые деревья.")
    st.info(f"Ожидаемый путь к данным: {os.path.abspath(DATA_PATH)}")
else:
    # Вкладка 1: Просмотр дерева
    with tab1:
        # Боковая панель для первой вкладки
        st.sidebar.header("Настройки просмотра")
        
        # Фильтр по типу запроса
        query_types = list(set(tree['query_type'] for tree in trees))
        selected_type = st.sidebar.selectbox(
            "Фильтр по типу запроса",
            ["Все"] + query_types
        )
        
        # Фильтрация деревьев по типу
        filtered_trees = trees
        if selected_type != "Все":
            filtered_trees = [tree for tree in trees if tree['query_type'] == selected_type]
        
        # Выбор дерева
        tree_options = {tree['display_name']: tree['filename'] for tree in filtered_trees}
        selected_tree_name = st.sidebar.selectbox(
            "Выберите дерево решений",
            list(tree_options.keys())
        )
        
        selected_tree_filename = tree_options[selected_tree_name]
        
        # Загрузка данных выбранного дерева
        tree_data = load_tree_data(selected_tree_filename)
        
        if tree_data:
            # Метаданные дерева
            st.sidebar.subheader("Информация о дереве")
            st.sidebar.write(f"**Тип запроса:** {tree_data.get('query_type', 'Неизвестно')}")
            st.sidebar.write(f"**Создано:** {tree_data.get('timestamp', 'Неизвестно')}")
            st.sidebar.write(f"**Запрос:** {tree_data.get('query_text', 'Неизвестно')}")
            
            # Статистика
            stats = tree_data.get('statistics', {})
            if stats:
                st.sidebar.write(f"**Всего узлов:** {stats.get('total_nodes', 0)}")
                st.sidebar.write(f"**Всего путей:** {stats.get('total_paths', 0)}")
                st.sidebar.write(f"**Глубина дерева:** {stats.get('max_depth', 0)}")
            
            # Настройки визуализации
            st.sidebar.subheader("Настройки визуализации")
            color_scheme = st.sidebar.selectbox(
                "Цветовая схема",
                ["default", "probability"],
                format_func=lambda x: "По умолчанию" if x == "default" else "По вероятности"
            )
            show_probabilities = st.sidebar.checkbox("Показывать вероятности", value=True)
            layout_type = st.sidebar.selectbox(
                "Тип макета",
                ["hierarchical", "spring", "circular"],
                format_func=lambda x: {"hierarchical": "Иерархический", "spring": "Пружинный", "circular": "Круговой"}[x]
            )
            
            # Построение графа
            G = build_graph(tree_data)
            
            if G and len(G.nodes()) > 0:
                # Визуализация
                fig = visualize_tree_plotly(G, color_scheme, show_probabilities, layout_type)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                
                # Экспорт
                st.sidebar.subheader("Экспорт")
                export_format = st.sidebar.selectbox(
                    "Формат экспорта",
                    ["PNG", "SVG", "PDF"]
                )
                
                if st.sidebar.button("Экспортировать"):
                    with st.spinner(f"Экспорт в {export_format}..."):
                        try:
                            buf = export_graph_to_image(G, format=export_format.lower())
                            st.sidebar.download_button(
                                label=f"Скачать {export_format}",
                                data=buf,
                                file_name=f"decision_tree_{tree_data.get('query_type', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format.lower()}",
                                mime=f"image/{export_format.lower()}"
                            )
                        except Exception as e:
                            st.sidebar.error(f"Ошибка при экспорте: {str(e)}")
                
                # Анализ путей
                st.header("Анализ путей принятия решений")
                
                paths = calculate_paths(G)
                if paths:
                    path_data = []
                    for i, path in enumerate(paths):
                        path_data.append({
                            "№": i + 1,
                            "Путь": " → ".join(path["labels"]),
                            "Вероятность": f"{path['total_probability']:.4f}",
                            "Длина": len(path["nodes"])
                        })
                    
                    st.dataframe(pd.DataFrame(path_data), use_container_width=True)
                    
                    # Визуализация вероятностей путей
                    if len(paths) > 0:
                        top_n = min(10, len(paths))
                        st.subheader(f"Топ-{top_n} путей по вероятности")
                        
                        top_paths = paths[:top_n]
                        fig = go.Figure(data=[
                            go.Bar(
                                x=[f"Путь {i+1}" for i in range(len(top_paths))],
                                y=[path["total_probability"] for path in top_paths],
                                marker_color=[
                                    get_node_color(path["total_probability"]) 
                                    for path in top_paths
                                ]
                            )
                        ])
                        
                        fig.update_layout(
                            title="Вероятности путей принятия решений",
                            xaxis_title="Путь",
                            yaxis_title="Вероятность",
                            yaxis=dict(range=[0, 1])
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Не удалось рассчитать пути для данного дерева.")
            else:
                st.error("Не удалось построить граф из данных дерева решений.")
        else:
            st.error("Не удалось загрузить данные выбранного дерева решений.")
    
    # Вкладка 2: Сравнение деревьев
    with tab2:
        st.header("🔄 Сравнение деревьев решений")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Первое дерево")
            tree_options_1 = {tree['display_name']: tree['filename'] for tree in trees}
            selected_tree_1 = st.selectbox(
                "Выберите первое дерево",
                list(tree_options_1.keys()),
                key="tree1"
            )
            
        with col2:
            st.subheader("Второе дерево")
            tree_options_2 = {tree['display_name']: tree['filename'] for tree in trees}
            selected_tree_2 = st.selectbox(
                "Выберите второе дерево",
                list(tree_options_2.keys()),
                key="tree2"
            )
        
        if selected_tree_1 and selected_tree_2 and selected_tree_1 != selected_tree_2:
            tree_data_1 = load_tree_data(tree_options_1[selected_tree_1])
            tree_data_2 = load_tree_data(tree_options_2[selected_tree_2])
            
            if tree_data_1 and tree_data_2:
                # Сравнение деревьев
                comparison = compare_trees(tree_data_1, tree_data_2)
                
                # Базовая статистика
                st.subheader("📊 Базовая статистика")
                
                stats_df = pd.DataFrame({
                    'Метрика': ['Количество узлов', 'Количество путей', 'Глубина дерева', 'Тип запроса'],
                    'Первое дерево': [
                        comparison['basic_stats']['tree1']['nodes'],
                        comparison['basic_stats']['tree1']['paths'],
                        comparison['basic_stats']['tree1']['depth'],
                        comparison['basic_stats']['tree1']['query_type']
                    ],
                    'Второе дерево': [
                        comparison['basic_stats']['tree2']['nodes'],
                        comparison['basic_stats']['tree2']['paths'],
                        comparison['basic_stats']['tree2']['depth'],
                        comparison['basic_stats']['tree2']['query_type']
                    ]
                })
                
                st.dataframe(stats_df, use_container_width=True)
                
                # Анализ путей
                st.subheader("🛤️ Анализ путей")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Общие пути", len(comparison['common_paths']))
                    
                with col2:
                    st.metric("Уникальные пути (дерево 1)", len(comparison['unique_paths_tree1']))
                    
                with col3:
                    st.metric("Уникальные пути (дерево 2)", len(comparison['unique_paths_tree2']))
                
                # Детальное сравнение путей
                if comparison['common_paths']:
                    st.subheader("🤝 Общие пути")
                    for i, path in enumerate(comparison['common_paths'][:10], 1):
                        st.write(f"{i}. {path}")
                
                if comparison['unique_paths_tree1']:
                    st.subheader("🔵 Уникальные пути первого дерева")
                    for i, path in enumerate(comparison['unique_paths_tree1'][:10], 1):
                        st.write(f"{i}. {path}")
                
                if comparison['unique_paths_tree2']:
                    st.subheader("🔴 Уникальные пути второго дерева")
                    for i, path in enumerate(comparison['unique_paths_tree2'][:10], 1):
                        st.write(f"{i}. {path}")
                
                # Визуализация сравнения
                st.subheader("📈 Визуальное сравнение")
                
                # Создаем графы для визуализации
                G1 = build_graph(tree_data_1)
                G2 = build_graph(tree_data_2)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Первое дерево**")
                    fig1 = visualize_tree_plotly(G1)
                    if fig1:
                        st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    st.write("**Второе дерево**")
                    fig2 = visualize_tree_plotly(G2)
                    if fig2:
                        st.plotly_chart(fig2, use_container_width=True)
            else:
                st.error("Не удалось загрузить данные одного или обоих деревьев.")
        else:
            st.info("Выберите два разных дерева для сравнения.")
    
    # Вкладка 3: Настройки
    with tab3:
        st.header("⚙️ Настройки приложения")
        
        # Настройки отображения
        st.subheader("🎨 Настройки отображения")
        
        # Цветовые схемы
        st.write("**Доступные цветовые схемы:**")
        st.write("- **По умолчанию**: Фиксированные цвета в зависимости от вероятности")
        st.write("- **По вероятности**: Градиентная шкала от красного к зеленому")
        
        # Типы макетов
        st.write("**Доступные типы макетов:**")
        st.write("- **Иерархический**: Древовидная структура сверху вниз")
        st.write("- **Пружинный**: Автоматическое размещение с отталкиванием")
        st.write("- **Круговой**: Размещение узлов по кругу")
        
        # Настройки экспорта
        st.subheader("📤 Настройки экспорта")
        st.write("**Поддерживаемые форматы:**")
        st.write("- **PNG**: Растровое изображение высокого качества")
        st.write("- **SVG**: Векторное изображение для масштабирования")
        st.write("- **PDF**: Документ для печати")
        
        # Информация о данных
        st.subheader("📁 Информация о данных")
        st.write(f"**Путь к данным:** `{os.path.abspath(DATA_PATH)}`")
        st.write(f"**Всего деревьев:** {len(trees)}")
        
        # Статистика по типам запросов
        if trees:
            query_type_counts = {}
            for tree in trees:
                query_type = tree['query_type']
                query_type_counts[query_type] = query_type_counts.get(query_type, 0) + 1
            
            st.write("**Распределение по типам запросов:**")
            for query_type, count in query_type_counts.items():
                st.write(f"- {query_type}: {count}")
        
        # Очистка кэша
        st.subheader("🧹 Управление кэшем")
        if st.button("Очистить кэш приложения"):
            st.cache_data.clear()
            st.success("Кэш очищен!")
        
        # Информация о версии
        st.subheader("ℹ️ О приложении")
        st.write("**Версия:** 2.0.0")
        st.write("**Функции:**")
        st.write("- Интерактивная визуализация деревьев решений")
        st.write("- Сравнение деревьев решений")
        st.write("- Анализ путей принятия решений")
        st.write("- Экспорт в различные форматы")
        st.write("- Настраиваемые цветовые схемы и макеты")

# Информация о приложении в боковой панели
st.sidebar.markdown("---")
st.sidebar.info(
    """
    **О приложении**
    
    Визуализация деревьев решений AI агента для анализа процесса принятия решений.
    
    Версия: 2.0.0
    """
)