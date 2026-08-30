FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY control_plane/ ./control_plane/

EXPOSE 8443
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8443"]

fix: copy control_plane package into image so main.py's import resolves
