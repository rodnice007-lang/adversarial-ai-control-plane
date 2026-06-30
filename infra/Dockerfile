# Use a lightweight, secure Python base image
FROM python:3.12-slim

# Set the operational directory inside the virtual container
WORKDIR /app

# 1. Copy over just requirements first and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the remaining repository contents into the container filesystem
COPY . /app/

# Automatically run the verification matrix when the container launches
CMD ["python", "mission_start.py"]
