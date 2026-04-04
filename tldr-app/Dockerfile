# Get pyton runtime
FROM python:3.13-slim

# Target dir for image build
WORKDIR /app

# Copy packages from requirements.txt to working directory
COPY requirements.txt .
# Install the packages from requirements.txt but do not store in cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code files from local repo to image filesystem
COPY main.py llm_client.py ./
COPY static ./static

# Expecting traffic on port 8000
EXPOSE 8000

# Command to run when container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
