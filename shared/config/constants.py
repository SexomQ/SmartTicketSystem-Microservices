"""
Shared configuration constants for Smart Ticket System Microservices
"""
import os
from typing import List, Dict

# Department Configuration
DEPARTMENTS: List[str] = [
    "IT Support",
    "HR",
    "Facilities",
    "Finance",
    "General"
]

DEPARTMENT_KEYWORDS: Dict[str, List[str]] = {
    "IT Support": [
        "computer", "laptop", "software", "hardware", "network", "internet",
        "email", "password", "login", "access", "vpn", "printer", "server",
        "database", "application", "system", "wifi", "connection", "error"
    ],
    "HR": [
        "leave", "vacation", "payroll", "salary", "benefits", "insurance",
        "holiday", "sick", "resignation", "termination", "hiring", "onboarding",
        "performance", "review", "complaint", "harassment", "policy"
    ],
    "Facilities": [
        "office", "building", "maintenance", "repair", "cleaning", "hvac",
        "parking", "security", "key", "card", "access", "room", "desk",
        "chair", "equipment", "supplies", "air conditioning", "heating"
    ],
    "Finance": [
        "invoice", "payment", "expense", "reimbursement", "budget", "purchase",
        "vendor", "contract", "billing", "receipt", "credit", "debit", "tax",
        "accounting", "financial", "cost", "refund"
    ],
    "General": [
        "question", "inquiry", "request", "other", "help", "support", "general"
    ]
}

# Ticket Status Configuration
TICKET_STATUSES: List[str] = [
    "pending",
    "in_progress",
    "resolved"
]

# AI Configuration
CLAUDE_MODEL: str = "claude-3-5-haiku-20241022"
CLAUDE_MAX_TOKENS: int = 500
CLAUDE_TEMPERATURE: float = 0.3
CLAUDE_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# AI Retry Configuration
AI_MAX_RETRIES: int = 3
AI_RETRY_DELAY: int = 2  # seconds

# Confidence Score Configuration
MIN_CONFIDENCE_SCORE: int = 0
MAX_CONFIDENCE_SCORE: int = 100
LOW_CONFIDENCE_THRESHOLD: int = 50

# Service Ports
API_GATEWAY_PORT: int = int(os.getenv("API_GATEWAY_PORT", "5000"))
TICKET_SERVICE_PORT: int = int(os.getenv("TICKET_SERVICE_PORT", "5001"))
AI_SERVICE_PORT: int = int(os.getenv("AI_SERVICE_PORT", "5002"))
ROUTING_SERVICE_PORT: int = int(os.getenv("ROUTING_SERVICE_PORT", "5003"))
ANALYTICS_SERVICE_PORT: int = int(os.getenv("ANALYTICS_SERVICE_PORT", "5004"))

# Service URLs
TICKET_SERVICE_URL: str = os.getenv("TICKET_SERVICE_URL", "http://ticket-service:5001")
AI_SERVICE_URL: str = os.getenv("AI_SERVICE_URL", "http://ai-service:5002")
ROUTING_SERVICE_URL: str = os.getenv("ROUTING_SERVICE_URL", "http://routing-service:5003")
ANALYTICS_SERVICE_URL: str = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:5004")

# Database Configuration
DB_HOST: str = os.getenv("DB_HOST", "postgres")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_USER: str = os.getenv("DB_USER", "postgres")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
DB_NAME: str = os.getenv("DB_NAME", "smartticket")

# RabbitMQ Configuration
RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")

# Queue Names
QUEUE_TICKET_CREATED: str = "ticket.created"
QUEUE_TICKET_CATEGORIZED: str = "ticket.categorized"
QUEUE_TICKET_ROUTED: str = "ticket.routed"
QUEUE_TICKET_STATUS_UPDATED: str = "ticket.status.updated"

# Exchange Names
EXCHANGE_TICKETS: str = "tickets"
EXCHANGE_TYPE: str = "topic"

# Flask Configuration
FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# API Configuration
API_VERSION: str = "1.0.0"
SYSTEM_NAME: str = "Smart Ticket System"
ARCHITECTURE: str = "Microservices"

# Timeout Configuration (seconds)
SERVICE_TIMEOUT: int = 30
DATABASE_TIMEOUT: int = 10
RABBITMQ_TIMEOUT: int = 5
