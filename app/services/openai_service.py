"""
OpenAI Service for document transformation.

This module provides a service for transforming documents using OpenAI's API
with template-based document transformation.
"""

import os
import logging
import json
import requests
from typing import Dict, Any, Optional, List
import time
from dotenv import load_dotenv

# Set up logging first so we can use it
logger = logging.getLogger(__name__)

# Conditionally load environment variables only if OPENAI_API_KEY is not set
if not os.getenv("OPENAI_API_KEY"):
    try:
        logger.info("OPENAI_API_KEY not found in environment, attempting to load from .env file")
        load_dotenv()
    except Exception as e:
        logger.warning(f"Could not load .env file, using environment variables only: {e}")

class OpenAIService:
    """Service for OpenAI API interactions"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the OpenAI service
        
        Args:
            api_key: The OpenAI API key. If not provided, will try to get from environment variable
        """
        # Get API key from parameter, environment variable, or .env file (loaded by load_dotenv())
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API key not found. Service will not work without a valid key.")
        
        # API configuration
        self.api_url = "https://api.openai.com/v1/chat/completions"
        
        # Get model and other parameters from environment variables or use defaults
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")  # Default to GPT-4o which has larger context
        self.temperature = float(os.environ.get("OPENAI_TEMPERATURE", "0.3"))
        
        logger.info(f"OpenAI Service initialized with model: {self.model}, temperature: {self.temperature}")
        # Don't log API key for security reasons
    
    def transform_document(
        self,
        document_content: str,
        template_input_content: str,
        template_output_content: str,
        document_format: str,
        template_input_format: str,
        template_output_format: str,
        document_title: str = "",
        template_input_title: str = "",
        template_output_title: str = "",
        document_type: str = "other"
    ) -> str:
        """Transform a document using input/output template examples with OpenAI
        
        Args:
            document_content: The content of the document to transform
            template_input_content: The content of the input template
            template_output_content: The content of the output template
            document_format: File extension of the document
            template_input_format: File extension of the input template
            template_output_format: File extension of the output template
            document_title: Title of the document to transform
            template_input_title: Title of the input template
            template_output_title: Title of the output template
            
        Returns:
            str: The transformed document content
        """
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Cannot perform transformation.")
        
        # Content chunking strategy to handle large documents
        # GPT-4o has about 128K token capacity
        
        # For repo document type (depositions), use a higher limit since we need the full text
        if document_type == "repo":
            max_document_chars = 100000  # Increased limit for deposition documents
            max_template_chars = 5000    # Reduced template chars to compensate
        else:
            max_document_chars = 50000   # Default limit for other document types
            max_template_chars = 10000   # Default template limit
        
        # Check document and template lengths
        original_doc_length = len(document_content)
        original_input_template_length = len(template_input_content)
        original_output_template_length = len(template_output_content)
        
        # Truncate templates if needed
        if len(template_input_content) > max_template_chars:
            template_input_content = template_input_content[:max_template_chars] + "\n...[content truncated]"
            logger.warning(f"Input template truncated from {original_input_template_length} to {max_template_chars} characters")
        
        if len(template_output_content) > max_template_chars:
            template_output_content = template_output_content[:max_template_chars] + "\n...[content truncated]"
            logger.warning(f"Output template truncated from {original_output_template_length} to {max_template_chars} characters")
        
        # Create the system prompt with document type
        system_prompt = self._create_system_prompt(
            document_format, template_input_format, template_output_format, document_type
        )
        
        # Check if document needs chunking (larger than max_document_chars)
        if len(document_content) > max_document_chars:
            logger.info(f"Document size ({original_doc_length} chars) exceeds limit ({max_document_chars} chars). Using document chunking.")
            return self._process_document_in_chunks(
                document_content=document_content,
                template_input_content=template_input_content,
                template_output_content=template_output_content,
                document_format=document_format,
                template_input_format=template_input_format,
                template_output_format=template_output_format,
                document_title=document_title,
                template_input_title=template_input_title,
                template_output_title=template_output_title,
                document_type=document_type,
                system_prompt=system_prompt,
                max_document_chars=max_document_chars
            )
        
        # If document is small enough, process it normally without chunking
        # Create the user prompt with document content and templates
        user_prompt = self._create_user_prompt(
            document_content, template_input_content, template_output_content,
            document_title, template_input_title, template_output_title
        )
        
        # Log the prompts for debugging (without the full document content for brevity)
        logger.info(f"Using system prompt: {system_prompt}")
        logger.info(f"Using user prompt template structure for document transformation")
        logger.info(f"Document size: {len(document_content)} chars, Input template: {len(template_input_content)} chars, Output template: {len(template_output_content)} chars")
        
        # Call the OpenAI API
        try:
            start_time = time.time()
            response = self._call_openai_api(system_prompt, user_prompt)
            end_time = time.time()
            
            logger.info(f"OpenAI API call completed in {end_time - start_time:.2f} seconds")
            
            # Return the parsed response (which should be a dict with file_type and content)
            return response
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            
            # If context length exceeded error, try with more aggressive truncation
            if "context_length_exceeded" in str(e):
                try:
                    logger.warning("Context length exceeded, retrying with more aggressive truncation")
                    
                    # More aggressive truncation
                    further_max_document_chars = max_document_chars // 2
                    further_max_template_chars = max_template_chars // 2
                    
                    document_content_retry = document_content[:further_max_document_chars] + "\n...[content truncated]"
                    template_input_content_retry = template_input_content[:further_max_template_chars] + "\n...[content truncated]"
                    template_output_content_retry = template_output_content[:further_max_template_chars] + "\n...[content truncated]"
                    
                    # Create new prompt with truncated content
                    user_prompt_retry = self._create_user_prompt(
                        document_content_retry, 
                        template_input_content_retry, 
                        template_output_content_retry,
                        document_title, template_input_title, template_output_title
                    )
                    
                    logger.info("Retrying with truncated content")
                    # For the retry, we're using the same system prompt which already has the document type
                    response_retry = self._call_openai_api(system_prompt, user_prompt_retry)
                    
                    # Create truncation info
                    truncation_info = {
                        "original_document_length": original_doc_length,
                        "processed_document_length": len(document_content_retry),
                        "original_input_template_length": original_input_template_length,
                        "processed_input_template_length": len(template_input_content_retry),
                        "original_output_template_length": original_output_template_length,
                        "processed_output_template_length": len(template_output_content_retry),
                        "aggressive_truncation": True
                    }
                    
                    # Add truncation info 
                    response_retry["truncation_info"] = truncation_info
                    
                    # Add truncation note for non-repo documents only
                    if document_type != "repo" and isinstance(response_retry, dict) and "content" in response_retry:
                        truncation_note = (
                            "\n\n[NOTE: Content was significantly truncated due to token limits. "
                            "The original document was " + str(original_doc_length) + " characters, but was reduced to " + 
                            str(len(document_content_retry)) + " characters for processing.]"
                        )
                        response_retry["content"] = response_retry["content"] + truncation_note
                    
                    return response_retry
                    
                except Exception as retry_error:
                    # Handle case where retry response isn't properly formatted
                    logger.error(f"Error on retry with truncated content: {retry_error}")
                    try:
                        # Try to use whatever we got from the retry
                        content = str(response_retry)
                        if document_type != "repo":
                            content += "\n\n[NOTE: Content was significantly truncated due to token limits.]"
                        
                        return {
                            "file_type": "txt",
                            "content": content,
                            "truncation_info": truncation_info,
                            "parse_error": "The API retry response wasn't properly formatted"
                        }
                    except:
                        raise ValueError(f"Document is too large to process even after truncation: {retry_error}")
            
            raise
            
    def _process_document_in_chunks(
        self,
        document_content: str,
        template_input_content: str,
        template_output_content: str,
        document_format: str,
        template_input_format: str,
        template_output_format: str,
        document_title: str,
        template_input_title: str,
        template_output_title: str,
        document_type: str,
        system_prompt: str,
        max_document_chars: int
    ) -> Dict[str, Any]:
        """Process a document by splitting it into 5 equal chunks and concatenating results
        
        Args:
            document_content: The full document content
            template_input_content: The input template content
            template_output_content: The output template content
            document_format: The document format (extension)
            template_input_format: The input template format
            template_output_format: The output template format
            document_title: The document title
            template_input_title: The input template title
            template_output_title: The output template title
            document_type: The document type
            system_prompt: The system prompt
            max_document_chars: Maximum characters for each chunk
            
        Returns:
            Dict[str, Any]: The combined transformation result
        """
        logger.info(f"Processing document in 5 chunks")
        
        # Split document into 5 equal chunks
        doc_length = len(document_content)
        chunk_size = doc_length // 5
        
        # Create 5 chunks
        chunks = []
        for i in range(5):
            start = i * chunk_size
            # For the last chunk, include any remaining characters
            end = (i + 1) * chunk_size if i < 4 else doc_length
            chunk = document_content[start:end]
            chunks.append(chunk)
            logger.info(f"Chunk {i+1}: {len(chunk)} characters")
        
        # Create specific system prompt for chunked processing
        chunk_system_prompt = system_prompt + "\n\nIMPORTANT: You are processing part of a document that has been split into chunks. Focus only on transforming this chunk according to the template formats."
        
        # Process each chunk
        chunk_results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/5")
            
            # Create user prompt for this chunk
            chunk_user_prompt = self._create_user_prompt(
                chunk, template_input_content, template_output_content,
                f"{document_title} (Part {i+1}/5)", template_input_title, template_output_title
            )
            
            # Process the chunk
            try:
                start_time = time.time()
                result = self._call_openai_api(chunk_system_prompt, chunk_user_prompt)
                duration = time.time() - start_time
                logger.info(f"Chunk {i+1}/5 processed in {duration:.2f} seconds")
                chunk_results.append(result)
            except Exception as e:
                logger.error(f"Error processing chunk {i+1}/5: {e}")
                # Add error placeholder for this chunk
                chunk_results.append({
                    "file_type": template_output_format.lstrip("."),
                    "content": f"[Error processing part {i+1}/5: {str(e)}]",
                    "error": str(e)
                })
        
        # Combine results
        combined_result = self._combine_chunk_results(chunk_results, document_type, template_output_format)
        
        # Add metadata about chunking
        combined_result["chunking_info"] = {
            "original_document_length": doc_length,
            "chunks": 5,
            "chunk_sizes": [len(chunk) for chunk in chunks],
            "chunks_processed": len(chunk_results),
            "chunks_with_errors": sum(1 for r in chunk_results if "error" in r)
        }
        
        return combined_result
    
    def _combine_chunk_results(
        self, 
        chunk_results: List[Dict[str, Any]], 
        document_type: str,
        template_output_format: str
    ) -> Dict[str, Any]:
        """Combine results from multiple chunks into a single result
        
        Args:
            chunk_results: List of results from individual chunks
            document_type: The document type
            template_output_format: The output template format
            
        Returns:
            Dict[str, Any]: The combined result
        """
        logger.info(f"Combining results from {len(chunk_results)} chunks")
        
        # Initialize with metadata from the first chunk
        combined_result = {
            "file_type": chunk_results[0].get("file_type", template_output_format.lstrip(".")),
            "content": "",
        }
        
        # Handle different output formats
        file_type = combined_result["file_type"].lower()
        
        # Special handling for CSV format - keep header from first chunk, skip headers in remaining chunks
        if file_type == "csv" and document_type == "repo":
            # For repo type (deposition), we need special handling for the CSV
            # First chunk contains metadata rows that need to be preserved
            lines = []
            header_line = None
            
            # Process first chunk to extract headers
            first_chunk_lines = chunk_results[0].get("content", "").splitlines()
            if len(first_chunk_lines) >= 1:
                header_line = first_chunk_lines[0]  # CSV header row
                lines.extend(first_chunk_lines)  # Include all lines from first chunk
            
            # Process remaining chunks, skipping header rows if present
            for i, result in enumerate(chunk_results[1:], 1):
                chunk_lines = result.get("content", "").splitlines()
                if len(chunk_lines) >= 1 and header_line and chunk_lines[0] == header_line:
                    # Skip header row in subsequent chunks
                    chunk_lines = chunk_lines[1:]
                lines.extend(chunk_lines)
            
            combined_result["content"] = "\n".join(lines)
            
        elif file_type == "csv":
            # For regular CSV, similar approach but simpler
            lines = []
            header_line = None
            
            # Process first chunk to extract headers
            first_chunk_lines = chunk_results[0].get("content", "").splitlines()
            if len(first_chunk_lines) >= 1:
                header_line = first_chunk_lines[0]  # CSV header row
                lines.extend(first_chunk_lines)  # Include all lines from first chunk
            
            # Process remaining chunks, skipping header rows if present
            for i, result in enumerate(chunk_results[1:], 1):
                chunk_lines = result.get("content", "").splitlines()
                if len(chunk_lines) >= 1 and header_line and chunk_lines[0] == header_line:
                    # Skip header row in subsequent chunks
                    chunk_lines = chunk_lines[1:]
                lines.extend(chunk_lines)
            
            combined_result["content"] = "\n".join(lines)
            
        else:
            # For other formats, simple concatenation with section markers
            sections = []
            for i, result in enumerate(chunk_results):
                content = result.get("content", "")
                sections.append(content)
            
            combined_result["content"] = "\n\n".join(sections)
        
        logger.info(f"Combined result generated with {len(combined_result['content'])} characters")
        return combined_result
    
    def _create_system_prompt(
        self, document_format: str, template_input_format: str, template_output_format: str, document_type: str = "other"
    ) -> str:
        """Create the system prompt for the OpenAI API
        
        Args:
            document_format: File extension of the document
            template_input_format: File extension of the input template
            template_output_format: File extension of the output template
            document_type: Type of document (legal, real_estate, contract, lease, other)
            
        Returns:
            str: The system prompt
        """
        # Base prompt
        base_prompt = (
            "You are an expert document transformation assistant that helps convert documents "
            "from one format to another based on template examples.\n\n"
            
            "You will be provided with three documents:\n"
            "1. INPUT DOCUMENT: The document that needs to be transformed\n"
            "2. INPUT TEMPLATE: A template example in a similar format to the input document\n"
            "3. OUTPUT TEMPLATE: A template showing the desired output format\n\n"
            
            f"The input document is in {document_format} format.\n"
            f"The input template is in {template_input_format} format.\n"
            f"The output template is in {template_output_format} format.\n"
            f"The document type is: {document_type}\n\n"
        )
        
        # Document type specific instructions
        type_specific_instructions = {
            "legal": (
                "As you're working with a legal document, pay special attention to:\n"
                "- Legal terminology and phrasing\n"
                "- Citation formats and references to statutes, cases, or regulations\n"
                "- Formal document structure including sections, clauses and numbered paragraphs\n"
                "- Dates, parties, and defined terms which should be preserved exactly\n"
                "- Any disclaimers or warnings that should be maintained\n\n"
            ),
            "real_estate": (
                "As you're working with a real estate document, pay special attention to:\n"
                "- Property descriptions and addresses\n"
                "- Financial figures, prices, and payment terms\n"
                "- Dates of transactions, inspections, and closings\n"
                "- Party names and their roles (buyer, seller, agent, etc.)\n"
                "- Any contingencies or conditions mentioned\n\n"
            ),
            "contract": (
                "As you're working with a contract, pay special attention to:\n"
                "- Parties to the agreement and their obligations\n"
                "- Terms and conditions, especially regarding payment and deliverables\n"
                "- Timeframes, deadlines, and effective dates\n"
                "- Warranties, representations, and indemnities\n"
                "- Termination clauses and dispute resolution procedures\n\n"
            ),
            "lease": (
                "As you're working with a lease agreement, pay special attention to:\n"
                "- Tenant and landlord information\n"
                "- Property details and condition statements\n"
                "- Lease terms, rent amounts, and payment schedules\n"
                "- Security deposits and fees\n"
                "- Maintenance responsibilities and terms for entry\n\n"
            ),
            "repo": (
                '''
                    You are turning a deposition transcript (PDF text or plaintext) into a UTF-8 CSV with exactly four columns in this order: (blank), From (Pg/Line), To (Pg/Line), Summary

                    ────────────────────────────────────────────────────────
                    │                │ From (Pg/Line) │ To (Pg/Line) │ Summary │  ← header row
                    ────────────────────────────────────────────────────────

                    STEP 1 – Fixed Metadata Rows

                    • Row 2, Column 1 = <Witness Name>      (all other columns must be blank)
                    • Row 3, Column 1 = <Depo Date>         (e.g., 28-Aug-23)
                    • Row 4, Column 1 = <Depo Type>         (e.g., “Video Depo”)
                      ↳ Extract these three values from the transcript header. Leave blank if missing.

                    *Example*  
                    Header shows: “REMOTE VIDEO CONFERENCE DEPOSITION OF KRISTINA WARD ENGEL – Monday, August 28, 2023”  
                    → Row 2 = Kristina Ward Engel  
                    → Row 3 = 28-Aug-23  
                    → Row 4 = Video Depo  

                    STEP 2 – Fact Blocks

                    Starting from Row 5, each row captures a coherent fact block (a continuous section discussing a single idea).

                    • Column 1: Leave blank  
                    • Column 2: First Pg/Line (e.g., 6/9)  
                    • Column 3: Last Pg/Line (e.g., 7/2)  
                    • Column 4: Summary  
                      - Must be in plain English  
                      - Present tense only
                      - **The entire summary must go in this one cell (Column 4 only)**  
                      - **Do NOT split summary across multiple rows or columns**  
                      - **Do NOT include line breaks**  
                      - **Do NOT include ANY commas — not even in addresses, lists, or numbers**  
                        → Replace commas with semicolons or rephrase the sentence

                    ✅ Correct:
                    ,11/22,12/5,The board has always required buyer approval; she saw roughly four applications while she was a director

                    ✅ Also Correct (no commas in address):
                    ,6/9,7/2,She lives in Unit 302 of the Inlet Building and also resides part of the year in Lake Forest Illinois

                    ❌ Incorrect (uses commas or spans multiple lines):
                    ,11/22,12/5,The board has always required buyer approval;  
                    ,she saw roughly four applications while she was a director

                    ❌ Incorrect (commas in address):
                    ,6/9,7/2,She lives in Unit 302, Inlet Building, and also resides in Lake Forest, IL

                    STEP 3 – Ordering & Formatting Rules

                    • Preserve original appearance order  
                    • Do NOT add or delete columns  
                    • Do NOT use quotes or extra commas  
                    • Do NOT include explanations or formatting notes in output  

                    STEP 4 – Important for Large Documents

                    • Process the ENTIRE transcript without skipping content  
                    • Do NOT add any truncation markers or headers  
                    • The output must be a clean, complete CSV file — no extra notes

                '''
            ),
            "other": (
                "Pay special attention to:\n"
                "- The document's main purpose and key points\n"
                "- Any structured data, tables, or lists\n"
                "- Important dates, names, and numerical values\n"
                "- The logical flow and organization of information\n\n"
            )
        }
        
        # Get the appropriate instructions or default to "other"
        type_instructions = type_specific_instructions.get(document_type, type_specific_instructions["other"])
        
        # Task instructions
        task_instructions = (
            "Your task is to recognize the structure and format of both the input document and input template, "
            "understand how they relate to each other, and then transform the input document to match "
            "the format of the output template. Preserve all relevant information from the input document "
            "while organizing it according to the output template structure.\n\n"
            
            f"You MUST return a valid JSON object with the following structure:\n"
            "{\n"
            f'  "file_type": "{template_output_format}",\n'
            '  "content": "The transformed document content"\n'
            "}\n\n"
            
            f"The 'file_type' should be '{template_output_format}' (without the dot).\n"
            f"The 'content' should contain the transformed document in {template_output_format} format.\n\n"
            
            "Important: Your entire response must be a single, valid JSON object that can be parsed. "
            "Do not include any explanations, comments, or text outside of the JSON object."
        )
        
        # Combine all parts
        return base_prompt + type_instructions + task_instructions
    
    def _create_user_prompt(
        self,
        document_content: str,
        template_input_content: str,
        template_output_content: str,
        document_title: str = "",
        template_input_title: str = "",
        template_output_title: str = ""
    ) -> str:
        """Create the user prompt with document content and templates
        
        Args:
            document_content: The content of the document to transform
            template_input_content: The content of the input template
            template_output_content: The content of the output template
            document_title: Title of the document to transform
            template_input_title: Title of the input template
            template_output_title: Title of the output template
            
        Returns:
            str: The user prompt
        """
        return (
            "Please transform the following document to match the format of the output template.\n\n"
            
            "# INPUT DOCUMENT" + (f" ({document_title})" if document_title else "") + ":\n"
            "```\n"
            f"{document_content}\n"
            "```\n\n"
            
            "# INPUT TEMPLATE" + (f" ({template_input_title})" if template_input_title else "") + ":\n"
            "```\n"
            f"{template_input_content}\n"
            "```\n\n"
            
            "# OUTPUT TEMPLATE" + (f" ({template_output_title})" if template_output_title else "") + ":\n"
            "```\n"
            f"{template_output_content}\n"
            "```\n\n"
            
            "The input document and input template are similar in format. Transform the input document "
            "to match the format of the output template. Return only the transformed content."
        )
    
    def _call_openai_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call the OpenAI API
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            
        Returns:
            Dict[str, Any]: The parsed JSON response with file_type and content
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,  # Uses temperature from config or environment
            "response_format": {"type": "json_object"}  # Request JSON response format
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=300  # Allow up to 5 minutes for the request
            )
            
            response.raise_for_status()  # Raise an exception for 4xx/5xx responses
            
            response_data = response.json()
            
            # Extract the assistant's message content
            if "choices" in response_data and len(response_data["choices"]) > 0:
                assistant_message = response_data["choices"][0]["message"]["content"]
                
                try:
                    # Parse the JSON response
                    parsed_response = json.loads(assistant_message)
                    
                    # Validate the response has the required structure
                    if "file_type" not in parsed_response or "content" not in parsed_response:
                        logger.warning(f"Incomplete API response, missing required fields: {parsed_response.keys()}")
                        # Create a valid response format even if the model's response is incomplete
                        parsed_response = {
                            "file_type": parsed_response.get("file_type", "txt"),
                            "content": parsed_response.get("content", assistant_message)
                        }
                    
                    return parsed_response
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in API response: {assistant_message[:100]}...")
                    # Return a fallback format if the response isn't valid JSON
                    return {
                        "file_type": "txt",
                        "content": assistant_message,
                        "parse_error": "The API response wasn't valid JSON"
                    }
            else:
                raise ValueError("Unexpected API response format")
            
        except requests.exceptions.HTTPError as e:
            # Handle API errors
            error_info = {}
            try:
                error_info = response.json()
            except:
                error_info = {"error": str(e)}
                
            logger.error(f"API error: {error_info}")
            raise ValueError(f"OpenAI API error: {error_info}")
        
        except Exception as e:
            logger.error(f"Error in API call: {e}")
            raise

# Create a singleton instance
openai_service = OpenAIService()