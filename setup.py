"""
Setup script for Delilah Prime
"""

from setuptools import setup, find_packages

setup(
    name="delilah-prime",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
        "python-docx>=0.8.11",
        "PyPDF2>=3.0.0",
        "spacy>=3.5.0",
        "cryptography>=39.0.0",
        "python-dotenv>=1.0.0",
        "tqdm>=4.65.0",
    ],
    python_requires=">=3.8",
    author="Your Name",
    author_email="your.email@example.com",
    description="A secure clinical report generation system",
    keywords="clinical, report, ai, de-identification",
    url="https://github.com/yourusername/delilah-prime",
    project_urls={
        "Documentation": "https://github.com/yourusername/delilah-prime",
        "Source Code": "https://github.com/yourusername/delilah-prime",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Healthcare Industry",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
    ],
)
