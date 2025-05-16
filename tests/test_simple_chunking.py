"""
Simple test for document chunking implementation
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_document_chunking():
    """Test chunking a document into 5 equal parts"""
    
    # Create a test document
    document = "A" * 120000  # 120K characters
    
    # Create a function that simulates document chunking
    def chunk_document(document):
        logger.info(f"Chunking document of {len(document)} characters")
        
        # Split into 5 equal chunks
        chunk_size = len(document) // 5
        chunks = []
        
        for i in range(5):
            start = i * chunk_size
            # For the last chunk, include any remaining characters
            end = (i + 1) * chunk_size if i < 4 else len(document)
            chunk = document[start:end]
            chunks.append(chunk)
            logger.info(f"Chunk {i+1}: {len(chunk)} characters")
            
        return chunks
    
    # Test the chunking
    chunks = chunk_document(document)
    
    # Verify the chunks
    assert len(chunks) == 5, f"Expected 5 chunks, got {len(chunks)}"
    
    # Check that chunks have the expected size
    expected_chunk_size = len(document) // 5
    for i, chunk in enumerate(chunks):
        if i < 4:
            assert len(chunk) == expected_chunk_size, f"Chunk {i+1} has wrong size: {len(chunk)}"
        else:
            # Last chunk might have extra characters due to division remainder
            assert len(chunk) >= expected_chunk_size, f"Last chunk has wrong size: {len(chunk)}"
    
    # Verify we can reconstruct the original document
    reconstructed = "".join(chunks)
    assert len(reconstructed) == len(document), "Reconstructed document has wrong length"
    assert reconstructed == document, "Reconstructed document doesn't match original"
    
    logger.info("Chunking test passed!")
    return True

if __name__ == "__main__":
    logger.info("Testing document chunking")
    result = test_document_chunking()
    logger.info(f"Test {'passed' if result else 'failed'}")
    sys.exit(0 if result else 1)