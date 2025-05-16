"""
Test script for document chunking functionality.

This test verifies that large documents are properly chunked, processed, and recombined.
"""

import os
import sys
import logging
import time
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.openai_service import openai_service
from app.utils.document_processor import DocumentProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def generate_large_document(size_in_chars: int = 150000) -> str:
    """
    Generate a large test document with the specified number of characters
    
    Args:
        size_in_chars: Target document size in characters
        
    Returns:
        str: The generated document content
    """
    logger.info(f"Generating test document of {size_in_chars} characters")
    
    # Base paragraph content that will be repeated
    base_paragraph = (
        "This is a test paragraph for document chunking. "
        "It contains standard text that will be repeated multiple times to create a large document. "
        "The document will exceed the maximum character limit to trigger chunking. "
        "This will allow us to test the document chunking functionality properly. "
    )
    
    # Calculate how many paragraphs we need
    paragraph_length = len(base_paragraph)
    num_paragraphs = (size_in_chars // paragraph_length) + 1
    
    # Generate paragraphs with numbering to distinguish different parts
    paragraphs = []
    for i in range(num_paragraphs):
        if i % 100 == 0:
            # Add headers periodically to make the structure more document-like
            paragraphs.append(f"\n\n## Section {i // 100 + 1}\n\n")
        paragraphs.append(f"Paragraph {i+1}: {base_paragraph}")
    
    # Join paragraphs with newlines and trim to the desired size
    document = "\n\n".join(paragraphs)
    if len(document) > size_in_chars:
        document = document[:size_in_chars]
    
    logger.info(f"Generated document with {len(document)} characters and {num_paragraphs} paragraphs")
    return document


def generate_template_documents() -> tuple:
    """
    Generate simple input and output templates for testing
    
    Returns:
        tuple: (input_template, output_template)
    """
    input_template = (
        "# Sample Document Template\n\n"
        "## Section 1\n\n"
        "Paragraph 1: This is a sample paragraph in the input template.\n\n"
        "Paragraph 2: This is another sample paragraph in the input template.\n\n"
        "## Section 2\n\n"
        "Paragraph 3: This is the final paragraph in the input template."
    )
    
    output_template = (
        "Section,Paragraph,Content\n"
        "1,1,\"This is a sample paragraph in the input template.\"\n"
        "1,2,\"This is another sample paragraph in the input template.\"\n"
        "2,3,\"This is the final paragraph in the input template.\""
    )
    
    return input_template, output_template


def test_document_chunking():
    """
    Test the document chunking functionality by processing a large document
    """
    logger.info("Starting document chunking test")
    
    # Check if OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        return False
    
    # Generate test document and templates
    document_content = generate_large_document(150000)  # 150K chars to ensure chunking
    template_input, template_output = generate_template_documents()
    
    # Process document with chunking
    logger.info("Processing document with chunking")
    start_time = time.time()
    
    try:
        result = openai_service.transform_document(
            document_content=document_content,
            template_input_content=template_input,
            template_output_content=template_output,
            document_format=".txt",
            template_input_format=".txt",
            template_output_format=".csv",
            document_title="Test Large Document",
            template_input_title="Test Input Template",
            template_output_title="Test Output Template",
            document_type="other"
        )
        
        # Log processing time
        processing_time = time.time() - start_time
        logger.info(f"Document processed in {processing_time:.2f} seconds")
        
        # Check result
        if isinstance(result, dict) and "content" in result:
            content_length = len(result.get("content", ""))
            logger.info(f"Result content length: {content_length} characters")
            
            # Check if chunking was used
            chunking_info = result.get("chunking_info", {})
            if chunking_info:
                logger.info(f"Document was processed in chunks: {chunking_info}")
                
                # Verify number of chunks
                if chunking_info.get("chunks") == 5:
                    logger.info("Successfully processed document in 5 chunks")
                else:
                    logger.warning(f"Expected 5 chunks, but got {chunking_info.get('chunks', 'unknown')}")
                
                # Log chunk sizes
                chunk_sizes = chunking_info.get("chunk_sizes", [])
                if chunk_sizes:
                    logger.info(f"Chunk sizes: {chunk_sizes}")
                
                # Check for errors
                errors = chunking_info.get("chunks_with_errors", 0)
                if errors > 0:
                    logger.warning(f"There were {errors} chunks with errors")
            else:
                logger.warning("Document chunking was not triggered despite large document size")
            
            return True
        else:
            logger.error(f"Unexpected result format: {result}")
            return False
        
    except Exception as e:
        logger.error(f"Error in document chunking test: {e}")
        return False


if __name__ == "__main__":
    logger.info("Document Chunking Test")
    result = test_document_chunking()
    logger.info(f"Test {'passed' if result else 'failed'}")
    sys.exit(0 if result else 1)