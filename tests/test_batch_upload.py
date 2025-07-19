"""Tests for batch upload functionality."""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock the problematic imports before importing our modules
with patch.dict('sys.modules', {
    'chromadb': Mock(),
    'chromadb.config': Mock(),
    'docx': Mock(),
    'ollama': Mock(),
}):
    from ai_agent.cli.commands import (
        _find_files_for_batch_upload,
        _format_file_size,
        _perform_batch_upload
    )
from ai_agent.core.document_manager import DocumentManagerError


class TestBatchUploadHelpers:
    """Test batch upload helper functions."""
    
    def test_find_files_for_batch_upload_single_file(self):
        """Test finding files when a single file is provided."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b'test content')
            tmp_path = tmp.name
        
        try:
            files = _find_files_for_batch_upload(tmp_path, '*.txt', False)
            assert len(files) == 1
            assert files[0] == Path(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_find_files_for_batch_upload_directory_non_recursive(self):
        """Test finding files in directory without recursion."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Create test files
            (tmp_path / 'file1.txt').write_text('content1')
            (tmp_path / 'file2.md').write_text('content2')
            (tmp_path / 'file3.docx').write_text('content3')
            (tmp_path / 'ignore.pdf').write_text('ignore')
            
            # Create subdirectory with files (should be ignored)
            sub_dir = tmp_path / 'subdir'
            sub_dir.mkdir()
            (sub_dir / 'sub_file.txt').write_text('sub content')
            
            files = _find_files_for_batch_upload(str(tmp_path), '*.txt,*.md', False)
            
            assert len(files) == 2
            file_names = [f.name for f in files]
            assert 'file1.txt' in file_names
            assert 'file2.md' in file_names
            assert 'sub_file.txt' not in file_names
    
    def test_find_files_for_batch_upload_directory_recursive(self):
        """Test finding files in directory with recursion."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Create test files
            (tmp_path / 'file1.txt').write_text('content1')
            
            # Create subdirectory with files
            sub_dir = tmp_path / 'subdir'
            sub_dir.mkdir()
            (sub_dir / 'sub_file.txt').write_text('sub content')
            
            # Create nested subdirectory
            nested_dir = sub_dir / 'nested'
            nested_dir.mkdir()
            (nested_dir / 'nested_file.txt').write_text('nested content')
            
            files = _find_files_for_batch_upload(str(tmp_path), '*.txt', True)
            
            assert len(files) == 3
            file_names = [f.name for f in files]
            assert 'file1.txt' in file_names
            assert 'sub_file.txt' in file_names
            assert 'nested_file.txt' in file_names
    
    def test_format_file_size(self):
        """Test file size formatting."""
        assert _format_file_size(500) == "500 B"
        assert _format_file_size(1024) == "1.0 KB"
        assert _format_file_size(1536) == "1.5 KB"
        assert _format_file_size(1024 * 1024) == "1.0 MB"
        assert _format_file_size(1024 * 1024 * 1024) == "1.0 GB"


class TestDocumentManagerBatchUpload:
    """Test DocumentManager batch upload functionality."""
    
    @pytest.fixture
    def mock_document_manager(self):
        """Create a mock document manager."""
        with patch('ai_agent.core.document_manager.chromadb'), \
             patch('ai_agent.core.document_manager.OllamaClient'):
            
            from ai_agent.core.document_manager import DocumentManager
            manager = DocumentManager()
            manager.upload_document = Mock()
            return manager
    
    def test_batch_upload_documents_success(self, mock_document_manager):
        """Test successful batch upload."""
        # Setup
        file_paths = ['file1.txt', 'file2.md', 'file3.docx']
        common_metadata = {'category': 'test', 'batch': 'true'}
        
        # Mock successful uploads
        mock_document_manager.upload_document.side_effect = [
            'doc_id_1', 'doc_id_2', 'doc_id_3'
        ]
        
        # Execute
        results = mock_document_manager.batch_upload_documents(
            file_paths, common_metadata
        )
        
        # Verify
        assert len(results) == 3
        
        for i, result in enumerate(results):
            assert result['success'] is True
            assert result['file_path'] == file_paths[i]
            assert result['document_id'] == f'doc_id_{i + 1}'
            assert result['error'] is None
        
        # Verify upload_document was called correctly
        assert mock_document_manager.upload_document.call_count == 3
        
        for i, call in enumerate(mock_document_manager.upload_document.call_args_list):
            args, kwargs = call
            assert kwargs['file_path'] == file_paths[i]  # file_path is now keyword argument
            
            expected_metadata = common_metadata.copy()
            expected_metadata.update({
                'batch_upload': 'true',
                'batch_index': str(i)
            })
            assert kwargs['metadata'] == expected_metadata
    
    def test_batch_upload_documents_with_errors(self, mock_document_manager):
        """Test batch upload with some failures."""
        # Setup
        file_paths = ['file1.txt', 'file2.md', 'file3.docx']
        
        # Mock mixed results
        def upload_side_effect(file_path, metadata=None, category=None, tags=None):
            if 'file2.md' in file_path:
                raise DocumentManagerError("File format not supported")
            return f'doc_id_{file_path}'
        
        mock_document_manager.upload_document.side_effect = upload_side_effect
        
        # Execute
        results = mock_document_manager.batch_upload_documents(file_paths)
        
        # Verify
        assert len(results) == 3
        
        # First file - success
        assert results[0]['success'] is True
        assert results[0]['document_id'] == 'doc_id_file1.txt'
        
        # Second file - failure
        assert results[1]['success'] is False
        assert results[1]['document_id'] is None
        assert 'File format not supported' in results[1]['error']
        
        # Third file - success
        assert results[2]['success'] is True
        assert results[2]['document_id'] == 'doc_id_file3.docx'
    
    def test_batch_upload_documents_with_progress_callback(self, mock_document_manager):
        """Test batch upload with progress callback."""
        # Setup
        file_paths = ['file1.txt', 'file2.md']
        progress_callback = Mock()
        
        mock_document_manager.upload_document.side_effect = ['doc_id_1', 'doc_id_2']
        
        # Execute
        results = mock_document_manager.batch_upload_documents(
            file_paths, progress_callback=progress_callback
        )
        
        # Verify progress callback was called
        assert progress_callback.call_count == 2
        
        # Check first callback
        first_call = progress_callback.call_args_list[0]
        args = first_call[0]
        assert args[0] == 1  # current
        assert args[1] == 2  # total
        assert args[2] == 'file1.txt'  # current file
        assert args[3]['success'] is True  # result
        
        # Check second callback
        second_call = progress_callback.call_args_list[1]
        args = second_call[0]
        assert args[0] == 2  # current
        assert args[1] == 2  # total
        assert args[2] == 'file2.md'  # current file
        assert args[3]['success'] is True  # result


class TestBatchUploadCLI:
    """Test CLI batch upload functionality."""
    
    @pytest.fixture
    def mock_cli_instance(self):
        """Create a mock CLI instance."""
        cli_instance = Mock()
        cli_instance.document_manager = Mock()
        return cli_instance
    
    def test_perform_batch_upload_success(self, mock_cli_instance):
        """Test successful batch upload through CLI."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Create test files
            file1 = tmp_path / 'file1.txt'
            file2 = tmp_path / 'file2.md'
            file1.write_text('content1')
            file2.write_text('content2')
            
            files = [file1, file2]
            common_metadata = {'category': 'test'}
            
            # Mock successful uploads
            mock_cli_instance.document_manager.upload_document.side_effect = [
                'doc_id_1', 'doc_id_2'
            ]
            
            # Execute
            from ai_agent.models.document import DocumentCategory
            results = _perform_batch_upload(
                mock_cli_instance, files, common_metadata, DocumentCategory.GENERAL, [], skip_errors=False
            )
            
            # Verify
            assert results['total_files'] == 2
            assert len(results['successful']) == 2
            assert len(results['failed']) == 0
            
            # Check successful uploads
            assert results['successful'][0]['doc_id'] == 'doc_id_1'
            assert results['successful'][1]['doc_id'] == 'doc_id_2'
    
    def test_perform_batch_upload_with_errors_skip(self, mock_cli_instance):
        """Test batch upload with errors and skip_errors=True."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Create test files
            file1 = tmp_path / 'file1.txt'
            file2 = tmp_path / 'file2.md'
            file1.write_text('content1')
            file2.write_text('content2')
            
            files = [file1, file2]
            
            # Mock mixed results
            def upload_side_effect(file_path, metadata=None, category=None, tags=None):
                if 'file2.md' in str(file_path):
                    raise DocumentManagerError("Upload failed")
                return 'doc_id_1'
            
            mock_cli_instance.document_manager.upload_document.side_effect = upload_side_effect
            
            # Execute
            from ai_agent.models.document import DocumentCategory
            results = _perform_batch_upload(
                mock_cli_instance, files, {}, DocumentCategory.GENERAL, [], skip_errors=True
            )
            
            # Verify
            assert results['total_files'] == 2
            assert len(results['successful']) == 1
            assert len(results['failed']) == 1
            
            # Check results
            assert results['successful'][0]['doc_id'] == 'doc_id_1'
            assert 'Upload failed' in results['failed'][0]['error']
    
    def test_perform_batch_upload_with_errors_no_skip(self, mock_cli_instance):
        """Test batch upload with errors and skip_errors=False."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Create test files
            file1 = tmp_path / 'file1.txt'
            file2 = tmp_path / 'file2.md'
            file1.write_text('content1')
            file2.write_text('content2')
            
            files = [file1, file2]
            
            # Mock first success, second failure
            def upload_side_effect(file_path, metadata=None, category=None, tags=None):
                if 'file2.md' in str(file_path):
                    raise DocumentManagerError("Upload failed")
                return 'doc_id_1'
            
            mock_cli_instance.document_manager.upload_document.side_effect = upload_side_effect
            
            # Execute
            from ai_agent.models.document import DocumentCategory
            results = _perform_batch_upload(
                mock_cli_instance, files, {}, DocumentCategory.GENERAL, [], skip_errors=False
            )
            
            # Verify - should stop at first error
            assert results['total_files'] == 2
            assert len(results['successful']) == 1
            assert len(results['failed']) == 1


class TestBatchUploadIntegration:
    """Integration tests for batch upload functionality."""
    
    def test_batch_upload_integration(self):
        """Test end-to-end batch upload integration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Create test files
            (tmp_path / 'doc1.txt').write_text('Document 1 content')
            (tmp_path / 'doc2.md').write_text('# Document 2\nMarkdown content')
            
            # Create subdirectory
            sub_dir = tmp_path / 'subdir'
            sub_dir.mkdir()
            (sub_dir / 'doc3.txt').write_text('Document 3 content')
            
            # Test file discovery
            files_non_recursive = _find_files_for_batch_upload(
                str(tmp_path), '*.txt,*.md', False
            )
            assert len(files_non_recursive) == 2
            
            files_recursive = _find_files_for_batch_upload(
                str(tmp_path), '*.txt,*.md', True
            )
            assert len(files_recursive) == 3
            
            # Verify file names
            file_names = [f.name for f in files_recursive]
            assert 'doc1.txt' in file_names
            assert 'doc2.md' in file_names
            assert 'doc3.txt' in file_names


if __name__ == '__main__':
    pytest.main([__file__])