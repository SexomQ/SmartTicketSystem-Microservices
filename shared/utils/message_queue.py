"""
Shared RabbitMQ utility for Smart Ticket System Microservices
"""
import pika
import json
import logging
from typing import Callable, Optional, Dict, Any
from functools import wraps
import time


class MessageQueue:
    """RabbitMQ wrapper for publishing and consuming messages"""

    def __init__(self, host: str, port: int, user: str, password: str, vhost: str = '/'):
        """
        Initialize MessageQueue

        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            user: RabbitMQ username
            password: RabbitMQ password
            vhost: RabbitMQ virtual host
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.vhost = vhost
        self.connection = None
        self.channel = None
        self.logger = logging.getLogger(__name__)

    def connect(self, max_retries: int = 5, retry_delay: int = 5) -> None:
        """
        Connect to RabbitMQ with retries

        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retries in seconds
        """
        for attempt in range(max_retries):
            try:
                credentials = pika.PlainCredentials(self.user, self.password)
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    virtual_host=self.vhost,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                self.logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")
                return
            except Exception as e:
                self.logger.warning(
                    f"Connection attempt {attempt + 1}/{max_retries} failed: {str(e)}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to connect to RabbitMQ after {max_retries} attempts")

    def disconnect(self) -> None:
        """Disconnect from RabbitMQ"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            self.logger.error(f"Error disconnecting from RabbitMQ: {str(e)}")

    def declare_exchange(self, exchange_name: str, exchange_type: str = 'topic') -> None:
        """
        Declare an exchange

        Args:
            exchange_name: Name of the exchange
            exchange_type: Type of exchange (topic, direct, fanout, headers)
        """
        if not self.channel:
            raise Exception("Not connected to RabbitMQ")

        self.channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=exchange_type,
            durable=True
        )
        self.logger.info(f"Declared exchange: {exchange_name} (type: {exchange_type})")

    def declare_queue(self, queue_name: str, durable: bool = True) -> None:
        """
        Declare a queue

        Args:
            queue_name: Name of the queue
            durable: Whether the queue should survive broker restarts
        """
        if not self.channel:
            raise Exception("Not connected to RabbitMQ")

        self.channel.queue_declare(queue=queue_name, durable=durable)
        self.logger.info(f"Declared queue: {queue_name}")

    def bind_queue(self, queue_name: str, exchange_name: str, routing_key: str) -> None:
        """
        Bind a queue to an exchange

        Args:
            queue_name: Name of the queue
            exchange_name: Name of the exchange
            routing_key: Routing key pattern
        """
        if not self.channel:
            raise Exception("Not connected to RabbitMQ")

        self.channel.queue_bind(
            queue=queue_name,
            exchange=exchange_name,
            routing_key=routing_key
        )
        self.logger.info(f"Bound queue {queue_name} to exchange {exchange_name} with key {routing_key}")

    def _ensure_connection(self) -> None:
        """
        Ensure connection and channel are open, reconnect if needed
        """
        try:
            if not self.connection or self.connection.is_closed:
                self.logger.warning("Connection is closed, reconnecting...")
                self.connect()
            elif not self.channel or self.channel.is_closed:
                self.logger.warning("Channel is closed, reopening...")
                self.channel = self.connection.channel()
        except Exception as e:
            self.logger.error(f"Error ensuring connection: {str(e)}")
            self.connect()

    def publish(
        self,
        exchange_name: str,
        routing_key: str,
        message: Dict[str, Any],
        persistent: bool = True,
        max_retries: int = 3
    ) -> None:
        """
        Publish a message to an exchange with retry logic

        Args:
            exchange_name: Name of the exchange
            routing_key: Routing key
            message: Message dictionary to publish
            persistent: Whether the message should be persistent
            max_retries: Maximum number of retry attempts
        """
        body = json.dumps(message)

        for attempt in range(max_retries):
            try:
                # Ensure connection is active before publishing
                self._ensure_connection()

                properties = pika.BasicProperties(
                    delivery_mode=2 if persistent else 1,
                    content_type='application/json'
                )

                self.channel.basic_publish(
                    exchange=exchange_name,
                    routing_key=routing_key,
                    body=body,
                    properties=properties
                )
                self.logger.debug(f"Published message to {exchange_name} with key {routing_key}")
                return  # Success, exit retry loop

            except (pika.exceptions.ConnectionClosed,
                    pika.exceptions.ChannelClosed,
                    pika.exceptions.AMQPError) as e:
                self.logger.warning(
                    f"Publish attempt {attempt + 1}/{max_retries} failed: {str(e)}"
                )
                if attempt < max_retries - 1:
                    # Force full reconnection
                    try:
                        if self.connection and not self.connection.is_closed:
                            self.connection.close()
                    except:
                        pass
                    self.connection = None
                    self.channel = None
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    self.logger.error(
                        f"Failed to publish message after {max_retries} attempts"
                    )
                    raise

    def consume(
        self,
        queue_name: str,
        callback: Callable,
        auto_ack: bool = False
    ) -> None:
        """
        Start consuming messages from a queue

        Args:
            queue_name: Name of the queue
            callback: Callback function to process messages
            auto_ack: Whether to automatically acknowledge messages
        """
        if not self.channel:
            raise Exception("Not connected to RabbitMQ")

        def wrapped_callback(ch, method, properties, body):
            try:
                message = json.loads(body)
                self.logger.debug(f"Received message from {queue_name}")
                callback(message)
                if not auto_ack:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                if not auto_ack:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=wrapped_callback,
            auto_ack=auto_ack
        )

        self.logger.info(f"Started consuming from queue: {queue_name}")
        self.channel.start_consuming()

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
