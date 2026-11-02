#!/bin/bash
# VDS PDF Orchestrator Team Setup Script

set -e

echo "🚀 Setting up VDS PDF Orchestrator for team development..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python() {
    print_status $BLUE "Checking Python installation..."

    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_status $RED "❌ Python is not installed. Please install Python 3.13+ first."
        echo "   Visit https://www.python.org/downloads/ for installation instructions"
        exit 1
    fi

    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$PYTHON_VERSION >= 3.13" | bc -l 2>/dev/null || echo "0") == "1" ]]; then
        print_status $GREEN "✅ Python $PYTHON_VERSION found (3.13+ required)"
    else
        print_status $YELLOW "⚠️  Python $PYTHON_VERSION found (3.13+ recommended)"
        echo "   Consider upgrading to Python 3.13+ for better performance and features"
    fi
}

# Function to check and install uv
check_uv() {
    print_status $BLUE "Checking uv installation..."

    if command_exists uv; then
        print_status $GREEN "✅ uv is installed"
        # Update uv to latest version
        print_status $BLUE "Updating uv to latest version..."
        uv self update
    else
        print_status $YELLOW "⚠️  uv is not installed. Installing uv..."
        echo "   Installing uv (fast Python package manager)..."

        # Download and install uv
        curl -LsSf https://astral.sh/uv/install.sh | sh

        # Add uv to PATH
        export PATH="$HOME/.cargo/bin:$PATH"

        if command_exists uv; then
            print_status $GREEN "✅ uv installed successfully!"
        else
            print_status $RED "❌ uv installation failed. Please install manually:"
            echo "   Visit https://github.com/astral-sh/uv for installation instructions"
            exit 1
        fi
    fi
}

# Function to setup development environment
setup_environment() {
    print_status $BLUE "Setting up development environment..."

    # Create necessary directories
    mkdir -p data logs cache

    # Create .env file if it doesn't exist
    if [[ ! -f .env ]]; then
        print_status $BLUE "Creating .env file..."
        cat > .env << EOF
# VDS PDF Orchestrator Environment Configuration

# Development Settings
ENV=development
LOG_LEVEL=debug
PYTHONPATH=/app/src
PYTHONUNBUFFERED=1

# Security Settings (Development)
VDS_PDF_MAX_FILE_SIZE=104857600  # 100MB for dev testing
VDS_PDF_MAX_PAGES=500
VDS_PDF_ENABLE_SECURITY_VALIDATION=true
VDS_PDF_ENABLE_URI_VALIDATION=false  # Disabled for dev convenience
VDS_PDF_CONVERSION_TIMEOUT=300

# Resource Limits
VDS_PDF_MAX_MEMORY_MB=1024
VDS_PDF_MAX_CONVERSIONS_PER_MINUTE=20

# MCP Server Configuration
MCP_SERVER_NAME=vds-pdf-orchestrator-dev
MCP_SERVER_VERSION=0.1.0-dev
EOF
        print_status $GREEN "✅ .env file created"
    else
        print_status $GREEN "✅ .env file already exists"
    fi
}

# Function to install dependencies
install_dependencies() {
    print_status $BLUE "Installing Python dependencies..."

    # Use uv to install dependencies
    if uv sync; then
        print_status $GREEN "✅ Dependencies installed successfully!"
    else
        print_status $RED "❌ Failed to install dependencies"
        exit 1
    fi
}

# Function to run tests
run_tests() {
    print_status $BLUE "Running tests to verify installation..."

    # Activate virtual environment and run tests
    if uv run pytest; then
        print_status $GREEN "✅ All tests passed!"
    else
        print_status $YELLOW "⚠️  Some tests failed. Check the output above for details."
        echo "   This might be due to missing optional dependencies or configuration issues."
    fi
}

# Function to setup Docker
setup_docker() {
    print_status $BLUE "Checking Docker setup..."

    if command_exists docker && command_exists docker-compose; then
        print_status $GREEN "✅ Docker and Docker Compose are available"

        # Test Docker Compose configuration
        if docker-compose config > /dev/null 2>&1; then
            print_status $GREEN "✅ Docker Compose configuration is valid"

            print_status $BLUE "You can start the development environment with:"
            echo "   docker-compose up -d"
        else
            print_status $YELLOW "⚠️  Docker Compose configuration has issues"
            echo "   Check the docker-compose.yml file for errors"
        fi
    else
        print_status $YELLOW "⚠️  Docker or Docker Compose is not available"
        echo "   Docker is optional but recommended for full development experience"
        echo "   Install Docker from: https://docs.docker.com/get-docker/"
    fi
}

# Function to create development scripts
create_dev_scripts() {
    print_status $BLUE "Creating development convenience scripts..."

    # Create start script
    cat > start_dev.sh << 'EOF'
#!/bin/bash
# Start VDS PDF Orchestrator development environment

echo "🚀 Starting VDS PDF Orchestrator development environment..."

# Start Docker services
echo "Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Check service status
echo "Checking service status..."
docker-compose ps

# Show health status
echo "Checking service health..."
curl -s http://localhost:8000/health 2>/dev/null || echo "Health check not available yet"

echo "✅ Development environment started!"
echo ""
echo "Services available:"
echo "  - MCP Server: http://localhost:8000"
echo "  - Redis: localhost:6379"
echo "  - Logs: docker-compose logs -f vds-pdf-orchestrator"
echo ""
echo "To stop: docker-compose down"
EOF
    chmod +x start_dev.sh

    # Create test script
    cat > run_tests.sh << 'EOF'
#!/bin/bash
# Run tests for VDS PDF Orchestrator

echo "🧪 Running VDS PDF Orchestrator tests..."

# Activate virtual environment and run tests
source .venv/bin/activate
pytest -v

echo "✅ Tests completed!"
EOF
    chmod +x run_tests.sh

    # Create lint script
    cat > lint.sh << 'EOF'
#!/bin/bash
# Run linting for VDS PDF Orchestrator

echo "🔍 Running code linting..."

# Activate virtual environment
source .venv/bin/activate

# Run ruff
ruff check .
if [ $? -eq 0 ]; then
    echo "✅ No linting issues found!"
else
    echo "⚠️  Linting issues found. Run 'ruff check --fix .' to fix auto-fixable issues."
fi

# Run formatting check
ruff format --check .
if [ $? -eq 0 ]; then
    echo "✅ Code formatting is correct!"
else
    echo "⚠️  Code formatting issues found. Run 'ruff format .' to fix."
fi
EOF
    chmod +x lint.sh

    print_status $GREEN "✅ Development scripts created:"
    echo "   - start_dev.sh: Start development environment"
    echo "   - run_tests.sh: Run test suite"
    echo "   - lint.sh: Run code linting"
}

# Function to show next steps
show_next_steps() {
    print_status $GREEN "🎉 VDS PDF Orchestrator setup completed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo ""
    echo "1. Start development environment:"
    echo "   ./start_dev.sh"
    echo "   or: docker-compose up -d"
    echo ""
    echo "2. Run tests:"
    echo "   ./run_tests.sh"
    echo "   or: uv run pytest"
    echo ""
    echo "3. Run MCP server locally:"
    echo "   source .venv/bin/activate"
    echo "   python -m src.vds_pdf_orchestrator.mcp_server"
    echo ""
    echo "4. Check code quality:"
    echo "   ./lint.sh"
    echo ""
    echo "5. View logs:"
    echo "   docker-compose logs -f vds-pdf-orchestrator"
    echo ""
    echo "6. Check service health:"
    echo "   curl http://localhost:8000/health"
    echo ""
    echo "📚 For more information, see:"
    echo "   - README.md: General documentation"
    echo "   - README_DOCKER.md: Docker development guide"
    echo "   - TEAM_INSTALLATION.md: Team installation guide"
}

# Main execution
main() {
    echo "========================================"
    echo "VDS PDF Orchestrator Team Setup"
    echo "========================================"
    echo ""

    # Check prerequisites
    check_python
    check_uv

    # Setup environment
    setup_environment

    # Install dependencies
    install_dependencies

    # Run tests
    run_tests

    # Setup Docker (optional)
    setup_docker

    # Create development scripts
    create_dev_scripts

    # Show next steps
    show_next_steps
}

# Handle Ctrl+C gracefully
trap 'print_status $YELLOW "\n⚠️ Setup interrupted. You can resume by running this script again."; exit 1' INT

# Run main function
main "$@"