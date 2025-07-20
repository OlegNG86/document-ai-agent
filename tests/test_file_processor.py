"""Tests for file processor functionality."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from ai_agent.utils.file_processor import FileProcessor, FileProcessorError


class TestFileProcessor:
    """Test file processor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = FileProcessor()
    
    def test_supported_extensions(self):
        """Test supported extensions list."""
        extensions = self.processor.get_supported_extensions()
        expected = ['.txt', '.md', '.docx', '.pdf', '.rtf']
        assert all(ext in extensions for ext in expected)
    
    def test_is_supported_format(self):
        """Test format support checking."""
        assert self.processor.is_supported_format(Path('test.txt'))
        assert self.processor.is_supported_format(Path('test.md'))
        assert self.processor.is_supported_format(Path('test.docx'))
        assert self.processor.is_supported_format(Path('test.pdf'))
        assert self.processor.is_supported_format(Path('test.rtf'))
        assert not self.processor.is_supported_format(Path('test.doc'))
        assert not self.processor.is_supported_format(Path('test.xlsx'))
    
    def test_get_file_type_description(self):
        """Test file type descriptions."""
        assert self.processor.get_file_type_description(Path('test.txt')) == 'Plain Text'
        assert self.processor.get_file_type_description(Path('test.md')) == 'Markdown'
        assert self.processor.get_file_type_description(Path('test.docx')) == 'Microsoft Word Document'
        assert self.processor.get_file_type_description(Path('test.pdf')) == 'PDF Document'
        assert self.processor.get_file_type_description(Path('test.rtf')) == 'Rich Text Format'
    
    def test_extract_text_file_not_found(self):
        """Test extraction from non-existent file."""
        with pytest.raises(FileProcessorError) as exc_info:
            self.processor.extract_text(Path('nonexistent.txt'))
        assert 'File not found' in str(exc_info.value)
    
    def test_extract_text_unsupported_format(self):
        """Test extraction from unsupported format."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as tmp:
            tmp.write(b'test content')
            tmp_path = Path(tmp.name)
        
        try:
            with pytest.raises(FileProcessorError) as exc_info:
                self.processor.extract_text(tmp_path)
            assert 'Unsupported file format' in str(exc_info.value)
        finally:
            os.unlink(tmp_path)
    
    def test_extract_text_txt_file(self):
        """Test text extraction from TXT file."""
        test_content = "This is a test document.\nWith multiple lines.\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
            tmp.write(test_content)
            tmp_path = Path(tmp.name)
        
        try:
            content, metadata = self.processor.extract_text(tmp_path)
            assert content.strip() == test_content.strip()
            assert metadata['file_type'] == 'text'
            assert metadata['character_count'] == len(content)
            assert metadata['line_count'] == 2
        finally:
            os.unlink(tmp_path)
    
    def test_extract_text_markdown_file(self):
        """Test text extraction from Markdown file."""
        test_content = """# Header 1

This is a paragraph with [a link](http://example.com).

## Header 2

```python
print("code block")
```
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmp:
            tmp.write(test_content)
            tmp_path = Path(tmp.name)
        
        try:
            content, metadata = self.processor.extract_text(tmp_path)
            assert '# Header 1' in content
            assert 'a link' in content
            assert metadata['file_type'] == 'markdown'
            assert metadata['headers_count'] == 2
            assert metadata['links_count'] == 1
            assert metadata['code_blocks_count'] == 1
        finally:
            os.unlink(tmp_path)
    
    @patch('ai_agent.utils.file_processor.DocxDocument')
    def test_extract_text_docx_file(self, mock_docx):
        """Test text extraction from DOCX file."""
        # Mock DOCX document
        mock_doc = MagicMock()
        mock_para1 = MagicMock()
        mock_para1.text = "First paragraph"
        mock_para1._element = MagicMock()
        
        mock_para2 = MagicMock()
        mock_para2.text = "Second paragraph"
        mock_para2._element = MagicMock()
        
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_doc.tables = []
        mock_doc.sections = [MagicMock()]
        
        # Mock document body elements
        mock_element1 = MagicMock()
        mock_element1.tag = 'w:p'
        mock_element2 = MagicMock()
        mock_element2.tag = 'w:p'
        
        mock_doc.element.body = [mock_element1, mock_element2]
        
        # Mock core properties
        mock_doc.core_properties.title = "Test Document"
        mock_doc.core_properties.author = "Test Author"
        
        mock_docx.return_value = mock_doc
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            content, metadata = self.processor.extract_text(tmp_path)
            assert 'First paragraph' in content
            assert 'Second paragraph' in content
            assert metadata['file_type'] == 'docx'
            assert metadata['paragraph_count'] == 2
            assert metadata['tables_count'] == 0
            assert metadata['document_title'] == "Test Document"
            assert metadata['document_author'] == "Test Author"
        finally:
            os.unlink(tmp_path)
    
    @patch('ai_agent.utils.file_processor.PyPDF2')
    def test_extract_text_pdf_file(self, mock_pypdf2):
        """Test text extraction from PDF file."""
        # Mock PDF reader
        mock_reader = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_reader.pages = [mock_page1, mock_page2]
        mock_reader.is_encrypted = False
        mock_reader.metadata = {
            '/Title': 'Test PDF',
            '/Author': 'Test Author'
        }
        
        mock_pypdf2.PdfReader.return_value = mock_reader
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            content, metadata = self.processor.extract_text(tmp_path)
            assert '[PAGE 1]' in content
            assert 'Page 1 content' in content
            assert '[PAGE 2]' in content
            assert 'Page 2 content' in content
            assert metadata['file_type'] == 'pdf'
            assert metadata['pages_count'] == 2
            assert metadata['is_encrypted'] == False
            assert metadata['document_title'] == 'Test PDF'
            assert metadata['document_author'] == 'Test Author'
        finally:
            os.unlink(tmp_path)
    
    @patch('ai_agent.utils.file_processor.rtf_to_text')
    def test_extract_text_rtf_file(self, mock_rtf_to_text):
        """Test text extraction from RTF file."""
        rtf_content = r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}} \f0\fs24 Hello World!}"
        plain_text = "Hello World!"
        
        mock_rtf_to_text.return_value = plain_text
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rtf', delete=False, encoding='utf-8') as tmp:
            tmp.write(rtf_content)
            tmp_path = Path(tmp.name)
        
        try:
            content, metadata = self.processor.extract_text(tmp_path)
            assert content == plain_text
            assert metadata['file_type'] == 'rtf'
            assert metadata['original_rtf_size'] == len(rtf_content)
            mock_rtf_to_text.assert_called_once_with(rtf_content)
        finally:
            os.unlink(tmp_path)
    
    def test_clean_text(self):
        """Test text cleaning functionality."""
        dirty_text = "  Line 1  \n\n\n\n  Line 2  \t\t\n\n\n  Line 3  "
        clean_text = self.processor._clean_text(dirty_text)
        
        expected = "Line 1\n\nLine 2\n\nLine 3"
        assert clean_text == expected
    
    def test_validate_extracted_text(self):
        """Test text validation."""
        # Valid text
        assert self.processor.validate_extracted_text("This is valid text content")
        
        # Empty text
        assert not self.processor.validate_extracted_text("")
        assert not self.processor.validate_extracted_text("   ")
        
        # Too short text
        assert not self.processor.validate_extracted_text("short")
        
        # Text with too many non-printable characters
        bad_text = "a" + "\x00" * 100 + "b"
        assert not self.processor.validate_extracted_text(bad_text)
    
    def test_show_extracted_text_option(self):
        """Test show extracted text option."""
        processor_with_show = FileProcessor(show_extracted_text=True)
        assert processor_with_show.show_extracted_text == True
        
        processor_without_show = FileProcessor(show_extracted_text=False)
        assert processor_without_show.show_extracted_text == False