FROM python:3.11-slim

WORKDIR /app

# Copy shared modules
COPY shared/ /app/shared/

# Copy service files
COPY analytics-service/requirements.txt .
COPY analytics-service/src/ /app/src/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5004

# Run application
CMD ["python", "src/app.py"]
