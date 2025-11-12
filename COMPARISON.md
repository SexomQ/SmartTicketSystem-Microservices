# Monolith vs Microservices Architecture - Comparison

This document compares the Smart Ticket System implementations in both monolith and microservices architectures.

## Quick Comparison Table

| Aspect | Monolith | Microservices |
|--------|----------|---------------|
| **Deployment** | Single container | 7 containers (5 services + DB + MQ) |
| **Database** | SQLite (single file) | PostgreSQL (shared but logically separated) |
| **Communication** | In-process function calls | HTTP REST + Message Queue (RabbitMQ) |
| **Scaling** | Vertical only (bigger machine) | Horizontal per service |
| **Startup Time** | 10-20 seconds | 1-2 minutes (all services) |
| **Memory Usage** | ~200MB | ~1.5GB (all services combined) |
| **Complexity** | Low | High |
| **Development Speed** | Fast (single codebase) | Slower (multiple services) |
| **Fault Tolerance** | Single point of failure | Isolated failures |
| **Technology Stack** | Uniform (Python + Flask) | Flexible per service |
| **Code Lines** | ~1,200 lines | ~2,500 lines (including infrastructure) |
| **Team Size** | 1-3 developers | 3-10 developers |

## Architecture Diagrams

### Monolith Architecture

```
┌─────────────────────────────────────────┐
│          Flask Application              │
│  ┌─────────────────────────────────┐   │
│  │        API Routes               │   │
│  └──────────┬──────────────────────┘   │
│             │                           │
│  ┌──────────┼──────────┬───────────┐   │
│  │          │          │           │   │
│  ▼          ▼          ▼           ▼   │
│ Database   AI      Routing      Config │
│ Module  Module     Module       Module │
│  │          │          │           │   │
│  └──────────┴──────────┴───────────┘   │
│             │                           │
│             ▼                           │
│      ┌─────────────┐                   │
│      │  SQLite DB  │                   │
│      └─────────────┘                   │
└─────────────────────────────────────────┘
```

### Microservices Architecture

```
                    ┌─────────────┐
                    │   Clients   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ API Gateway │
                    │   (5000)    │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼─────┐      ┌────▼─────┐      ┌────▼─────┐
   │ Ticket   │      │    AI    │      │ Routing  │
   │ Service  │◄────►│ Service  │◄────►│ Service  │
   │  (5001)  │      │  (5002)  │      │  (5003)  │
   └────┬─────┘      └────┬─────┘      └────┬─────┘
        │                 │                  │
        │            ┌────▼─────┐            │
        │            │Analytics │            │
        │            │ Service  │            │
        │            │  (5004)  │            │
        │            └────┬─────┘            │
        │                 │                  │
        └─────────────────┼──────────────────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
       ┌────▼────┐   ┌───▼────┐   ┌───▼────┐
       │PostgreSQL│   │RabbitMQ│   │ Shared │
       │    DB    │   │  Queue │   │ Libs   │
       └──────────┘   └────────┘   └────────┘
```

## Detailed Comparison

### 1. Code Structure

#### Monolith
```
SmartTicketSystem-Monolith/
├── app.py                    # All API routes (586 lines)
├── database.py               # Database operations (242 lines)
├── ai_categorization.py      # AI logic (271 lines)
├── routing.py                # Routing logic (149 lines)
├── config.py                 # Configuration (52 lines)
├── init_db.py                # DB initialization
├── requirements.txt          # Dependencies
├── Dockerfile                # Single Dockerfile
└── docker-compose.yml        # 2 services (app + optional db)
```

#### Microservices
```
SmartTicketSystem-Microservices/
├── api-gateway/              # Gateway service
│   ├── src/app.py
│   ├── requirements.txt
│   └── Dockerfile
├── ticket-service/           # Ticket management
│   ├── src/app.py
│   ├── src/database.py
│   ├── requirements.txt
│   └── Dockerfile
├── ai-categorization-service/  # AI service
│   ├── src/app.py
│   ├── requirements.txt
│   └── Dockerfile
├── routing-service/          # Routing service
│   ├── src/app.py
│   ├── src/database.py
│   ├── requirements.txt
│   └── Dockerfile
├── analytics-service/        # Analytics service
│   ├── src/app.py
│   ├── src/database.py
│   ├── requirements.txt
│   └── Dockerfile
├── shared/                   # Shared utilities
│   ├── config/constants.py
│   ├── models/ticket.py
│   └── utils/
│       ├── logger.py
│       └── message_queue.py
├── postgres-init/            # DB initialization
├── docker-compose.yml        # 7 services
└── .env.example
```

### 2. Deployment

#### Monolith

**Docker Compose**:
```yaml
services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

**Start Command**:
```bash
docker-compose up -d
```

**Startup Time**: 10-20 seconds

#### Microservices

**Docker Compose**:
```yaml
services:
  postgres:        # Database
  rabbitmq:        # Message broker
  ticket-service:  # 5 microservices
  ai-service:
  routing-service:
  analytics-service:
  api-gateway:
```

**Start Command**:
```bash
docker-compose up -d
```

**Startup Time**: 1-2 minutes (waiting for health checks)

### 3. Request Flow

#### Monolith - Create Ticket

```
1. Client → POST /api/tickets
2. app.py receives request
3. database.create_ticket() → SQLite
4. ai_categorization.categorize_ticket() → Claude API
5. routing.route_ticket_to_department() → SQLite
6. Response to client

Total: 1 network hop, 3 function calls
```

#### Microservices - Create Ticket

```
1. Client → API Gateway (HTTP)
2. API Gateway → Ticket Service (HTTP)
3. Ticket Service → PostgreSQL (SQL)
4. Ticket Service → RabbitMQ (publish ticket.created)
5. AI Service ← RabbitMQ (consume ticket.created)
6. AI Service → Claude API
7. AI Service → RabbitMQ (publish ticket.categorized)
8. Routing Service ← RabbitMQ (consume ticket.categorized)
9. Routing Service → Ticket Service (HTTP update)
10. Routing Service → PostgreSQL (SQL)
11. Routing Service → RabbitMQ (publish ticket.routed)
12. Analytics Service ← RabbitMQ (consume all events)
13. Response to client

Total: 6 service hops, 3 databases, 4 events
```

**Trade-off**: More complexity but better scalability and fault isolation.

### 4. Scaling

#### Monolith

**Vertical Scaling Only**:
```bash
# Increase resources
docker update --cpus="2" --memory="2g" smartticket-app

# Cannot scale parts independently
```

**Problem**: If AI categorization is slow, must scale entire app.

#### Microservices

**Horizontal Scaling Per Service**:
```bash
# Scale only AI service (the bottleneck)
docker-compose up -d --scale ai-service=5

# Or scale everything
docker-compose up -d \
  --scale api-gateway=2 \
  --scale ticket-service=2 \
  --scale ai-service=5 \
  --scale routing-service=2 \
  --scale analytics-service=2
```

**Benefit**: Scale only what needs scaling, save resources.

### 5. Fault Tolerance

#### Monolith

**Single Point of Failure**:
```
If AI categorization fails → Entire app may crash
If database locks → Entire app affected
If any module has memory leak → Entire app affected
```

**Recovery**: Restart entire application

#### Microservices

**Isolated Failures**:
```
If AI service fails → Tickets still created (no categorization)
If Analytics service fails → Core functionality unaffected
If Routing service fails → Manual routing still possible
```

**Graceful Degradation**:
- AI service down → Fallback to keyword categorization
- Analytics down → Events queued for later processing
- Individual service restarts without affecting others

### 6. Database

#### Monolith

**SQLite**:
- Single file: `tickets.db`
- No server process
- No network overhead
- Limited concurrency
- No built-in replication

**Schema**:
```sql
tickets (
  id, title, description, user_name, user_email,
  department, confidence_score, status,
  created_at, updated_at
)
```

#### Microservices

**PostgreSQL**:
- Client-server architecture
- Better concurrency
- Replication support
- ACID compliance
- Better scaling

**Schema** (logically separated):
```sql
-- Ticket Service
tickets (...)

-- Routing Service
departments (...)
ticket_routing (...)

-- Analytics Service
analytics_events (...)
```

### 7. Communication

#### Monolith

**In-Process Function Calls**:
```python
# All in same process
ticket_id = database.create_ticket(ticket)
department, score = ai_categorization.categorize_ticket(title, desc)
routing.route_ticket_to_department(ticket_id, department)
```

**Pros**:
- Fast (no network)
- Simple error handling
- Transactions work easily

**Cons**:
- Tight coupling
- Can't scale independently
- Shared memory/resources

#### Microservices

**HTTP REST**:
```python
# Synchronous calls
response = requests.post(f"{TICKET_SERVICE_URL}/tickets", json=data)
```

**Message Queue (RabbitMQ)**:
```python
# Asynchronous events
mq.publish(exchange='tickets', routing_key='ticket.created', message=ticket)
```

**Pros**:
- Loose coupling
- Independent scaling
- Language agnostic

**Cons**:
- Network latency
- More complex error handling
- Eventual consistency

### 8. Development Experience

#### Monolith

**Advantages**:
- Single codebase to understand
- Easy to run locally (just `python app.py`)
- Simple debugging (one process)
- Faster initial development
- Easy to test (one app)

**Disadvantages**:
- Large codebase grows complex
- Merge conflicts in big teams
- Can't use different technologies
- Tight coupling between modules

#### Microservices

**Advantages**:
- Clear service boundaries
- Teams can work independently
- Technology flexibility per service
- Easier to understand individual services

**Disadvantages**:
- Complex local development (7 services)
- Distributed debugging is harder
- More boilerplate code
- Integration testing is complex
- Network issues to deal with

### 9. Testing

#### Monolith

**Unit Tests**:
```python
# Test individual functions
def test_categorize_ticket():
    dept, score = categorize_ticket("Email issue", "Cannot login")
    assert dept == "IT Support"
```

**Integration Tests**:
```python
# Test full flow in one process
def test_create_ticket():
    response = client.post('/api/tickets', json=ticket_data)
    assert response.status_code == 201
    assert 'department' in response.json
```

#### Microservices

**Unit Tests** (per service):
```python
# Test ticket service
def test_ticket_creation():
    response = client.post('/tickets', json=ticket_data)
    assert response.status_code == 201
```

**Integration Tests** (requires all services):
```python
# Test full flow across services
def test_ticket_workflow():
    # Create ticket
    response = gateway.post('/api/tickets', json=data)

    # Wait for async categorization
    time.sleep(2)

    # Verify routing
    ticket = gateway.get(f'/api/tickets/{ticket_id}')
    assert ticket['department'] is not None
```

**Contract Tests** (between services):
```python
# Ensure AI service contract is maintained
def test_ai_service_contract():
    response = ai_service.post('/categorize', json={
        'ticket_id': 1,
        'title': 'Test',
        'description': 'Test'
    })
    assert 'department' in response.json
    assert 'confidence_score' in response.json
```

### 10. Operational Complexity

#### Monolith

**Monitoring**:
- Single application to monitor
- One set of logs
- One health check

**Deployment**:
- One Docker image to build
- One container to deploy
- Simple rollback (previous image)

**Debugging**:
- Single log file
- One process to attach debugger
- Stack traces are complete

#### Microservices

**Monitoring**:
- 5 services to monitor
- 7 containers total
- Distributed tracing needed
- Aggregated logging required

**Deployment**:
- 5 Docker images to build
- Coordinated deployment
- Service version compatibility
- More complex rollback

**Debugging**:
- Logs across multiple services
- Correlation IDs needed
- Distributed tracing tools
- Request flow across services

### 11. Cost Analysis

#### Monolith

**Development Cost**: Low
- 1-3 developers
- Faster initial development
- Less infrastructure knowledge needed

**Infrastructure Cost**: Low
- 1 container (app)
- 1 database file
- Minimal RAM: ~200MB
- Single server sufficient

**Operational Cost**: Low
- Simple monitoring
- Easy deployment
- Less DevOps overhead

**Total**: Best for small teams/projects

#### Microservices

**Development Cost**: High
- 3-10 developers
- More initial setup
- Distributed systems knowledge needed

**Infrastructure Cost**: Medium
- 7 containers
- PostgreSQL server
- RabbitMQ server
- RAM: ~1.5GB minimum
- Multiple servers for HA

**Operational Cost**: High
- Complex monitoring (Prometheus, Grafana)
- Service mesh (Istio, Linkerd)
- Container orchestration (Kubernetes)
- More DevOps engineers

**Total**: Best for large teams/enterprise

## When to Use Each

### Use Monolith When:

✅ **Team Size**: 1-5 developers
✅ **Project Size**: Small to medium
✅ **Domain Complexity**: Simple, well-understood
✅ **Scaling Needs**: Moderate, predictable
✅ **Timeline**: Need to ship fast
✅ **Resources**: Limited budget
✅ **Expertise**: General web development

**Example**: Internal tools, MVPs, startups, small businesses

### Use Microservices When:

✅ **Team Size**: 10+ developers (multiple teams)
✅ **Project Size**: Large, complex
✅ **Domain Complexity**: Multiple bounded contexts
✅ **Scaling Needs**: Different per feature
✅ **Availability**: 99.9%+ uptime required
✅ **Resources**: Good budget, infrastructure
✅ **Expertise**: Distributed systems experience

**Example**: Large enterprise apps, SaaS platforms, high-traffic systems

## Migration Path

If starting with monolith and need to migrate to microservices:

### Phase 1: Preparation
1. Add logging and monitoring
2. Identify bounded contexts
3. Separate concerns in code
4. Add integration tests

### Phase 2: Extract Services (Strangler Pattern)
1. Start with least risky service (e.g., Analytics)
2. Set up message queue
3. Duplicate functionality in new service
4. Route some traffic to new service
5. Monitor and compare results
6. Gradually increase traffic

### Phase 3: Complete Migration
1. Extract remaining services
2. Update clients to use new services
3. Decommission monolith
4. Optimize microservices

## Conclusion

Both architectures have their place:

**Monolith** is perfect for:
- Getting started quickly
- Small teams and projects
- Simple domains
- Limited resources

**Microservices** excel at:
- Large, complex systems
- Independent scaling needs
- Multiple teams
- High availability requirements

**Smart Ticket System**:
- **Start with monolith** for proof of concept
- **Migrate to microservices** when scaling or complexity demands it

The microservices version shows how to properly decompose a monolith while maintaining functionality and adding resilience.
