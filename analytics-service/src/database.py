"""
Database operations for Analytics Service
Uses PostgreSQL for persistent storage
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Dict, Any, List, Optional
import logging
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.config import constants


class AnalyticsDatabase:
    """Handle all database operations for analytics"""

    def __init__(self):
        """Initialize database connection parameters"""
        self.db_config = {
            'host': constants.DB_HOST,
            'port': constants.DB_PORT,
            'database': constants.DB_NAME,
            'user': constants.DB_USER,
            'password': constants.DB_PASSWORD
        }
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections

        Yields:
            Connection object
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    def initialize_database(self) -> None:
        """Initialize database schema"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Create analytics_events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analytics_events (
                        id SERIAL PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        ticket_id INTEGER,
                        department TEXT,
                        status TEXT,
                        confidence_score INTEGER,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analytics_event_type
                    ON analytics_events(event_type)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analytics_ticket_id
                    ON analytics_events(ticket_id)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analytics_department
                    ON analytics_events(department)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_analytics_created_at
                    ON analytics_events(created_at)
                """)

                self.logger.info("Analytics database initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            raise

    def record_ticket_event(self, event_type: str, ticket_id: int, metadata: Dict[str, Any]) -> None:
        """
        Record a ticket event

        Args:
            event_type: Type of event
            ticket_id: Ticket ID
            metadata: Additional metadata
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO analytics_events (event_type, ticket_id, metadata)
                    VALUES (%s, %s, %s)
                """, (event_type, ticket_id, psycopg2.extras.Json(metadata)))

                self.logger.debug(f"Recorded {event_type} event for ticket {ticket_id}")

        except Exception as e:
            self.logger.error(f"Error recording event: {str(e)}")
            raise

    def record_categorization_event(self, ticket_id: int, department: str, confidence_score: int) -> None:
        """
        Record a categorization event

        Args:
            ticket_id: Ticket ID
            department: Department name
            confidence_score: Confidence score
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO analytics_events (event_type, ticket_id, department, confidence_score)
                    VALUES ('categorized', %s, %s, %s)
                """, (ticket_id, department, confidence_score))

                self.logger.debug(f"Recorded categorization event for ticket {ticket_id}")

        except Exception as e:
            self.logger.error(f"Error recording categorization event: {str(e)}")
            raise

    def record_routing_event(self, ticket_id: int, department: str) -> None:
        """
        Record a routing event

        Args:
            ticket_id: Ticket ID
            department: Department name
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO analytics_events (event_type, ticket_id, department)
                    VALUES ('routed', %s, %s)
                """, (ticket_id, department))

                self.logger.debug(f"Recorded routing event for ticket {ticket_id}")

        except Exception as e:
            self.logger.error(f"Error recording routing event: {str(e)}")
            raise

    def record_status_update_event(self, ticket_id: int, status: str) -> None:
        """
        Record a status update event

        Args:
            ticket_id: Ticket ID
            status: New status
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO analytics_events (event_type, ticket_id, status)
                    VALUES ('status_updated', %s, %s)
                """, (ticket_id, status))

                self.logger.debug(f"Recorded status update event for ticket {ticket_id}")

        except Exception as e:
            self.logger.error(f"Error recording status update event: {str(e)}")
            raise

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get overall dashboard summary

        Returns:
            Dictionary with summary statistics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                # Total tickets created
                cursor.execute("""
                    SELECT COUNT(DISTINCT ticket_id) as total
                    FROM analytics_events
                    WHERE event_type = 'created'
                """)
                total_tickets = cursor.fetchone()['total'] or 0

                # By department
                cursor.execute("""
                    SELECT department, COUNT(DISTINCT ticket_id) as count
                    FROM analytics_events
                    WHERE event_type = 'routed' AND department IS NOT NULL
                    GROUP BY department
                """)
                by_department = {row['department']: row['count'] for row in cursor.fetchall()}

                # By status (latest status per ticket)
                cursor.execute("""
                    WITH latest_status AS (
                        SELECT DISTINCT ON (ticket_id) ticket_id, status
                        FROM analytics_events
                        WHERE event_type = 'status_updated' AND status IS NOT NULL
                        ORDER BY ticket_id, created_at DESC
                    )
                    SELECT status, COUNT(*) as count
                    FROM latest_status
                    GROUP BY status
                """)
                by_status = {row['status']: row['count'] for row in cursor.fetchall()}

                # Average confidence
                cursor.execute("""
                    SELECT AVG(confidence_score) as avg_confidence
                    FROM analytics_events
                    WHERE event_type = 'categorized' AND confidence_score IS NOT NULL
                """)
                avg_confidence = cursor.fetchone()['avg_confidence'] or 0

                # Recent activity (last 24 hours)
                cursor.execute("""
                    SELECT COUNT(DISTINCT ticket_id) as count
                    FROM analytics_events
                    WHERE event_type = 'created'
                    AND created_at >= NOW() - INTERVAL '24 hours'
                """)
                recent_tickets = cursor.fetchone()['count'] or 0

                return {
                    'total_tickets': total_tickets,
                    'by_department': by_department,
                    'by_status': by_status,
                    'average_confidence': round(float(avg_confidence), 2),
                    'recent_tickets_24h': recent_tickets
                }

        except Exception as e:
            self.logger.error(f"Error getting dashboard summary: {str(e)}")
            raise

    def get_routing_analytics(self) -> Dict[str, Any]:
        """
        Get routing analytics

        Returns:
            Dictionary with routing analytics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                # Department distribution
                cursor.execute("""
                    SELECT department, COUNT(DISTINCT ticket_id) as count
                    FROM analytics_events
                    WHERE event_type = 'routed' AND department IS NOT NULL
                    GROUP BY department
                """)
                department_distribution = {row['department']: row['count'] for row in cursor.fetchall()}

                # Calculate percentages
                total = sum(department_distribution.values())
                department_percentages = {}
                if total > 0:
                    for dept, count in department_distribution.items():
                        department_percentages[dept] = round((count / total) * 100, 2)

                # Average confidence by department
                cursor.execute("""
                    SELECT department, AVG(confidence_score) as avg_confidence
                    FROM analytics_events
                    WHERE event_type = 'categorized' AND department IS NOT NULL
                    GROUP BY department
                """)
                avg_confidence_by_dept = {}
                for row in cursor.fetchall():
                    avg_confidence_by_dept[row['department']] = round(float(row['avg_confidence']), 2)

                return {
                    'department_distribution': department_distribution,
                    'department_percentages': department_percentages,
                    'average_confidence_by_department': avg_confidence_by_dept
                }

        except Exception as e:
            self.logger.error(f"Error getting routing analytics: {str(e)}")
            raise

    def get_ticket_analytics(self, period: str = 'all', department: Optional[str] = None) -> Dict[str, Any]:
        """
        Get ticket analytics for a specific period

        Args:
            period: Time period (day, week, month, all)
            department: Filter by department (optional)

        Returns:
            Dictionary with ticket analytics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                # Determine time filter
                time_filter = ""
                if period == 'day':
                    time_filter = "AND created_at >= NOW() - INTERVAL '1 day'"
                elif period == 'week':
                    time_filter = "AND created_at >= NOW() - INTERVAL '7 days'"
                elif period == 'month':
                    time_filter = "AND created_at >= NOW() - INTERVAL '30 days'"

                # Department filter
                dept_filter = ""
                if department:
                    dept_filter = f"AND department = '{department}'"

                # Total tickets
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT ticket_id) as total
                    FROM analytics_events
                    WHERE event_type = 'created' {time_filter}
                """)
                total = cursor.fetchone()['total'] or 0

                # By department
                cursor.execute(f"""
                    SELECT department, COUNT(DISTINCT ticket_id) as count
                    FROM analytics_events
                    WHERE event_type = 'routed' AND department IS NOT NULL {time_filter} {dept_filter}
                    GROUP BY department
                """)
                by_department = {row['department']: row['count'] for row in cursor.fetchall()}

                return {
                    'period': period,
                    'total_tickets': total,
                    'by_department': by_department
                }

        except Exception as e:
            self.logger.error(f"Error getting ticket analytics: {str(e)}")
            raise

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics

        Returns:
            Dictionary with performance metrics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                # Resolution rate (resolved / total)
                cursor.execute("""
                    WITH latest_status AS (
                        SELECT DISTINCT ON (ticket_id) ticket_id, status
                        FROM analytics_events
                        WHERE event_type = 'status_updated' AND status IS NOT NULL
                        ORDER BY ticket_id, created_at DESC
                    )
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved
                    FROM latest_status
                """)
                result = cursor.fetchone()
                total = result['total'] or 0
                resolved = result['resolved'] or 0
                resolution_rate = round((resolved / total * 100), 2) if total > 0 else 0

                # Average categorization confidence
                cursor.execute("""
                    SELECT AVG(confidence_score) as avg_confidence
                    FROM analytics_events
                    WHERE event_type = 'categorized' AND confidence_score IS NOT NULL
                """)
                avg_confidence = cursor.fetchone()['avg_confidence'] or 0

                return {
                    'total_tickets': total,
                    'resolved_tickets': resolved,
                    'resolution_rate': resolution_rate,
                    'average_categorization_confidence': round(float(avg_confidence), 2)
                }

        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {str(e)}")
            raise

    def get_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Get trend data over time

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with trend data
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                # Daily ticket creation trend
                cursor.execute(f"""
                    SELECT DATE(created_at) as date, COUNT(DISTINCT ticket_id) as count
                    FROM analytics_events
                    WHERE event_type = 'created'
                    AND created_at >= NOW() - INTERVAL '{days} days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """)
                daily_tickets = [dict(row) for row in cursor.fetchall()]

                return {
                    'days': days,
                    'daily_ticket_creation': daily_tickets
                }

        except Exception as e:
            self.logger.error(f"Error getting trends: {str(e)}")
            raise

    def get_department_analytics(self, department: str) -> Dict[str, Any]:
        """
        Get analytics for a specific department

        Args:
            department: Department name

        Returns:
            Dictionary with department analytics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                # Total tickets for department
                cursor.execute("""
                    SELECT COUNT(DISTINCT ticket_id) as total
                    FROM analytics_events
                    WHERE event_type = 'routed' AND department = %s
                """, (department,))
                total = cursor.fetchone()['total'] or 0

                # Average confidence
                cursor.execute("""
                    SELECT AVG(confidence_score) as avg_confidence
                    FROM analytics_events
                    WHERE event_type = 'categorized' AND department = %s
                """, (department,))
                avg_confidence = cursor.fetchone()['avg_confidence'] or 0

                # Status distribution
                cursor.execute("""
                    WITH dept_tickets AS (
                        SELECT DISTINCT ticket_id
                        FROM analytics_events
                        WHERE event_type = 'routed' AND department = %s
                    ),
                    latest_status AS (
                        SELECT DISTINCT ON (ae.ticket_id) ae.ticket_id, ae.status
                        FROM analytics_events ae
                        INNER JOIN dept_tickets dt ON ae.ticket_id = dt.ticket_id
                        WHERE ae.event_type = 'status_updated' AND ae.status IS NOT NULL
                        ORDER BY ae.ticket_id, ae.created_at DESC
                    )
                    SELECT status, COUNT(*) as count
                    FROM latest_status
                    GROUP BY status
                """, (department,))
                by_status = {row['status']: row['count'] for row in cursor.fetchall()}

                return {
                    'department': department,
                    'total_tickets': total,
                    'average_confidence': round(float(avg_confidence), 2),
                    'by_status': by_status
                }

        except Exception as e:
            self.logger.error(f"Error getting department analytics: {str(e)}")
            raise
