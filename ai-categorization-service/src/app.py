"""
AI Categorization Service
Uses Anthropic's Claude API to categorize tickets into departments
"""
import sys
import os

# Add shared module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, request, jsonify
from typing import Dict, Any
import logging
import time
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError

from shared.config import constants
from shared.utils import setup_logger, MessageQueue
from shared.models import CategorizationResult

# Initialize Flask app
app = Flask(__name__)

# Setup logging
logger = setup_logger('ai-categorization-service', constants.LOG_LEVEL)

# Initialize Anthropic client
anthropic_client = None
if constants.CLAUDE_API_KEY:
    anthropic_client = Anthropic(
        api_key=constants.CLAUDE_API_KEY,
        timeout=30.0
    )
else:
    logger.warning("CLAUDE_API_KEY not set - AI categorization will use fallback only")

# Initialize message queue
mq = MessageQueue(
    host=constants.RABBITMQ_HOST,
    port=constants.RABBITMQ_PORT,
    user=constants.RABBITMQ_USER,
    password=constants.RABBITMQ_PASSWORD,
    vhost=constants.RABBITMQ_VHOST
)


def build_categorization_prompt(title: str, description: str) -> str:
    """
    Build the prompt for AI categorization

    Args:
        title: Ticket title
        description: Ticket description

    Returns:
        Formatted prompt for the AI
    """
    prompt = f"""Categorize this support ticket into exactly one of these departments: IT Support, HR, Facilities, Finance, or General.

Ticket Title: {title}
Ticket Description: {description}

Respond in this exact format:
Department: [department name]
Confidence: [number from 0-100]

Rules:
- IT Support: Technical issues, software, hardware, network, passwords, computers, internet, email, applications
- HR: Employee relations, benefits, payroll, hiring, leave, training, performance reviews, workplace issues
- Facilities: Building maintenance, office space, equipment, cleaning, parking, security, temperature
- Finance: Budgets, expenses, invoicing, purchasing, reimbursements, accounting, financial reports
- General: Everything else that doesn't fit above categories"""

    return prompt


def call_ai_service(prompt: str) -> str:
    """
    Make a call to the Claude API

    Args:
        prompt: The prompt to send to the AI

    Returns:
        AI response text

    Raises:
        Exception: If the AI service call fails
    """
    if not anthropic_client:
        raise ValueError("Anthropic client not initialized")

    try:
        response = anthropic_client.messages.create(
            model=constants.CLAUDE_MODEL,
            max_tokens=constants.CLAUDE_MAX_TOKENS,
            temperature=constants.CLAUDE_TEMPERATURE,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = response.content[0].text.strip()
        logger.debug(f"AI Response: {response_text}")

        return response_text

    except (RateLimitError, APIConnectionError, APIError) as e:
        logger.error(f"API error: {str(e)}")
        raise


def parse_ai_response(response_text: str) -> tuple:
    """
    Parse the AI response to extract department and confidence

    Args:
        response_text: Raw text response from AI

    Returns:
        tuple: (department, confidence) or (None, None) if parsing fails
    """
    department = None
    confidence = None

    for line in response_text.split('\n'):
        line = line.strip()

        if line.startswith('Department:'):
            dept = line.replace('Department:', '').strip()
            # Match department case-insensitively
            for valid_dept in constants.DEPARTMENTS:
                if valid_dept.lower() == dept.lower():
                    department = valid_dept
                    break

        elif line.startswith('Confidence:'):
            try:
                confidence = int(line.replace('Confidence:', '').strip())
                # Clamp confidence to valid range
                confidence = max(0, min(100, confidence))
            except ValueError:
                logger.warning(f"Could not parse confidence value: {line}")
                confidence = None

    return department, confidence


def fallback_categorization(title: str, description: str) -> tuple:
    """
    Fallback categorization using simple keyword matching

    Args:
        title: Ticket title
        description: Ticket description

    Returns:
        tuple: (department_name, confidence_score)
    """
    text = (title + " " + description).lower()

    # Count keyword matches for each department
    scores = {}
    for department, keywords in constants.DEPARTMENT_KEYWORDS.items():
        scores[department] = sum(1 for keyword in keywords if keyword in text)

    # Find department with most matches
    department = max(scores, key=scores.get)

    # If no keywords matched, use General
    if scores[department] == 0:
        department = 'General'
        confidence = 30  # Low confidence for fallback
    else:
        # Calculate confidence based on match count
        confidence = min(50 + (scores[department] * 10), 75)

    logger.info(f"Fallback categorization: {department} (confidence: {confidence}%)")
    return department, confidence


def categorize_ticket(title: str, description: str) -> tuple:
    """
    Categorize a ticket into a department using AI

    Args:
        title: Ticket title
        description: Ticket description

    Returns:
        tuple: (department_name, confidence_score)
    """
    # Build the prompt
    prompt = build_categorization_prompt(title, description)

    # Try to get AI categorization with retries
    for attempt in range(constants.AI_MAX_RETRIES):
        try:
            logger.info(f"AI categorization attempt {attempt + 1}/{constants.AI_MAX_RETRIES}")

            # Call AI service
            response_text = call_ai_service(prompt)

            # Parse the response
            department, confidence = parse_ai_response(response_text)

            # Validate and return if successful
            if department and department in constants.DEPARTMENTS:
                if confidence is None:
                    confidence = 70  # Default confidence
                logger.info(f"Categorized as: {department} (confidence: {confidence}%)")
                return department, confidence
            else:
                logger.warning(f"Invalid department in response: {department}")

        except Exception as e:
            logger.error(f"AI categorization error (attempt {attempt + 1}): {str(e)}")

            # Wait before retrying (except on last attempt)
            if attempt < constants.AI_MAX_RETRIES - 1:
                time.sleep(constants.AI_RETRY_DELAY)

    # All attempts failed - use fallback strategy
    logger.warning("All AI categorization attempts failed, using fallback")
    return fallback_categorization(title, description)


@app.route('/health', methods=['GET'])
def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ai-categorization-service',
        'ai_available': anthropic_client is not None
    }), 200


@app.route('/categorize', methods=['POST'])
def categorize() -> Dict[str, Any]:
    """
    Categorize a ticket

    Request Body:
        {
            "ticket_id": int,
            "title": str,
            "description": str
        }

    Returns:
        {
            "ticket_id": int,
            "department": str,
            "confidence_score": int
        }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['ticket_id', 'title', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        ticket_id = data['ticket_id']
        title = data['title']
        description = data['description']

        # Categorize the ticket
        department, confidence_score = categorize_ticket(title, description)

        result = {
            'ticket_id': ticket_id,
            'department': department,
            'confidence_score': confidence_score
        }

        # Publish categorization result
        mq.publish(
            exchange_name=constants.EXCHANGE_TICKETS,
            routing_key=constants.QUEUE_TICKET_CATEGORIZED,
            message=result
        )

        logger.info(f"Categorized ticket {ticket_id} as {department}")

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error categorizing ticket: {str(e)}")
        return jsonify({'error': str(e)}), 500


def handle_ticket_created(message: Dict[str, Any]) -> None:
    """
    Handle ticket created event from message queue

    Args:
        message: Message containing ticket data
    """
    try:
        ticket = message.get('ticket', {})
        ticket_id = ticket.get('id')
        title = ticket.get('title')
        description = ticket.get('description')

        if not all([ticket_id, title, description]):
            logger.error("Invalid ticket data in message")
            return

        logger.info(f"Processing ticket created event for ticket {ticket_id}")

        # Categorize the ticket
        department, confidence_score = categorize_ticket(title, description)

        result = {
            'ticket_id': ticket_id,
            'department': department,
            'confidence_score': confidence_score
        }

        # Publish categorization result
        mq.publish(
            exchange_name=constants.EXCHANGE_TICKETS,
            routing_key=constants.QUEUE_TICKET_CATEGORIZED,
            message=result
        )

        logger.info(f"Published categorization for ticket {ticket_id}")

    except Exception as e:
        logger.error(f"Error handling ticket created event: {str(e)}")


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({'error': 'Method not allowed'}), 405


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    try:
        # Connect to message queue
        mq.connect()
        mq.declare_exchange(constants.EXCHANGE_TICKETS, constants.EXCHANGE_TYPE)
        mq.declare_queue(constants.QUEUE_TICKET_CREATED)
        mq.bind_queue(
            constants.QUEUE_TICKET_CREATED,
            constants.EXCHANGE_TICKETS,
            constants.QUEUE_TICKET_CREATED
        )

        logger.info(f"Starting AI Categorization Service on port {constants.AI_SERVICE_PORT}")

        # Run Flask app
        app.run(
            host='0.0.0.0',
            port=constants.AI_SERVICE_PORT,
            debug=constants.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("Shutting down AI Categorization Service")
        mq.disconnect()
    except Exception as e:
        logger.error(f"Failed to start AI Categorization Service: {str(e)}")
        sys.exit(1)
