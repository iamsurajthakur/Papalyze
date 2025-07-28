FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libpq-dev \
    gcc \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose port (match your gunicorn or Flask port)
EXPOSE 10000

# Start the app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:10000", "run:app"]
