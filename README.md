# Smart Ticket System - Microservices Architecture

AI-powered support ticket management system built with microservices architecture, featuring automatic ticket categorization using Anthropic's Claude API.

## 🏗️ Architecture Overview

This is a **microservices-based** refactoring of the Smart Ticket System monolith, designed for scalability, resilience, and independent deployment.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API Gateway                          │
│                     (Port 5000)                             │
└────────┬──────────────────────────────────────────────┬─────┘
         │                                               │
    ┌────┴─────┬──────────────┬──────────────┬─────────┴────┐
    │          │              │              │              │
┌───▼────┐ ┌──▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌──────▼─────┐
│Ticket  │ │   AI    │ │  Routing  │ │Analytics  │ │  Message   │
│Service │ │ Service │ │  Service  │ │ Service   │ │   Queue    │
│(5001)  │ │ (5002)  │ │  (5003)   │ │  (5004)   │ │(RabbitMQ)  │
└───┬────┘ └────┬────┘ └─────┬─────┘ └─────┬─────┘ └──────┬─────┘
    │           │             │              │              │
    └───────────┴─────────────┴──────────────┴──────────────┘
                              │
                    ┌─────────▼──────────┐
                    │    PostgreSQL      │
                    │    Database        │
                    └────────────────────┘
```

### Microservices

1. **API Gateway** (Port 5000)
   - Central entry point for all client requests
   - Routes requests to appropriate services
   - Handles API documentation and health checks

2. **Ticket Management Service** (Port 5001)
   - CRUD operations for tickets
   - Ticket lifecycle management
   - PostgreSQL for persistent storage

3. **AI Categorization Service** (Port 5002)
   - AI-powered ticket categorization using Claude 3.5 Haiku
   - Confidence scoring
   - Fallback keyword-based categorization

4. **Routing/Department Service** (Port 5003)
   - Department management
   - Ticket routing to departments
   - Routing analytics and history

5. **Analytics/Dashboard Service** (Port 5004)
   - Real-time analytics and dashboards
   - Performance metrics
   - Trend analysis

### Supporting Infrastructure

- **PostgreSQL**: Relational database for all services
- **RabbitMQ**: Message broker for event-driven communication
- **Docker & Docker Compose**: Container orchestration

## 🚀 Features

### Core Features
- ✅ **Automated AI Categorization**: Uses Claude 3.5 Haiku to categorize tickets
- ✅ **Multi-Department Support**: IT Support, HR, Facilities, Finance, General
- ✅ **Ticket Lifecycle Management**: Pending → In Progress → Resolved
- ✅ **Event-Driven Architecture**: Asynchronous communication via RabbitMQ
- ✅ **Real-Time Analytics**: Dashboards and performance metrics
- ✅ **Independent Scaling**: Scale services based on load
- ✅ **Fault Isolation**: Service failures don't cascade
- ✅ **Health Monitoring**: Health checks for all services

### Microservices Benefits
- 🔄 **Independent Deployment**: Update services without system downtime
- 📈 **Horizontal Scaling**: Scale AI service independently for heavy loads
- 🛡️ **Fault Tolerance**: Graceful degradation when services fail
- 🔧 **Technology Flexibility**: Different tech stacks per service
- 👥 **Team Autonomy**: Separate teams can own different services

## 📋 Prerequisites

- Docker Desktop 20.10+
- Docker Compose 2.0+
- Anthropic API Key ([Get one here](https://console.anthropic.com/))
- 4GB+ RAM available for Docker
- Git (optional, for cloning)

## 🛠️ Quick Start

### 1. Clone or Navigate to Project

```bash
cd SmartTicketSystem-Microservices
```

### 2. Set Up Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```env
ANTHROPIC_API_KEY=your_actual_api_key_here
```

### 3. Start All Services

```bash
docker-compose up -d
```

This will:
- Start PostgreSQL database
- Start RabbitMQ message broker
- Build and start all 5 microservices
- Set up networking and volumes

### 4. Verify Services

Check that all services are healthy:

```bash
docker-compose ps
```

You should see all services with status "Up (healthy)".

### 5. Access the API

The API Gateway is available at: `http://localhost:5000`

Get API documentation:

```bash
curl http://localhost:5000/
```

Check system health:

```bash
curl http://localhost:5000/api/health
```

## 📖 API Documentation

### Base URL

All requests go through the API Gateway: `http://localhost:5000`

### Ticket Endpoints

#### Create a Ticket

```bash
POST /api/tickets
Content-Type: application/json

{
  "title": "Cannot access email",
  "description": "I'm unable to log into my email account. Getting password error.",
  "user_name": "John Doe",
  "user_email": "john.doe@company.com"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "Cannot access email",
  "description": "I'm unable to log into my email account. Getting password error.",
  "user_name": "John Doe",
  "user_email": "john.doe@company.com",
  "department": "IT Support",
  "confidence_score": 95,
  "status": "pending",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

#### Get All Tickets

```bash
GET /api/tickets
```

Optional query parameters:
- `status`: Filter by status (pending, in_progress, resolved)
- `department`: Filter by department

#### Get Ticket by ID

```bash
GET /api/tickets/{id}
```

#### Update Ticket Status

```bash
PUT /api/tickets/{id}/status
Content-Type: application/json

{
  "status": "in_progress"
}
```

### Department Endpoints

#### Get All Departments

```bash
GET /api/departments
```

#### Get Department Tickets

```bash
GET /api/departments/{department_name}/tickets
```

Optional query parameter:
- `status`: Filter by status

### Analytics Endpoints

#### Dashboard Summary

```bash
GET /api/dashboard/summary
```

**Response:**
```json
{
  "total_tickets": 150,
  "by_department": {
    "IT Support": 65,
    "HR": 30,
    "Facilities": 25,
    "Finance": 20,
    "General": 10
  },
  "by_status": {
    "pending": 45,
    "in_progress": 60,
    "resolved": 45
  },
  "average_confidence": 87.5,
  "recent_tickets_24h": 12
}
```

#### Routing Analytics

```bash
GET /api/dashboard/routing
```

#### Performance Metrics

```bash
GET /api/analytics/performance
```

#### Trends

```bash
GET /api/analytics/trends?days=30
```

### Routing Endpoints

#### Manual Routing

```bash
POST /api/route
Content-Type: application/json

{
  "ticket_id": 1,
  "department": "IT Support",
  "confidence_score": 100
}
```

#### Reroute Ticket

```bash
PUT /api/route/{ticket_id}
Content-Type: application/json

{
  "department": "HR"
}
```

#### Routing Statistics

```bash
GET /api/routing/statistics
```

#### Routing History

```bash
GET /api/routing/history/{ticket_id}
```

## 🏛️ System Architecture Details

### Event-Driven Flow

1. **Ticket Created**
   - Client → API Gateway → Ticket Service
   - Ticket Service publishes `ticket.created` event
   - AI Service consumes event

2. **AI Categorization**
   - AI Service categorizes ticket
   - Publishes `ticket.categorized` event
   - Routing Service consumes event
   - Analytics Service consumes event

3. **Routing**
   - Routing Service routes ticket to department
   - Updates Ticket Service
   - Publishes `ticket.routed` event
   - Analytics Service consumes event

4. **Status Updates**
   - Client updates ticket status
   - Ticket Service publishes `ticket.status.updated` event
   - Analytics Service consumes event

### Database Schema

Each service has its own tables in the shared PostgreSQL database:

**Ticket Service:**
- `tickets` - Main ticket data

**Routing Service:**
- `departments` - Department information
- `ticket_routing` - Routing history

**Analytics Service:**
- `analytics_events` - Event log for analytics

### Message Queue Topics

- `ticket.created` - New ticket created
- `ticket.categorized` - Ticket categorized by AI
- `ticket.routed` - Ticket routed to department
- `ticket.status.updated` - Ticket status changed

## 🔧 Development

### Running Services Individually

Each service can be run independently for development:

```bash
# Set environment variables
export DB_HOST=localhost
export DB_PORT=5432
export RABBITMQ_HOST=localhost
export ANTHROPIC_API_KEY=your_key

# Run a service
cd ticket-service
pip install -r requirements.txt
python src/app.py
```

### Viewing Logs

View logs for all services:

```bash
docker-compose logs -f
```

View logs for a specific service:

```bash
docker-compose logs -f ticket-service
```

### Accessing RabbitMQ Management

RabbitMQ Management UI: `http://localhost:15672`
- Username: `guest`
- Password: `guest`

### Accessing PostgreSQL

```bash
docker exec -it smartticket-postgres psql -U postgres -d smartticket
```

## 🧪 Testing

### Test Ticket Creation

```bash
curl -X POST http://localhost:5000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Broken office chair",
    "description": "My office chair is broken and needs replacement",
    "user_name": "Jane Smith",
    "user_email": "jane.smith@company.com"
  }'
```

### Test Dashboard

```bash
curl http://localhost:5000/api/dashboard/summary | json_pp
```

### Test Health Check

```bash
curl http://localhost:5000/api/health | json_pp
```

## 🐛 Troubleshooting

### Services Not Starting

1. Check Docker resources:
   ```bash
   docker stats
   ```

2. Check service logs:
   ```bash
   docker-compose logs service-name
   ```

3. Restart services:
   ```bash
   docker-compose restart
   ```

### Database Connection Issues

1. Ensure PostgreSQL is healthy:
   ```bash
   docker-compose ps postgres
   ```

2. Check database logs:
   ```bash
   docker-compose logs postgres
   ```

3. Reinitialize database:
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

### RabbitMQ Connection Issues

1. Check RabbitMQ is running:
   ```bash
   docker-compose ps rabbitmq
   ```

2. Access management UI: `http://localhost:15672`

3. Check message queues are declared

### AI Categorization Not Working

1. Verify API key is set:
   ```bash
   docker-compose exec ai-service env | grep ANTHROPIC
   ```

2. Check AI service logs:
   ```bash
   docker-compose logs ai-service
   ```

3. Test fallback categorization (should work without API key)

## 📊 Monitoring

### Service Health Endpoints

- API Gateway: `http://localhost:5000/api/health`
- Ticket Service: `http://localhost:5001/health`
- AI Service: `http://localhost:5002/health`
- Routing Service: `http://localhost:5003/health`
- Analytics Service: `http://localhost:5004/health`

### RabbitMQ Monitoring

Access RabbitMQ Management UI at `http://localhost:15672` to monitor:
- Queue depths
- Message rates
- Consumer connections
- Memory usage

### PostgreSQL Monitoring

```bash
# Connect to database
docker exec -it smartticket-postgres psql -U postgres -d smartticket

# Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## 🛑 Stopping the System

### Stop All Services

```bash
docker-compose down
```

### Stop and Remove Volumes

```bash
docker-compose down -v
```

This will delete all database data and RabbitMQ state.

## 🔄 Scaling Services

Scale a specific service:

```bash
docker-compose up -d --scale ai-service=3
```

This creates 3 instances of the AI service for load balancing.

## 📈 Performance Optimization

### AI Service Optimization
- Scale horizontally during peak loads
- Implement caching for common categorizations
- Use faster Claude model variants

### Database Optimization
- Add indexes for frequently queried fields
- Use connection pooling
- Implement read replicas for analytics

### Message Queue Optimization
- Increase prefetch count for consumers
- Use multiple queues for different priorities
- Enable message persistence selectively

## 🔐 Security Considerations

### Production Deployment
- [ ] Change default PostgreSQL password
- [ ] Change default RabbitMQ credentials
- [ ] Use secrets management (e.g., Docker secrets, Vault)
- [ ] Enable TLS/SSL for all services
- [ ] Implement API authentication (JWT, OAuth2)
- [ ] Set up rate limiting
- [ ] Enable CORS properly
- [ ] Use non-root users in containers (already configured)

## 📚 Additional Resources

- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 🤝 Architecture Comparison

### Monolith vs Microservices

| Aspect | Monolith | Microservices |
|--------|----------|---------------|
| **Deployment** | Single unit | Independent services |
| **Scaling** | Vertical only | Horizontal per service |
| **Technology** | Single stack | Polyglot architecture |
| **Database** | Single SQLite | Shared PostgreSQL |
| **Fault Tolerance** | Single point of failure | Isolated failures |
| **Development** | Simple | Complex coordination |
| **Testing** | Simpler | More integration tests |
| **Operational Complexity** | Low | High |

## 📝 License

See LICENSE file for details.

## 🙋 Support

For issues and questions:
1. Check the Troubleshooting section
2. Review service logs
3. Check RabbitMQ and PostgreSQL health
4. Verify environment variables

---

**Built with ❤️ using Flask, PostgreSQL, RabbitMQ, Docker, and Anthropic Claude**
