# Delilah Prime v1.0

A secure clinical report generation system that transforms assessment notes into structured professional reports while protecting patient confidentiality.

## Overview

Delilah Prime is designed to streamline the report writing process for clinical assessments by:

1. Securely de-identifying patient information
2. Processing clinical notes and file reviews
3. Generating narrative content with AI assistance
4. Assembling complete, professional reports that maintain clinical accuracy

## System Components

- **De-identification Module**: Removes and securely stores personal identifiers
- **Document Processor**: Extracts and organizes content from multiple sources
- **AI Integration**: Leverages Claude API for narrative enhancement
- **Report Assembler**: Creates final documents according to professional templates

## Directory Structure

- `src/`: Source code
  - `deidentifier/`: De-identification module
  - `api/`: Claude API integration
  - `processor/`: Document processing logic
- `templates/`: Report templates
- `docs/`: Documentation
- `input/`: Input files directory
- `output/`: Generated reports

## Setup Instructions

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `.env.template` to `.env` and add your Claude API key:
   ```
   CLAUDE_API_KEY=your_api_key_here
   ENCRYPTION_KEY=your_secure_encryption_key
   ```
4. Place your assessment notes and file reviews in the `input/` directory
5. Run the application:
   ```
   python src/main.py
   ```

## Usage

### Input Files

Place your clinical documents in the `input/` directory. The system supports:
- Text files (.txt)
- Markdown files (.md)
- Word documents (.docx)
- PDF files (.pdf)

File naming conventions help the system categorize your documents:
- Assessment notes: Include "assessment" or "notes" in the filename
- File reviews: Include "file" or "review" in the filename
- Medical documents: Include "medical" or "health" in the filename

### Output Files

The system generates several files in the `output/` directory:
- De-identified versions of your input files
- A draft report with enhanced content
- The final re-identified report

### Templates

You can customize report templates by editing or adding files in the `templates/` directory. Each template corresponds to a section in the final report.

## Security

This system is designed with privacy as a core principle:
- No personal health information (PHI) is transmitted to external systems
- All identifiers are stored in a secure local reference table
- Processing occurs on the local system

## Troubleshooting

- If you encounter errors related to document processing, ensure you have the required dependencies installed
- For issues with the Claude API, verify your API key in the `.env` file
- If de-identification is incomplete, you may need to add custom patterns to the configuration

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Data Flow

1. Assessment notes, file reviews, and supporting documents are placed in the `input` directory
2. Personal information is de-identified and securely stored locally
3. De-identified content is processed and structured according to report templates
4. Claude API enhances narrative quality while maintaining clinical accuracy
5. Personal information is securely re-identified
6. Complete reports are generated in the `output` directory

## Development Status

This project is currently in initial development.
