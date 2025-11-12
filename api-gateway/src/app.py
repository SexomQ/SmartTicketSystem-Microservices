"""
API Gateway Service
Central entry point for all client requests
Routes requests to appropriate microservices
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
from shared.utils import setup_logger

# Initialize Flask app
app = Flask(__name__)

# Setup logging
logger = setup_logger('api-gateway', constants.LOG_LEVEL)


def forward_request(service_url: str, path: str, method: str = 'GET', data: Dict[str, Any] = None) -> tuple:
    """
    Forward request to a microservice

    Args:
        service_url: Base URL of the service
        path: API path
        method: HTTP method
        data: Request data (for POST, PUT)

    Returns:
        Tuple of (response_data, status_code)
    """
    try:
        url = f"{service_url}{path}"
        logger.debug(f"Forwarding {method} request to {url}")

        if method == 'GET':
            response = requests.get(url, timeout=constants.SERVICE_TIMEOUT)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=constants.SERVICE_TIMEOUT)
        elif method == 'PUT':
            response = requests.put(url, json=data, timeout=constants.SERVICE_TIMEOUT)
        elif method == 'DELETE':
            response = requests.delete(url, timeout=constants.SERVICE_TIMEOUT)
        else:
            return {'error': 'Method not supported'}, 405

        return response.json(), response.status_code

    except requests.exceptions.Timeout:
        logger.error(f"Timeout forwarding request to {service_url}")
        return {'error': 'Service timeout'}, 504
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error to {service_url}")
        return {'error': 'Service unavailable'}, 503
    except Exception as e:
        logger.error(f"Error forwarding request: {str(e)}")
        return {'error': str(e)}, 500


@app.route('/', methods=['GET'])
def index() -> Dict[str, Any]:
    """
    API Gateway index - provides API documentation

    Returns:
        API information and available endpoints
    """
    return jsonify({
        'service': constants.SYSTEM_NAME,
        'architecture': constants.ARCHITECTURE,
        'version': constants.API_VERSION,
        'status': 'running',
        'endpoints': {
            'health': {
                'path': '/api/health',
                'method': 'GET',
                'description': 'Health check for all services'
            },
            'tickets': {
                'create': {'path': '/api/tickets', 'method': 'POST'},
                'list': {'path': '/api/tickets', 'method': 'GET'},
                'get': {'path': '/api/tickets/<id>', 'method': 'GET'},
                'update': {'path': '/api/tickets/<id>', 'method': 'PUT'},
                'update_status': {'path': '/api/tickets/<id>/status', 'method': 'PUT'}
            },
            'departments': {
                'list': {'path': '/api/departments', 'method': 'GET'},
                'get': {'path': '/api/departments/<name>', 'method': 'GET'},
                'tickets': {'path': '/api/departments/<name>/tickets', 'method': 'GET'}
            },
            'routing': {
                'route': {'path': '/api/route', 'method': 'POST'},
                'reroute': {'path': '/api/route/<ticket_id>', 'method': 'PUT'},
                'statistics': {'path': '/api/routing/statistics', 'method': 'GET'},
                'history': {'path': '/api/routing/history/<ticket_id>', 'method': 'GET'}
            },
            'analytics': {
                'dashboard_summary': {'path': '/api/dashboard/summary', 'method': 'GET'},
                'routing_analytics': {'path': '/api/dashboard/routing', 'method': 'GET'},
                'ticket_analytics': {'path': '/api/analytics/tickets', 'method': 'GET'},
                'performance': {'path': '/api/analytics/performance', 'method': 'GET'},
                'trends': {'path': '/api/analytics/trends', 'method': 'GET'},
                'department_analytics': {'path': '/api/analytics/department/<name>', 'method': 'GET'}
            },
            'categorization': {
                'categorize': {'path': '/api/categorize', 'method': 'POST'}
            }
        }
    }), 200


@app.route('/api/health', methods=['GET'])
def health_check() -> Dict[str, Any]:
    """
    Health check for all services

    Returns:
        Health status of all microservices
    """
    services = {
        'api-gateway': 'healthy',
        'ticket-service': 'unknown',
        'ai-service': 'unknown',
        'routing-service': 'unknown',
        'analytics-service': 'unknown'
    }

    # Check ticket service
    try:
        response = requests.get(f"{constants.TICKET_SERVICE_URL}/health", timeout=5)
        services['ticket-service'] = 'healthy' if response.status_code == 200 else 'unhealthy'
    except:
        services['ticket-service'] = 'unhealthy'

    # Check AI service
    try:
        response = requests.get(f"{constants.AI_SERVICE_URL}/health", timeout=5)
        services['ai-service'] = 'healthy' if response.status_code == 200 else 'unhealthy'
    except:
        services['ai-service'] = 'unhealthy'

    # Check routing service
    try:
        response = requests.get(f"{constants.ROUTING_SERVICE_URL}/health", timeout=5)
        services['routing-service'] = 'healthy' if response.status_code == 200 else 'unhealthy'
    except:
        services['routing-service'] = 'unhealthy'

    # Check analytics service
    try:
        response = requests.get(f"{constants.ANALYTICS_SERVICE_URL}/health", timeout=5)
        services['analytics-service'] = 'healthy' if response.status_code == 200 else 'unhealthy'
    except:
        services['analytics-service'] = 'unhealthy'

    overall_status = 'healthy' if all(s == 'healthy' for s in services.values()) else 'degraded'

    return jsonify({
        'status': overall_status,
        'services': services
    }), 200


# ============================================================================
# TICKET ENDPOINTS
# ============================================================================

@app.route('/api/tickets', methods=['POST'])
def create_ticket() -> Dict[str, Any]:
    """Create a new ticket"""
    data = request.get_json()
    return forward_request(constants.TICKET_SERVICE_URL, '/tickets', 'POST', data)


@app.route('/api/tickets', methods=['GET'])
def get_all_tickets() -> Dict[str, Any]:
    """Get all tickets"""
    # Forward query parameters
    query_params = request.args.to_dict()
    path = '/tickets'
    if query_params:
        query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
        path = f"{path}?{query_string}"
    return forward_request(constants.TICKET_SERVICE_URL, path, 'GET')


@app.route('/api/tickets/<int:ticket_id>', methods=['GET'])
def get_ticket(ticket_id: int) -> Dict[str, Any]:
    """Get a specific ticket"""
    return forward_request(constants.TICKET_SERVICE_URL, f'/tickets/{ticket_id}', 'GET')


@app.route('/api/tickets/<int:ticket_id>', methods=['PUT'])
def update_ticket(ticket_id: int) -> Dict[str, Any]:
    """Update a ticket"""
    data = request.get_json()
    return forward_request(constants.TICKET_SERVICE_URL, f'/tickets/{ticket_id}', 'PUT', data)


@app.route('/api/tickets/<int:ticket_id>/status', methods=['PUT'])
def update_ticket_status(ticket_id: int) -> Dict[str, Any]:
    """Update ticket status"""
    data = request.get_json()
    return forward_request(constants.TICKET_SERVICE_URL, f'/tickets/{ticket_id}/status', 'PUT', data)


# ============================================================================
# DEPARTMENT ENDPOINTS
# ============================================================================

@app.route('/api/departments', methods=['GET'])
def get_departments() -> Dict[str, Any]:
    """Get all departments"""
    return forward_request(constants.ROUTING_SERVICE_URL, '/departments', 'GET')


@app.route('/api/departments/<department_name>', methods=['GET'])
def get_department(department_name: str) -> Dict[str, Any]:
    """Get department details"""
    return forward_request(constants.ROUTING_SERVICE_URL, f'/departments/{department_name}', 'GET')


@app.route('/api/departments/<department_name>/tickets', methods=['GET'])
def get_department_tickets(department_name: str) -> Dict[str, Any]:
    """Get tickets for a department"""
    query_params = request.args.to_dict()
    path = f'/tickets?department={department_name}'
    if 'status' in query_params:
        path = f"{path}&status={query_params['status']}"
    return forward_request(constants.TICKET_SERVICE_URL, path, 'GET')


# ============================================================================
# ROUTING ENDPOINTS
# ============================================================================

@app.route('/api/route', methods=['POST'])
def route_ticket() -> Dict[str, Any]:
    """Route a ticket to a department"""
    data = request.get_json()
    return forward_request(constants.ROUTING_SERVICE_URL, '/route', 'POST', data)


@app.route('/api/route/<int:ticket_id>', methods=['PUT'])
def reroute_ticket(ticket_id: int) -> Dict[str, Any]:
    """Reroute a ticket to a different department"""
    data = request.get_json()
    return forward_request(constants.ROUTING_SERVICE_URL, f'/route/{ticket_id}', 'PUT', data)


@app.route('/api/routing/statistics', methods=['GET'])
def get_routing_statistics() -> Dict[str, Any]:
    """Get routing statistics"""
    return forward_request(constants.ROUTING_SERVICE_URL, '/routing/statistics', 'GET')


@app.route('/api/routing/history/<int:ticket_id>', methods=['GET'])
def get_routing_history(ticket_id: int) -> Dict[str, Any]:
    """Get routing history for a ticket"""
    return forward_request(constants.ROUTING_SERVICE_URL, f'/routing/history/{ticket_id}', 'GET')


# ============================================================================
# ANALYTICS/DASHBOARD ENDPOINTS
# ============================================================================

@app.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary() -> Dict[str, Any]:
    """Get dashboard summary"""
    return forward_request(constants.ANALYTICS_SERVICE_URL, '/dashboard/summary', 'GET')


@app.route('/api/dashboard/routing', methods=['GET'])
def get_routing_analytics() -> Dict[str, Any]:
    """Get routing analytics"""
    return forward_request(constants.ANALYTICS_SERVICE_URL, '/dashboard/routing', 'GET')


@app.route('/api/analytics/tickets', methods=['GET'])
def get_ticket_analytics() -> Dict[str, Any]:
    """Get ticket analytics"""
    query_params = request.args.to_dict()
    path = '/analytics/tickets'
    if query_params:
        query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
        path = f"{path}?{query_string}"
    return forward_request(constants.ANALYTICS_SERVICE_URL, path, 'GET')


@app.route('/api/analytics/performance', methods=['GET'])
def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics"""
    return forward_request(constants.ANALYTICS_SERVICE_URL, '/analytics/performance', 'GET')


@app.route('/api/analytics/trends', methods=['GET'])
def get_trends() -> Dict[str, Any]:
    """Get trend data"""
    query_params = request.args.to_dict()
    path = '/analytics/trends'
    if query_params:
        query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
        path = f"{path}?{query_string}"
    return forward_request(constants.ANALYTICS_SERVICE_URL, path, 'GET')


@app.route('/api/analytics/department/<department_name>', methods=['GET'])
def get_department_analytics(department_name: str) -> Dict[str, Any]:
    """Get department analytics"""
    return forward_request(constants.ANALYTICS_SERVICE_URL, f'/analytics/department/{department_name}', 'GET')


# ============================================================================
# AI CATEGORIZATION ENDPOINTS
# ============================================================================

@app.route('/api/categorize', methods=['POST'])
def categorize_ticket() -> Dict[str, Any]:
    """Categorize a ticket using AI"""
    data = request.get_json()
    return forward_request(constants.AI_SERVICE_URL, '/categorize', 'POST', data)


# ============================================================================
# INFO ENDPOINTS
# ============================================================================

@app.route('/api/statuses', methods=['GET'])
def get_statuses() -> Dict[str, Any]:
    """Get available ticket statuses"""
    return jsonify({
        'statuses': constants.TICKET_STATUSES
    }), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================

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
        logger.info(f"Starting API Gateway on port {constants.API_GATEWAY_PORT}")
        logger.info(f"Service: {constants.SYSTEM_NAME}")
        logger.info(f"Architecture: {constants.ARCHITECTURE}")

        # Run Flask app
        app.run(
            host='0.0.0.0',
            port=constants.API_GATEWAY_PORT,
            debug=constants.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("Shutting down API Gateway")
    except Exception as e:
        logger.error(f"Failed to start API Gateway: {str(e)}")
        sys.exit(1)
