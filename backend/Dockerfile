# Start with the official Python base image
FROM public.ecr.aws/docker/library/python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry

# Set the working directory
WORKDIR /app

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock ./

# Configure poetry
RUN poetry config virtualenvs.create false

# Install project dependencies
ENV POETRY_REQUESTS_TIMEOUT=60
RUN poetry install --no-cache --without dev --no-root --no-interaction --no-ansi -vvv

# Download NLTK data during build
RUN python -m nltk.downloader -d /usr/local/share/nltk_data punkt punkt_tab stopwords
RUN pip install flashrank

# Copy the FastAPI application code
COPY backend backend
COPY scout scout
COPY alembic.ini alembic.ini
COPY alembic alembic

# Expose the port the app runs on

EXPOSE 8080

# Command to run the FastAPI app using Uvicorn
CMD ["poetry", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
