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
                        trees.append({
                            'filename': file,
                            'created_at': created_at,
                            'query_type': query_type,
                            'display_name': f"{query_type} ({created_at})"
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
        st.error(f"Ошибка при загрузке данных дерева: {str(e)}")
        return None

def build_graph(tree_data):
    """Построение графа из данных дерева решений"""
    G = nx.DiGraph()
    
    def add_nodes_edges(node, parent=None):
        node_id = node.get('id', str(hash(node.get('label', ''))))
        prob = node.get('probability', 1.0)
        label = node.get('label', '')
        description = node.get('description', '')
        
        # Добавление узла
        G.add_node(node_id, label=label, probability=prob, description=description)
        
        # Добавление ребра от родителя
        if parent:
            G.add_edge(parent, node_id)
        
        # Рекурсивное добавление дочерних узлов
        for child in node.get('children', []):
            add_nodes_edges(child, node_id)
    
    # Начинаем с корневого узла
    if 'root' in tree_data:
        add_nodes_edges(tree_data['root'])
    else:
        st.warning("Неверный формат данных дерева решений. Отсутствует корневой узел.")
    
    return G

def get_node_color(probability):
    """Определение цвета узла по вероятности"""
    if probability >= 0.7:
        return '#2ECC71'  # Зеленый
    elif probability >= 0.4:
        return '#F1C40F'  # Желтый
    else:
        return '#E74C3C'  # Красный

def visualize_tree_plotly(G):
    """Визуализация дерева с помощью Plotly"""
    if not G or len(G.nodes()) == 0:
        st.warning("Граф пуст или не содержит узлов.")
        return None
    
    try:
        # Используем graphviz для расположения узлов
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    except Exception as e:
        st.warning(f"Ошибка при расчете позиций узлов: {str(e)}. Используем альтернативный метод.")
        pos = nx.spring_layout(G)
    
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    node_x = []
    node_y = []
    node_text = []
    node_size = []
    node_color = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        label = G.nodes[node].get('label', '')
        prob = G.nodes[node].get('probability', 0)
        desc = G.nodes[node].get('description', '')
        
        node_text.append(f"<b>{label}</b><br>Вероятность: {prob:.2f}<br>{desc}")
        node_size.append(25 + prob * 20)
        node_color.append(get_node_color(prob))

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        text=node_text,
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=2, color='#FFFFFF'))
    )

    # Добавляем метки узлов
    node_label_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='text',
        text=[G.nodes[node].get('label', '').split(' ')[0] for node in G.nodes()],
        textposition="middle center",
        textfont=dict(
            family="Arial",
            size=10,
            color="black"
        ),
        hoverinfo='none'
    )

    fig = go.Figure(data=[edge_trace, node_trace, node_label_trace],
                 layout=go.Layout(
                    title='<b>Дерево решений</b>',
                    titlefont_size=18,
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    height=800,
                    plot_bgcolor='rgba(250,250,250,1)')
                    )
    
    return fig

def calculate_paths(G, root_node=None):
    """Расчет всех путей в дереве от корня до листьев"""
    if not G or len(G.nodes()) == 0:
        return []
    
    # Если корневой узел не указан, берем первый узел без входящих ребер
    if root_node is None:
        root_candidates = [n for n in G.nodes() if G.in_degree(n) == 0]
        if not root_candidates:
            return []
        root_node = root_candidates[0]
    
    # Находим все листовые узлы (без исходящих ребер)
    leaf_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]
    
    # Если нет листовых узлов, возвращаем пустой список
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

# Боковая панель
st.sidebar.header("Настройки")

# Загрузка списка деревьев
trees = load_decision_trees()

if not trees:
    st.warning("Деревья решений не найдены. Проверьте путь к данным или создайте новые деревья.")
    st.info(f"Ожидаемый путь к данным: {os.path.abspath(DATA_PATH)}")
else:
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
        
        # Статистика
        stats = tree_data.get('statistics', {})
        if stats:
            st.sidebar.write(f"**Всего узлов:** {stats.get('total_nodes', 0)}")
            st.sidebar.write(f"**Всего путей:** {stats.get('total_paths', 0)}")
            st.sidebar.write(f"**Глубина дерева:** {stats.get('max_depth', 0)}")
        
        # Настройки визуализации
        st.sidebar.subheader("Настройки визуализации")
        show_labels = st.sidebar.checkbox("Показывать метки узлов", value=True)
        
        # Построение графа
        G = build_graph(tree_data)
        
        if G and len(G.nodes()) > 0:
            # Визуализация
            fig = visualize_tree_plotly(G)
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

# Информация о приложении
st.sidebar.markdown("---")
st.sidebar.info(
    """
    **О приложении**
    
    Визуализация деревьев решений AI агента для анализа процесса принятия решений.
    
    Версия: 1.0.0
    """
)