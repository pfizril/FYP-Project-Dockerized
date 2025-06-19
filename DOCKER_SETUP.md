# Docker Setup Guide - API Security System

This guide provides complete instructions for setting up and running the API Security System using Docker and Docker Compose.

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+
- At least 4GB RAM available for Docker
- Git

### 1. Clone and Setup

```bash
# Clone the repository (if not already done)
git clone <your-repo-url>
cd FYP-ProtoDocker

# Copy environment file
cp env.example .env

# Edit environment variables (optional)
nano .env
```

### 2. Production Deployment

```bash
# Build and start all services
docker-compose up --build -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Development Mode (with Hot-Reload)

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up --build -d

# Check service status
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs -f
```

## 📋 Service Architecture

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

## 🔧 Configuration

### Environment Variables

Key environment variables in `.env`:

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

### Ports

- **Frontend**: http://localhost:80 (production) or http://localhost:3000 (development)
- **Backend API**: http://localhost:8000
- **Database**: localhost:5432
- **Redis**: localhost:6379

## 🛠️ Development Workflow

### Hot-Reload Development

1. **Start development environment:**
   ```bash
   docker-compose -f docker-compose.dev.yml up --build -d
   ```

2. **Access services:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

3. **Code changes:**
   - Frontend changes auto-reload at http://localhost:3000
   - Backend changes auto-reload at http://localhost:8000

### Database Management

```bash
# Connect to database
docker-compose exec db psql -U postgres -d api_security

# View database logs
docker-compose logs db

# Reset database (WARNING: destroys all data)
docker-compose down -v
docker-compose up -d db
```

## 🔍 Monitoring and Debugging

### Health Checks

All services include health checks:

```bash
# Check service health
docker-compose ps

# View health check logs
docker-compose exec backend curl http://localhost:8000/health
docker-compose exec frontend wget --spider http://localhost:80/
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db

# View last 100 lines
docker-compose logs --tail=100 backend
```

### Debugging

```bash
# Access container shell
docker-compose exec backend bash
docker-compose exec frontend sh
docker-compose exec db psql -U postgres

# Check container resources
docker stats

# Inspect container
docker-compose exec backend env
```

## 🚨 Troubleshooting

### Common Issues

1. **Port conflicts:**
   ```bash
   # Check what's using the port
   netstat -tulpn | grep :8000
   
   # Stop conflicting services
   sudo systemctl stop apache2  # if using port 80
   ```

2. **Database connection issues:**
   ```bash
   # Check database status
   docker-compose exec db pg_isready -U postgres
   
   # Restart database
   docker-compose restart db
   ```

3. **Build failures:**
   ```bash
   # Clean build cache
   docker-compose build --no-cache
   
   # Remove all containers and volumes
   docker-compose down -v
   docker system prune -a
   ```

4. **Permission issues:**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   chmod -R 755 .
   ```

### Performance Issues

1. **Increase Docker resources:**
   - Docker Desktop: Settings → Resources → Memory (8GB+)
   - Docker Engine: Edit `/etc/docker/daemon.json`

2. **Optimize database:**
   ```bash
   # Check database performance
   docker-compose exec db psql -U postgres -d api_security -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
   ```

## 🔒 Security Considerations

### Production Deployment

1. **Change default passwords:**
   ```bash
   # Generate secure passwords
   openssl rand -base64 32
   ```

2. **Use secrets management:**
   ```bash
   # Create Docker secrets
   echo "your-secret-key" | docker secret create secret_key -
   ```

3. **Enable HTTPS:**
   - Add SSL certificates
   - Configure Nginx for HTTPS
   - Update CORS settings

4. **Network security:**
   ```bash
   # Use custom networks
   docker network create --driver bridge --subnet=172.20.0.0/16 api_network
   ```

### Environment Variables

Never commit `.env` files to version control:

```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo ".env.*" >> .gitignore
```

## 📊 Monitoring

### Application Metrics

```bash
# Check API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Monitor database connections
docker-compose exec db psql -U postgres -d api_security -c "SELECT count(*) FROM pg_stat_activity;"
```

### Resource Usage

```bash
# Monitor container resources
docker stats

# Check disk usage
docker system df
```

## 🧹 Maintenance

### Regular Maintenance

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

For additional help, please refer to the project documentation or create an issue in the repository. 