# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Create necessary directories
RUN mkdir -p /app/data/input /app/data/output

# Set the entrypoint to run the script
ENTRYPOINT ["python", "scripts/run_processors.py"]

# Set a default command (which can be overridden)
CMD ["control_file.xlsx"]
