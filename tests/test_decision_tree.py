"""Tests for decision tree visualization system."""

import os
import sys
from unittest.mock import patch
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_agent.utils.decision_tree import (
    DecisionNode, DecisionTree, DecisionTreeBuilder, DecisionTreeVisualizer,
    QueryType, DetailLevel, get_decision_tree_settings
)


class TestDecisionNode:
    """Test DecisionNode functionality."""
    
    def test_create_node(self):
        """Test creating a decision node."""
        node = DecisionNode(
            id="test-1",
            label="Test Node",
            probability=0.8,
            description="Test description"
        )
        
        assert node.id == "test-1"
        assert node.label == "Test Node"
        assert node.probability == 0.8
        assert node.description == "Test description"
        assert len(node.children) == 0
        assert node.is_leaf()
    
    def test_add_child(self):
        """Test adding child nodes."""
        parent = DecisionNode("parent", "Parent", 1.0)
        child1 = DecisionNode("child1", "Child 1", 0.6)
        child2 = DecisionNode("child2", "Child 2", 0.4)
        
        parent.add_child(child1)
        parent.add_child(child2)
        
        assert len(parent.children) == 2
        assert not parent.is_leaf()
        assert child1 in parent.children
        assert child2 in parent.children
    
    def test_normalize_children_probabilities(self):
        """Test probability normalization."""
        parent = DecisionNode("parent", "Parent", 1.0)
        child1 = DecisionNode("child1", "Child 1", 0.3)
        child2 = DecisionNode("child2", "Child 2", 0.7)
        
        parent.add_child(child1)
        parent.add_child(child2)
        parent.normalize_children_probabilities()
        
        # Probabilities should sum to 1.0
        total_prob = sum(child.probability for child in parent.children)
        assert abs(total_prob - 1.0) < 0.001
        
        # Individual probabilities should be normalized
        assert abs(parent.children[0].probability - 0.3) < 0.001
        assert abs(parent.children[1].probability - 0.7) < 0.001
    
    def test_normalize_unequal_probabilities(self):
        """Test normalizing unequal probabilities."""
        parent = DecisionNode("parent", "Parent", 1.0)
        child1 = DecisionNode("child1", "Child 1", 0.2)
        child2 = DecisionNode("child2", "Child 2", 0.8)
        
        parent.add_child(child1)
        parent.add_child(child2)
        parent.normalize_children_probabilities()
        
        total_prob = sum(child.probability for child in parent.children)
        assert abs(total_prob - 1.0) < 0.001
        assert abs(parent.children[0].probability - 0.2) < 0.001
        assert abs(parent.children[1].probability - 0.8) < 0.001
    
    def test_get_path_probability(self):
        """Test calculating path probability."""
        root = DecisionNode("root", "Root", 1.0)
        child1 = DecisionNode("child1", "Child 1", 0.6)
        child2 = DecisionNode("child2", "Child 2", 0.4)
        grandchild = DecisionNode("grandchild", "Grandchild", 0.8)
        
        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild)
        
        # Test path probability calculation
        path_prob = root.get_path_probability(["child1", "grandchild"])
        expected_prob = 1.0 * 0.6 * 0.8
        assert abs(path_prob - expected_prob) < 0.001
        
        # Test non-existent path
        path_prob = root.get_path_probability(["nonexistent"])
        assert path_prob == 0.0


class TestDecisionTree:
    """Test DecisionTree functionality."""
    
    def test_create_tree(self):
        """Test creating a decision tree."""
        root = DecisionNode("root", "Root", 1.0)
        tree = DecisionTree(
            id="test-tree",
            root=root,
            query_type=QueryType.GENERAL_QUESTION
        )
        
        assert tree.id == "test-tree"
        assert tree.root == root
        assert tree.query_type == QueryType.GENERAL_QUESTION
        assert isinstance(tree.created_at, datetime)
    
    def test_get_all_paths(self):
        """Test getting all paths from root to leaves."""
        root = DecisionNode("root", "Root", 1.0)
        child1 = DecisionNode("child1", "Child 1", 0.6)
        child2 = DecisionNode("child2", "Child 2", 0.4)
        grandchild1 = DecisionNode("gc1", "Grandchild 1", 0.8)
        grandchild2 = DecisionNode("gc2", "Grandchild 2", 0.2)
        
        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild1)
        child1.add_child(grandchild2)
        
        tree = DecisionTree("test", root, QueryType.GENERAL_QUESTION)
        paths = tree.get_all_paths()
        
        assert len(paths) == 3  # Two paths through child1, one through child2
        
        # Check path lengths
        path_lengths = [len(path) for path in paths]
        assert 2 in path_lengths  # Path to child2 (leaf)
        assert 3 in path_lengths  # Paths to grandchildren
    
    def test_get_path_by_labels(self):
        """Test getting path by following labels."""
        root = DecisionNode("root", "Root", 1.0)
        child1 = DecisionNode("child1", "Child 1", 0.6)
        grandchild = DecisionNode("gc", "Grandchild", 0.8)
        
        root.add_child(child1)
        child1.add_child(grandchild)
        
        tree = DecisionTree("test", root, QueryType.GENERAL_QUESTION)
        
        # Test valid path
        path = tree.get_path_by_labels(["Child 1", "Grandchild"])
        assert path is not None
        assert len(path) == 3
        assert path[0] == root
        assert path[1] == child1
        assert path[2] == grandchild
        
        # Test invalid path
        path = tree.get_path_by_labels(["Nonexistent"])
        assert path is None
    
    def test_calculate_path_probability(self):
        """Test calculating total path probability."""
        root = DecisionNode("root", "Root", 1.0)
        child = DecisionNode("child", "Child", 0.7)
        grandchild = DecisionNode("gc", "Grandchild", 0.5)
        
        root.add_child(child)
        child.add_child(grandchild)
        
        tree = DecisionTree("test", root, QueryType.GENERAL_QUESTION)
        path = [root, child, grandchild]
        
        prob = tree.calculate_path_probability(path)
        expected = 1.0 * 0.7 * 0.5
        assert abs(prob - expected) < 0.001


class TestDecisionTreeBuilder:
    """Test DecisionTreeBuilder functionality."""
    
    def test_create_tree(self):
        """Test creating a tree with builder."""
        builder = DecisionTreeBuilder()
        tree = builder.create_tree(QueryType.COMPLIANCE_CHECK, "Start")
        
        assert tree.query_type == QueryType.COMPLIANCE_CHECK
        assert tree.root.label == "Start"
        assert tree.root.probability == 1.0
        assert tree.id in builder.trees
    
    def test_add_decision_branch(self):
        """Test adding decision branches."""
        builder = DecisionTreeBuilder()
        tree = builder.create_tree(QueryType.GENERAL_QUESTION)
        
        # Add branches to root
        branches = [
            ("Option A", 0.6, "First option"),
            ("Option B", 0.4, "Second option")
        ]
        builder.add_decision_branch(tree, [], branches)
        
        assert len(tree.root.children) == 2
        
        # Check normalization
        total_prob = sum(child.probability for child in tree.root.children)
        assert abs(total_prob - 1.0) < 0.001
    
    def test_build_general_query_tree(self):
        """Test building general query tree."""
        builder = DecisionTreeBuilder()
        tree = builder.build_general_query_tree("test query", context_available=True)
        
        assert tree.query_type == QueryType.GENERAL_QUESTION
        assert len(tree.root.children) > 0
        
        # Check that tree has multiple levels
        paths = tree.get_all_paths()
        assert len(paths) > 1
        assert any(len(path) > 2 for path in paths)
    
    def test_build_compliance_check_tree(self):
        """Test building compliance check tree."""
        builder = DecisionTreeBuilder()
        tree = builder.build_compliance_check_tree(has_reference_docs=True)
        
        assert tree.query_type == QueryType.COMPLIANCE_CHECK
        assert len(tree.root.children) > 0
        
        # Check tree structure
        paths = tree.get_all_paths()
        assert len(paths) > 1
    
    def test_categorize_query(self):
        """Test query categorization."""
        builder = DecisionTreeBuilder()
        
        # Test compliance queries
        assert builder.categorize_query("проверить документ на соответствие") == QueryType.COMPLIANCE_CHECK
        assert builder.categorize_query("есть ли нарушения в договоре") == QueryType.COMPLIANCE_CHECK
        
        # Test search queries
        assert builder.categorize_query("найти документ о закупках") == QueryType.DOCUMENT_SEARCH
        assert builder.categorize_query("где найти информацию") == QueryType.DOCUMENT_SEARCH
        
        # Test normative queries
        assert builder.categorize_query("какие нормативы действуют") == QueryType.NORMATIVE_LOOKUP
        assert builder.categorize_query("что говорит закон") == QueryType.NORMATIVE_LOOKUP
        
        # Test comparison queries
        assert builder.categorize_query("сравнить два документа") == QueryType.COMPARISON
        assert builder.categorize_query("в чем отличие") == QueryType.COMPARISON
        
        # Test general queries
        assert builder.categorize_query("как дела") == QueryType.GENERAL_QUESTION


class TestDecisionTreeVisualizer:
    """Test DecisionTreeVisualizer functionality."""
    
    def test_create_visualizer(self):
        """Test creating visualizer."""
        visualizer = DecisionTreeVisualizer(use_colors=True)
        assert visualizer.use_colors is True
        
        visualizer = DecisionTreeVisualizer(use_colors=False)
        assert visualizer.use_colors is False
    
    def test_visualize_simple_tree(self):
        """Test visualizing a simple tree."""
        root = DecisionNode("root", "Root", 1.0, "Root description")
        child1 = DecisionNode("child1", "Child 1", 0.7, "First child")
        child2 = DecisionNode("child2", "Child 2", 0.3, "Second child")
        
        root.add_child(child1)
        root.add_child(child2)
        
        tree = DecisionTree("test", root, QueryType.GENERAL_QUESTION)
        visualizer = DecisionTreeVisualizer(use_colors=False)
        
        output = visualizer.visualize_tree(tree, DetailLevel.BRIEF)
        
        assert "Decision Tree" in output
        assert "Root" in output
        assert "Child 1" in output
        assert "Child 2" in output
        assert "(1.00)" in output
        assert "(0.70)" in output
        assert "(0.30)" in output
    
    def test_visualize_with_descriptions(self):
        """Test visualizing tree with descriptions."""
        root = DecisionNode("root", "Root", 1.0, "Root description")
        child = DecisionNode("child", "Child", 0.8, "Child description")
        root.add_child(child)
        
        tree = DecisionTree("test", root, QueryType.GENERAL_QUESTION)
        visualizer = DecisionTreeVisualizer(use_colors=False)
        
        output = visualizer.visualize_tree(tree, DetailLevel.FULL)
        
        assert "Root description" in output
        assert "Child description" in output
    
    def test_visualize_path(self):
        """Test visualizing a specific path."""
        root = DecisionNode("root", "Root", 1.0)
        child = DecisionNode("child", "Child", 0.8)
        grandchild = DecisionNode("gc", "Grandchild", 0.6)
        
        root.add_child(child)
        child.add_child(grandchild)
        
        tree = DecisionTree("test", root, QueryType.GENERAL_QUESTION)
        path = [root, child, grandchild]
        
        visualizer = DecisionTreeVisualizer(use_colors=False)
        output = visualizer.visualize_path(tree, path)
        
        assert "Selected Path" in output
        assert "Root" in output
        assert "Child" in output
        assert "Grandchild" in output
        assert "Total path probability" in output
    
    def test_get_probability_color(self):
        """Test probability color assignment."""
        visualizer = DecisionTreeVisualizer(use_colors=True)
        
        assert visualizer._get_probability_color(0.8) == 'green'
        assert visualizer._get_probability_color(0.5) == 'yellow'
        assert visualizer._get_probability_color(0.2) == 'red'
    
    def test_colorize(self):
        """Test text colorization."""
        visualizer = DecisionTreeVisualizer(use_colors=True)
        
        colored = visualizer._colorize("test", "green")
        assert "\033[92m" in colored  # Green color code
        assert "\033[0m" in colored   # Reset code
        assert "test" in colored
        
        # Test without colors
        visualizer = DecisionTreeVisualizer(use_colors=False)
        plain = visualizer._colorize("test", "green")
        assert plain == "test"


class TestDecisionTreeSettings:
    """Test decision tree settings functionality."""
    
    def test_default_settings(self):
        """Test default settings."""
        with patch.dict(os.environ, {}, clear=True):
            settings = get_decision_tree_settings()
            
            assert settings['enabled'] is False
            assert settings['detail_level'] == DetailLevel.FULL
            assert settings['use_colors'] is True
            assert settings['max_width'] == 80
    
    def test_environment_settings(self):
        """Test settings from environment variables."""
        env_vars = {
            'SHOW_DECISION_TREE': 'true',
            'DECISION_TREE_DETAIL': 'brief',
            'DECISION_TREE_COLORS': 'false',
            'DECISION_TREE_WIDTH': '120'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = get_decision_tree_settings()
            
            assert settings['enabled'] is True
            assert settings['detail_level'] == DetailLevel.BRIEF
            assert settings['use_colors'] is False
            assert settings['max_width'] == 120
    
    def test_boolean_environment_values(self):
        """Test various boolean environment values."""
        test_cases = [
            ('true', True),
            ('1', True),
            ('yes', True),
            ('false', False),
            ('0', False),
            ('no', False),
            ('invalid', False)
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'SHOW_DECISION_TREE': env_value}, clear=True):
                settings = get_decision_tree_settings()
                assert settings['enabled'] == expected


class TestDecisionTreeIntegration:
    """Test decision tree integration scenarios."""
    
    def test_complete_workflow(self):
        """Test complete decision tree workflow."""
        # Create builder and build tree
        builder = DecisionTreeBuilder()
        tree = builder.build_general_query_tree("test query", context_available=True)
        
        # Visualize tree
        visualizer = DecisionTreeVisualizer(use_colors=False)
        output = visualizer.visualize_tree(tree, DetailLevel.FULL)
        
        # Verify output contains expected elements
        assert "Decision Tree" in output
        assert "general_question" in output
        assert len(output.split('\n')) > 5  # Multi-line output
        
        # Test path visualization
        paths = tree.get_all_paths()
        if paths:
            path_output = visualizer.visualize_path(tree, paths[0])
            assert "Selected Path" in path_output
            assert "Total path probability" in path_output
    
    def test_tree_statistics(self):
        """Test tree statistics calculation."""
        builder = DecisionTreeBuilder()
        tree = builder.build_compliance_check_tree(has_reference_docs=True)
        
        visualizer = DecisionTreeVisualizer(use_colors=False)
        output = visualizer.visualize_tree(tree, DetailLevel.EXTENDED)
        
        # Should include statistics
        assert "Statistics:" in output
        assert "Total nodes:" in output
        assert "Total paths:" in output
        assert "Tree depth:" in output
    
    def test_error_handling(self):
        """Test error handling in decision tree components."""
        builder = DecisionTreeBuilder()
        tree = builder.create_tree(QueryType.GENERAL_QUESTION)
        
        # Test adding branch to non-existent parent
        builder.add_decision_branch(tree, ["nonexistent"], [("test", 1.0, "test")])
        
        # Tree should remain unchanged
        assert len(tree.root.children) == 0
        
        # Test empty path probability
        assert tree.calculate_path_probability([]) == 0.0


def run_tests():
    """Run all tests manually."""
    test_classes = [
        TestDecisionNode(),
        TestDecisionTree(),
        TestDecisionTreeBuilder(),
        TestDecisionTreeVisualizer(),
        TestDecisionTreeSettings(),
        TestDecisionTreeIntegration()
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n=== Running {class_name} ===")
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_class, method_name)
                method()
                print(f"✅ {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"❌ {method_name}: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)