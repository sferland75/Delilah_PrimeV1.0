"""
Delilah Prime - Claude API Integration Module

This module handles communication with the Claude API for narrative generation
while ensuring no PHI is transmitted.
"""

import os
import json
import requests
import time
from pathlib import Path
import threading

# Global lock for section processing
section_locks = {}
# Global set to track sections being processed
processing_sections = set()

class ClaudeAPIClient:
    """Client for interacting with Claude API to enhance clinical report narratives."""
    
    def __init__(self, config_path=None):
        """
        Initialize the Claude API client.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.json"
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.api_config = config['api']
        self.api_key = os.environ.get("CLAUDE_API_KEY")
        
        # Rate limiting configuration
        self.last_request_time = 0
        self.min_request_interval = 10  # Seconds
        self.max_retries = 3
        self.initial_retry_delay = 20  # Seconds
        self.concurrent_request = False  # Flag to avoid concurrent requests
        
        if not self.api_key:
            print("Warning: CLAUDE_API_KEY environment variable not set")
    
    def prepare_prompt(self, section_name, content):
        """
        Prepare a prompt for the Claude API based on the section and content.
        
        Args:
            section_name: Name of the report section
            content: De-identified content for this section
            
        Returns:
            Formatted prompt for Claude API
        """
        # Format the section name for readability
        formatted_section = section_name.replace('_', ' ').title()
        
        # Define section-specific guidance
        section_guidance = {
            "case_synopsis": "Provide a concise overview of the client's situation, reason for referral, and general assessment purpose. Focus on clarity and context.",
            "background_information": "Organize relevant history chronologically. Highlight key events that impact current function. Include relevant personal, medical, and vocational history.",
            "assessment_methodology": "Detail evaluation methods with specific tests performed and standardized measures. Describe the assessment environment and any adaptations made.",
            "functional_observations": "Present objective findings in clear categories (physical, cognitive, emotional). Link observations to functional impact and daily activities.",
            "activities_of_daily_living": "Structure by activity type (self-care, instrumental ADLs, etc.). For each activity, describe current ability, limitations, and adaptations.",
            "social_functioning": "Describe interpersonal capabilities, community integration, and support systems. Note changes from pre-injury/illness baseline if mentioned.",
            "concentration_persistence_pace": "Detail attentional capacity, task sustainability, and work rhythm. Include specific examples of performance limitations and strengths.",
            "adaptability_work_settings": "Analyze ability to adapt to various environments and respond to workplace demands. Note specific accommodations that may be beneficial.",
            "summary_recommendations": "Synthesize key findings and provide clear, specific recommendations tied directly to assessment results. Prioritize recommendations by importance."
        }
        
        # Get guidance for this section, or use default if not found
        guidance = section_guidance.get(section_name, "Organize content logically and enhance clarity while maintaining all clinical information.")
        
        # Create a prompt that instructs Claude on the task
        prompt = f"""
You are an expert clinical documentation specialist with extensive experience in occupational therapy and medico-legal report writing. Your task is to enhance the following {formatted_section} section of a clinical report.

## IMPORTANT GUIDELINES

1. MAINTAIN ALL PLACEHOLDERS: The content has been de-identified, with placeholders like [NAME_abc123] or [DATE_xyz789]. You MUST preserve these placeholders EXACTLY as they appear.

2. CLINICAL LANGUAGE: Use precise, professional terminology appropriate for occupational therapy assessments, while maintaining clarity for non-clinical readers.

3. NARRATIVE STRUCTURE:
   - Create smooth transitions between paragraphs
   - Use appropriate headings and subheadings for organization
   - Maintain a logical flow from observations to clinical interpretations
   - Present information in order of clinical relevance

4. CONTENT REQUIREMENTS:
   - Preserve all factual information and clinical data from the original
   - Do not introduce new medical facts, diagnoses, or clinical interpretations
   - When describing functional limitations, clearly connect them to activities of daily living
   - For assessments, clearly differentiate between objective findings and clinical impressions

5. STYLE AND TONE:
   - Maintain objective, evidence-based language
   - Use active voice where appropriate
   - Avoid redundancy and unnecessary repetition
   - Eliminate vague or ambiguous statements
   - Ensure statements are supported by the information provided

6. SECTION-SPECIFIC GUIDANCE:
{guidance}

## ORIGINAL CONTENT TO ENHANCE:

{content}

## TASK:

Please rewrite the {formatted_section} section, adhering to all guidelines above. Your response should be a cohesive, well-structured narrative ready to be integrated into a professional clinical report. Maintain all clinical accuracy while improving readability and professional quality.
"""
        return prompt
    
    def generate_custom_narrative(self, section_name, content, custom_prompt_template):
        """
        Generate an enhanced narrative using a custom prompt template.
        
        Args:
            section_name: Name of the report section
            content: De-identified content for this section
            custom_prompt_template: Custom prompt template with {section} and {content} placeholders
            
        Returns:
            Enhanced narrative content
        """
        if not self.api_key:
            print(f"Skipping enhancement for {section_name} - API key not set")
            return content
        
        # Format the section name for readability
        formatted_section = section_name.replace('_', ' ').title()
        
        # Replace placeholders in the custom prompt
        custom_prompt = custom_prompt_template.replace("{section}", formatted_section).replace("{content}", content)
        
        # Call the API with the custom prompt
        return self._call_claude_api(custom_prompt, section_name)
    
    def _wait_for_rate_limit(self):
        """
        Implement rate limiting by waiting between API calls.
        Ensures we don't exceed Claude API's rate limits.
        """
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        # If we've made a request recently, wait until minimum interval has passed
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            print(f"Rate limiting: Waiting {wait_time:.1f} seconds before next API call...")
            time.sleep(wait_time)
        
        # Update last request time
        self.last_request_time = time.time()
    
    def generate_narrative(self, section_name, content):
        """
        Generate an enhanced narrative for a report section using Claude API.
        Implements rate limiting and retries for rate limit errors.
        
        Args:
            section_name: Name of the report section
            content: De-identified content for this section
            
        Returns:
            Enhanced narrative content
        """
        if not self.api_key:
            print(f"Skipping enhancement for {section_name} - API key not set")
            return content

        # Use a unique identifier for the content to prevent duplicate processing
        content_id = f"{section_name}_{hash(content)}"
        
        # Check if this section is already being processed
        if content_id in processing_sections:
            print(f"⚠ Section {section_name} is already being processed elsewhere. Skipping duplicate.")
            return content
            
        # Acquire a lock for this section to prevent concurrent processing
        if section_name not in section_locks:
            section_locks[section_name] = threading.Lock()
            
        # Try to acquire the lock, but don't block if it's already locked
        if not section_locks[section_name].acquire(blocking=False):
            print(f"⚠ Another thread is processing section {section_name}. Skipping duplicate.")
            return content
            
        try:
            # Add to the set of processing sections
            processing_sections.add(content_id)
        
            # Format section name for logging
            formatted_section = section_name.replace('_', ' ').title()
            print(f"\n==== PROCESSING SECTION: {formatted_section} ====")
            
            # Cache the response to avoid duplicate processing
            cache_key = f"{section_name}_{hash(content)}"
            cache_file = Path(__file__).parent.parent.parent / "cache" / f"{cache_key}.txt"
            
            # Check if we have a cached result
            if cache_file.parent.exists() and cache_file.exists():
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_content = f.read()
                    print(f"✓ Using cached results for {formatted_section}")
                    return cached_content
                except Exception as e:
                    print(f"✗ Error reading cache: {str(e)}")
            
            # If content is very large, split it into chunks
            max_chunk_size = 6000  # Characters per chunk
            if len(content) > max_chunk_size:
                # Split content into smaller chunks
                chunks = self._split_content_into_chunks(content, max_chunk_size)
                total_chunks = len(chunks)
                print(f"→ Section {formatted_section} split into {total_chunks} chunks due to size")
                
                # Process each chunk sequentially
                enhanced_chunks = []
                for i, chunk in enumerate(chunks):
                    chunk_num = i + 1
                    print(f"\n-- Processing chunk {chunk_num}/{total_chunks} for {formatted_section} --")
                    
                    # Create a unique cache key for this chunk
                    chunk_cache_key = f"{section_name}_chunk{chunk_num}_{hash(chunk)}"
                    chunk_cache_file = Path(__file__).parent.parent.parent / "cache" / f"{chunk_cache_key}.txt"
                    
                    # Check if we have a cached result for this chunk
                    if chunk_cache_file.parent.exists() and chunk_cache_file.exists():
                        try:
                            with open(chunk_cache_file, 'r', encoding='utf-8') as f:
                                cached_chunk = f.read()
                            print(f"✓ Using cached results for chunk {chunk_num}/{total_chunks}")
                            enhanced_chunks.append(cached_chunk)
                            continue
                        except Exception as e:
                            print(f"✗ Error reading chunk cache: {str(e)}")
                    
                    # Prepare the prompt for this chunk with context about chunking
                    chunk_prompt = self._prepare_chunk_prompt(section_name, chunk, chunk_num, total_chunks)
                    
                    # Call the API and handle potential rate limits with retries
                    enhanced_chunk = self._call_claude_api(chunk_prompt, f"{section_name} chunk {chunk_num}")
                    
                    # If we got a valid response
                    if enhanced_chunk and enhanced_chunk != chunk_prompt:
                        enhanced_chunks.append(enhanced_chunk)
                        
                        # Cache the result for this chunk
                        try:
                            os.makedirs(chunk_cache_file.parent, exist_ok=True)
                            with open(chunk_cache_file, 'w', encoding='utf-8') as f:
                                f.write(enhanced_chunk)
                            print(f"✓ Cached chunk {chunk_num}/{total_chunks}")
                        except Exception as e:
                            print(f"✗ Error writing chunk cache: {str(e)}")
                    else:
                        # If API failed, use original content
                        print(f"! Using original content for chunk {chunk_num}/{total_chunks} due to API failure")
                        enhanced_chunks.append(chunk)
                
                # Combine the enhanced chunks
                print(f"\n✓ Combining {len(enhanced_chunks)} enhanced chunks for {formatted_section}")
                combined_content = self._combine_enhanced_chunks(enhanced_chunks)
                
                # Cache the combined result
                try:
                    os.makedirs(cache_file.parent, exist_ok=True)
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        f.write(combined_content)
                    print(f"✓ Cached complete section: {formatted_section}")
                except Exception as e:
                    print(f"✗ Error writing cache: {str(e)}")
                    
                return combined_content
            else:
                # Process normal-sized content
                print(f"→ Processing entire section (single chunk)")
                prompt = self.prepare_prompt(section_name, content)
                result = self._call_claude_api(prompt, section_name)
                
                # If we got a valid response
                if result and result != prompt:
                    # Cache the result
                    try:
                        os.makedirs(cache_file.parent, exist_ok=True)
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            f.write(result)
                        print(f"✓ Cached section: {formatted_section}")
                    except Exception as e:
                        print(f"✗ Error writing cache: {str(e)}")
                    
                    return result
                else:
                    # If API failed, use original content
                    print(f"! Using original content for {formatted_section} due to API failure")
                    return content
        finally:
            # Always release resources
            processing_sections.discard(content_id)
            section_locks[section_name].release()
    
    def _split_content_into_chunks(self, content, max_chunk_size):
        """
        Split large content into chunks at logical break points.
        
        Args:
            content: The content to split
            max_chunk_size: Maximum size of each chunk
            
        Returns:
            List of content chunks
        """
        # Try to split at paragraph breaks
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # If adding this paragraph would exceed max size, start a new chunk
            if len(current_chunk) + len(para) + 2 > max_chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)
        
        # If any chunks are still too large, split them further
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > max_chunk_size:
                # Split at sentence boundaries
                sentences = []
                for para in chunk.split('\n\n'):
                    # Basic sentence splitting (not perfect but good enough)
                    para_sentences = para.replace('. ', '.\n').replace('! ', '!\n').replace('? ', '?\n').split('\n')
                    sentences.extend([s + ' ' for s in para_sentences if s])
                
                sub_chunk = ""
                for sentence in sentences:
                    if len(sub_chunk) + len(sentence) > max_chunk_size and sub_chunk:
                        final_chunks.append(sub_chunk)
                        sub_chunk = sentence
                    else:
                        sub_chunk += sentence
                
                if sub_chunk:
                    final_chunks.append(sub_chunk)
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def _prepare_chunk_prompt(self, section_name, chunk, chunk_num, total_chunks):
        """
        Prepare a prompt for processing a chunk of content.
        
        Args:
            section_name: Name of the report section
            chunk: The content chunk
            chunk_num: The current chunk number
            total_chunks: Total number of chunks
            
        Returns:
            Formatted prompt for Claude API
        """
        # Format the section name for readability
        formatted_section = section_name.replace('_', ' ').title()
        
        # Create a prompt that instructs Claude on the chunk processing task
        prompt = f"""
You are an expert clinical documentation specialist enhancing a {formatted_section} section that has been split into {total_chunks} parts due to length. This is part {chunk_num} of {total_chunks}.

## IMPORTANT GUIDELINES

1. MAINTAIN ALL PLACEHOLDERS: The content has been de-identified, with placeholders like [NAME_abc123] or [DATE_xyz789]. You MUST preserve these placeholders EXACTLY as they appear.

2. CLINICAL LANGUAGE: Use precise, professional terminology appropriate for occupational therapy assessments, while maintaining clarity for non-clinical readers.

3. CONTENT INTEGRITY: 
   - Enhance only this chunk - don't worry about connections to other chunks
   - Maintain all clinical facts and information from the original
   - Do not introduce new medical facts or diagnoses
   - If a sentence is cut off, finish it naturally based on context

4. STYLE AND TONE:
   - Maintain objective, evidence-based language
   - Use active voice where appropriate
   - Eliminate redundancy and vague statements
   - Ensure statements are supported by the information provided

## ORIGINAL CHUNK {chunk_num}/{total_chunks} TO ENHANCE:

{chunk}

## TASK:

Provide an enhanced version of this chunk. Your response should improve clinical readability while maintaining all facts and placeholders exactly.
"""
        return prompt
    
    def _combine_enhanced_chunks(self, chunks):
        """
        Combine enhanced chunks into a cohesive narrative.
        
        Args:
            chunks: List of enhanced content chunks
            
        Returns:
            Combined narrative content
        """
        # Join chunks with paragraph breaks
        combined = "\n\n".join(chunks)
        
        # Fix any issues with consecutive paragraph breaks
        combined = combined.replace("\n\n\n\n", "\n\n")
        combined = combined.replace("\n\n\n", "\n\n")
        
        return combined
    
    def _call_claude_api(self, prompt, section_identifier):
        """
        Call the Claude API with rate limiting and retries.
        
        Args:
            prompt: The prepared prompt to send to Claude
            section_identifier: Name of section for logging
            
        Returns:
            Generated content or None on failure
        """
        # Return original if no API key
        if not self.api_key:
            return None
            
        # Check if we should wait before making a request
        self._apply_rate_limiting()
        
        # Track the current time
        self.last_request_time = time.time()
        
        # Try to make the API call with retries
        retry_count = 0
        max_retries = self.max_retries
        retry_delay = self.initial_retry_delay
        
        while retry_count <= max_retries:
            try:
                # Start with a reasonable timeout
                timeout = 60  # seconds
                
                headers = {
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                }
                
                data = {
                    "model": self.api_config["model"],
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": self.api_config["max_tokens"],
                    "temperature": 0.3  # Lower temperature for more consistent outputs
                }
                
                print(f"⟳ Sending API request for {section_identifier}...")
                
                response = requests.post(
                    self.api_config["endpoint"],
                    headers=headers,
                    json=data,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    # Success!
                    result = response.json()
                    generated_text = result['content'][0]['text']
                    print(f"✓ API request successful for {section_identifier} ({len(generated_text)} chars)")
                    return generated_text
                    
                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_count += 1
                    actual_retry_delay = retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                    
                    if retry_count <= max_retries:
                        print(f"⚠ Rate limit exceeded. Retrying in {actual_retry_delay} seconds (attempt {retry_count}/{max_retries})...")
                        time.sleep(actual_retry_delay)
                    else:
                        print(f"✗ Rate limit exceeded. Maximum retries reached for {section_identifier}.")
                        return None
                        
                else:
                    # Other error
                    print(f"✗ API error: {response.status_code} - {response.text}")
                    return None
                    
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"⚠ API request failed: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(f"✗ API request failed after {max_retries} retries: {str(e)}")
                    return None
        
        return None

    def _apply_rate_limiting(self):
        """Apply rate limiting before making an API call"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            wait_time = max(0, self.min_request_interval - elapsed)
            if wait_time > 0.1:  # Only log if waiting more than 0.1 seconds
                print(f"⏱️ Rate limiting: Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                
    def is_available(self):
        """Check if the Claude API is available and configured correctly."""
        return bool(self.api_key)


# Example usage
if __name__ == "__main__":
    # This would typically be set in the environment
    os.environ["CLAUDE_API_KEY"] = "your_api_key_here"
    
    client = ClaudeAPIClient()
    
    # Example content (de-identified)
    sample_content = """
    [PERSON_1] was involved in a motor vehicle accident on [DATE_1].
    Initial assessment shows:
    - Back pain rated 8/10
    - Difficulty with stair negotiation
    - Unable to maintain previous work as [OCCUPATION_1]
    - Lives with [PERSON_2] who provides assistance with daily tasks
    """
    
    # Generate a narrative for the case synopsis section
    narrative = client.generate_narrative("case_synopsis", sample_content)
    
    print("Generated Narrative:")
    print(narrative)
