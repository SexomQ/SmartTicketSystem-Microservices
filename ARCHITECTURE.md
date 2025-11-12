# Smart Ticket System - Microservices Architecture Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Service Details](#service-details)
4. [Communication Patterns](#communication-patterns)
5. [Data Management](#data-management)
6. [Deployment Architecture](#deployment-architecture)
7. [Scalability & Performance](#scalability--performance)
8. [Fault Tolerance & Resilience](#fault-tolerance--resilience)
9. [Migration from Monolith](#migration-from-monolith)

## Overview

The Smart Ticket System has been refactored from a monolithic architecture to a microservices-based architecture to achieve better scalability, maintainability, and fault isolation.

### Architecture Goals

1. **Independent Scalability**: Scale services based on individual load patterns
2. **Fault Isolation**: Prevent cascading failures across services
3. **Technology Flexibility**: Use appropriate technology for each service
4. **Independent Deployment**: Deploy services without affecting others
5. **Team Autonomy**: Enable separate teams to own different services

## Architecture Patterns

### 1. API Gateway Pattern

**Implementation**: API Gateway Service (Port 5000)

**Purpose**:
- Single entry point for all client requests
- Request routing to appropriate microservices
- API documentation and versioning
- Future: Authentication, rate limiting, caching

**Benefits**:
- Simplified client interface
- Centralized cross-cutting concerns
- Protocol translation if needed
- Reduced network calls from clients

### 2. Event-Driven Architecture

**Implementation**: RabbitMQ with Topic Exchange

**Event Flow**:
```
Ticket Created → AI Categorization → Routing → Analytics
```

**Events**:
- `ticket.created` - New ticket created
- `ticket.categorized` - AI categorization complete
- `ticket.routed` - Ticket routed to department
- `ticket.status.updated` - Status changed

**Benefits**:
- Loose coupling between services
- Asynchronous processing
- Event sourcing capabilities
- Audit trail of all actions

### 3. Database per Service Pattern (Modified)

**Implementation**: Shared PostgreSQL with logical separation

**Schema Ownership**:
- Ticket Service: `tickets` table
- Routing Service: `departments`, `ticket_routing` tables
- Analytics Service: `analytics_events` table

**Note**: We use a shared database for simplicity, but each service owns its tables. In a full implementation, each service would have its own database instance.

**Benefits**:
- Data encapsulation
- Independent schema evolution
- Service autonomy

### 4. Circuit Breaker Pattern (Planned)

**Future Implementation**: For inter-service communication

**Purpose**:
- Prevent cascading failures
- Graceful degradation
- Fast failure detection

## Service Details

### 1. API Gateway Service

**Technology**: Flask

**Responsibilities**:
- Route requests to microservices
- Aggregate responses if needed
- Provide API documentation
- Health check aggregation

**Endpoints**: See README.md for full list

**Scaling Strategy**: Horizontal (multiple instances behind load balancer)

**Dependencies**:
- All backend services
- No database dependency

### 2. Ticket Management Service

**Technology**: Flask + PostgreSQL

**Responsibilities**:
- CRUD operations for tickets
- Ticket lifecycle management
- Publish ticket events to message queue
- Data validation

**Database Tables**:
```sql
tickets (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    user_name TEXT NOT NULL,
    user_email TEXT NOT NULL,
    department TEXT,
    confidence_score INTEGER,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Events Published**:
- `ticket.created`
- `ticket.status.updated`
- `ticket.department.updated`

**Scaling Strategy**: Horizontal with database connection pooling

**Dependencies**:
- PostgreSQL
- RabbitMQ

### 3. AI Categorization Service

**Technology**: Flask + Anthropic Claude API

**Responsibilities**:
- Categorize tickets using Claude 3.5 Haiku
- Calculate confidence scores
- Fallback to keyword matching if AI unavailable
- Retry logic for API failures

**Algorithm**:
1. Receive ticket data from event queue
2. Build categorization prompt
3. Call Claude API with retry logic (3 attempts)
4. Parse response for department and confidence
5. Fallback to keyword matching if all attempts fail
6. Publish categorization result

**Events Consumed**:
- `ticket.created`

**Events Published**:
- `ticket.categorized`

**Scaling Strategy**: Horizontal (AI calls are stateless)

**Dependencies**:
- Anthropic API
- RabbitMQ

### 4. Routing/Department Service

**Technology**: Flask + PostgreSQL

**Responsibilities**:
- Manage department data
- Route tickets to departments
- Track routing history
- Manual rerouting
- Routing analytics

**Database Tables**:
```sql
departments (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

ticket_routing (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    department TEXT NOT NULL,
    confidence_score INTEGER NOT NULL,
    routed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Events Consumed**:
- `ticket.categorized`

**Events Published**:
- `ticket.routed`

**Scaling Strategy**: Horizontal

**Dependencies**:
- PostgreSQL
- RabbitMQ
- Ticket Service (for updates)

### 5. Analytics/Dashboard Service

**Technology**: Flask + PostgreSQL

**Responsibilities**:
- Real-time analytics and dashboards
- Performance metrics
- Trend analysis
- Department analytics
- Event logging for audit trail

**Database Tables**:
```sql
analytics_events (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    ticket_id INTEGER,
    department TEXT,
    status TEXT,
    confidence_score INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Events Consumed**:
- `ticket.created`
- `ticket.categorized`
- `ticket.routed`
- `ticket.status.updated`

**Scaling Strategy**:
- Horizontal for API endpoints
- Read replicas for heavy analytics queries
- Consider caching layer (Redis) for real-time dashboards

**Dependencies**:
- PostgreSQL
- RabbitMQ

## Communication Patterns

### Synchronous Communication (HTTP/REST)

Used for:
- Client → API Gateway
- API Gateway → Services (for read operations)
- Service-to-Service (when immediate response needed)

**Example**: Get ticket by ID
```
Client → API Gateway → Ticket Service → Response
```

### Asynchronous Communication (Message Queue)

Used for:
- Event-driven workflows
- Service notifications
- Decoupled operations

**Example**: Create ticket workflow
```
Client → API Gateway → Ticket Service
                            ↓
                    Publish ticket.created
                            ↓
                    ┌──────────────────┐
                    ↓                  ↓
              AI Service         Analytics Service
                    ↓
        Publish ticket.categorized
                    ↓
            Routing Service
                    ↓
        Publish ticket.routed
                    ↓
          Analytics Service
```

### Message Queue Configuration

**Exchange**: `tickets` (Topic Exchange)

**Queues**:
- `ticket.created` - Consumed by AI Service, Analytics Service
- `ticket.categorized` - Consumed by Routing Service, Analytics Service
- `ticket.routed` - Consumed by Analytics Service
- `ticket.status.updated` - Consumed by Analytics Service

**Message Format**:
```json
{
  "event_type": "created",
  "ticket": {
    "id": 1,
    "title": "...",
    "description": "...",
    ...
  }
}
```

## Data Management

### Data Consistency

**Strategy**: Eventual Consistency

**Rationale**:
- Real-time analytics don't need immediate consistency
- Allows for higher availability and partition tolerance (CAP theorem)
- Acceptable trade-off for ticket management system

**Implementation**:
- Events ensure all services eventually receive updates
- Message queue guarantees delivery
- Services can rebuild state from event log if needed

### Data Flow

1. **Ticket Creation**:
   - Ticket Service writes to database
   - Publishes event to queue
   - Other services consume asynchronously

2. **AI Categorization**:
   - AI Service receives event
   - Categorizes ticket
   - Publishes result
   - Routing Service and Analytics consume

3. **Routing**:
   - Routing Service receives categorization
   - Writes routing record
   - Updates Ticket Service via HTTP
   - Publishes routing event

### Transaction Management

**Local Transactions**: Each service manages its own transactions

**Saga Pattern** (Future): For distributed transactions across services

## Deployment Architecture

### Container Orchestration

**Current**: Docker Compose

**Production**: Kubernetes (recommended)

### Service Discovery

**Current**: Docker networking with service names

**Production**:
- Kubernetes Services
- Service Mesh (Istio, Linkerd)

### Load Balancing

**API Gateway**:
- External load balancer (Nginx, HAProxy)
- Multiple gateway instances

**Internal Services**:
- Docker Compose: Round-robin
- Kubernetes: Service load balancing

### Networking

**Docker Network**: `smartticket-network` (Bridge)

**Port Mapping**:
- 5000: API Gateway (external)
- 5001-5004: Services (internal only)
- 5432: PostgreSQL (internal only)
- 5672: RabbitMQ AMQP (internal only)
- 15672: RabbitMQ Management (external for monitoring)

## Scalability & Performance

### Horizontal Scaling

Each service can be scaled independently:

```bash
# Scale AI service to 3 instances
docker-compose up -d --scale ai-service=3

# Scale all services
docker-compose up -d \
  --scale api-gateway=2 \
  --scale ticket-service=2 \
  --scale ai-service=3 \
  --scale routing-service=2 \
  --scale analytics-service=2
```

### Scaling Strategies by Service

| Service | Scaling Trigger | Strategy |
|---------|----------------|----------|
| API Gateway | High request rate | Horizontal, multiple instances |
| Ticket Service | Database load | Horizontal + connection pooling |
| AI Service | AI API calls | Horizontal (most important) |
| Routing Service | Routing operations | Horizontal |
| Analytics Service | Dashboard queries | Horizontal + read replicas |

### Performance Optimizations

**AI Service**:
- Cache common categorizations (Redis)
- Batch API calls if possible
- Use faster Claude models for simple queries

**Ticket Service**:
- Database indexing on frequently queried fields
- Connection pooling
- Prepared statements

**Analytics Service**:
- Materialized views for complex aggregations
- Caching layer (Redis) for dashboards
- Separate read replicas

**Message Queue**:
- Persistent messages only when necessary
- Message TTL to prevent queue buildup
- Dead letter queues for failed messages

## Fault Tolerance & Resilience

### Service Health Checks

All services implement health check endpoints:

```python
@app.route('/health', methods=['GET'])
def health_check():
    return {'status': 'healthy', 'service': 'service-name'}, 200
```

**Docker Compose** uses these for container health:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:5001/health')"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Graceful Degradation

**AI Service Unavailable**:
- Fallback to keyword-based categorization
- System continues to function with reduced accuracy

**Analytics Service Down**:
- Core ticket functionality unaffected
- Events queued for later processing

**Routing Service Down**:
- Tickets created but not routed
- Manual routing still possible when service recovers

### Retry Logic

**AI Service**:
```python
for attempt in range(AI_MAX_RETRIES):
    try:
        result = call_ai_service()
        return result
    except Exception as e:
        if attempt < AI_MAX_RETRIES - 1:
            time.sleep(AI_RETRY_DELAY)
```

**Message Queue**:
- Automatic redelivery on failure
- Dead letter queue after max retries
- Message acknowledgment for reliability

### Circuit Breaker (Planned)

Prevent cascading failures:
```python
# Pseudo-code
if circuit_breaker.is_open('ticket-service'):
    return cached_response or error_response
else:
    try:
        response = call_service()
        circuit_breaker.record_success()
        return response
    except Exception:
        circuit_breaker.record_failure()
        raise
```

## Migration from Monolith

### Refactoring Strategy

We used the **Strangler Fig Pattern**:

1. **Extract Services**: Identify bounded contexts
2. **Implement Microservices**: Build services independently
3. **Gradual Migration**: Route traffic to new services
4. **Decommission Monolith**: Once all functionality migrated

### Key Differences

| Aspect | Monolith | Microservices |
|--------|----------|---------------|
| **Architecture** | Single application | 5 independent services |
| **Database** | SQLite (single file) | PostgreSQL (shared) |
| **Communication** | Function calls | HTTP + Message Queue |
| **Deployment** | Single Docker container | 7 containers (5 services + DB + MQ) |
| **Scaling** | Vertical only | Horizontal per service |
| **Fault Tolerance** | Single point of failure | Isolated failures |

### Code Migration

**Monolith Structure**:
```
app.py                 # All routes and logic
database.py            # Database operations
ai_categorization.py   # AI logic
routing.py             # Routing logic
config.py              # Configuration
```

**Microservices Structure**:
```
api-gateway/           # Route handling
ticket-service/        # Ticket CRUD
ai-categorization-service/  # AI logic
routing-service/       # Routing logic
analytics-service/     # Analytics (new)
shared/                # Common utilities
```

### Benefits Achieved

1. **Independent Scaling**: AI service can scale separately
2. **Fault Isolation**: Analytics down doesn't affect tickets
3. **Technology Flexibility**: Can use different databases, languages
4. **Team Ownership**: Separate teams per service
5. **Faster Deployment**: Deploy one service without redeploying all
6. **Better Testing**: Test services independently

### Trade-offs

**Complexity**:
- More moving parts
- Distributed system challenges
- Network latency between services

**Operational Overhead**:
- More containers to monitor
- Service discovery and coordination
- Distributed logging and tracing

**Development**:
- Inter-service API contracts
- Testing integration scenarios
- Local development setup complexity

### When to Use Microservices

✅ **Use Microservices When**:
- Application is large and complex
- Different scaling requirements per feature
- Multiple teams working on codebase
- Need independent deployment cycles
- Fault isolation is critical

❌ **Stick with Monolith When**:
- Small application with simple domain
- Single development team
- Uniform scaling requirements
- Simplicity is more important than flexibility

## Conclusion

The Smart Ticket System microservices architecture provides a scalable, resilient, and maintainable solution for ticket management. While more complex than the monolith, it offers significant benefits for production deployments, especially when scaling and fault tolerance are priorities.

The architecture demonstrates key microservices patterns and can serve as a reference for similar applications requiring distributed, event-driven systems.
