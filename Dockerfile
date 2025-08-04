FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Install system dependencies as root
RUN apt-get update && apt-get install -y \
    libg11 \
    tesseract-ocr \
    poppler-utils \
    libpq-dev \
    gcc \
    build-essential \  
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set work directory and change ownership
WORKDIR /app
RUN chown appuser:appgroup /app

# Copy requirements and install python dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data as root (optional: could run as non-root, but simpler here)
RUN python -m nltk.downloader punkt stopwords wordnet

# Copy rest of the app code and change ownership so non-root user can access
COPY . .
RUN chown -R appuser:appgroup /app

# Switch to non-root user for running the app
USER appuser

# Expose port (match your gunicorn or Flask port)
EXPOSE 10000

# Start the app as non-root user
CMD ["gunicorn", "-b", "0.0.0.0:10000", "run:app"]
