FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libpq-dev \
    gcc \
    build-essential \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -m nltk.downloader punkt stopwords wordnet

# Copy the rest of the code
COPY . .

# Expose port (match your gunicorn or Flask port)
EXPOSE 10000

# Start the app
CMD ["gunicorn", "-b", "0.0.0.0:10000", "run:app"]
