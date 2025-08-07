FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Install system dependencies (expanded to fix Tesseract + image handling)
RUN apt-get update && apt-get install -y \
    libgl1 \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libpq-dev \
    gcc \
    build-essential \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libleptonica-dev \
    libtiff-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libwebp-dev \
    libopenjp2-7 \
    fonts-dejavu-core \
    fonts-freefont-ttf \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set work directory and change ownership
WORKDIR /app
RUN mkdir -p /app/nltk_data && chown -R appuser:appgroup /app

# Set environment variables for non-root user
ENV NLTK_DATA=/app/nltk_data
ENV MPLCONFIGDIR=/tmp/matplotlib

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download required NLTK data to /app/nltk_data (custom location)
RUN python -m nltk.downloader -d /app/nltk_data punkt stopwords wordnet

# Copy app code and fix permissions
COPY . .
RUN chown -R appuser:appgroup /app

# Switch to non-root user for running the app
USER appuser

# Expose the port that your app runs on
EXPOSE 10000

# Run the app
CMD ["gunicorn", "-b", "0.0.0.0:10000", "run:app"]
