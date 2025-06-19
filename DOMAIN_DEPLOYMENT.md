# 🌐 Domain Deployment Guide - API Security System

This guide will help you deploy your API Security System with a domain name and SSL certificates.

## 📋 Prerequisites

- A domain name (e.g., `yourdomain.com`)
- A server/VPS with Docker and Docker Compose installed
- SSL certificates (Let's Encrypt recommended)
- DNS access to configure domain records

## 🚀 Quick Deployment Steps

### 1. Prepare Your Domain

#### DNS Configuration
Configure your DNS records:

```
# For main domain
A    yourdomain.com     → YOUR_SERVER_IP
A    www.yourdomain.com → YOUR_SERVER_IP

# For API subdomain (optional)
A    api.yourdomain.com → YOUR_SERVER_IP
```

#### SSL Certificates
Get SSL certificates using Let's Encrypt:

```bash
# Install certbot
sudo apt update
sudo apt install certbot

# Get certificates
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# Certificates will be saved to:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

### 2. Configure Environment

```bash
# Copy production environment template
cp env.production.example .env

# Edit environment variables
nano .env
```

**Update these key variables in `.env`:**

```bash
# Replace 'yourdomain.com' with your actual domain
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://api.yourdomain.com

# Frontend Configuration
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_DEFAULT_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_APP_URL=https://yourdomain.com

# Production settings
ENVIRONMENT=production
LOG_LEVEL=WARNING

# Generate secure passwords
SECRET_KEY=your-production-secret-key-minimum-32-characters
POSTGRES_PASSWORD=your-production-db-password
REDIS_PASSWORD=your-production-redis-password
HEALTH_CHECK_API_KEY=your-production-health-check-key
```

### 3. Configure SSL Certificates

```bash
# Create SSL directory
mkdir -p ssl

# Copy certificates (adjust paths as needed)
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem

# Set proper permissions
sudo chown -R $USER:$USER ssl/
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem
```

### 4. Update Nginx Configuration

Edit `nginx.prod.conf` and replace `yourdomain.com` with your actual domain:

```bash
# Replace all occurrences of 'yourdomain.com' with your domain
sed -i 's/yourdomain.com/YOUR_ACTUAL_DOMAIN/g' nginx.prod.conf
```

### 5. Deploy with Production Compose

```bash
# Start production services
docker-compose -f docker-compose.prod.yml up --build -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

## 🔧 Configuration Options

### Option 1: Single Domain Setup
- Frontend and API on same domain: `https://yourdomain.com`
- API endpoints: `https://yourdomain.com/api/`

### Option 2: Subdomain Setup (Recommended)
- Frontend: `https://yourdomain.com`
- API: `https://api.yourdomain.com`

### Option 3: Custom Domain Setup
- Frontend: `https://app.yourdomain.com`
- API: `https://api.yourdomain.com`

## 🔒 Security Configuration

### Environment Variables for Production

```bash
# Security settings
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Strict

# Rate limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=900

# CORS - Only allow your domains
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://api.yourdomain.com
```

### SSL/TLS Configuration

The Nginx configuration includes:
- TLS 1.2 and 1.3 only
- Strong cipher suites
- HSTS headers
- HTTP to HTTPS redirect
- Security headers

## 📊 Monitoring and Maintenance

### Health Checks

```bash
# Check application health
curl https://yourdomain.com/health
curl https://api.yourdomain.com/health

# Check service status
docker-compose -f docker-compose.prod.yml ps
```

### SSL Certificate Renewal

```bash
# Create renewal script
cat > renew-ssl.sh << 'EOF'
#!/bin/bash
# Stop nginx to free port 80
docker-compose -f docker-compose.prod.yml stop nginx

# Renew certificates
sudo certbot renew

# Copy new certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem

# Set permissions
sudo chown -R $USER:$USER ssl/
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem

# Restart nginx
docker-compose -f docker-compose.prod.yml start nginx
EOF

chmod +x renew-ssl.sh

# Add to crontab for automatic renewal
echo "0 12 * * * /path/to/your/project/renew-ssl.sh" | crontab -
```

### Backup Strategy

```bash
# Database backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres api_security > backup_$(date +%Y%m%d_%H%M%S).sql

# SSL certificates backup
cp -r ssl/ ssl_backup_$(date +%Y%m%d)/

# Environment backup
cp .env .env.backup.$(date +%Y%m%d)
```

## 🚨 Troubleshooting

### Common Issues

1. **SSL Certificate Issues**
   ```bash
   # Check certificate validity
   openssl x509 -in ssl/cert.pem -text -noout
   
   # Test SSL connection
   openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
   ```

2. **DNS Issues**
   ```bash
   # Check DNS resolution
   nslookup yourdomain.com
   dig yourdomain.com
   
   # Check if ports are open
   telnet yourdomain.com 80
   telnet yourdomain.com 443
   ```

3. **Container Issues**
   ```bash
   # Check container logs
   docker-compose -f docker-compose.prod.yml logs nginx
   docker-compose -f docker-compose.prod.yml logs backend
   docker-compose -f docker-compose.prod.yml logs frontend
   
   # Restart services
   docker-compose -f docker-compose.prod.yml restart
   ```

4. **CORS Issues**
   ```bash
   # Check CORS configuration
   curl -H "Origin: https://yourdomain.com" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Content-Type" \
        -X OPTIONS https://api.yourdomain.com/auth/token
   ```

### Performance Optimization

1. **Enable HTTP/2**
   - Already configured in nginx.prod.conf

2. **Enable Gzip Compression**
   - Already configured in nginx.prod.conf

3. **Database Optimization**
   ```bash
   # Check database performance
   docker-compose -f docker-compose.prod.yml exec db psql -U postgres -d api_security -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
   ```

## 🔄 Updates and Maintenance

### Application Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up --build -d

# Check for any breaking changes
docker-compose -f docker-compose.prod.yml logs -f
```

### SSL Certificate Renewal

```bash
# Manual renewal
./renew-ssl.sh

# Check renewal status
sudo certbot certificates
```

### Database Migrations

```bash
# Run migrations if needed
docker-compose -f docker-compose.prod.yml exec backend python -m alembic upgrade head
```

## 📈 Production Checklist

- [ ] Domain DNS configured correctly
- [ ] SSL certificates obtained and configured
- [ ] Environment variables set for production
- [ ] Strong passwords generated and set
- [ ] CORS origins configured correctly
- [ ] SSL certificate renewal automated
- [ ] Database backups configured
- [ ] Monitoring and logging enabled
- [ ] Rate limiting configured
- [ ] Security headers enabled
- [ ] Health checks working
- [ ] Error pages configured
- [ ] Performance optimized

## 🆘 Support

If you encounter issues:

1. Check the logs: `docker-compose -f docker-compose.prod.yml logs -f`
2. Verify SSL certificates: `openssl x509 -in ssl/cert.pem -text -noout`
3. Test connectivity: `curl -I https://yourdomain.com`
4. Check DNS: `nslookup yourdomain.com`

For additional help, refer to the main [DOCKER_SETUP.md](DOCKER_SETUP.md) guide. 