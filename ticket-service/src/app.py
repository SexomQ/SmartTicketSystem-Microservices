"""
Ticket Management Service
Handles CRUD operations for tickets
"""
import sys
import os

# Add shared module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, request, jsonify
from typing import Dict, Any, Optional
import logging

from shared.config import constants
from shared.utils import setup_logger, MessageQueue
from shared.models import Ticket
from database import TicketDatabase

# Initialize Flask app
app = Flask(__name__)

# Setup logging
logger = setup_logger('ticket-service', constants.LOG_LEVEL)

# Initialize database
db = TicketDatabase()

# Initialize message queue
mq = MessageQueue(
    host=constants.RABBITMQ_HOST,
    port=constants.RABBITMQ_PORT,
    user=constants.RABBITMQ_USER,
    password=constants.RABBITMQ_PASSWORD,
    vhost=constants.RABBITMQ_VHOST
)


def serialize_ticket(ticket_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize ticket data for JSON encoding (convert datetime to ISO format strings)

    Args:
        ticket_data: Ticket data dictionary

    Returns:
        Serialized ticket dictionary
    """
    from datetime import datetime
    serialized = {}
    for key, value in ticket_data.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def publish_ticket_event(event_type: str, ticket_data: Dict[str, Any]) -> None:
    """
    Publish ticket event to message queue

    Args:
        event_type: Type of event (created, updated, etc.)
        ticket_data: Ticket data dictionary
    """
    try:
        routing_key = f"ticket.{event_type}"
        # Serialize datetime objects before publishing
        serialized_ticket = serialize_ticket(ticket_data)
        mq.publish(
            exchange_name=constants.EXCHANGE_TICKETS,
            routing_key=routing_key,
            message={
                'event_type': event_type,
                'ticket': serialized_ticket
            }
        )
        logger.debug(f"Published {event_type} event for ticket {ticket_data.get('id')}")
    except Exception as e:
        logger.error(f"Failed to publish event: {str(e)}")


@app.route('/health', methods=['GET'])
def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ticket-service'
    }), 200


@app.route('/tickets', methods=['POST'])
def create_ticket() -> Dict[str, Any]:
    """
    Create a new ticket

    Request Body:
        {
            "title": str,
            "description": str,
            "user_name": str,
            "user_email": str
        }

    Returns:
        Created ticket object
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['title', 'description', 'user_name', 'user_email']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Create ticket object
        ticket = Ticket(
            title=data['title'],
            description=data['description'],
            user_name=data['user_name'],
            user_email=data['user_email'],
            status='pending'
        )

        # Save to database
        ticket_id = db.create_ticket(ticket)
        ticket.id = ticket_id

        # Get the created ticket
        created_ticket = db.get_ticket_by_id(ticket_id)

        # Publish ticket created event
        publish_ticket_event('created', created_ticket)

        logger.info(f"Created ticket {ticket_id}: {ticket.title}")

        return jsonify(created_ticket), 201

    except Exception as e:
        logger.error(f"Error creating ticket: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/tickets', methods=['GET'])
def get_all_tickets() -> Dict[str, Any]:
    """
    Get all tickets

    Query Parameters:
        status: Filter by status (optional)
        department: Filter by department (optional)

    Returns:
        List of tickets
    """
    try:
        status = request.args.get('status')
        department = request.args.get('department')

        if department:
            tickets = db.get_tickets_by_department(department, status)
        else:
            tickets = db.get_all_tickets(status)

        return jsonify({
            'count': len(tickets),
            'tickets': tickets
        }), 200

    except Exception as e:
        logger.error(f"Error getting tickets: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/tickets/<int:ticket_id>', methods=['GET'])
def get_ticket(ticket_id: int) -> Dict[str, Any]:
    """
    Get a specific ticket by ID

    Args:
        ticket_id: Ticket ID

    Returns:
        Ticket object
    """
    try:
        ticket = db.get_ticket_by_id(ticket_id)

        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404

        return jsonify(ticket), 200

    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/tickets/<int:ticket_id>', methods=['PUT'])
def update_ticket(ticket_id: int) -> Dict[str, Any]:
    """
    Update a ticket

    Args:
        ticket_id: Ticket ID

    Request Body:
        {
            "status": str (optional),
            "department": str (optional)
        }

    Returns:
        Updated ticket object
    """
    try:
        # Check if ticket exists
        ticket = db.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404

        data = request.get_json()
        updated = False

        # Update status
        if 'status' in data:
            if data['status'] not in constants.TICKET_STATUSES:
                return jsonify({'error': f'Invalid status. Must be one of: {constants.TICKET_STATUSES}'}), 400
            db.update_ticket_status(ticket_id, data['status'])
            publish_ticket_event('status_updated', {'id': ticket_id, 'status': data['status']})
            updated = True
            logger.info(f"Updated ticket {ticket_id} status to {data['status']}")

        # Update department
        if 'department' in data:
            if data['department'] not in constants.DEPARTMENTS:
                return jsonify({'error': f'Invalid department. Must be one of: {constants.DEPARTMENTS}'}), 400
            confidence_score = data.get('confidence_score', ticket.get('confidence_score', 0))
            db.update_ticket_department(ticket_id, data['department'], confidence_score)
            publish_ticket_event('department_updated', {
                'id': ticket_id,
                'department': data['department'],
                'confidence_score': confidence_score
            })
            updated = True
            logger.info(f"Updated ticket {ticket_id} department to {data['department']}")

        if not updated:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Get updated ticket
        updated_ticket = db.get_ticket_by_id(ticket_id)

        return jsonify(updated_ticket), 200

    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/tickets/<int:ticket_id>/status', methods=['PUT'])
def update_ticket_status(ticket_id: int) -> Dict[str, Any]:
    """
    Update ticket status

    Args:
        ticket_id: Ticket ID

    Request Body:
        {
            "status": str
        }

    Returns:
        Updated ticket object
    """
    try:
        # Check if ticket exists
        if not db.ticket_exists(ticket_id):
            return jsonify({'error': 'Ticket not found'}), 404

        data = request.get_json()

        # Validate status
        if 'status' not in data:
            return jsonify({'error': 'Missing required field: status'}), 400

        if data['status'] not in constants.TICKET_STATUSES:
            return jsonify({'error': f'Invalid status. Must be one of: {constants.TICKET_STATUSES}'}), 400

        # Update status
        db.update_ticket_status(ticket_id, data['status'])

        # Publish event
        publish_ticket_event('status_updated', {'id': ticket_id, 'status': data['status']})

        # Get updated ticket
        updated_ticket = db.get_ticket_by_id(ticket_id)

        logger.info(f"Updated ticket {ticket_id} status to {data['status']}")

        return jsonify(updated_ticket), 200

    except Exception as e:
        logger.error(f"Error updating ticket status: {str(e)}")
        return jsonify({'error': str(e)}), 500


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

        logger.info(f"Starting Ticket Service on port {constants.TICKET_SERVICE_PORT}")

        # Initialize database
        db.initialize_database()

        # Run Flask app
        app.run(
            host='0.0.0.0',
            port=constants.TICKET_SERVICE_PORT,
            debug=constants.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("Shutting down Ticket Service")
        mq.disconnect()
    except Exception as e:
        logger.error(f"Failed to start Ticket Service: {str(e)}")
        sys.exit(1)
