# Dockerfile
# Use a lightweight Python image for the backend
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies (FastAPI, SQLAlchemy, uvicorn, etc.)
WORKDIR /app
COPY ./backend/requirements.txt . # Assuming a requirements.txt exists for backend dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./backend /app/backend

# Expose the port FastAPI runs on
EXPOSE 80

# Command to run the FastAPI application using Uvicorn
# Note: In a real production scenario, you would likely use a reverse proxy like Nginx 
# or run both frontend and backend in separate containers.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "80"]