# 🐳 Docker Setup for API Security System

This repository now includes a complete Docker setup for the API Security System, enabling easy deployment and development with containerization.

## 📁 Files Created

### Core Docker Files
- **`Dockerfile.backend`** - FastAPI backend container with Python 3.11
- **`Dockerfile.frontend`** - Next.js frontend container with Nginx (production)
- **`Dockerfile.frontend.dev`** - Next.js frontend container for development
- **`docker-compose.yml`** - Production orchestration
- **`docker-compose.dev.yml`** - Development orchestration with hot-reload

### Configuration Files
- **`nginx.conf`** - Nginx configuration for frontend serving and API proxying
- **`init-db.sql`** - PostgreSQL database initialization script
- **`.dockerignore`** - Docker build optimization
- **`env.example`** - Environment variables template

### Setup Scripts
- **`setup-docker.sh`** - Linux/macOS setup script
- **`setup-docker.bat`** - Windows setup script
- **`DOCKER_SETUP.md`** - Comprehensive setup guide

## 🚀 Quick Start

### Windows Users
```cmd
# Run the setup script
setup-docker.bat

# For development mode
setup-docker.bat --dev
```

### Linux/macOS Users
```bash
# Make script executable (if needed)
chmod +x setup-docker.sh

# Run the setup script
./setup-docker.sh

# For development mode
./setup-docker.sh --dev
```

### Manual Setup
```bash
# 1. Copy environment file
cp env.example .env

# 2. Edit environment variables (optional)
nano .env

# 3. Start production environment
docker-compose up --build -d

# 4. Or start development environment
docker-compose -f docker-compose.dev.yml up --build -d
```

## 🌐 Service URLs

### Production Mode
- **Frontend**: http://localhost:80
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database**: localhost:5432
- **Redis**: localhost:6379

### Development Mode
- **Frontend**: http://localhost:3000 (with hot-reload)
- **Backend API**: http://localhost:8000 (with hot-reload)
- **API Documentation**: http://localhost:8000/docs
- **Database**: localhost:5432
- **Redis**: localhost:6379

## 🔧 Key Features

### ✅ Production Ready
- **Multi-stage builds** for optimized images
- **Nginx reverse proxy** with security headers
- **PostgreSQL database** with proper initialization
- **Redis caching** for performance
- **Health checks** for all services
- **Volume persistence** for data
- **Security hardening** with non-root users

### ✅ Development Friendly
- **Hot-reload** for both frontend and backend
- **Source code mounting** for live development
- **Separate development compose file**
- **Debug-friendly logging**
- **Easy environment switching**

### ✅ Security Features
- **CORS configuration** for cross-origin requests
- **Rate limiting** on API endpoints
- **Security headers** in Nginx
- **CSRF protection** maintained
- **Environment variable management**
- **Non-root container execution**

## 🛠️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   PostgreSQL    │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   Database      │
│   Port: 80/3000 │    │   Port: 8000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │     Redis       │
                    │   (Optional)    │
                    │   Port: 6379    │
                    └─────────────────┘
```

## 📋 Environment Variables

Key variables in `.env`:

```bash
# Database
POSTGRES_DB=api_security
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password_change_in_production

# Backend
SECRET_KEY=your-super-secret-key-change-in-production
DATABASE_URL=postgresql://postgres:secure_password@db:5432/api_security

# Frontend
NEXT_PUBLIC_API_URL=http://backend:8000
NEXT_PUBLIC_DEFAULT_API_URL=http://backend:8000
```

## 🔍 Monitoring & Debugging

### Health Checks
```bash
# Check service status
docker-compose ps

# Test health endpoints
curl http://localhost:8000/health
```

### Logs
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### Debugging
```bash
# Access container shells
docker-compose exec backend bash
docker-compose exec frontend sh
docker-compose exec db psql -U postgres -d api_security

# Check container resources
docker stats
```

## 🚨 Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check port usage
   netstat -tulpn | grep :8000
   
   # Stop conflicting services
   sudo systemctl stop apache2  # if using port 80
   ```

2. **Build Failures**
   ```bash
   # Clean build cache
   docker-compose build --no-cache
   
   # Remove all containers and volumes
   docker-compose down -v
   docker system prune -a
   ```

3. **Database Issues**
   ```bash
   # Check database status
   docker-compose exec db pg_isready -U postgres
   
   # Restart database
   docker-compose restart db
   ```

## 🔒 Security Considerations

### Production Deployment
1. **Change default passwords** in `.env`
2. **Use secrets management** for sensitive data
3. **Enable HTTPS** with SSL certificates
4. **Configure firewall rules**
5. **Regular security updates**

### Environment Variables
- Never commit `.env` files to version control
- Use different passwords for each environment
- Rotate secrets regularly

## 📊 Performance Optimization

### Database
- Connection pooling configured
- Indexes for common queries
- Optimized PostgreSQL settings

### Frontend
- Nginx caching for static assets
- Gzip compression enabled
- Optimized build process

### Backend
- Uvicorn with multiple workers
- Connection pooling
- Redis caching support

## 🧹 Maintenance

### Regular Tasks
```bash
# Update images
docker-compose pull

# Rebuild services
docker-compose up --build -d

# Clean up unused resources
docker system prune -f

# Backup database
docker-compose exec db pg_dump -U postgres api_security > backup.sql
```

### Backup and Restore
```bash
# Backup
docker-compose exec db pg_dump -U postgres api_security > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
docker-compose exec -T db psql -U postgres api_security < backup.sql
```

## 📚 Additional Resources

- [DOCKER_SETUP.md](DOCKER_SETUP.md) - Detailed setup guide
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 🆘 Support

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Verify environment variables: `docker-compose exec backend env`
3. Test connectivity: `docker-compose exec backend curl http://localhost:8000/health`
4. Check resource usage: `docker stats`

For additional help, refer to the detailed [DOCKER_SETUP.md](DOCKER_SETUP.md) guide. 