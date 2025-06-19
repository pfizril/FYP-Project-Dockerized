@echo off
setlocal enabledelayedexpansion

REM =============================================================================
REM API Security System - Docker Setup Script (Windows)
REM =============================================================================

echo ==============================================================================
echo                     API Security System - Docker Setup
echo ==============================================================================
echo.

REM Check if we're in the right directory
if not exist "docker-compose.yml" (
    echo [ERROR] docker-compose.yml not found. Please run this script from the project root.
    exit /b 1
)

REM Parse command line arguments
set MODE=production
if "%1"=="--dev" set MODE=development
if "%1"=="--development" set MODE=development
if "%1"=="--help" goto :help
if "%1"=="-h" goto :help

echo [INFO] Starting setup in %MODE% mode...
echo.

REM Check Docker installation
echo [INFO] Checking Docker installation...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    echo [INFO] Visit: https://docs.docker.com/desktop/install/windows/
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose is not installed. Please install Docker Compose first.
    echo [INFO] Visit: https://docs.docker.com/compose/install/
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo [SUCCESS] Docker and Docker Compose are properly installed and running.
echo.

REM Setup environment file
echo [INFO] Setting up environment configuration...
if not exist ".env" (
    if exist "env.example" (
        copy env.example .env >nul
        echo [SUCCESS] Created .env file from env.example
    ) else (
        echo [WARNING] env.example not found. Creating basic .env file...
        (
            echo # Database Configuration
            echo POSTGRES_DB=api_security
            echo POSTGRES_USER=postgres
            echo POSTGRES_PASSWORD=secure_password_change_in_production
            echo.
            echo # Backend Configuration
            echo SECRET_KEY=your-super-secret-key-change-in-production-minimum-32-characters
            echo ALGORITHM=HS256
            echo ACCESS_TOKEN_EXPIRE_MINUTES=30
            echo HEALTH_CHECK_API_KEY=health-monitor-key-change-in-production
            echo.
            echo # CORS Configuration
            echo CORS_ORIGINS=http://localhost:3000,http://localhost:80,http://frontend:80,http://127.0.0.1:3000
            echo.
            echo # Environment
            echo ENVIRONMENT=development
            echo LOG_LEVEL=INFO
            echo.
            echo # Frontend Configuration
            echo NEXT_PUBLIC_API_URL=http://backend:8000
            echo NEXT_PUBLIC_DEFAULT_API_URL=http://backend:8000
            echo NEXT_PUBLIC_APP_URL=http://localhost:80
            echo NODE_ENV=production
        ) > .env
        echo [SUCCESS] Created basic .env file
    )
) else (
    echo [WARNING] .env file already exists. Skipping creation.
)
echo.

REM Check ports
echo [INFO] Checking if required ports are available...
set CONFLICTS=
for %%p in (80 8000 5432 6379) do (
    netstat -an | find "%%p" | find "LISTENING" >nul 2>&1
    if not errorlevel 1 (
        if defined CONFLICTS (
            set CONFLICTS=!CONFLICTS!, %%p
        ) else (
            set CONFLICTS=%%p
        )
    )
)

if defined CONFLICTS (
    echo [WARNING] The following ports are already in use: %CONFLICTS%
    echo [INFO] You may need to stop conflicting services or change ports in docker-compose.yml
    set /p CONTINUE="Continue anyway? (y/N): "
    if /i not "!CONTINUE!"=="y" exit /b 1
) else (
    echo [SUCCESS] All required ports are available.
)
echo.

REM Stop any existing services
echo [INFO] Stopping any existing services...
docker-compose down >nul 2>&1
docker-compose -f docker-compose.dev.yml down >nul 2>&1

REM Start services
echo [INFO] Starting services in %MODE% mode...
if "%MODE%"=="development" (
    docker-compose -f docker-compose.dev.yml up --build -d
) else (
    docker-compose up --build -d
)

if errorlevel 1 (
    echo [ERROR] Failed to start services.
    echo [INFO] Check logs with: docker-compose logs
    pause
    exit /b 1
)

echo [SUCCESS] Services started successfully!
echo.

REM Wait for services
echo [INFO] Waiting for services to be ready...
set /a ATTEMPT=1
set /a MAX_ATTEMPTS=30

:wait_loop
docker-compose ps | find "healthy" >nul 2>&1
if not errorlevel 1 (
    echo [SUCCESS] All services are ready!
    goto :show_status
)

docker-compose ps | find "Up" >nul 2>&1
if not errorlevel 1 (
    echo [SUCCESS] All services are ready!
    goto :show_status
)

if %ATTEMPT% geq %MAX_ATTEMPTS% (
    echo [ERROR] Services failed to start within expected time.
    echo [INFO] Check logs with: docker-compose logs
    pause
    exit /b 1
)

echo [INFO] Waiting for services... (attempt %ATTEMPT%/%MAX_ATTEMPTS%)
timeout /t 10 /nobreak >nul
set /a ATTEMPT+=1
goto :wait_loop

:show_status
echo.
echo [INFO] Service Status:
docker-compose ps

echo.
echo [INFO] Service URLs:
echo   Frontend: http://localhost:80 (production) or http://localhost:3000 (development)
echo   Backend API: http://localhost:8000
echo   API Documentation: http://localhost:8000/docs
echo   Database: localhost:5432
echo   Redis: localhost:6379

echo.
echo [INFO] Useful Commands:
echo   View logs: docker-compose logs -f
echo   Stop services: docker-compose down
echo   Restart services: docker-compose restart
echo   Access backend shell: docker-compose exec backend bash
echo   Access database: docker-compose exec db psql -U postgres -d api_security
echo   View service health: docker-compose ps

echo.
echo [SUCCESS] Setup completed successfully!
echo [INFO] Your API Security System is now running in %MODE% mode.
pause
exit /b 0

:help
echo Usage: %0 [OPTIONS]
echo Options:
echo   --dev, --development    Start in development mode with hot-reload
echo   --help, -h              Show this help message
pause
exit /b 0 