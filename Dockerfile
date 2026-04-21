# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if any are needed
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download the spacy model
RUN python -m spacy download en_core_web_sm

# Copy the current directory contents into the container at /app
COPY . .

# Set environment variables
ENV PORT=5000
ENV FLASK_DEBUG=false
ENV GROQ_API_KEY=your_api_key_here
ENV FRONTEND_URL=*

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run the application
CMD ["python", "run.py"]
