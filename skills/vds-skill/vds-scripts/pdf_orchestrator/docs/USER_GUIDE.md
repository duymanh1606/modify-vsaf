# VDS PDF Orchestrator - User Guide

## 📖 Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Command Line Usage](#command-line-usage)
4. [Python API Usage](#python-api-usage)
5. [Security Best Practices](#security-best-practices)
6. [Performance Optimization](#performance-optimization)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

## 🚀 Quick Start

### For Command Line Users

```bash
# Activate virtual environment first
source .venv/bin/activate

# 1. Validate a PDF file
python -m src.vds_pdf_orchestrator.cli validate document.pdf

# 2. Extract text from a PDF
python -m src.vds_pdf_orchestrator.cli extract-text document.pdf

# 3. Extract text to a file
python -m src.vds_pdf_orchestrator.cli extract-text document.pdf --output extracted.txt
```

### For Python Developers

```python
from src.vds_pdf_orchestrator import PDFClient, load_settings

# Initialize
settings = load_settings()
client = PDFClient(settings)

# Validate and extract text
is_valid, issues, risk_level, _ = client.validate_file("document.pdf")
if is_valid:
    result = client.extract_text("document.pdf")
    print(result["text"])
else:
    print(f"Security issues found: {issues}")
```

### Optional Security Add-ons

- `yara-x` for shellcode detection
- `esprima` for JavaScript AST checks
- `phishing-detection-py` for phishing URL heuristics (compiled in but **OFF by default**; enable with `VDS_PDF_ENABLE_PHISHING=1` and a Torch/TF backend; otherwise it is skipped to avoid model startup stalls)
- `presidio-analyzer` / `presidio-anonymizer` + `spacy` for PII detection
- `pypandoc-binary` (install with `uv sync --extra pandoc`) to bundle pandoc when no system binary exists

### Quick CLI Examples

```bash
# Validate
uv run --project . vds-pdf validate cli_verification_test/test.pdf --format json

# Markdown → PDF (bundled pandoc if installed)
uv run --project . vds-pdf convert-md cli_verification_test/test.md -o /tmp/out.pdf
```

### Branching Note

Default branch: `master`. Publish via `uv run vds-cli git push --branch master --path vds-pdf-orchestrator --project insurance`.

## 📦 Installation

### System Requirements

- **Python**: 3.13 or higher (required for performance optimizations)
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 512MB RAM for PDF processing
- **Disk Space**: 100MB for installation + processing space

### Prerequisites Installation

#### macOS (using Homebrew)

```bash
# Install system dependencies
brew install pandoc poppler ghostscript imagemagick pango cairo libffi

# Install Python 3.13+ if not already installed
brew install python@3.13
```

#### Ubuntu/Debian

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y pandoc poppler-utils ghostscript imagemagick libpango1.0-0 libcairo2-dev libffi-dev

# Install Python 3.13+ if not already installed
sudo apt-get install -y python3.13 python3.13-pip python3.13-venv
```

#### Windows

```powershell
# Install using Chocolatey (recommended)
choco install python313 pandoc poppler ghostscript imagemagick

# Or install manually from official websites
# - Python 3.13+: https://www.python.org/downloads/
# - Pandoc: https://pandoc.org/installing.html
# - Poppler: https://github.com/oschwartz10612/poppler-windows/releases/
```

### Package Installation

```bash
# Clone the repository
git clone <repository-url>
cd vds-pdf-orchestrator

# Install with uv (recommended)
uv sync

# Verify installation
vds-pdf --help
```

### Development Setup

```bash
# Install development dependencies
uv sync --group dev

# Run tests to verify installation
uv run --project vds-pdf-orchestrator pytest

# Run code quality checks
uv run ruff check .
uv run black .
```

## 💻 Command Line Usage

### PDF Validation

#### Basic Validation

```bash
# Validate with default settings
python -m src.vds_pdf_orchestrator.cli validate document.pdf

# Enable strict validation mode
python -m src.vds_pdf_orchestrator.cli validate document.pdf --strict

# Get table format output
python -m src.vds_pdf_orchestrator.cli validate document.pdf --format table
```

**Output Example:**

```json
{
  "file": "document.pdf",
  "is_valid": true,
  "risk_level": "low",
  "issues": [],
  "recommendations": ["Document appears safe"]
}
```

#### Understanding Validation Results

| Field | Description |
|-------|-------------|
| `is_valid` | Whether the PDF passed security validation |
| `risk_level` | Risk assessment (low, medium, high, critical) |
| `issues` | List of security issues found |
| `recommendations` | Recommended actions for secure processing |

### Text Extraction

#### Basic Text Extraction

```bash
# Extract all text
python -m src.vds_pdf_orchestrator.cli extract-text document.pdf

# Extract specific pages
python -m src.vds_pdf_orchestrator.cli extract-text document.pdf --pages 1-5

# Extract specific non-consecutive pages
python -m src.vds_pdf_orchestrator.cli extract-text document.pdf --pages 1 3 5

# Save extracted text to file
python -m src.vds_pdf_orchestrator.cli extract-text document.pdf --output extracted.txt
```

#### Advanced Usage Examples

```bash
# Extract first 10 pages and save to file
python -m src.vds_pdf_orchestrator.cli extract-text large_document.pdf --pages 1-10 --output chapter1.txt

# Extract text from multiple PDFs
for file in *.pdf; do
    python -m src.vds_pdf_orchestrator.cli extract-text "$file" --output "${file%.pdf}_extracted.txt"
done
```

### CLI Options Reference

#### Validate Command Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--strict` | | Enable strict validation mode | False |
| `--format` | | Output format (json, table) | json |

#### Extract-Text Command Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--output` | `-o` | Output file path | stdout |
| `--pages` | `-p` | Specific pages to extract | all pages |

## 🐍 Python API Usage

### Basic Setup

```python
from src.vds_pdf_orchestrator import PDFClient, load_settings
from pathlib import Path

# Initialize with default settings
settings = load_settings()
client = PDFClient(settings)

# Or create custom settings
from vds_pdf_orchestrator.config import PDFSettings

custom_settings = PDFSettings(
    max_file_size=100 * 1024 * 1024,  # 100MB
    max_pages=200,
    processing_timeout=120,
    enable_uri_validation=True
)
client = PDFClient(custom_settings)
```

### Security Validation

```python
# Basic validation
is_valid, issues, risk_level, recommendations = client.validate_file("document.pdf")

if not is_valid:
    print(f"❌ Validation failed: {issues}")
    print(f"Risk level: {risk_level}")
    for recommendation in recommendations:
        print(f"💡 Recommendation: {recommendation}")
else:
    print("✅ Document is safe to process")
```

### Text Extraction

```python
# Basic text extraction
result = client.extract_text("document.pdf")

if result["success"]:
    print(f"Extracted {result['character_count']} characters from {result['pages_extracted']} pages")
    print(f"Processing time: {result['processing_time']:.2f}s")
    print("\nText content:")
    print(result["text"])
else:
    print(f"❌ Extraction failed: {result['error']}")

# Extract specific pages
result = client.extract_text("document.pdf", pages=[1, 2, 3])

# Extract without caching
result = client.extract_text("document.pdf", use_cache=False)
```

### LLM-Optimized Extraction

```python
# Extract text optimized for LLM workflows
result = client.extract_text_llm_optimized("document.pdf")

if result["success"]:
    # Output is in Markdown format, ideal for LLM processing
    print(result["text"])
```

### Metadata Extraction

```python
# Extract PDF metadata
metadata = client.extract_metadata("document.pdf")

print(f"Title: {metadata.get('title', 'Unknown')}")
print(f"Author: {metadata.get('author', 'Unknown')}")
print(f"Creator: {metadata.get('creator', 'Unknown')}")
print(f"Producer: {metadata.get('producer', 'Unknown')}")
print(f"Creation Date: {metadata.get('creation_date', 'Unknown')}")
print(f"Modification Date: {metadata.get('modification_date', 'Unknown')}")
```

### Table Extraction

```python
# Extract tables from PDF
tables = client.extract_tables("document.pdf")

for i, table in enumerate(tables):
    print(f"\nTable {i+1}:")
    print(table)

# Extract tables as pandas DataFrames (if pandas is available)
try:
    import pandas as pd
    for i, table in enumerate(tables):
        df = pd.DataFrame(table)
        print(f"\nTable {i+1} as DataFrame:")
        print(df.head())
except ImportError:
    print("pandas not available for DataFrame conversion")
```

### Document Conversion

```python
# Convert Markdown to PDF
client.convert_markdown_to_pdf(
    input_path="document.md",
    output_path="document.pdf"
)

# Convert HTML to PDF
client.convert_html_to_pdf(
    input_path="document.html",
    output_path="document.pdf"
)
```

### Comprehensive File Analysis

```python
# Get complete information about a PDF file
info = client.get_comprehensive_info("document.pdf")

print(f"File: {info['file_info']['file_path']}")
print(f"Size: {info['file_info']['file_size']:,} bytes")
print(f"Pages: {info['file_info']['number_of_pages']}")

print(f"\nSecurity Risk: {info['security']['risk_level']}")
if info['security']['issues']:
    for issue in info['security']['issues']:
        print(f"  ⚠️  {issue}")

print(f"\nProcessing Time: {info['performance']['processing_time']:.2f}s")
print(f"Memory Used: {info['performance']['memory_used_mb']:.1f}MB")

print(f"\nCache Status: {info['cache']['hits']} hits, {info['cache']['misses']} misses")
```

## 🔒 Security Best Practices

### Always Validate Files

```python
# NEVER process files without validation
pdf_path = "untrusted_document.pdf"

# Step 1: Always validate first
is_valid, issues, risk_level, recommendations = client.validate_file(pdf_path)

if not is_valid or risk_level in ["high", "critical"]:
    print(f"🚨 Security validation failed!")
    print(f"Risk level: {risk_level}")
    for issue in issues:
        print(f"  - {issue}")
    # Do NOT process the file
    return

# Step 2: Only process if validation passes
result = client.extract_text(pdf_path)
```

### Configure Appropriate Security Levels

```python
# For untrusted sources (email attachments, web uploads)
strict_settings = PDFSettings(
    max_file_size=10 * 1024 * 1024,  # 10MB limit
    max_pages=50,                    # Page limit
    processing_timeout=30,           # Shorter timeout
    enable_uri_validation=True,      # Prevent SSRF
    enable_content_sanitization=True # Remove dangerous content
)

# For trusted internal documents
lenient_settings = PDFSettings(
    max_file_size=100 * 1024 * 1024,  # 100MB limit
    max_pages=500,                     # Higher page limit
    processing_timeout=300,            # Longer timeout
    enable_uri_validation=False,       # Allow internal links
    enable_content_sanitization=False  # Preserve original content
)
```

### Monitor Resource Usage

```python
from vds_pdf_orchestrator.validation import ResourceMonitor
import time

def safe_extract_with_monitoring(pdf_path):
    monitor = ResourceMonitor()
    monitor.start_monitoring()

    try:
        start_time = time.time()
        result = client.extract_text(pdf_path)
        processing_time = time.time() - start_time

        monitor.stop_monitoring()

        print(f"✅ Extraction completed in {processing_time:.2f}s")
        print(f"📊 Peak memory: {monitor.get_memory_usage():.1f}MB")
        print(f"💻 CPU usage: {monitor.get_cpu_usage():.1f}%")

        return result

    except Exception as e:
        monitor.stop_monitoring()
        print(f"❌ Extraction failed: {e}")
        raise
```

## ⚡ Performance Optimization

### Python 3.13+ Features

```python
from vds_pdf_orchestrator.performance import (
    Python13Optimizations,
    process_pdfs_free_threaded,
    get_performance_recommendations
)

# Enable Python 3.13+ optimizations
optimizations = Python13Optimizations()
optimizations.enable_optimal_processing()

# Check available optimizations
recommendations = get_performance_recommendations()
print(f"Python version: {recommendations['python_version']}")
print(f"Available features: {recommendations['features_available']}")
print(f"Enabled optimizations: {recommendations['optimizations_enabled']}")
```

### Parallel Processing

```python
# Process multiple PDFs in parallel (standard threading)
from vds_pdf_orchestrator.performance import process_pdfs_parallel

pdf_files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]

def extract_text_from_file(file_path):
    result = client.extract_text(file_path)
    return file_path, result

# Process with 4 workers
results = process_pdfs_parallel(
    pdf_files,
    extract_text_from_file,
    max_workers=4
)

for file_path, result in results:
    print(f"✅ Processed {file_path}: {len(result['text'])} characters")
```

### Free-Threading (Python 3.13+)

```python
# Process multiple PDFs with free-threading (Python 3.13+ only)
pdf_files = ["large_doc1.pdf", "large_doc2.pdf", "large_doc3.pdf"]

results = process_pdfs_free_threaded(
    pdf_files,
    client.extract_text,
    max_workers=8  # Can use more workers with free-threading
)

for file_path, result in results:
    if result["success"]:
        print(f"✅ {file_path}: {result['character_count']} chars in {result['processing_time']:.2f}s")
    else:
        print(f"❌ {file_path}: {result['error']}")
```

### Caching

```python
from vds_pdf_orchestrator.performance import cached_extraction

# Enable caching for repeated operations
@cached_extraction
def cached_extract(pdf_path: str, **kwargs):
    return client.extract_text(pdf_path, **kwargs)

# First call processes the file
result1 = cached_extract("document.pdf")
print(f"First call: {result1['cached']}")  # False

# Second call uses cache
result2 = cached_extract("document.pdf")
print(f"Second call: {result2['cached']}")  # True

# Get cache statistics
cache_info = client.get_cache_info()
print(f"Cache hits: {cache_info['hits']}")
print(f"Cache misses: {cache_info['misses']}")
print(f"Hit ratio: {cache_info['hit_ratio']:.2%}")
```

## 🔧 Advanced Configuration

### Environment Variables

Create a `.env` file in your project directory:

```bash
# Security limits
VDS_PDF_MAX_FILE_SIZE=52428800    # 50MB
VDS_PDF_MAX_PAGES=100
VDS_PDF_PROCESSING_TIMEOUT=60

# Performance settings
VDS_PDF_MAX_WORKERS=4
VDS_PDF_ENABLE_CACHING=true
VDS_PDF_CACHE_SIZE=128

# MCP server settings
VDS_PDF_MCP_HOST=0.0.0.0
VDS_PDF_MCP_PORT=8000

# Security settings
VDS_PDF_ENABLE_URI_VALIDATION=true
VDS_PDF_ENABLE_CONTENT_SANITIZATION=true

# Logging
VDS_PDF_LOG_LEVEL=INFO
VDS_PDF_LOG_FORMAT=json
```

### Custom Settings

```python
from vds_pdf_orchestrator.config import PDFSettings

# Create custom configuration for your use case
custom_settings = PDFSettings(
    # File limits
    max_file_size=200 * 1024 * 1024,  # 200MB
    max_pages=1000,
    max_stream_size=20 * 1024 * 1024,  # 20MB per stream

    # Timeouts
    processing_timeout=300,           # 5 minutes
    conversion_timeout=600,           # 10 minutes

    # Resource limits
    max_memory_mb=1024,               # 1GB RAM
    max_cpu_percent=90,               # High CPU usage

    # Security settings
    enable_javascript_removal=True,
    enable_uri_validation=True,
    enable_content_sanitization=True,

    # Performance settings
    enable_parallel_processing=True,
    max_workers=8,
    enable_caching=True,
    cache_size=256,

    # Output settings
    output_directory="./processed_pdfs",
    temp_directory="/tmp/pdf_processing",

    # Logging
    log_level="DEBUG",
    log_format="console"
)

client = PDFClient(custom_settings)
```

### MCP Server Integration

```python
from vds_pdf_orchestrator.mcp_server import create_mcp_server
from vds_pdf_orchestrator.config import PDFSettings

# Configure settings for MCP server
mcp_settings = PDFSettings(
    mcp_host="0.0.0.0",
    mcp_port=8000,
    mcp_transport="stdio",  # or "http"
    log_level="INFO"
)

# Create and run MCP server
server = create_mcp_server(mcp_settings)

# Run server (blocking)
server.run(host=mcp_settings.mcp_host, port=mcp_settings.mcp_port)

# Or run in background
import threading
server_thread = threading.Thread(
    target=server.run,
    kwargs={"host": mcp_settings.mcp_host, "port": mcp_settings.mcp_port}
)
server_thread.daemon = True
server_thread.start()

print(f"MCP server running on {mcp_settings.mcp_host}:{mcp_settings.mcp_port}")
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Installation Problems

**Issue**: `ModuleNotFoundError: No module named 'vds_pdf_orchestrator'`

**Solution**:

```bash
# Ensure you're in the correct directory
cd vds-pdf-orchestrator

# Sync dependencies (creates/updates .venv)
uv sync

# Verify installation
uv run --project vds-pdf-orchestrator python -c "import vds_pdf_orchestrator; print('✅ Installation successful')"
```

**Issue**: System dependency not found (pandoc, poppler, etc.)

**Solution**:

```bash
# macOS
brew install pandoc poppler ghostscript

# Ubuntu/Debian
sudo apt-get install pandoc poppler-utils ghostscript

# Verify installation
pandoc --version
pdftotext -v
```

#### 2. PDF Processing Errors

**Issue**: `SecurityError: File validation failed`

**Solution**:

```python
# Check what validation failed
is_valid, issues, risk_level, recommendations = client.validate_file("problem.pdf")

print(f"Validation result: {is_valid}")
print(f"Issues: {issues}")
print(f"Risk level: {risk_level}")

# For testing, you can temporarily disable strict validation
# (NOT recommended for production)
test_settings = PDFSettings(
    enable_uri_validation=False,
    enable_content_sanitization=False
)
test_client = PDFClient(test_settings)
```

**Issue**: Memory error with large PDFs

**Solution**:

```python
# Increase memory limits
high_memory_settings = PDFSettings(
    max_memory_mb=2048,  # 2GB
    max_file_size=500 * 1024 * 1024,  # 500MB
    processing_timeout=600  # 10 minutes
)

# Or process in chunks
large_pdf_settings = PDFSettings(
    max_pages=50,  # Process 50 pages at a time
    enable_caching=True  # Cache intermediate results
)
```

#### 3. Performance Issues

**Issue**: Slow processing speed

**Solution**:

```python
# Enable all optimizations
from vds_pdf_orchestrator.performance import Python13Optimizations

optimizations = Python13Optimizations()
optimizations.enable_optimal_processing()

# Use parallel processing
from vds_pdf_orchestrator.performance import process_pdfs_parallel

# Increase worker count (but don't exceed CPU cores)
import multiprocessing
max_workers = min(multiprocessing.cpu_count(), 8)

settings = PDFSettings(max_workers=max_workers)
```

**Issue**: High memory usage

**Solution**:

```python
# Reduce memory footprint
low_memory_settings = PDFSettings(
    max_memory_mb=256,      # Limit to 256MB
    max_workers=2,          # Fewer workers
    cache_size=32,          # Smaller cache
    enable_caching=False    # Disable caching if needed
)

# Process files individually instead of in parallel
```

### Debug Mode

```python
# Enable debug logging
from vds_pdf_orchestrator.config import configure_logging

debug_settings = PDFSettings(
    log_level="DEBUG",
    log_format="console"
)

configure_logging(debug_settings)

# Now all operations will produce detailed logs
result = client.extract_text("document.pdf")
```

### Error Reference

| Error Type | Common Cause | Solution |
|------------|--------------|----------|
| `SecurityError` | PDF failed validation | Check validation result, adjust security settings |
| `ProcessingError` | Corrupted PDF or processing failure | Verify PDF integrity, check file permissions |
| `ValidationError` | Invalid input parameters | Check file path, page numbers, and configuration |
| `TimeoutError` | Processing took too long | Increase timeout or reduce file size/pages |
| `ResourceError` | Memory or CPU limits exceeded | Increase resource limits or optimize processing |
| `ConversionError` | Document conversion failed | Check input file format, ensure dependencies installed |

### Getting Help

```python
# Get system information for debugging
from vds_pdf_orchestrator.performance import get_performance_recommendations
import sys

print("=== System Information ===")
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")

recommendations = get_performance_recommendations()
print(f"\n=== Performance Recommendations ===")
for rec in recommendations.get('recommendations', []):
    print(f"• {rec}")

# Get configuration info
print(f"\n=== Current Configuration ===")
print(f"Max file size: {settings.max_file_size:,} bytes")
print(f"Max pages: {settings.max_pages}")
print(f"Processing timeout: {settings.processing_timeout}s")
print(f"Max workers: {settings.max_workers}")
```

## 📚 Additional Resources

- **Features Guide**: See `FEATURES_GUIDE.md` for comprehensive feature documentation
- **API Reference**: See docstrings in source code for detailed API information
- **Security Information**: See README.md for CVE mitigations and security features
- **Performance Tuning**: See README.md for performance benchmarks and optimization tips

## 🆘 Support

If you encounter issues not covered in this guide:

1. Check the error reference section above
2. Enable debug mode to get detailed logging
3. Verify all system dependencies are installed
4. Ensure you're using Python 3.13+ for best performance

---

*Last updated: 2025-11-15*
*Version: 0.1.0*
*Python: 3.13+*
