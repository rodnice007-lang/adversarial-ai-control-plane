# Use a lightweight, secure Python base image
FROM python:3.12-slim

# Set the operational directory inside the virtual container
WORKDIR /app

# Copy all repository contents from your Mac folder into the container filesystem
COPY . /app/

# Automatically run the verification matrix when the container launches
CMD ["python", "mission_start.py"]