# VDS PDF Orchestrator - Multi-User Deployment Guide

**Version**: 1.0
**Date**: November 18, 2025
**Purpose**: Complete deployment guide for multi-user and AI agent access

---

## 🎯 **Overview**

This guide provides comprehensive instructions for deploying the VDS PDF Orchestrator in a production environment supporting multiple users and AI agents. The deployment includes containerized services, monitoring, security hardening, and automated scaling capabilities.

### **Deployment Features**
- ✅ **Multi-User Support**: Concurrent access for multiple users
- ✅ **AI Agent Integration**: MCP protocol support for AI agents
- ✅ **Load Balancing**: Nginx-based load balancing with health checks
- ✅ **Session Management**: Redis-based session persistence
- ✅ **Security Hardening**: Enterprise-grade security measures
- ✅ **Monitoring Stack**: Prometheus + Grafana + AlertManager
- ✅ **Auto-Scaling**: Container orchestration support
- ✅ **CI/CD Pipeline**: Automated deployment and testing

---

## 📋 **Prerequisites**

### **System Requirements**
- **Operating System**: Linux (Ubuntu 20.04+ recommended)
- **Docker**: 20.10+ with Docker Compose 2.0+
- **Memory**: 8GB+ RAM minimum (16GB+ recommended)
- **Storage**: 20GB+ free disk space
- **Network**: Internet access for container downloads

### **Required Software**
- **Docker Engine**: Latest stable version
- **Docker Compose**: Latest stable version
- **Git**: For cloning the repository
- **Make**: For build automation (optional)

### **External Dependencies**
- **Domain Name**: For SSL certificates (optional but recommended)
- **Load Balancer**: For high availability (can use built-in Nginx)
- **SSL Certificates**: For HTTPS termination

---

## 🚀 **Quick Start Production Deployment**

### **Step 1: Clone and Prepare Repository**
```bash
# Clone the repository
git clone https://github.com/your-org/vds-pdf-orchestrator.git
cd vds-pdf-orchestrator

# Create production directories
sudo mkdir -p /opt/vds/pdf-orchestrator/{data,logs,cache,redis,prometheus,grafana,alertmanager,sessions}
sudo chown -R $USER:$USER /opt/vds/pdf-orchestrator
```

### **Step 2: Configure Environment Variables**
```bash
# Create production environment file
cp .env.example .env

# Edit environment variables
nano .env
```

**Required Environment Variables:**
```bash
# Production Settings
ENV=production
LOG_LEVEL=info
PYTHONPATH=/app/src
PYTHONUNBUFFERED=1

# Security Settings
VDS_PDF_MAX_FILE_SIZE=52428800  # 50MB
VDS_PDF_MAX_PAGES=100
VDS_PDF_ENABLE_SECURITY_VALIDATION=true
VDS_PDF_ENABLE_URI_VALIDATION=true
VDS_PDF_CONVERSION_TIMEOUT=180

# Resource Limits
VDS_PDF_MAX_MEMORY_MB=2048
VDS_PDF_MAX_CONVERSIONS_PER_MINUTE=50

# MCP Multi-User Settings
MCP_MULTI_USER=true
MCP_CONCURRENT_SESSIONS=100

# Monitoring Settings
PROMETHEUS_ENABLED=true
METRICS_PORT=8080

# Grafana Settings
GRAFANA_ADMIN_PASSWORD=your-secure-password
GRAFANA_DOMAIN=monitoring.your-domain.com

# AlertManager Settings
ALERT_EMAIL=alerts@your-domain.com
ALERT_SMTP_PASSWORD=your-smtp-password
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

### **Step 3: Deploy Production Services**
```bash
# Deploy all services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### **Step 4: Verify Deployment**
```bash
# Wait for services to start (60-90 seconds)
sleep 90

# Test health endpoint
curl http://localhost/health

# Test MCP server
curl -X POST http://localhost/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_service_health",
    "arguments": {}
  }'

# Test load balancer
curl http://localhost/api/health
```

---

## 🔧 **Advanced Configuration**

### **Load Balancer Configuration**

#### **Nginx Configuration** (`config/nginx/nginx.conf`)
```nginx
upstream vds_pdf_backend {
    server vds-pdf-orchestrator:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Load Balancing
    location / {
        proxy_pass http://vds_pdf_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 16k;
    }

    # Health Check Endpoint
    location /health {
        proxy_pass http://vds_pdf_backend/health;
        access_log off;
    }

    # Metrics Endpoint
    location /metrics {
        proxy_pass http://vds_pdf_backend:8080/metrics;
        allow 127.0.0.1;
        allow 10.0.0.0/8;
        deny all;
    }
}
```

### **Redis Configuration** (`config/redis.prod.conf`)
```conf
# Redis Production Configuration
bind 0.0.0.0
port 6379
timeout 300
tcp-keepalive 60

# Persistence
save 900 1
save 300 10
save 60 10000

# Memory Management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Security
requirepass your-redis-password
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Logging
loglevel notice
logfile /var/log/redis/redis.log
syslog-enabled yes

# Performance
tcp-backlog 511
databases 16
```

---

## 📊 **Monitoring and Observability**

### **Access Monitoring Dashboards**

#### **Grafana Dashboard**
- **URL**: `http://localhost:3000`
- **Username**: `admin`
- **Password**: Environment variable `GRAFANA_ADMIN_PASSWORD`

#### **Prometheus**
- **URL**: `http://localhost:9090`
- **Query Interface**: Available at the same URL

#### **AlertManager**
- **URL**: `http://localhost:9093`
- **Silence/Alert Management**: Available at the same URL

### **Key Metrics**

#### **Application Metrics**
- PDF processing rate and duration
- Request patterns and response times
- Error rates and types
- Active MCP sessions
- PII detection statistics
- Compliance scores

#### **Infrastructure Metrics**
- Container resource usage
- Redis performance
- Load balancer metrics
- System resource usage

#### **Alert Rules**
- High error rates (>5%)
- Long processing times (>2s)
- Service downtime
- Resource exhaustion
- Security events

### **Custom Dashboards**

Create custom Grafana dashboards for:

1. **Multi-User Activity**: Track concurrent users and session patterns
2. **AI Agent Integration**: Monitor MCP session performance
3. **Security Events**: Track security validations and threats
4. **Compliance Monitoring**: Real-time compliance score tracking

---

## 🔒 **Security Configuration**

### **Container Security**
```yaml
# Security hardening in Docker Compose
services:
  vds-pdf-orchestrator:
    security_opt:
      - no-new-privileges:true
    read_only: true
    user: "1000:1000"
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
```

### **Network Security**
```yaml
# Network segmentation
networks:
  vds-network:
    driver: bridge
    internal: false
    ipam:
      config:
        - subnet: 172.21.0.0/16
          gateway: 172.21.0.1
```

### **Application Security**
- Input validation and sanitization
- File type verification
- Size limitations
- Malicious content detection
- Session authentication
- Rate limiting

---

## 📈 **Scaling and High Availability**

### **Horizontal Scaling**
```bash
# Scale the application
docker-compose -f docker-compose.prod.yml up -d --scale vds-pdf-orchestrator=3

# Scale with Kubernetes (if using)
kubectl scale deployment vds-pdf-orchestrator --replicas=5
```

### **Auto-Scaling Configuration**

#### **Docker Swarm Mode**
```yaml
version: '3.8'
services:
  vds-pdf-orchestrator:
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      failure_action: rollback
      restart_policy:
        condition: on-failure
      placement:
        max_replicas_per_node: 2
        constraints:
          - node.role == worker
      resources:
        limits:
          memory: 2G
          cpus: '1.5'
        reservations:
          memory: 1G
          cpus: '0.5'
```

#### **Kubernetes Deployment** (`k8s/deployment.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vds-pdf-orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vds-pdf-orchestrator
  template:
    metadata:
      labels:
        app: vds-pdf-orchestrator
    spec:
      containers:
      - name: vds-pdf-orchestrator
        image: vds-pdf-orchestrator:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1.5"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 90
          periodSeconds: 30
```

---

## 🤖 **AI Agent Integration**

### **MCP Protocol Support**
The VDS PDF Orchestrator provides full MCP (Model Context Protocol) support for AI agents:

#### **AI Agent Configuration**
```python
# MCP Client Configuration
MCP_CONFIG = {
    "server_url": "http://your-domain.com",
    "port": 8000,
    "timeout": 300,
    "max_concurrent_sessions": 100,
    "session_timeout": 3600
}
```

#### **Available MCP Tools**
- `validate_pdf_file`: Validate and analyze PDF files
- `extract_text`: Extract text from PDF documents
- `detect_pii`: Detect personally identifiable information
- `redact_content`: Redact sensitive content
- `get_compliance_status`: Check compliance status
- `process_document`: Complete document processing pipeline

#### **AI Agent Usage Examples**
```python
# Example: LangChain Integration
from langchain.tools import tool
from mcp_client import MCPClient

# Initialize MCP client
client = MCPClient("http://your-domain.com:8000")

# Create LangChain tool wrapper
@tool
def process_pdf_document(file_path: str) -> str:
    """Process a PDF document using VDS PDF Orchestrator."""
    return client.call_tool("process_document", {"file_path": file_path})

# Use in LangChain chain
from langchain.chains import RetrievalQA

# Integrate with your AI workflow
```

---

## 🛠 **Operations and Maintenance**

### **Daily Operations**
```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs --tail=100

# Backup data
docker run --rm -v /opt/vds/pdf-orchestrator:/data alpine tar czf /backup/vds-pdf-data-$(date +%Y%m%d).tar.gz -C /data .

# Clean up old logs
docker-compose -f docker-compose.prod.yml exec vds-pdf-orchestrator find /app/logs -name "*.log" -mtime +30 -delete
```

### **Weekly Maintenance**
```bash
# Update containers
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --force-recreate

# Monitor disk space
df -h /opt/vds/pdf-orchestrator

# Check resource usage
docker stats --no-stream

# Review security logs
docker-compose -f docker-compose.prod.yml logs vds-pdf-orchestrator | grep -i security
```

### **Monthly Maintenance**
```bash
# Clean Docker images and containers
docker system prune -a

# Update base images
docker-compose -f docker-compose.prod.yml build --no-cache

# Security scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image vds-pdf-orchestrator:latest

# Backup configuration
tar czf vds-pdf-config-$(date +%Y%m%d).tar.gz config/
```

### **Troubleshooting**

#### **Service Won't Start**
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs vds-pdf-orchestrator

# Check resource usage
docker stats

# Check port conflicts
netstat -tlnp | grep :8000

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

#### **Performance Issues**
```bash
# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Check Redis performance
docker-compose -f docker-compose.prod.yml exec redis redis-cli info memory

# Analyze logs for errors
docker-compose -f docker-compose.prod.yml logs vds-pdf-orchestrator | grep -i error
```

#### **Security Incidents**
```bash
# Check for suspicious activity
docker-compose -f docker-compose.prod.yml logs vds-pdf-orchestrator | grep -i "security\|attack\|breach"

# Review access logs
docker-compose -f docker-compose.prod.yml logs nginx | grep -i "401\|403\|404"

# Check file integrity
docker-compose -f docker-compose.prod.yml exec vds-pdf-orchestrator find /app -name "*.py" -exec md5sum {} \;
```

---

## 📝 **Checklist**

### **Pre-Deployment Checklist**
- [ ] System requirements met
- [ ] Environment variables configured
- [ ] SSL certificates obtained (if using HTTPS)
- [ ] Firewall rules configured
- [ ] Backup strategy defined
- [ ] Monitoring alerts configured
- [ ] Load testing completed

### **Post-Deployment Checklist**
- [ ] All services running healthy
- [ ] Load balancer working correctly
- [ ] SSL certificate valid
- [ ] Monitoring dashboards accessible
- [ ] Alerts configured and tested
- [ ] Backup procedures verified
- [ ] Security scan completed

### **Operations Checklist**
- [ ] Regular backups configured
- [ ] Log rotation enabled
- [ ] Monitoring alerts active
- [ ] Performance benchmarks established
- [ ] Security updates scheduled
- [ ] Documentation updated
- [ ] Team training completed

---

## 📞 **Support and Resources**

### **Getting Help**
- **Documentation**: Check `docs/` directory for detailed guides
- **Issues**: Report via GitHub Issues or internal ticketing system
- **Security**: Contact security team for security incidents
- **Performance**: Monitor Grafana dashboards for performance issues

### **Community Resources**
- **GitHub Repository**: https://github.com/your-org/vds-pdf-orchestrator
- **Discord Community**: Join for community support
- **Knowledge Base**: Access internal documentation portal
- **Training Materials**: Review training materials and tutorials

---

**Deployment Guide Completed**: November 18, 2025
**Version**: 1.0
**Environment**: Production
**Multi-User Support**: ✅ Enabled
**AI Agent Integration**: ✅ Ready

---

**🚀 Happy Deploying!**