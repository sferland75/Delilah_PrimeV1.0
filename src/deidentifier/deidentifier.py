"""
Delilah Prime - De-identification Module

This module handles the detection and replacement of personal identifiers in clinical documents.
It creates a secure local reference table for re-identification during final report generation.
"""

import re
import uuid
import json
import os
from datetime import datetime
from pathlib import Path


class Deidentifier:
    """
    Handles the de-identification of personal health information (PHI) in documents.
    """
    
    def __init__(self, ref_table_path=None):
        """
        Initialize the de-identification system.
        
        Args:
            ref_table_path: Path to store the reference table. If None, a default path is used.
        """
        if ref_table_path is None:
            # Store in user's home directory by default
            self.ref_table_path = Path.home() / ".delilah" / "reference_tables"
        else:
            self.ref_table_path = Path(ref_table_path)
            
        # Create directory if it doesn't exist
        os.makedirs(self.ref_table_path, exist_ok=True)
        
        # Initialize reference table for this session
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.reference_table = {}
        
        # Define regex patterns for PHI detection - specifically for OT reports
        self.patterns = {
            # Names - Focus on patient name patterns with both titles and full names in context
            "NAME": [
                # Client/patient with title (most common in OT reports)
                r"(?<!\w)(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s[A-Z][a-z]+(?:\s[A-Z][a-z]+)*(?!\w)",
                
                # Full names in specific contexts often found in OT reports
                r"(?<!\w)(?:patient|client|individual|subject)\s(?:name|is):\s*[A-Z][a-z]+(?:\s[A-Z][a-z]+)+(?!\w)",
                r"(?<!\w)(?:name|patient|client):\s*[A-Z][a-z]+(?:\s[A-Z][a-z]+)+(?!\w)",
                
                # Patient full name pattern (First Last) at beginning of sentence or after period - fixed width lookbehind
                r"(?:\.\s+|\n\s*|^\s*)[A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:was|is|has|had|will|received|underwent|reported)",
                
                # Full name pattern before "date of birth" - no lookbehind
                r"[A-Z][a-z]+\s+[A-Z][a-z]+\s+(?=date of birth|DOB|born on)",
            ],
            
            # Dates - typical medical date formats
            "DATE": [
                r"(?<!\w)(?:DOB|Date\sof\sBirth|Birth\sDate):\s*\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}(?!\w)",  # DOB: MM/DD/YYYY
                r"(?<!\w)(?:Assessment\sDate|Evaluation\sDate|Date\sof\sAssessment|Date\sof\sEvaluation):\s*\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}(?!\w)",  # Assessment Date: MM/DD/YYYY
                r"(?<!\w)(?:Date\sof\sLoss|Accident\sDate|Injury\sDate):\s*\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}(?!\w)",  # Date of Loss: MM/DD/YYYY
            ],
            
            # Phone numbers
            "PHONE": [
                r"(?<!\w)(?:Phone|Tel|Telephone|Cell|Mobile|Contact)(?:\s#|\s[Nn]umber|\s[Nn]o\.)?:\s*(?:\+\d{1,2}\s)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\w)"  # Phone: (123) 456-7890
            ],
            
            # Identifiers like claim numbers, file numbers that need protection
            "ID_NUMBER": [
                r"(?<!\w)(?:Claim\s(?:No\.|Number)|File\s(?:No\.|Number)):\s*[A-Z0-9-]{5,}(?!\w)",  # Claim No: ABC12345
                r"(?<!\w)(?:MRN|Medical\sRecord\s(?:Number|No\.)|Patient\sID|Record\s#):\s*[A-Z0-9-]{5,}(?!\w)",  # MRN: 12345678
            ],
        }
        
        # Professional terms that should NOT be identified as PHI
        self.professional_terms = [
            "Occupational Therapist", "OT Reg", "Health Professional", "Rehabilitation",
            "Sebastien Ferland", "Neusy Pierre", "Assessment", "Therapy", "Evaluation",
            "Clinical", "Functional", "Physical", "Cognitive", "Emotional", "Psychological",
            "Montreal Cognitive Assessment", "Patient Health Questionnaire",
            "AMA Guides", "Activities of Daily Living", "Functional Capacity Evaluation",
            "Glasgow Outcome Scale", "Extended", "Report", "Documentation", "Mobility",
            "Independence", "Function", "Adaptability", "Concentration", "Persistence", "Pace",
            "Deterioration", "Decompensation", "Work Settings", "Social Functioning",
            "Vocational", "Capital", "Associates", "Specialists", "Baseline Road", "Ottawa"
        ]
    
    def _generate_placeholder(self, phi_type):
        """Generate a unique placeholder for a specific type of PHI."""
        placeholder_id = str(uuid.uuid4())[:8]
        return f"[{phi_type}_{placeholder_id}]"
    
    def _is_professional_term(self, text):
        """Check if the text is a professional term that should not be identified as PHI."""
        # Convert to lowercase for case-insensitive comparison
        text_lower = text.lower().strip()
        
        # Check if it's in our list of professional terms
        for term in self.professional_terms:
            if term.lower() in text_lower:
                return True
                
        return False
    
    def deidentify_text(self, text):
        """
        De-identify text by replacing PHI with placeholders.
        
        Args:
            text: The text to de-identify
            
        Returns:
            De-identified text with PHI replaced by placeholders
        """
        deidentified_text = text
        
        # Process each PHI type
        for phi_type, patterns in self.patterns.items():
            # Process each pattern for this PHI type
            for pattern in patterns:
                # Find all matches
                matches = re.finditer(pattern, deidentified_text, re.IGNORECASE)
                
                # Replace each match with a placeholder
                # We process in reverse order to avoid changing the positions of subsequent matches
                matches = list(matches)
                for match in reversed(matches):
                    phi_value = match.group(0)
                    
                    # Skip if this is a professional term that should not be identified as PHI
                    if self._is_professional_term(phi_value):
                        continue
                    
                    placeholder = self._generate_placeholder(phi_type)
                    
                    # Store the mapping
                    self.reference_table[placeholder] = phi_value
                    
                    # Replace in the text
                    start, end = match.span()
                    deidentified_text = deidentified_text[:start] + placeholder + deidentified_text[end:]
        
        return deidentified_text
    
    def reidentify_text(self, text):
        """
        Re-identify text by replacing placeholders with original PHI.
        
        Args:
            text: The de-identified text
            
        Returns:
            Re-identified text with original PHI values
        """
        reidentified_text = text
        
        # Replace each placeholder with its original value
        for placeholder, original in self.reference_table.items():
            reidentified_text = reidentified_text.replace(placeholder, original)
        
        return reidentified_text
    
    def save_reference_table(self):
        """
        Save the reference table to a file.
        
        Returns:
            Path to the saved reference table
        """
        ref_table_file = self.ref_table_path / f"ref_table_{self.session_id}.json"
        
        with open(ref_table_file, 'w') as f:
            json.dump(self.reference_table, f, indent=2)
        
        return ref_table_file
    
    def load_reference_table(self, ref_table_file):
        """
        Load a reference table from a file.
        
        Args:
            ref_table_file: Path to the reference table file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(ref_table_file, 'r') as f:
                self.reference_table = json.load(f)
            return True
        except (FileNotFoundError, json.JSONDecodeError):
            return False
            
    def get_reference_table(self):
        """
        Get the current reference table.
        
        Returns:
            Dictionary containing the reference table mappings
        """
        return self.reference_table
        
    def reidentify_content(self, content, reference_table=None):
        """
        Re-identify content by replacing placeholders with original values.
        
        Args:
            content: The de-identified content to re-identify
            reference_table: Optional external reference table to use
            
        Returns:
            Re-identified content with original values
        """
        # Use provided reference table if available, otherwise use the internal one
        ref_table = reference_table if reference_table else self.reference_table
        
        # If content is a string, reidentify directly
        if isinstance(content, str):
            reidentified = content
            for placeholder, original in ref_table.items():
                reidentified = reidentified.replace(placeholder, original)
            return reidentified
        
        # If content is a dictionary (e.g., sections), reidentify each value
        elif isinstance(content, dict):
            reidentified = {}
            for key, value in content.items():
                if isinstance(value, str):
                    reidentified_value = value
                    for placeholder, original in ref_table.items():
                        reidentified_value = reidentified_value.replace(placeholder, original)
                    reidentified[key] = reidentified_value
                else:
                    reidentified[key] = value
            return reidentified
        
        # Return original content if not a string or dictionary
        return content


# Example usage
if __name__ == "__main__":
    # Sample text with PHI
    sample_text = """
    Mr. John Smith was seen on January 15, 2023, at his residence at 123 Main Street. 
    He was referred by Dr. Jane Doe for evaluation following an incident on 12/10/2022.
    """
    
    print("Original text:")
    print(sample_text)
    print("\n" + "-"*50 + "\n")
    
    # De-identify the text
    deidentifier = Deidentifier()
    deidentified_text = deidentifier.deidentify_text(sample_text)
    
    print("De-identified text:")
    print(deidentified_text)
    print("\n" + "-"*50 + "\n")
    
    # Save the reference table
    deidentifier.save_reference_table()
    
    # Re-identify the text
    reidentified_text = deidentifier.reidentify_text(deidentified_text)
    
    print("Re-identified text:")
    print(reidentified_text)
