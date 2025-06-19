#!/bin/bash

# =============================================================================
# API Security System - Docker Setup Script
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Docker installation
check_docker() {
    print_status "Checking Docker installation..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        print_status "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        print_status "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are properly installed and running."
}

# Function to setup environment file
setup_env() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        if [ -f env.example ]; then
            cp env.example .env
            print_success "Created .env file from env.example"
        else
            print_warning "env.example not found. Creating basic .env file..."
            cat > .env << EOF
# Database Configuration
POSTGRES_DB=api_security
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password_change_in_production

# Backend Configuration
SECRET_KEY=your-super-secret-key-change-in-production-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
HEALTH_CHECK_API_KEY=health-monitor-key-change-in-production

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:80,http://frontend:80,http://127.0.0.1:3000

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://backend:8000
NEXT_PUBLIC_DEFAULT_API_URL=http://backend:8000
NEXT_PUBLIC_APP_URL=http://localhost:80
NODE_ENV=production
EOF
            print_success "Created basic .env file"
        fi
    else
        print_warning ".env file already exists. Skipping creation."
    fi
}

# Function to check ports
check_ports() {
    print_status "Checking if required ports are available..."
    
    local ports=("80" "8000" "5432" "6379")
    local conflicts=()
    
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            conflicts+=("$port")
        fi
    done
    
    if [ ${#conflicts[@]} -gt 0 ]; then
        print_warning "The following ports are already in use: ${conflicts[*]}"
        print_status "You may need to stop conflicting services or change ports in docker-compose.yml"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "All required ports are available."
    fi
}

# Function to build and start services
start_services() {
    local mode=$1
    
    print_status "Starting services in $mode mode..."
    
    if [ "$mode" = "development" ]; then
        docker-compose -f docker-compose.dev.yml up --build -d
    else
        docker-compose up --build -d
    fi
    
    print_success "Services started successfully!"
}

# Function to wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps | grep -q "healthy\|Up"; then
            print_success "All services are ready!"
            return 0
        fi
        
        print_status "Waiting for services... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    print_error "Services failed to start within expected time."
    print_status "Check logs with: docker-compose logs"
    return 1
}

# Function to show service status
show_status() {
    print_status "Service Status:"
    docker-compose ps
    
    echo
    print_status "Service URLs:"
    echo "  Frontend: http://localhost:80 (production) or http://localhost:3000 (development)"
    echo "  Backend API: http://localhost:8000"
    echo "  API Documentation: http://localhost:8000/docs"
    echo "  Database: localhost:5432"
    echo "  Redis: localhost:6379"
}

# Function to show useful commands
show_commands() {
    echo
    print_status "Useful Commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Stop services: docker-compose down"
    echo "  Restart services: docker-compose restart"
    echo "  Access backend shell: docker-compose exec backend bash"
    echo "  Access database: docker-compose exec db psql -U postgres -d api_security"
    echo "  View service health: docker-compose ps"
}

# Main function
main() {
    echo "=============================================================================="
    echo "                    API Security System - Docker Setup"
    echo "=============================================================================="
    echo
    
    # Check if we're in the right directory
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found. Please run this script from the project root."
        exit 1
    fi
    
    # Parse command line arguments
    MODE="production"
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dev|--development)
                MODE="development"
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --dev, --development    Start in development mode with hot-reload"
                echo "  --help, -h              Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information."
                exit 1
                ;;
        esac
    done
    
    print_status "Starting setup in $MODE mode..."
    
    # Run setup steps
    check_docker
    setup_env
    check_ports
    
    # Stop any existing services
    print_status "Stopping any existing services..."
    docker-compose down 2>/dev/null || true
    docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
    
    # Start services
    start_services "$MODE"
    
    # Wait for services
    wait_for_services
    
    # Show status and commands
    show_status
    show_commands
    
    echo
    print_success "Setup completed successfully!"
    print_status "Your API Security System is now running in $MODE mode."
}

# Run main function with all arguments
main "$@" 