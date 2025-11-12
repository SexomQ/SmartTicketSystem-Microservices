"""
Database operations for Routing Service
Uses PostgreSQL for persistent storage
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Dict, Any, List, Optional
import logging
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.config import constants


class RoutingDatabase:
    """Handle all database operations for routing"""

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

                # Create departments table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS departments (
                        id SERIAL PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create ticket_routing table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ticket_routing (
                        id SERIAL PRIMARY KEY,
                        ticket_id INTEGER NOT NULL,
                        department TEXT NOT NULL,
                        confidence_score INTEGER NOT NULL,
                        routed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_routing_ticket_id
                    ON ticket_routing(ticket_id)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_routing_department
                    ON ticket_routing(department)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_routing_routed_at
                    ON ticket_routing(routed_at)
                """)

                # Insert default departments if they don't exist
                for dept in constants.DEPARTMENTS:
                    cursor.execute("""
                        INSERT INTO departments (name, description)
                        VALUES (%s, %s)
                        ON CONFLICT (name) DO NOTHING
                    """, (dept, f"{dept} department"))

                self.logger.info("Routing database initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            raise

    def create_routing(self, ticket_id: int, department: str, confidence_score: int) -> int:
        """
        Create a new routing record

        Args:
            ticket_id: Ticket ID
            department: Department name
            confidence_score: Confidence score

        Returns:
            ID of created routing record
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO ticket_routing (ticket_id, department, confidence_score)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (ticket_id, department, confidence_score))

                routing_id = cursor.fetchone()[0]
                self.logger.info(f"Created routing {routing_id} for ticket {ticket_id}")
                return routing_id

        except Exception as e:
            self.logger.error(f"Error creating routing: {str(e)}")
            raise

    def get_routing_history(self, ticket_id: int) -> List[Dict[str, Any]]:
        """
        Get routing history for a ticket

        Args:
            ticket_id: Ticket ID

        Returns:
            List of routing records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                cursor.execute("""
                    SELECT * FROM ticket_routing
                    WHERE ticket_id = %s
                    ORDER BY routed_at DESC
                """, (ticket_id,))

                results = cursor.fetchall()
                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error getting routing history: {str(e)}")
            raise

    def get_all_departments(self) -> List[Dict[str, Any]]:
        """
        Get all departments

        Returns:
            List of departments
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                cursor.execute("""
                    SELECT * FROM departments
                    WHERE is_active = TRUE
                    ORDER BY name
                """)

                results = cursor.fetchall()
                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error getting departments: {str(e)}")
            raise

    def get_department_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a department by name

        Args:
            name: Department name

        Returns:
            Department dictionary or None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                cursor.execute("""
                    SELECT * FROM departments WHERE name = %s
                """, (name,))

                result = cursor.fetchone()
                return dict(result) if result else None

        except Exception as e:
            self.logger.error(f"Error getting department: {str(e)}")
            raise

    def get_routing_statistics(self) -> Dict[str, Any]:
        """
        Get routing statistics

        Returns:
            Dictionary with statistics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                # Total routings
                cursor.execute("SELECT COUNT(*) as total FROM ticket_routing")
                total = cursor.fetchone()['total']

                # By department (count latest routing per ticket)
                cursor.execute("""
                    WITH latest_routing AS (
                        SELECT DISTINCT ON (ticket_id) ticket_id, department, confidence_score
                        FROM ticket_routing
                        ORDER BY ticket_id, routed_at DESC
                    )
                    SELECT department, COUNT(*) as count, AVG(confidence_score) as avg_confidence
                    FROM latest_routing
                    GROUP BY department
                """)
                by_department = {}
                avg_by_department = {}
                for row in cursor.fetchall():
                    by_department[row['department']] = row['count']
                    avg_by_department[row['department']] = round(float(row['avg_confidence']), 2)

                # Overall average confidence
                cursor.execute("""
                    SELECT AVG(confidence_score) as avg_confidence
                    FROM ticket_routing
                """)
                avg_confidence = cursor.fetchone()['avg_confidence'] or 0

                # Calculate percentages
                department_percentages = {}
                if total > 0:
                    for dept, count in by_department.items():
                        department_percentages[dept] = round((count / total) * 100, 2)

                return {
                    'total_routings': total,
                    'department_distribution': by_department,
                    'department_percentages': department_percentages,
                    'average_confidence_by_department': avg_by_department,
                    'overall_average_confidence': round(float(avg_confidence), 2)
                }

        except Exception as e:
            self.logger.error(f"Error getting routing statistics: {str(e)}")
            raise
