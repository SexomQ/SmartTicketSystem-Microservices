"""
Database operations for Ticket Service
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
from shared.models import Ticket


class TicketDatabase:
    """Handle all database operations for tickets"""

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

                # Create tickets table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
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
                """)

                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tickets_department
                    ON tickets(department)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tickets_status
                    ON tickets(status)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tickets_created_at
                    ON tickets(created_at)
                """)

                self.logger.info("Database initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            raise

    def create_ticket(self, ticket: Ticket) -> int:
        """
        Create a new ticket

        Args:
            ticket: Ticket object

        Returns:
            ID of created ticket
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO tickets (title, description, user_name, user_email, status)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    ticket.title,
                    ticket.description,
                    ticket.user_name,
                    ticket.user_email,
                    ticket.status
                ))

                ticket_id = cursor.fetchone()[0]
                self.logger.info(f"Created ticket {ticket_id}")
                return ticket_id

        except Exception as e:
            self.logger.error(f"Error creating ticket: {str(e)}")
            raise

    def get_ticket_by_id(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a ticket by ID

        Args:
            ticket_id: Ticket ID

        Returns:
            Ticket dictionary or None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                cursor.execute("""
                    SELECT * FROM tickets WHERE id = %s
                """, (ticket_id,))

                result = cursor.fetchone()
                return dict(result) if result else None

        except Exception as e:
            self.logger.error(f"Error getting ticket {ticket_id}: {str(e)}")
            raise

    def get_all_tickets(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all tickets with optional status filter

        Args:
            status: Filter by status (optional)

        Returns:
            List of ticket dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                if status:
                    cursor.execute("""
                        SELECT * FROM tickets WHERE status = %s
                        ORDER BY created_at DESC
                    """, (status,))
                else:
                    cursor.execute("""
                        SELECT * FROM tickets
                        ORDER BY created_at DESC
                    """)

                results = cursor.fetchall()
                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error getting all tickets: {str(e)}")
            raise

    def get_tickets_by_department(
        self,
        department: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tickets by department with optional status filter

        Args:
            department: Department name
            status: Filter by status (optional)

        Returns:
            List of ticket dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                if status:
                    cursor.execute("""
                        SELECT * FROM tickets
                        WHERE department = %s AND status = %s
                        ORDER BY created_at DESC
                    """, (department, status))
                else:
                    cursor.execute("""
                        SELECT * FROM tickets
                        WHERE department = %s
                        ORDER BY created_at DESC
                    """, (department,))

                results = cursor.fetchall()
                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error getting tickets for department {department}: {str(e)}")
            raise

    def update_ticket_status(self, ticket_id: int, status: str) -> bool:
        """
        Update ticket status

        Args:
            ticket_id: Ticket ID
            status: New status

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE tickets
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (status, ticket_id))

                self.logger.info(f"Updated ticket {ticket_id} status to {status}")
                return True

        except Exception as e:
            self.logger.error(f"Error updating ticket status: {str(e)}")
            raise

    def update_ticket_department(
        self,
        ticket_id: int,
        department: str,
        confidence_score: int
    ) -> bool:
        """
        Update ticket department and confidence score

        Args:
            ticket_id: Ticket ID
            department: Department name
            confidence_score: Confidence score

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE tickets
                    SET department = %s, confidence_score = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (department, confidence_score, ticket_id))

                self.logger.info(f"Updated ticket {ticket_id} department to {department}")
                return True

        except Exception as e:
            self.logger.error(f"Error updating ticket department: {str(e)}")
            raise

    def ticket_exists(self, ticket_id: int) -> bool:
        """
        Check if a ticket exists

        Args:
            ticket_id: Ticket ID

        Returns:
            True if ticket exists
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT EXISTS(SELECT 1 FROM tickets WHERE id = %s)
                """, (ticket_id,))

                return cursor.fetchone()[0]

        except Exception as e:
            self.logger.error(f"Error checking ticket existence: {str(e)}")
            raise

    def get_ticket_statistics(self) -> Dict[str, Any]:
        """
        Get ticket statistics

        Returns:
            Dictionary with statistics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                # Total tickets
                cursor.execute("SELECT COUNT(*) as total FROM tickets")
                total = cursor.fetchone()['total']

                # By department
                cursor.execute("""
                    SELECT department, COUNT(*) as count
                    FROM tickets
                    WHERE department IS NOT NULL
                    GROUP BY department
                """)
                by_department = {row['department']: row['count'] for row in cursor.fetchall()}

                # By status
                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM tickets
                    GROUP BY status
                """)
                by_status = {row['status']: row['count'] for row in cursor.fetchall()}

                # Average confidence
                cursor.execute("""
                    SELECT AVG(confidence_score) as avg_confidence
                    FROM tickets
                    WHERE confidence_score IS NOT NULL
                """)
                avg_confidence = cursor.fetchone()['avg_confidence'] or 0

                return {
                    'total_tickets': total,
                    'by_department': by_department,
                    'by_status': by_status,
                    'average_confidence': round(float(avg_confidence), 2)
                }

        except Exception as e:
            self.logger.error(f"Error getting ticket statistics: {str(e)}")
            raise
