"""
Routing/Department Service
Handles department management and ticket routing
"""
import sys
import os

# Add shared module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, request, jsonify
from typing import Dict, Any, List
import logging
import requests

from shared.config import constants
from shared.utils import setup_logger, MessageQueue
from database import RoutingDatabase

# Initialize Flask app
app = Flask(__name__)

# Setup logging
logger = setup_logger('routing-service', constants.LOG_LEVEL)

# Initialize database
db = RoutingDatabase()

# Initialize message queue
mq = MessageQueue(
    host=constants.RABBITMQ_HOST,
    port=constants.RABBITMQ_PORT,
    user=constants.RABBITMQ_USER,
    password=constants.RABBITMQ_PASSWORD,
    vhost=constants.RABBITMQ_VHOST
)


def update_ticket_department(ticket_id: int, department: str, confidence_score: int) -> bool:
    """
    Update ticket department in ticket service

    Args:
        ticket_id: Ticket ID
        department: Department name
        confidence_score: Confidence score

    Returns:
        True if successful
    """
    try:
        response = requests.put(
            f"{constants.TICKET_SERVICE_URL}/tickets/{ticket_id}",
            json={
                'department': department,
                'confidence_score': confidence_score
            },
            timeout=constants.SERVICE_TIMEOUT
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error updating ticket department: {str(e)}")
        return False


@app.route('/health', methods=['GET'])
def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'routing-service'
    }), 200


@app.route('/departments', methods=['GET'])
def get_departments() -> Dict[str, Any]:
    """
    Get all departments

    Returns:
        List of departments
    """
    try:
        departments = db.get_all_departments()
        return jsonify({
            'count': len(departments),
            'departments': departments
        }), 200
    except Exception as e:
        logger.error(f"Error getting departments: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/departments/<department_name>', methods=['GET'])
def get_department(department_name: str) -> Dict[str, Any]:
    """
    Get department details

    Args:
        department_name: Department name

    Returns:
        Department details
    """
    try:
        department = db.get_department_by_name(department_name)
        if not department:
            return jsonify({'error': 'Department not found'}), 404
        return jsonify(department), 200
    except Exception as e:
        logger.error(f"Error getting department: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/route', methods=['POST'])
def route_ticket() -> Dict[str, Any]:
    """
    Route a ticket to a department

    Request Body:
        {
            "ticket_id": int,
            "department": str,
            "confidence_score": int
        }

    Returns:
        Routing result
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['ticket_id', 'department', 'confidence_score']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        ticket_id = data['ticket_id']
        department = data['department']
        confidence_score = data['confidence_score']

        # Validate department
        if department not in constants.DEPARTMENTS:
            return jsonify({'error': f'Invalid department. Must be one of: {constants.DEPARTMENTS}'}), 400

        # Validate confidence score
        if not (constants.MIN_CONFIDENCE_SCORE <= confidence_score <= constants.MAX_CONFIDENCE_SCORE):
            return jsonify({'error': f'Confidence score must be between {constants.MIN_CONFIDENCE_SCORE} and {constants.MAX_CONFIDENCE_SCORE}'}), 400

        # Save routing to database
        routing_id = db.create_routing(ticket_id, department, confidence_score)

        # Update ticket in ticket service
        success = update_ticket_department(ticket_id, department, confidence_score)

        if not success:
            logger.warning(f"Failed to update ticket {ticket_id} in ticket service")

        # Publish routing event
        mq.publish(
            exchange_name=constants.EXCHANGE_TICKETS,
            routing_key=constants.QUEUE_TICKET_ROUTED,
            message={
                'ticket_id': ticket_id,
                'department': department,
                'confidence_score': confidence_score
            }
        )

        logger.info(f"Routed ticket {ticket_id} to {department}")

        return jsonify({
            'routing_id': routing_id,
            'ticket_id': ticket_id,
            'department': department,
            'confidence_score': confidence_score
        }), 200

    except Exception as e:
        logger.error(f"Error routing ticket: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/route/<int:ticket_id>', methods=['PUT'])
def reroute_ticket(ticket_id: int) -> Dict[str, Any]:
    """
    Reroute a ticket to a different department

    Args:
        ticket_id: Ticket ID

    Request Body:
        {
            "department": str,
            "confidence_score": int (optional, defaults to 100 for manual routing)
        }

    Returns:
        Routing result
    """
    try:
        data = request.get_json()

        # Validate required fields
        if 'department' not in data:
            return jsonify({'error': 'Missing required field: department'}), 400

        department = data['department']
        confidence_score = data.get('confidence_score', 100)  # Manual routing gets 100% confidence

        # Validate department
        if department not in constants.DEPARTMENTS:
            return jsonify({'error': f'Invalid department. Must be one of: {constants.DEPARTMENTS}'}), 400

        # Save routing to database
        routing_id = db.create_routing(ticket_id, department, confidence_score)

        # Update ticket in ticket service
        success = update_ticket_department(ticket_id, department, confidence_score)

        if not success:
            logger.warning(f"Failed to update ticket {ticket_id} in ticket service")

        # Publish routing event
        mq.publish(
            exchange_name=constants.EXCHANGE_TICKETS,
            routing_key=constants.QUEUE_TICKET_ROUTED,
            message={
                'ticket_id': ticket_id,
                'department': department,
                'confidence_score': confidence_score,
                'rerouted': True
            }
        )

        logger.info(f"Rerouted ticket {ticket_id} to {department}")

        return jsonify({
            'routing_id': routing_id,
            'ticket_id': ticket_id,
            'department': department,
            'confidence_score': confidence_score,
            'rerouted': True
        }), 200

    except Exception as e:
        logger.error(f"Error rerouting ticket: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/routing/statistics', methods=['GET'])
def get_routing_statistics() -> Dict[str, Any]:
    """
    Get routing statistics

    Returns:
        Routing statistics including department distribution
    """
    try:
        stats = db.get_routing_statistics()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting routing statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/routing/history/<int:ticket_id>', methods=['GET'])
def get_routing_history(ticket_id: int) -> Dict[str, Any]:
    """
    Get routing history for a ticket

    Args:
        ticket_id: Ticket ID

    Returns:
        List of routing records for the ticket
    """
    try:
        history = db.get_routing_history(ticket_id)
        return jsonify({
            'ticket_id': ticket_id,
            'count': len(history),
            'history': history
        }), 200
    except Exception as e:
        logger.error(f"Error getting routing history: {str(e)}")
        return jsonify({'error': str(e)}), 500


def handle_ticket_categorized(message: Dict[str, Any]) -> None:
    """
    Handle ticket categorized event from message queue

    Args:
        message: Message containing categorization data
    """
    try:
        ticket_id = message.get('ticket_id')
        department = message.get('department')
        confidence_score = message.get('confidence_score')

        if not all([ticket_id, department, confidence_score is not None]):
            logger.error("Invalid categorization data in message")
            return

        logger.info(f"Processing ticket categorized event for ticket {ticket_id}")

        # Route the ticket
        routing_id = db.create_routing(ticket_id, department, confidence_score)

        # Update ticket in ticket service
        success = update_ticket_department(ticket_id, department, confidence_score)

        if not success:
            logger.warning(f"Failed to update ticket {ticket_id} in ticket service")

        # Publish routing event
        mq.publish(
            exchange_name=constants.EXCHANGE_TICKETS,
            routing_key=constants.QUEUE_TICKET_ROUTED,
            message={
                'ticket_id': ticket_id,
                'department': department,
                'confidence_score': confidence_score
            }
        )

        logger.info(f"Routed ticket {ticket_id} to {department}")

    except Exception as e:
        logger.error(f"Error handling ticket categorized event: {str(e)}")


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
        mq.declare_queue(constants.QUEUE_TICKET_CATEGORIZED)
        mq.bind_queue(
            constants.QUEUE_TICKET_CATEGORIZED,
            constants.EXCHANGE_TICKETS,
            constants.QUEUE_TICKET_CATEGORIZED
        )

        logger.info(f"Starting Routing Service on port {constants.ROUTING_SERVICE_PORT}")

        # Initialize database
        db.initialize_database()

        # Run Flask app
        app.run(
            host='0.0.0.0',
            port=constants.ROUTING_SERVICE_PORT,
            debug=constants.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("Shutting down Routing Service")
        mq.disconnect()
    except Exception as e:
        logger.error(f"Failed to start Routing Service: {str(e)}")
        sys.exit(1)
