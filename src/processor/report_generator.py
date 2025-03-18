"""
Delilah Prime - Report Generator Module

This module handles the assembly of the final clinical report from processed content.
"""

import os
from pathlib import Path
import json
from datetime import datetime


class ReportGenerator:
    """Generates the final clinical report from processed content."""
    
    def __init__(self, config_path=None):
        """
        Initialize the report generator.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.json"
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.report_sections = config['report_sections']
        self.templates_dir = Path(__file__).parent.parent.parent / config["paths"]["templates_directory"]
    
    def _load_template(self, template_name):
        """
        Load a template file.
        
        Args:
            template_name: Name of the template to load
            
        Returns:
            Template content as string
        """
        template_path = self.templates_dir / f"{template_name}.txt"
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Return a default template if the file doesn't exist
            return f"# {template_name.replace('_', ' ').title()}\n\n{{content}}\n\n"
    
    def _format_section_title(self, section_name):
        """Format a section name into a readable title."""
        return section_name.replace('_', ' ').title()
    
    def generate_report(self, content_sections, enhanced_sections=None, custom_header=None, custom_footer=None, template=None):
        """
        Generate a complete report from content sections.
        
        Args:
            content_sections: Dictionary of section names and their content
            enhanced_sections: Optional dictionary of AI-enhanced sections
            custom_header: Optional custom header text for the report
            custom_footer: Optional custom footer text for the report
            template: Optional template for the entire report
            
        Returns:
            Complete report as string
        """
        # Initialize enhanced_sections if None
        if enhanced_sections is None:
            enhanced_sections = {}
            
        # If we have a full report template, use it
        if template:
            # Replace section placeholders in the template
            report_content = template
            for section in self.report_sections:
                placeholder = f"{{{section}}}"
                
                # Use enhanced content if available, otherwise use original
                content = enhanced_sections.get(section, "") or content_sections.get(section, "")
                
                # Replace the placeholder with content
                report_content = report_content.replace(placeholder, content or "")
                
            return report_content
            
        # Otherwise build the report section by section
        report = []
        
        # Add report header (custom or default)
        if custom_header:
            report.append(custom_header)
        else:
            report.append("# Clinical Assessment Report")
            report.append(f"Generated: {datetime.now().strftime('%B %d, %Y')}\n")
        
        # Process each section in the defined order
        for section in self.report_sections:
            # Get section content, preferring enhanced if available
            content = enhanced_sections.get(section, "") or content_sections.get(section, "")
            
            # Skip empty sections
            if not content:
                continue
            
            # Load section template
            section_template = self._load_template(section)
            
            # Format the section using the template
            formatted_section = section_template.replace("{content}", content)
            
            # Add to report
            report.append(formatted_section)
        
        # Add report footer (custom or default)
        if custom_footer:
            report.append(custom_footer)
        else:
            report.append("\n---")
            report.append("This report was generated using Delilah Prime v1.0")
            report.append("© " + str(datetime.now().year))
        
        return "\n\n".join(report)
    
    def save_report(self, report_content, output_path, filename=None):
        """
        Save the report to a file.
        
        Args:
            report_content: Report content as string
            output_path: Directory to save the report
            filename: Optional filename, defaults to timestamp-based name
            
        Returns:
            Path to the saved report
        """
        if filename is None:
            filename = f"clinical_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        output_path = Path(output_path)
        os.makedirs(output_path, exist_ok=True)
        
        file_path = output_path / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return file_path 