"""Decision tree visualization system for AI agent responses."""

import os
import uuid
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


logger = logging.getLogger(__name__)


class DetailLevel(Enum):
    """Detail levels for decision tree visualization."""
    BRIEF = "brief"
    FULL = "full"
    EXTENDED = "extended"


class QueryType(Enum):
    """Types of queries for decision tree categorization."""
    GENERAL_QUESTION = "general_question"
    DOCUMENT_SEARCH = "document_search"
    COMPLIANCE_CHECK = "compliance_check"
    NORMATIVE_LOOKUP = "normative_lookup"
    COMPARISON = "comparison"
    UNKNOWN = "unknown"


@dataclass
class DecisionNode:
    """Represents a node in the decision tree."""
    id: str
    label: str
    probability: float
    description: str = ""
    children: List['DecisionNode'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_child(self, child: 'DecisionNode') -> None:
        """Add a child node."""
        self.children.append(child)
    
    def normalize_children_probabilities(self) -> None:
        """Normalize probabilities of child nodes to sum to 1.0."""
        if not self.children:
            return
        
        total_prob = sum(child.probability for child in self.children)
        if total_prob > 0:
            for child in self.children:
                child.probability = child.probability / total_prob
    
    def get_path_probability(self, path: List[str]) -> float:
        """Calculate probability for a specific path through the tree."""
        if not path:
            return self.probability
        
        current_step = path[0]
        remaining_path = path[1:]
        
        for child in self.children:
            if child.id == current_step or child.label == current_step:
                return self.probability * child.get_path_probability(remaining_path)
        
        return 0.0
    
    def is_leaf(self) -> bool:
        """Check if this is a leaf node."""
        return len(self.children) == 0


@dataclass
class DecisionTree:
    """Represents a complete decision tree."""
    id: str
    root: DecisionNode
    query_type: QueryType
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_all_paths(self) -> List[List[DecisionNode]]:
        """Get all paths from root to leaves."""
        paths = []
        
        def traverse(node: DecisionNode, current_path: List[DecisionNode]):
            current_path.append(node)
            
            if node.is_leaf():
                paths.append(current_path.copy())
            else:
                for child in node.children:
                    traverse(child, current_path)
            
            current_path.pop()
        
        traverse(self.root, [])
        return paths
    
    def get_path_by_labels(self, labels: List[str]) -> Optional[List[DecisionNode]]:
        """Get path by following node labels."""
        path = []
        current = self.root
        
        for label in labels:
            path.append(current)
            found = False
            
            for child in current.children:
                if child.label == label:
                    current = child
                    found = True
                    break
            
            if not found:
                return None
        
        path.append(current)
        return path
    
    def calculate_path_probability(self, path: List[DecisionNode]) -> float:
        """Calculate total probability for a path."""
        if not path:
            return 0.0
        
        total_prob = 1.0
        for node in path:
            total_prob *= node.probability
        
        return total_prob


class DecisionTreeBuilder:
    """Builder for creating decision trees."""
    
    def __init__(self):
        """Initialize the builder."""
        self.trees: Dict[str, DecisionTree] = {}
    
    def create_tree(self, query_type: QueryType, root_label: str = "Start") -> DecisionTree:
        """Create a new decision tree.
        
        Args:
            query_type: Type of query this tree represents.
            root_label: Label for the root node.
            
        Returns:
            New decision tree instance.
        """
        tree_id = str(uuid.uuid4())
        root_node = DecisionNode(
            id=str(uuid.uuid4()),
            label=root_label,
            probability=1.0,
            description=f"Root node for {query_type.value} query"
        )
        
        tree = DecisionTree(
            id=tree_id,
            root=root_node,
            query_type=query_type
        )
        
        self.trees[tree_id] = tree
        return tree
    
    def add_decision_branch(
        self,
        tree: DecisionTree,
        parent_path: List[str],
        branches: List[Tuple[str, float, str]]
    ) -> None:
        """Add decision branches to a node.
        
        Args:
            tree: Decision tree to modify.
            parent_path: Path to parent node (list of node labels).
            branches: List of (label, probability, description) tuples.
        """
        # Find parent node
        parent = tree.root
        for label in parent_path:
            found = False
            for child in parent.children:
                if child.label == label:
                    parent = child
                    found = True
                    break
            if not found:
                logger.warning(f"Parent node with label '{label}' not found")
                return
        
        # Add branches
        for label, probability, description in branches:
            child_node = DecisionNode(
                id=str(uuid.uuid4()),
                label=label,
                probability=probability,
                description=description
            )
            parent.add_child(child_node)
        
        # Normalize probabilities
        parent.normalize_children_probabilities()
    
    def build_general_query_tree(self, query: str, context_available: bool = True) -> DecisionTree:
        """Build decision tree for general queries.
        
        Args:
            query: The user query.
            context_available: Whether relevant context was found.
            
        Returns:
            Decision tree for the query.
        """
        # Создаем уникальное описание корневого узла с информацией о запросе
        query_preview = query[:50] + "..." if len(query) > 50 else query
        tree = self.create_tree(QueryType.GENERAL_QUESTION, f"Обработка запроса: {query_preview}")
        
        # Обновляем описание корневого узла
        tree.root.description = f"Анализ запроса пользователя: '{query}'"
        
        # First level: Context availability
        if context_available:
            self.add_decision_branch(tree, [], [
                ("Найден релевантный контекст", 0.8, f"Найдены документы, релевантные запросу: '{query_preview}'"),
                ("Контекст частично релевантен", 0.15, f"Найдены частично релевантные документы для: '{query_preview}'"),
                ("Контекст не найден", 0.05, f"Релевантные документы не найдены для: '{query_preview}'")
            ])
        else:
            self.add_decision_branch(tree, [], [
                ("Контекст не найден", 1.0, f"Релевантные документы не найдены для запроса: '{query_preview}'")
            ])
        
        # Second level: Response generation
        self.add_decision_branch(tree, ["Найден релевантный контекст"], [
            ("Прямой ответ из документов", 0.7, "Ответ найден непосредственно в документах"),
            ("Синтез информации", 0.25, "Требуется объединение информации из нескольких источников"),
            ("Интерпретация требуется", 0.05, "Требуется интерпретация сложной информации")
        ])
        
        self.add_decision_branch(tree, ["Контекст частично релевантен"], [
            ("Частичный ответ", 0.6, "Можно дать частичный ответ"),
            ("Общие рекомендации", 0.4, "Предоставить общие рекомендации")
        ])
        
        self.add_decision_branch(tree, ["Контекст не найден"], [
            ("Сообщить об отсутствии данных", 1.0, "Честно сообщить об отсутствии информации")
        ])
        
        # Third level: Quality assessment
        self.add_decision_branch(tree, ["Найден релевантный контекст", "Прямой ответ из документов"], [
            ("Высокая точность", 0.8, "Ответ с высокой степенью точности"),
            ("Средняя точность", 0.2, "Ответ требует дополнительной проверки")
        ])
        
        return tree
    
    def _normalize_probabilities(self, probabilities: List[float]) -> List[float]:
        """Normalize probabilities so their sum equals 1.0.
        
        Args:
            probabilities: List of probability values.
            
        Returns:
            Normalized probabilities that sum to 1.0.
        """
        total = sum(probabilities)
        if total == 0:
            return [1.0 / len(probabilities)] * len(probabilities)
        return [p / total for p in probabilities]
    
    def build_compliance_check_tree(
        self, 
        has_reference_docs: bool = True, 
        query_context: str = "",
        context_confidence: float = 0.8,
        analysis_confidence: float = 0.7,
        compliance_confidence: float = 0.5
    ) -> DecisionTree:
        """Build dynamic decision tree for compliance checking based on AI confidence.
        
        Args:
            has_reference_docs: Whether reference documents are available.
            query_context: Additional context about the compliance check query.
            context_confidence: AI confidence in found context (0.0-1.0).
            analysis_confidence: AI confidence in analysis capability (0.0-1.0).
            compliance_confidence: AI confidence in compliance result (0.0-1.0).
            
        Returns:
            Decision tree for compliance check with dynamic probabilities.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        tree = self.create_tree(QueryType.COMPLIANCE_CHECK, f"Проверка соответствия ({timestamp})")
        
        # Добавляем контекст в описание корневого узла
        context_info = f" | Контекст: {query_context}" if query_context else ""
        tree.root.description = f"Анализ соответствия документа нормативным требованиям{context_info}"
        
        # First level: Reference documents availability (dynamic based on context_confidence)
        if has_reference_docs:
            # Динамические вероятности на основе уверенности в контексте
            if context_confidence >= 0.8:
                # Высокая уверенность в найденных документах
                found_prob = 0.85 + (context_confidence - 0.8) * 0.75  # 0.85-1.0
                partial_prob = 1.0 - found_prob
            elif context_confidence >= 0.5:
                # Средняя уверенность
                found_prob = 0.5 + (context_confidence - 0.5) * 1.17  # 0.5-0.85
                partial_prob = 1.0 - found_prob
            else:
                # Низкая уверенность - больше частичных документов
                found_prob = context_confidence  # 0.0-0.5
                partial_prob = 1.0 - found_prob
            
            # Нормализуем вероятности
            probs = self._normalize_probabilities([found_prob, partial_prob])
            
            self.add_decision_branch(tree, [], [
                ("Эталонные документы найдены", probs[0], f"Найдены нормативные документы для проверки{context_info} (уверенность: {context_confidence:.2f})"),
                ("Частичная база нормативов", probs[1], f"Найдена только часть необходимых нормативов{context_info} (уверенность: {context_confidence:.2f})")
            ])
        else:
            self.add_decision_branch(tree, [], [
                ("Нормативы отсутствуют", 1.0, f"Нормативные документы не найдены{context_info}")
            ])
        
        # Second level: Analysis type (dynamic based on analysis_confidence)
        if analysis_confidence >= 0.8:
            # Высокая уверенность в анализе - больше полных проверок
            full_prob = 0.7 + (analysis_confidence - 0.8) * 1.5  # 0.7-1.0
            selective_prob = 0.25 * (1.0 - analysis_confidence + 0.8)  # уменьшается
            basic_prob = 0.05 * (1.0 - analysis_confidence + 0.8)  # уменьшается
        elif analysis_confidence >= 0.5:
            # Средняя уверенность - больше выборочных проверок
            full_prob = 0.3 + (analysis_confidence - 0.5) * 1.33  # 0.3-0.7
            selective_prob = 0.4 + (analysis_confidence - 0.5) * 0.33  # 0.4-0.5
            basic_prob = 0.3 - (analysis_confidence - 0.5) * 0.67  # 0.3-0.1
        else:
            # Низкая уверенность - больше базовых проверок
            full_prob = analysis_confidence * 0.6  # 0.0-0.3
            selective_prob = 0.2 + analysis_confidence * 0.4  # 0.2-0.4
            basic_prob = 0.8 - analysis_confidence * 1.0  # 0.8-0.3
        
        # Нормализуем вероятности
        analysis_probs = self._normalize_probabilities([full_prob, selective_prob, basic_prob])
        
        self.add_decision_branch(tree, ["Эталонные документы найдены"], [
            ("Полная проверка", analysis_probs[0], f"Возможна полная проверка соответствия (уверенность в анализе: {analysis_confidence:.2f})"),
            ("Выборочная проверка", analysis_probs[1], f"Проверка по ключевым критериям (уверенность в анализе: {analysis_confidence:.2f})"),
            ("Базовая проверка", analysis_probs[2], f"Проверка основных требований (уверенность в анализе: {analysis_confidence:.2f})")
        ])
        
        # Third level: Compliance result (dynamic based on compliance_confidence)
        if compliance_confidence >= 0.8:
            # Высокая уверенность в соответствии
            full_compliance = 0.4 + (compliance_confidence - 0.8) * 3.0  # 0.4-1.0
            with_remarks = 0.4 * (1.0 - compliance_confidence + 0.8)  # уменьшается
            partial = 0.15 * (1.0 - compliance_confidence + 0.8)  # уменьшается
            non_compliance = 0.05 * (1.0 - compliance_confidence + 0.8)  # уменьшается
        elif compliance_confidence >= 0.5:
            # Средняя уверенность - больше соответствия с замечаниями
            full_compliance = 0.1 + (compliance_confidence - 0.5) * 1.0  # 0.1-0.4
            with_remarks = 0.5 + (compliance_confidence - 0.5) * 0.33  # 0.5-0.6
            partial = 0.3 - (compliance_confidence - 0.5) * 0.5  # 0.3-0.15
            non_compliance = 0.1 - (compliance_confidence - 0.5) * 0.17  # 0.1-0.05
        else:
            # Низкая уверенность - больше частичного соответствия или несоответствия
            full_compliance = compliance_confidence * 0.2  # 0.0-0.1
            with_remarks = 0.2 + compliance_confidence * 0.6  # 0.2-0.5
            partial = 0.5 + (0.5 - compliance_confidence) * 0.6  # 0.5-0.8
            non_compliance = 0.3 - compliance_confidence * 0.4  # 0.3-0.1
        
        # Нормализуем вероятности
        compliance_probs = self._normalize_probabilities([full_compliance, with_remarks, partial, non_compliance])
        
        self.add_decision_branch(tree, ["Эталонные документы найдены", "Полная проверка"], [
            ("Полное соответствие", compliance_probs[0], f"Документ полностью соответствует требованиям (уверенность: {compliance_confidence:.2f})"),
            ("Соответствие с замечаниями", compliance_probs[1], f"Соответствие с незначительными замечаниями (уверенность: {compliance_confidence:.2f})"),
            ("Частичное соответствие", compliance_probs[2], f"Значительные нарушения требований (уверенность: {compliance_confidence:.2f})"),
            ("Несоответствие", compliance_probs[3], f"Критические нарушения (уверенность: {compliance_confidence:.2f})")
        ])
        
        return tree
    
    def categorize_query(self, query: str) -> QueryType:
        """Categorize query type based on content.
        
        Args:
            query: User query text.
            
        Returns:
            Categorized query type.
        """
        query_lower = query.lower()
        
        # Keywords for different query types
        compliance_keywords = ["проверить", "соответствие", "нарушение", "требования", "договор"]
        search_keywords = ["найти", "поиск", "где", "какой документ"]
        normative_keywords = ["норматив", "закон", "правило", "регламент"]
        comparison_keywords = ["сравнить", "отличие", "разница", "лучше"]
        
        if any(keyword in query_lower for keyword in compliance_keywords):
            return QueryType.COMPLIANCE_CHECK
        elif any(keyword in query_lower for keyword in search_keywords):
            return QueryType.DOCUMENT_SEARCH
        elif any(keyword in query_lower for keyword in normative_keywords):
            return QueryType.NORMATIVE_LOOKUP
        elif any(keyword in query_lower for keyword in comparison_keywords):
            return QueryType.COMPARISON
        else:
            return QueryType.GENERAL_QUESTION


class DecisionTreeVisualizer:
    """Visualizes decision trees with ASCII art and colors."""
    
    # Color codes for terminal output
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'blue': '\033[94m',
        'purple': '\033[95m',
        'cyan': '\033[96m'
    }
    
    def __init__(self, use_colors: bool = True):
        """Initialize visualizer.
        
        Args:
            use_colors: Whether to use color output.
        """
        self.use_colors = use_colors and os.getenv('NO_COLOR') is None
    
    def visualize_tree(
        self,
        tree: DecisionTree,
        detail_level: DetailLevel = DetailLevel.FULL,
        max_width: int = 80
    ) -> str:
        """Visualize decision tree as ASCII art.
        
        Args:
            tree: Decision tree to visualize.
            detail_level: Level of detail to show.
            max_width: Maximum width of output.
            
        Returns:
            ASCII representation of the tree.
        """
        lines = []
        
        # Header
        header = f"Decision Tree: {tree.query_type.value}"
        lines.append(self._colorize(header, 'bold'))
        lines.append("=" * len(header))
        lines.append("")
        
        # Tree visualization
        tree_lines = self._visualize_node(tree.root, "", True, detail_level, max_width)
        lines.extend(tree_lines)
        
        # Footer with statistics
        if detail_level in [DetailLevel.FULL, DetailLevel.EXTENDED]:
            lines.append("")
            lines.append(self._get_tree_statistics(tree))
        
        return "\n".join(lines)
    
    def _visualize_node(
        self,
        node: DecisionNode,
        prefix: str,
        is_last: bool,
        detail_level: DetailLevel,
        max_width: int
    ) -> List[str]:
        """Visualize a single node and its children.
        
        Args:
            node: Node to visualize.
            prefix: Prefix for indentation.
            is_last: Whether this is the last child.
            detail_level: Level of detail.
            max_width: Maximum width.
            
        Returns:
            List of lines representing the node.
        """
        lines = []
        
        # Node connector
        connector = "└── " if is_last else "├── "
        
        # Node label with probability
        prob_color = self._get_probability_color(node.probability)
        prob_text = f"({node.probability:.2f})"
        
        node_text = f"{prefix}{connector}{node.label} {self._colorize(prob_text, prob_color)}"
        
        # Truncate if too long
        if len(node_text.replace('\033[0m', '').replace('\033[92m', '').replace('\033[93m', '').replace('\033[91m', '')) > max_width:
            visible_length = max_width - 3
            # Remove color codes for length calculation
            clean_text = node_text
            for color in self.COLORS.values():
                clean_text = clean_text.replace(color, '')
            if len(clean_text) > visible_length:
                node_text = clean_text[:visible_length] + "..."
        
        lines.append(node_text)
        
        # Add description if detailed view
        if detail_level in [DetailLevel.FULL, DetailLevel.EXTENDED] and node.description:
            desc_prefix = prefix + ("    " if is_last else "│   ")
            desc_text = f"{desc_prefix}└─ {self._colorize(node.description, 'cyan')}"
            lines.append(desc_text)
        
        # Add metadata if extended view
        if detail_level == DetailLevel.EXTENDED and node.metadata:
            meta_prefix = prefix + ("    " if is_last else "│   ")
            for key, value in node.metadata.items():
                meta_text = f"{meta_prefix}   {key}: {value}"
                lines.append(self._colorize(meta_text, 'purple'))
        
        # Visualize children
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(node.children):
            child_is_last = i == len(node.children) - 1
            child_lines = self._visualize_node(child, child_prefix, child_is_last, detail_level, max_width)
            lines.extend(child_lines)
        
        return lines
    
    def _get_probability_color(self, probability: float) -> str:
        """Get color for probability value.
        
        Args:
            probability: Probability value.
            
        Returns:
            Color name.
        """
        if probability >= 0.7:
            return 'green'
        elif probability >= 0.4:
            return 'yellow'
        else:
            return 'red'
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text.
        
        Args:
            text: Text to colorize.
            color: Color name.
            
        Returns:
            Colorized text.
        """
        if not self.use_colors or color not in self.COLORS:
            return text
        
        return f"{self.COLORS[color]}{text}{self.COLORS['reset']}"
    
    def _get_tree_statistics(self, tree: DecisionTree) -> str:
        """Get statistics about the tree.
        
        Args:
            tree: Decision tree.
            
        Returns:
            Statistics string.
        """
        paths = tree.get_all_paths()
        total_nodes = self._count_nodes(tree.root)
        
        stats = [
            f"Statistics:",
            f"  Total nodes: {total_nodes}",
            f"  Total paths: {len(paths)}",
            f"  Tree depth: {max(len(path) for path in paths) if paths else 0}",
            f"  Query type: {tree.query_type.value}"
        ]
        
        return "\n".join(stats)
    
    def _count_nodes(self, node: DecisionNode) -> int:
        """Count total nodes in tree.
        
        Args:
            node: Root node.
            
        Returns:
            Total node count.
        """
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count
    
    def visualize_path(self, tree: DecisionTree, path: List[DecisionNode]) -> str:
        """Visualize a specific path through the tree.
        
        Args:
            tree: Decision tree.
            path: Path to visualize.
            
        Returns:
            Path visualization.
        """
        if not path:
            return "Empty path"
        
        lines = []
        lines.append(self._colorize("Selected Path:", 'bold'))
        lines.append("-" * 20)
        
        total_probability = tree.calculate_path_probability(path)
        
        for i, node in enumerate(path):
            arrow = " → " if i < len(path) - 1 else ""
            prob_color = self._get_probability_color(node.probability)
            prob_text = f"({node.probability:.2f})"
            
            line = f"{i+1}. {node.label} {self._colorize(prob_text, prob_color)}{arrow}"
            lines.append(line)
        
        lines.append("")
        lines.append(f"Total path probability: {self._colorize(f'{total_probability:.3f}', self._get_probability_color(total_probability))}")
        
        return "\n".join(lines)


def get_decision_tree_settings() -> Dict[str, Any]:
    """Get decision tree settings from environment variables.
    
    Returns:
        Dictionary with settings.
    """
    return {
        'enabled': os.getenv('SHOW_DECISION_TREE', 'true').lower() in ['true', '1', 'yes'],
        'detail_level': DetailLevel(os.getenv('DECISION_TREE_DETAIL', 'full')),
        'use_colors': os.getenv('DECISION_TREE_COLORS', 'true').lower() in ['true', '1', 'yes'],
        'max_width': int(os.getenv('DECISION_TREE_WIDTH', '80'))
    }