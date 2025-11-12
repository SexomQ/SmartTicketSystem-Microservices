# Smart Ticket System Microservices - Setup Guide

Complete setup guide for running the Smart Ticket System with microservices architecture.

## Prerequisites

### Required Software

1. **Docker Desktop** (20.10+)
   - Download: https://www.docker.com/products/docker-desktop
   - Includes Docker Compose
   - Minimum 4GB RAM allocated to Docker

2. **Git** (optional, for cloning)
   - Download: https://git-scm.com/downloads

3. **Anthropic API Key**
   - Sign up: https://console.anthropic.com/
   - Create API key from dashboard
   - Free tier available for testing

### System Requirements

- **RAM**: 4GB+ available for Docker
- **Disk**: 2GB free space
- **OS**: Windows 10/11, macOS 10.15+, or Linux
- **Network**: Internet connection for Docker images and AI API

## Installation Steps

### Step 1: Navigate to Project Directory

```bash
cd SmartTicketSystem-Microservices
```

### Step 2: Configure Environment Variables

1. Copy the example environment file:

```bash
# On Windows (PowerShell)
Copy-Item .env.example .env

# On macOS/Linux
cp .env.example .env
```

2. Edit the `.env` file with your favorite text editor:

```bash
# Windows
notepad .env

# macOS
open -e .env

# Linux
nano .env
```

3. Update the `ANTHROPIC_API_KEY`:

```env
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
```

**Important**: Keep the other default values unless you have specific requirements.

### Step 3: Build and Start Services

Start all services with a single command:

```bash
docker-compose up -d
```

**What this does**:
- Downloads required Docker images (PostgreSQL, RabbitMQ, Python)
- Builds all 5 microservices
- Creates Docker network
- Initializes databases
- Starts message queue
- Sets up health checks

**Expected Output**:
```
Creating network "smartticketsystem-microservices_smartticket-network" ... done
Creating volume "smartticketsystem-microservices_postgres_data" ... done
Creating volume "smartticketsystem-microservices_rabbitmq_data" ... done
Creating smartticket-postgres ... done
Creating smartticket-rabbitmq ... done
Creating smartticket-ticket-service ... done
Creating smartticket-ai-service ... done
Creating smartticket-routing-service ... done
Creating smartticket-analytics-service ... done
Creating smartticket-api-gateway ... done
```

**Build Time**: First build takes 5-10 minutes depending on internet speed.

### Step 4: Verify Services

Check that all services are running and healthy:

```bash
docker-compose ps
```

**Expected Output**:
```
NAME                              STATUS                   PORTS
smartticket-analytics-service     Up (healthy)             0.0.0.0:5004->5004/tcp
smartticket-ai-service            Up (healthy)             0.0.0.0:5002->5002/tcp
smartticket-api-gateway           Up (healthy)             0.0.0.0:5000->5000/tcp
smartticket-postgres              Up (healthy)             0.0.0.0:5432->5432/tcp
smartticket-rabbitmq              Up (healthy)             0.0.0.0:5672->5672/tcp, 15672/tcp
smartticket-routing-service       Up (healthy)             0.0.0.0:5003->5003/tcp
smartticket-ticket-service        Up (healthy)             0.0.0.0:5001->5001/tcp
```

**Note**: Wait 1-2 minutes for all health checks to pass after initial startup.

### Step 5: Test the System

Test the health check endpoint:

```bash
# Windows (PowerShell)
Invoke-RestMethod -Uri http://localhost:5000/api/health | ConvertTo-Json

# macOS/Linux
curl http://localhost:5000/api/health | json_pp
```

**Expected Response**:
```json
{
  "status": "healthy",
  "services": {
    "api-gateway": "healthy",
    "ticket-service": "healthy",
    "ai-service": "healthy",
    "routing-service": "healthy",
    "analytics-service": "healthy"
  }
}
```

### Step 6: Create Your First Ticket

Create a test ticket:

```bash
# Windows (PowerShell)
$body = @{
    title = "Cannot access email"
    description = "I'm unable to log into my email account"
    user_name = "Test User"
    user_email = "test@example.com"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:5000/api/tickets -Body $body -ContentType "application/json" | ConvertTo-Json

# macOS/Linux
curl -X POST http://localhost:5000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cannot access email",
    "description": "I am unable to log into my email account",
    "user_name": "Test User",
    "user_email": "test@example.com"
  }' | json_pp
```

**Expected Response**:
```json
{
  "id": 1,
  "title": "Cannot access email",
  "description": "I am unable to log into my email account",
  "user_name": "Test User",
  "user_email": "test@example.com",
  "department": "IT Support",
  "confidence_score": 95,
  "status": "pending",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

**Success!** The ticket was automatically categorized to "IT Support" by the AI service.

## Service URLs

Once running, access the following:

| Service | URL | Purpose |
|---------|-----|---------|
| **API Gateway** | http://localhost:5000 | Main API endpoint |
| **RabbitMQ Management** | http://localhost:15672 | Message queue dashboard |
| Ticket Service | http://localhost:5001 | Internal only |
| AI Service | http://localhost:5002 | Internal only |
| Routing Service | http://localhost:5003 | Internal only |
| Analytics Service | http://localhost:5004 | Internal only |

**RabbitMQ Login**:
- Username: `guest`
- Password: `guest`

## Viewing Logs

### All Services

```bash
docker-compose logs -f
```

Press `Ctrl+C` to stop following logs.

### Specific Service

```bash
# View API Gateway logs
docker-compose logs -f api-gateway

# View AI Service logs
docker-compose logs -f ai-service

# View Ticket Service logs
docker-compose logs -f ticket-service
```

### Last 100 Lines

```bash
docker-compose logs --tail=100 ticket-service
```

## Stopping Services

### Stop All Services

```bash
docker-compose down
```

This stops and removes containers but **preserves data** (database, queues).

### Stop and Remove Data

```bash
docker-compose down -v
```

**Warning**: This deletes all tickets, analytics, and queue messages.

## Restarting Services

### Restart All

```bash
docker-compose restart
```

### Restart Specific Service

```bash
docker-compose restart ai-service
```

### Rebuild After Code Changes

```bash
docker-compose up -d --build
```

## Troubleshooting

### Services Not Starting

**Problem**: Containers exit immediately after starting.

**Solution**:
1. Check logs:
   ```bash
   docker-compose logs service-name
   ```

2. Common issues:
   - Missing API key → Check `.env` file
   - Port already in use → Change port in `.env`
   - Insufficient memory → Allocate more RAM to Docker

### API Gateway Returns 503

**Problem**: "Service unavailable" errors.

**Solution**:
1. Check if backend services are healthy:
   ```bash
   docker-compose ps
   ```

2. Wait for health checks to pass (1-2 minutes)

3. Restart services:
   ```bash
   docker-compose restart
   ```

### Database Connection Errors

**Problem**: Services can't connect to PostgreSQL.

**Solution**:
1. Verify PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Check PostgreSQL logs:
   ```bash
   docker-compose logs postgres
   ```

3. Restart database:
   ```bash
   docker-compose restart postgres
   ```

### RabbitMQ Connection Issues

**Problem**: Services can't connect to message queue.

**Solution**:
1. Check RabbitMQ status:
   ```bash
   docker-compose ps rabbitmq
   ```

2. Access management UI: http://localhost:15672

3. Verify queues are created (should see: ticket.created, ticket.categorized, etc.)

4. Restart RabbitMQ:
   ```bash
   docker-compose restart rabbitmq
   ```

### AI Service Not Categorizing

**Problem**: Tickets created but not categorized.

**Solution**:
1. Verify API key is set:
   ```bash
   docker-compose exec ai-service env | grep ANTHROPIC
   ```

2. Check AI service logs:
   ```bash
   docker-compose logs ai-service
   ```

3. Look for Claude API errors (rate limits, invalid key)

4. Fallback categorization should still work without API key (lower confidence)

### Port Already in Use

**Problem**: Cannot start service, port 5000 (or other) already in use.

**Solution**:
1. Find process using port:
   ```bash
   # Windows
   netstat -ano | findstr :5000

   # macOS/Linux
   lsof -i :5000
   ```

2. Stop the conflicting process or change port in `.env`:
   ```env
   API_GATEWAY_PORT=5050
   ```

3. Update docker-compose.yml port mapping if needed

### Complete System Reset

If everything is broken:

```bash
# Stop and remove everything
docker-compose down -v

# Remove all images (optional)
docker-compose down --rmi all

# Rebuild from scratch
docker-compose up -d --build
```

## Advanced Configuration

### Changing Ports

Edit `.env` file:

```env
API_GATEWAY_PORT=8000
TICKET_SERVICE_PORT=8001
AI_SERVICE_PORT=8002
ROUTING_SERVICE_PORT=8003
ANALYTICS_SERVICE_PORT=8004
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

### Changing Database Credentials

Edit `.env` file:

```env
DB_USER=myuser
DB_PASSWORD=mypassword
DB_NAME=mytickets
```

**Important**: Delete volume before restarting:
```bash
docker-compose down -v
docker-compose up -d
```

### Scaling Services

Run multiple instances of a service:

```bash
docker-compose up -d --scale ai-service=3
```

### Using External Database

To use an external PostgreSQL instance:

1. Update `.env`:
   ```env
   DB_HOST=your-postgres-host.com
   DB_PORT=5432
   DB_USER=your_user
   DB_PASSWORD=your_password
   ```

2. Remove postgres service from docker-compose.yml

3. Restart services

## Production Deployment

### Security Checklist

- [ ] Change default PostgreSQL password
- [ ] Change RabbitMQ credentials
- [ ] Use secrets management (not .env files)
- [ ] Enable HTTPS/TLS
- [ ] Implement authentication on API Gateway
- [ ] Set up rate limiting
- [ ] Configure CORS properly
- [ ] Use non-default ports
- [ ] Enable firewall rules
- [ ] Regular security updates

### Monitoring

Set up monitoring for:
- Service health checks
- CPU/Memory usage per service
- Database connection pool
- Message queue depth
- API response times
- Error rates

Recommended tools:
- Prometheus + Grafana
- ELK Stack (Elasticsearch, Logstash, Kibana)
- DataDog, New Relic, or similar APM

### Backup Strategy

1. **Database Backup**:
   ```bash
   docker exec smartticket-postgres pg_dump -U postgres smartticket > backup.sql
   ```

2. **Restore**:
   ```bash
   docker exec -i smartticket-postgres psql -U postgres smartticket < backup.sql
   ```

3. **Automated Backups**: Set up cron job or scheduled task

## Next Steps

1. **Explore the API**: See README.md for all endpoints
2. **View Architecture**: Read ARCHITECTURE.md for design details
3. **Create More Tickets**: Test different departments
4. **View Analytics**: Access dashboard endpoints
5. **Monitor RabbitMQ**: Check message flow at http://localhost:15672
6. **Scale Services**: Try scaling different services

## Getting Help

If you encounter issues:
1. Check this guide's Troubleshooting section
2. Review service logs: `docker-compose logs service-name`
3. Check RabbitMQ management UI
4. Verify PostgreSQL connectivity
5. Ensure API key is valid

---

**You're all set! Start building with the Smart Ticket System Microservices.** 🚀
