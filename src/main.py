"""
Delilah Prime v1.0 - Main Application

This is the main entry point for the Delilah Prime application, which processes
clinical assessment notes and generates professional reports while protecting
patient confidentiality.
"""

import os
import json
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Make sure we can import from sibling directories
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Delilah modules
from src.deidentifier.deidentifier import Deidentifier
from src.api.claude_api import ClaudeAPIClient
from src.processor.document_processor import DocumentProcessor
from src.processor.report_generator import ReportGenerator


class DelilahPrime:
    """Main application class for Delilah Prime."""
    
    def __init__(self, config_path=None):
        """
        Initialize the Delilah Prime application.
        
        Args:
            config_path: Path to the configuration file. If None, the default is used.
        """
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.json"
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Set up paths
        self.base_path = Path(__file__).parent.parent
        self.input_path = self.base_path / self.config["paths"]["input_directory"]
        self.output_path = self.base_path / self.config["paths"]["output_directory"]
        self.templates_path = self.base_path / self.config["paths"]["templates_directory"]
        
        # Initialize components
        self.deidentifier = Deidentifier(
            ref_table_path=Path.home() / Path(self.config["paths"]["reference_tables"])
        )
        self.document_processor = DocumentProcessor(config_path)
        self.report_generator = ReportGenerator(config_path)
        self.claude_api = ClaudeAPIClient(config_path)
        
        # Create directories if they don't exist
        os.makedirs(self.input_path, exist_ok=True)
        os.makedirs(self.output_path, exist_ok=True)
        os.makedirs(self.templates_path, exist_ok=True)
        
        print(f"Delilah Prime {self.config['app']['version']} initialized")
    
    def process_document(self, document_path):
        """
        Process a single document.
        
        Args:
            document_path: Path to the document to process
            
        Returns:
            The de-identified content of the document
        """
        # Extract content based on file type
        content = self.document_processor.process_file(document_path)
        
        # De-identify the content
        deidentified_content = self.deidentifier.deidentify_text(content)
        
        # Save a temporary de-identified version for inspection
        deidentified_path = self.output_path / f"deidentified_{Path(document_path).name}"
        with open(deidentified_path, 'w', encoding='utf-8') as f:
            f.write(deidentified_content)
        
        print(f"De-identified content saved to {deidentified_path}")
        
        return deidentified_content
    
    def process_input_directory(self):
        """
        Process all documents in the input directory.
        
        Returns:
            A dictionary of document types and their de-identified content
        """
        processed_documents = {}
        
        # Process each file in the input directory
        for file_path in self.input_path.glob("*.*"):
            if file_path.suffix.lower() in [".txt", ".md", ".docx", ".pdf"]:
                print(f"Processing {file_path}")
                processed_documents[file_path.name] = self.process_document(file_path)
        
        # Save the reference table
        ref_table_path = self.deidentifier.save_reference_table()
        print(f"Reference table saved to {ref_table_path}")
        
        return processed_documents
    
    def generate_report(self, processed_documents):
        """
        Generate a report from the processed documents.
        
        Args:
            processed_documents: Dictionary of processed document content
            
        Returns:
            The path to the generated report
        """
        # Organize content by section
        print("Organizing document content...")
        organized_content = self.document_processor.organize_content(processed_documents)
        
        # Enhance content with Claude API
        print("Enhancing content with Claude API...")
        enhanced_sections = {}
        
        # Check if API key is available
        if os.environ.get("CLAUDE_API_KEY"):
            for section, content in organized_content.items():
                if content:
                    print(f"Enhancing section: {section}")
                    enhanced_sections[section] = self.claude_api.generate_narrative(
                        section, content
                    )
        else:
            print("Warning: Claude API key not set. Skipping content enhancement.")
        
        # Generate the report
        print("Generating report...")
        report_content = self.report_generator.generate_report(
            organized_content, enhanced_sections
        )
        
        # Save the draft report
        draft_path = self.output_path / "draft_report.txt"
        with open(draft_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"Draft report generated at {draft_path}")
        return draft_path
    
    def reidentify_report(self, report_path):
        """
        Re-identify a generated report.
        
        Args:
            report_path: Path to the de-identified report
            
        Returns:
            The path to the re-identified report
        """
        # Read the de-identified report
        with open(report_path, 'r', encoding='utf-8') as f:
            deidentified_content = f.read()
        
        # Re-identify the content
        reidentified_content = self.deidentifier.reidentify_text(deidentified_content)
        
        # Save the re-identified report
        timestamp = Path(report_path).stem.replace("draft_", "")
        reidentified_path = self.output_path / f"final_report_{timestamp}.txt"
        with open(reidentified_path, 'w', encoding='utf-8') as f:
            f.write(reidentified_content)
        
        print(f"Final report generated at {reidentified_path}")
        return reidentified_path
    
    def run(self):
        """Run the complete document processing and report generation pipeline."""
        print("Starting document processing...")
        processed_documents = self.process_input_directory()
        
        if not processed_documents:
            print("No documents found to process.")
            return
        
        print("Generating draft report...")
        report_path = self.generate_report(processed_documents)
        
        print("Re-identifying report...")
        final_report_path = self.reidentify_report(report_path)
        
        print(f"Process complete. Final report available at {final_report_path}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Delilah Prime - Clinical Report Generator")
    parser.add_argument("--config", help="Path to configuration file")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Initialize and run the application
    app = DelilahPrime(config_path=args.config)
    app.run()
