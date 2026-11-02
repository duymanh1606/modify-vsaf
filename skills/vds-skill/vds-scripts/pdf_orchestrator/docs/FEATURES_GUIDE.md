# VDS PDF Orchestrator - Features Guide

## Overview

VDS PDF Orchestrator is a secure, high-performance PDF manipulation system built for Python 3.13+ with enterprise-grade security features. This guide provides comprehensive documentation of all available features and how to use them.

**Optional security add-ons:** `yara-x`, `esprima`, `phishing-detection-py`, `presidio-analyzer`/`presidio-anonymizer`, and `spacy` enhance scanning and redaction when installed. `phishing-detection-py` is bundled but **disabled by default** to avoid model startup stalls—set `VDS_PDF_ENABLE_PHISHING=1` to enable (requires ML backend).

**Branching note:** default branch is `master` (push via `uv run vds-cli git push --branch master --path vds-pdf-orchestrator --project insurance`).

**Bundled pandoc option:** install extra `pandoc` (`uv sync --extra pandoc`) to ship a built-in pandoc binary for Markdown/HTML → PDF when no system pandoc is available.

**Quick commands (uv-run local):**

- `uv run --project . vds-pdf validate <file.pdf> --format json`
- `uv run --project . vds-pdf convert-md file.md -o out.pdf`

## 🚀 Key Features

### Core Capabilities

- **Secure PDF Processing**: CVE-protected PDF manipulation with comprehensive security validation
- **Python 3.13+ Support**: Free-threading on nogil builds; JIT currently disabled by default; performance monitoring included
- **Enterprise Security**: Multi-layer security validation with malicious content detection
- **MCP Integration**: Model Context Protocol support for AI workflows
- **CLI Interface**: Command-line tools for easy automation
- **Performance Optimization**: Parallel processing, caching, and resource management

## 📋 Available Features

### 1. Command Line Interface (CLI)

#### PDF Validation

```bash
# Basic validation
python -m src.vds_pdf_orchestrator.cli validate document.pdf

# Strict validation with table output
python -m src.vds_pdf_orchestrator.cli validate document.pdf --strict --format table

# JSON output (default)
python -m src.vds_pdf_orchestrator.cli validate document.pdf --format json
```

**Output Example:**

```json
{
  "is_valid": true,
  "issues": [],
  "risk_level": "low",
  "recommendations": ["Document appears safe"]
}
```

#### Text Extraction

```bash
# Extract all text
python -m src.vds_pdf_orchestrator.cli extract-text document.pdf

# Extract specific pages
python -m src.vds_pdf_orchestrator.cli extract-text document.pdf --pages 1-5

# Save to file
python -m src.vds_pdf_orchestrator.cli extract-text document.pdf --output extracted_text.txt
```

### 2. Python API - PDFClient Class

#### Basic Usage

```python
from src.vds_pdf_orchestrator import PDFClient, load_settings

# Initialize with default settings
settings = load_settings()
client = PDFClient(settings)

# Validate a PDF file
is_valid, issues, risk_level, recommendations = client.validate_file("document.pdf")
if not is_valid:
    print(f"Security issues: {issues}")
```

#### Text Extraction

```python
# Basic text extraction
result = client.extract_text("document.pdf")
print(result["text"])

# Extract with page range
result = client.extract_text("document.pdf", pages=[1, 2, 3])

# Extract with layout preservation
result = client.extract_text("document.pdf", preserve_layout=True)
```

#### Metadata Extraction

```python
metadata = client.extract_metadata("document.pdf")
print(f"Title: {metadata.get('title', 'Unknown')}")
print(f"Author: {metadata.get('author', 'Unknown')}")
print(f"Page count: {metadata.get('page_count', 0)}")
```

#### Table Extraction

```python
tables = client.extract_tables("document.pdf")
for i, table in enumerate(tables):
    print(f"Table {i+1}:")
    print(table)
```

#### PDF Conversion

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

#### Comprehensive Information

```python
info = client.get_comprehensive_info("document.pdf")
print(f"Security risk: {info['security']['risk_level']}")
print(f"Processing time: {info['performance']['processing_time']}s")
print(f"Cache status: {info['cache']['hits']} hits")
```

### 3. Performance Optimizations (Python 3.13+)

#### Free-Threading Support

```python
from vds_pdf_orchestrator.performance import process_pdfs_free_threaded

# Process multiple PDFs with free-threading
pdf_files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
results = process_pdfs_free_threaded(
    pdf_files,
    client.extract_text,
    max_workers=8
)
```

#### JIT Compiler Optimization

```python
from vds_pdf_orchestrator.performance import optimize_with_jit

@optimize_with_jit
def cpu_intensive_function(pdf_data):
    # CPU-intensive processing
    return processed_data
```

#### Performance Recommendations

```python
from vds_pdf_orchestrator.performance import get_performance_recommendations

recommendations = get_performance_recommendations()
print(f"Python version: {recommendations['python_version']}")
print(f"Available features: {recommendations['features_available']}")
print(f"Optimizations: {recommendations['optimizations_enabled']}")
```

### 4. Security Validation

#### Comprehensive Security Check

```python
from vds_pdf_orchestrator.validation import PDFSecurityValidator

validator = PDFSecurityValidator(settings)
is_valid, issues, risk_level, recommendations = validator.validate_pdf_file_comprehensive(pdf_path)

print(f"Risk Level: {risk_level}")
print(f"Issues Found: {len(issues)}")
print(f"Recommendations: {recommendations}")
```

#### SSRF Protection

```python
from vds_pdf_orchestrator.validation import SSRFProtection

ssrf = SSRFProtection()
is_safe, reason = ssrf.validate_url("https://example.com")
if not is_safe:
    print(f"URL blocked: {reason}")
```

#### Resource Monitoring

```python
from vds_pdf_orchestrator.validation import ResourceMonitor

monitor = ResourceMonitor()
monitor.start_monitoring()
# ... processing ...
monitor.stop_monitoring()
print(f"Memory used: {monitor.get_memory_usage()}MB")
```

### 5. MCP Integration

#### Create MCP Server

```python
from vds_pdf_orchestrator.mcp_server import create_mcp_server

# Create MCP server with default settings
server = create_mcp_server()

# Run server (blocking)
server.run(host="0.0.0.0", port=8000)
```

#### Available MCP Tools

- **validate_pdf_security**: Comprehensive security validation
- **extract_content_with_validation**: Text/image extraction with security checks
- **process_pdf_with_security**: Complete processing pipeline with audit trail
- **convert_to_pdf**: Document conversion with security validation

### 6. Performance Features

#### LRU Cache

```python
from vds_pdf_orchestrator.performance import LRUCache

# Create cache with 128 items
cache = LRUCache(max_size=128)

# Use cache decorator
@cache.cached_function
def extract_with_cache(pdf_path):
    return client.extract_text(pdf_path)
```

#### Parallel Processing

```python
from vds_pdf_orchestrator.performance import process_pdfs_parallel

# Process multiple PDFs in parallel
results = process_pdfs_parallel(
    file_paths,
    client.extract_text,
    max_workers=4
)
```

#### Caching Wrapper

```python
from vds_pdf_orchestrator.performance import cached_extraction

# Enable caching for extraction
@cached_extraction
def cached_extract(pdf_path, **kwargs):
    return client.extract_text(pdf_path, **kwargs)
```

## 🔧 Configuration

### Environment Variables

```bash
# Security settings
VDS_PDF_MAX_FILE_SIZE=52428800  # 50MB
VDS_PDF_MAX_PAGES=100
VDS_PDF_PROCESSING_TIMEOUT=60

# Performance settings
VDS_PDF_CACHE_SIZE=128
VDS_PDF_ENABLE_JIT=true

# Logging
VDS_PDF_LOG_LEVEL=info
```

### Python Configuration

```python
from vds_pdf_orchestrator.config import PDFSettings

# Custom settings
settings = PDFSettings(
    max_file_size=100 * 1024 * 1024,  # 100MB
    max_pages=200,
    processing_timeout=120,
    log_level="debug"
)
```

## 🛡️ Security Features

### CVE Mitigations

The orchestrator includes protections for:

- **CVE-2025-55197**: PyPDF FlateDecode RAM exhaustion
- **CVE-2025-62708**: PyPDF LZWDecode memory issues
- **CVE-2025-62707**: PyPDF DCTDecode memory issues
- **CVE-2025-46568**: Stirling-PDF SSRF vulnerability
- **CVE-2023-36807**: PyPDF infinite loop DoS
- **CVE-2023-33733**: ReportLab RCE vulnerability

### Enhanced Security Dependencies

- **SafeUploads**: Malicious content detection
- **Peepdf-3**: Advanced PDF security analysis
- **File Type Validation**: Magic byte verification
- **Resource Limits**: Memory, CPU, and time constraints

### Security Validation Pipeline

```python
def secure_pdf_workflow(pdf_path):
    # 1. Basic file checks
    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    # 2. Size and page limits
    if pdf_path.stat().st_size > settings.max_file_size:
        raise SecurityError("File too large")

    # 3. Comprehensive security validation
    validator = PDFSecurityValidator(settings)
    is_valid, issues, risk_level, recommendations = validator.validate_pdf_file_comprehensive(pdf_path)

    if not is_valid or risk_level in ["high", "critical"]:
        raise SecurityError(f"Security validation failed: {issues}")

    # 4. Process with monitoring
    with secure_pdf_processing(settings, pdf_path):
        result = client.extract_text(pdf_path)

    return result
```

## 📊 Performance Monitoring

### Performance Metrics

```python
from vds_pdf_orchestrator.performance import get_performance_recommendations

# Get system recommendations
recommendations = get_performance_recommendations()
print(f"System Recommendations:")
for rec in recommendations.get('recommendations', []):
    print(f"  • {rec}")
```

### Resource Monitoring

```python
import time
from vds_pdf_orchestrator.validation import ResourceMonitor

def monitor_processing(pdf_path):
    monitor = ResourceMonitor()
    monitor.start_monitoring()

    start_time = time.time()
    result = client.extract_text(pdf_path)
    processing_time = time.time() - start_time

    monitor.stop_monitoring()

    print(f"Processing time: {processing_time:.2f}s")
    print(f"Memory peak: {monitor.get_memory_usage():.1f}MB")
    print(f"CPU usage: {monitor.get_cpu_usage():.1f}%")

    return result
```

## 🚨 Error Handling

### Common Error Types

```python
from vds_pdf_orchestrator.errors import (
    SecurityError,       # Security validation failures
    ProcessingError,    # General processing errors
    ValidationError,    # Input validation errors
    ConversionError,    # Conversion failures
    TimeoutError,       # Processing timeouts
    ResourceError,     # Resource limit exceeded
)

try:
    result = client.extract_text("document.pdf")
except SecurityError as e:
    print(f"Security error: {e}")
except ProcessingError as e:
    print(f"Processing error: {e}")
except ValidationError as e:
    print(f"Validation error: {e}")
```

## 🔍 Best Practices

### 1. Always Validate Files

```python
# Always validate before processing
is_valid, issues, risk_level, _ = client.validate_file(pdf_path)
if not is_valid:
    raise SecurityError(f"File validation failed: {issues}")
```

### 2. Use Appropriate Security Levels

```python
# For untrusted files, use strict validation
settings = PDFSettings(
    max_file_size=10 * 1024 * 1024,  # 10MB limit
    max_pages=50,                  # Page limit
    processing_timeout=30           # Shorter timeout
)
```

### 3. Monitor Performance

```python
# Use performance monitoring for large files
if pdf_path.stat().st_size > 10 * 1024 * 1024:  # > 10MB
    monitor_processing(pdf_path)
else:
    client.extract_text(pdf_path)
```

### 4. Use Caching for Repeated Operations

```python
from vds_pdf_orchestrator.performance import cached_extraction

@cached_extraction
def cached_extract(pdf_path):
    return client.extract_text(pdf_path)

# Subsequent calls to same file use cache
result1 = cached_extract("document.pdf")  # Processes file
result2 = cached_extract("document.pdf")  # Uses cache
```

### 5. Handle Errors Gracefully

```python
def safe_extract_text(pdf_path, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.extract_text(pdf_path)
        except (ProcessingError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
    except SecurityError:
        # Don't retry security errors
        raise
```

## 📚 API Reference

### PDFClient Methods

- `validate_file(pdf_path)`: Comprehensive security validation
- `extract_text(pdf_path, **kwargs)`: Text extraction
- `extract_metadata(pdf_path)`: Metadata extraction
- `extract_tables(pdf_path)`: Table extraction
- `extract_text_llm_optimized(pdf_path)`: LLM-optimized extraction
- `convert_markdown_to_pdf(input_path, output_path)`: MD to PDF conversion
- `convert_html_to_pdf(input_path, output_path)`: HTML to PDF conversion
- `get_comprehensive_info(pdf_path)`: Complete file analysis
- `process_multiple_pdfs(file_paths, operation)`: Batch processing
- `clear_cache()`: Clear extraction cache
- `get_cache_info()`: Get cache statistics

### Performance Functions

- `process_pdfs_parallel(file_paths, operation, **kwargs)`: Parallel processing
- `process_pdfs_free_threaded(file_paths, operation, **kwargs)`: Free-threaded processing
- `get_performance_recommendations()`: System recommendations
- `LRUCache(max_size)`: LRU cache implementation
- `optimize_with_jit(func)`: JIT optimization decorator
- `cached_extraction(func)`: Caching wrapper

### Security Classes

- `PDFSecurityValidator(settings)`: Security validation
- `SSRFProtection()`: SSRF protection
- `ResourceMonitor()`: Resource monitoring
- `secure_pdf_processing(settings, pdf_path)`: Secure processing context

---

*Last updated: 2025-11-15*
*Python version: 3.13+*
*Status: Production Ready*
