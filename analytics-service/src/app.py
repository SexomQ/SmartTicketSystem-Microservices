"""
Analytics/Dashboard Service
Provides real-time analytics and dashboard data
"""
import sys
import os

# Add shared module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, request, jsonify
from typing import Dict, Any
import logging
import requests

from shared.config import constants
from shared.utils import setup_logger, MessageQueue
from database import AnalyticsDatabase

# Initialize Flask app
app = Flask(__name__)

# Setup logging
logger = setup_logger('analytics-service', constants.LOG_LEVEL)

# Initialize database
db = AnalyticsDatabase()

# Initialize message queue
mq = MessageQueue(
    host=constants.RABBITMQ_HOST,
    port=constants.RABBITMQ_PORT,
    user=constants.RABBITMQ_USER,
    password=constants.RABBITMQ_PASSWORD,
    vhost=constants.RABBITMQ_VHOST
)


@app.route('/health', methods=['GET'])
def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'analytics-service'
    }), 200


@app.route('/dashboard/summary', methods=['GET'])
def get_dashboard_summary() -> Dict[str, Any]:
    """
    Get overall dashboard summary

    Returns:
        Dashboard summary with statistics
    """
    try:
        summary = db.get_dashboard_summary()
        return jsonify(summary), 200
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/dashboard/routing', methods=['GET'])
def get_routing_analytics() -> Dict[str, Any]:
    """
    Get routing analytics

    Returns:
        Routing analytics data
    """
    try:
        analytics = db.get_routing_analytics()
        return jsonify(analytics), 200
    except Exception as e:
        logger.error(f"Error getting routing analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/analytics/tickets', methods=['GET'])
def get_ticket_analytics() -> Dict[str, Any]:
    """
    Get ticket analytics

    Query Parameters:
        period: Time period (day, week, month, all) - default: all
        department: Filter by department (optional)

    Returns:
        Ticket analytics data
    """
    try:
        period = request.args.get('period', 'all')
        department = request.args.get('department')

        analytics = db.get_ticket_analytics(period, department)
        return jsonify(analytics), 200
    except Exception as e:
        logger.error(f"Error getting ticket analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/analytics/performance', methods=['GET'])
def get_performance_metrics() -> Dict[str, Any]:
    """
    Get performance metrics

    Returns:
        Performance metrics including response times and resolution rates
    """
    try:
        metrics = db.get_performance_metrics()
        return jsonify(metrics), 200
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/analytics/trends', methods=['GET'])
def get_trends() -> Dict[str, Any]:
    """
    Get trend data over time

    Query Parameters:
        days: Number of days to analyze (default: 30)

    Returns:
        Trend data for tickets over time
    """
    try:
        days = int(request.args.get('days', 30))
        trends = db.get_trends(days)
        return jsonify(trends), 200
    except Exception as e:
        logger.error(f"Error getting trends: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/analytics/department/<department_name>', methods=['GET'])
def get_department_analytics(department_name: str) -> Dict[str, Any]:
    """
    Get analytics for a specific department

    Args:
        department_name: Department name

    Returns:
        Department-specific analytics
    """
    try:
        if department_name not in constants.DEPARTMENTS:
            return jsonify({'error': 'Invalid department'}), 400

        analytics = db.get_department_analytics(department_name)
        return jsonify(analytics), 200
    except Exception as e:
        logger.error(f"Error getting department analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500


def handle_ticket_created(message: Dict[str, Any]) -> None:
    """
    Handle ticket created event

    Args:
        message: Message containing ticket data
    """
    try:
        ticket = message.get('ticket', {})
        ticket_id = ticket.get('id')

        logger.debug(f"Recording ticket created event for ticket {ticket_id}")
        db.record_ticket_event('created', ticket_id, ticket)

    except Exception as e:
        logger.error(f"Error handling ticket created event: {str(e)}")


def handle_ticket_categorized(message: Dict[str, Any]) -> None:
    """
    Handle ticket categorized event

    Args:
        message: Message containing categorization data
    """
    try:
        ticket_id = message.get('ticket_id')
        department = message.get('department')
        confidence_score = message.get('confidence_score')

        logger.debug(f"Recording categorization event for ticket {ticket_id}")
        db.record_categorization_event(ticket_id, department, confidence_score)

    except Exception as e:
        logger.error(f"Error handling ticket categorized event: {str(e)}")


def handle_ticket_routed(message: Dict[str, Any]) -> None:
    """
    Handle ticket routed event

    Args:
        message: Message containing routing data
    """
    try:
        ticket_id = message.get('ticket_id')
        department = message.get('department')

        logger.debug(f"Recording routing event for ticket {ticket_id}")
        db.record_routing_event(ticket_id, department)

    except Exception as e:
        logger.error(f"Error handling ticket routed event: {str(e)}")


def handle_ticket_status_updated(message: Dict[str, Any]) -> None:
    """
    Handle ticket status updated event

    Args:
        message: Message containing status update data
    """
    try:
        ticket_id = message.get('id')
        status = message.get('status')

        logger.debug(f"Recording status update event for ticket {ticket_id}")
        db.record_status_update_event(ticket_id, status)

    except Exception as e:
        logger.error(f"Error handling ticket status updated event: {str(e)}")


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

        # Declare and bind queues for analytics
        queues = [
            constants.QUEUE_TICKET_CREATED,
            constants.QUEUE_TICKET_CATEGORIZED,
            constants.QUEUE_TICKET_ROUTED,
            constants.QUEUE_TICKET_STATUS_UPDATED
        ]

        for queue in queues:
            mq.declare_queue(queue)
            mq.bind_queue(queue, constants.EXCHANGE_TICKETS, queue)

        logger.info(f"Starting Analytics Service on port {constants.ANALYTICS_SERVICE_PORT}")

        # Initialize database
        db.initialize_database()

        # Run Flask app
        app.run(
            host='0.0.0.0',
            port=constants.ANALYTICS_SERVICE_PORT,
            debug=constants.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("Shutting down Analytics Service")
        mq.disconnect()
    except Exception as e:
        logger.error(f"Failed to start Analytics Service: {str(e)}")
        sys.exit(1)
