@echo off
REM VDS PDF Orchestrator Team Setup Script (Windows)

setlocal enabledelayedexpansion

echo ========================================
echo VDS PDF Orchestrator Team Setup
echo ========================================
echo.

REM Function to check if command exists
:check_command
where %1 >nul 2>nul
goto :eof

REM Function to print colored output (Windows 10+)
:print_status
if "%~2"=="BLUE" echo [94m%~3[0m
if "%~2"=="GREEN" echo [92m%~3[0m
if "%~2"=="YELLOW" echo [93m%~3[0m
if "%~2"=="RED" echo [91m%~3[0m
goto :eof

REM Check Python installation
echo [94mChecking Python installation...[0m

call :check_command python3
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python3"
) else (
    call :check_command python
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=python"
    ) else (
        echo [91m❌ Python is not installed. Please install Python 3.13+ first.[0m
        echo    Visit https://www.python.org/downloads/ for installation instructions
        pause
        exit /b 1
    )
)

REM Check Python version
for /f "tokens=*" %%i in ('!PYTHON_CMD! -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PYTHON_VERSION=%%i

echo [92m✅ Python !PYTHON_VERSION! found[0m
echo.

REM Check uv installation
echo [94mChecking uv installation...[0m

call :check_command uv
if !errorlevel! equ 0 (
    echo [92m✅ uv is installed[0m
    echo [94mUpdating uv to latest version...[0m
    uv self update
) else (
    echo [93m⚠️  uv is not installed. Installing uv...[0m
    echo    Installing uv (fast Python package manager)...

    REM Download and install uv using PowerShell
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"

    REM Check if installation succeeded
    timeout /t 2 >nul
    call :check_command uv
    if !errorlevel! equ 0 (
        echo [92m✅ uv installed successfully![0m
    ) else (
        echo [91m❌ uv installation failed. Please install manually:[0m
        echo    Visit https://github.com/astral-sh/uv for installation instructions
        pause
        exit /b 1
    )
)

REM Setup development environment
echo [94mSetting up development environment...[0m

REM Create necessary directories
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "cache" mkdir cache

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo [94mCreating .env file...[0m
    (
        echo # VDS PDF Orchestrator Environment Configuration
        echo.
        echo # Development Settings
        echo ENV=development
        echo LOG_LEVEL=debug
        echo PYTHONPATH=/app/src
        echo PYTHONUNBUFFERED=1
        echo.
        echo # Security Settings ^(Development^)
        echo VDS_PDF_MAX_FILE_SIZE=104857600  REM 100MB for dev testing
        echo VDS_PDF_MAX_PAGES=500
        echo VDS_PDF_ENABLE_SECURITY_VALIDATION=true
        echo VDS_PDF_ENABLE_URI_VALIDATION=false  REM Disabled for dev convenience
        echo VDS_PDF_CONVERSION_TIMEOUT=300
        echo.
        echo # Resource Limits
        echo VDS_PDF_MAX_MEMORY_MB=1024
        echo VDS_PDF_MAX_CONVERSIONS_PER_MINUTE=20
        echo.
        echo # MCP Server Configuration
        echo MCP_SERVER_NAME=vds-pdf-orchestrator-dev
        echo MCP_SERVER_VERSION=0.1.0-dev
    ) > .env
    echo [92m✅ .env file created[0m
) else (
    echo [92m✅ .env file already exists[0m
)

REM Install dependencies
echo [94mInstalling Python dependencies...[0m

uv sync
if !errorlevel! equ 0 (
    echo [92m✅ Dependencies installed successfully![0m
) else (
    echo [91m❌ Failed to install dependencies[0m
    pause
    exit /b 1
)

REM Run tests
echo [94mRunning tests to verify installation...[0m

uv run pytest
if !errorlevel! equ 0 (
    echo [92m✅ All tests passed![0m
) else (
    echo [93m⚠️  Some tests failed. Check the output above for details.[0m
    echo    This might be due to missing optional dependencies or configuration issues.
)

REM Check Docker setup
echo [94mChecking Docker setup...[0m

call :check_command docker
if !errorlevel! equ 0 (
    call :check_command docker-compose
    if !errorlevel! equ 0 (
        echo [92m✅ Docker and Docker Compose are available[0m

        REM Test Docker Compose configuration
        docker-compose config >nul 2>&1
        if !errorlevel! equ 0 (
            echo [92m✅ Docker Compose configuration is valid[0m
            echo [94mYou can start the development environment with:[0m
            echo    docker-compose up -d
        ) else (
            echo [93m⚠️  Docker Compose configuration has issues[0m
            echo    Check the docker-compose.yml file for errors
        )
    ) else (
        echo [93m⚠️  Docker Compose is not available[0m
        echo    Docker Compose is optional but recommended for full development experience
        echo    Install Docker Desktop from: https://docs.docker.com/get-docker/
    )
) else (
    echo [93m⚠️  Docker is not available[0m
    echo    Docker is optional but recommended for full development experience
    echo    Install Docker from: https://docs.docker.com/get-docker/
)

REM Create development scripts
echo [94mCreating development convenience scripts...[0m

REM Create start script
(
    echo @echo off
    echo REM Start VDS PDF Orchestrator development environment
    echo.
    echo echo 🚀 Starting VDS PDF Orchestrator development environment...
    echo.
    echo REM Start Docker services
    echo echo Starting Docker services...
    echo docker-compose up -d
    echo.
    echo REM Wait for services to be ready
    echo echo Waiting for services to be ready...
    echo timeout /t 10 >nul
    echo.
    echo REM Check service status
    echo echo Checking service status...
    echo docker-compose ps
    echo.
    echo REM Show health status
    echo echo Checking service health...
    echo curl -s http://localhost:8000/health 2^>nul ^|^| echo Health check not available yet
    echo.
    echo echo ✅ Development environment started!
    echo echo.
    echo echo Services available:
    echo echo   - MCP Server: http://localhost:8000
    echo echo   - Redis: localhost:6379
    echo echo   - Logs: docker-compose logs -f vds-pdf-orchestrator
    echo echo.
    echo echo To stop: docker-compose down
) > start_dev.bat

REM Create test script
(
    echo @echo off
    echo REM Run tests for VDS PDF Orchestrator
    echo.
    echo echo 🧪 Running VDS PDF Orchestrator tests...
    echo.
    echo REM Activate virtual environment and run tests
    echo .venv\Scripts\activate ^&^& pytest -v
    echo.
    echo echo ✅ Tests completed!
) > run_tests.bat

REM Create lint script
(
    echo @echo off
    echo REM Run linting for VDS PDF Orchestrator
    echo.
    echo echo 🔍 Running code linting...
    echo.
    echo REM Activate virtual environment
    echo .venv\Scripts\activate
    echo.
    echo REM Run ruff
    echo ruff check .
    echo if !errorlevel! equ 0 ^(
    echo     echo ✅ No linting issues found!
    echo ^) else ^(
    echo     echo ⚠️  Linting issues found. Run 'ruff check --fix .' to fix auto-fixable issues.
    echo ^)
    echo.
    echo REM Run formatting check
    echo ruff format --check .
    echo if !errorlevel! equ 0 ^(
    echo     echo ✅ Code formatting is correct!
    echo ^) else ^(
    echo     echo ⚠️  Code formatting issues found. Run 'ruff format .' to fix.
    echo ^)
) > lint.bat

echo [92m✅ Development scripts created:[0m
echo    - start_dev.bat: Start development environment
echo    - run_tests.bat: Run test suite
echo    - lint.bat: Run code linting
echo.

REM Show next steps
echo [92m🎉 VDS PDF Orchestrator setup completed successfully![0m
echo.
echo 📋 Next steps:
echo.
echo 1. Start development environment:
echo    start_dev.bat
echo    or: docker-compose up -d
echo.
echo 2. Run tests:
echo    run_tests.bat
echo    or: uv run pytest
echo.
echo 3. Run MCP server locally:
echo    .venv\Scripts\activate
echo    python -m src.vds_pdf_orchestrator.mcp_server
echo.
echo 4. Check code quality:
echo    lint.bat
echo.
echo 5. View logs:
echo    docker-compose logs -f vds-pdf-orchestrator
echo.
echo 6. Check service health:
echo    curl http://localhost:8000/health
echo.
echo 📚 For more information, see:
echo    - README.md: General documentation
echo    - README_DOCKER.md: Docker development guide
echo    - TEAM_INSTALLATION.md: Team installation guide
echo.

pause