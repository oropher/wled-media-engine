FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema necesarias para ffmpeg u otros servicios
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copia solo requirements para aprovechar cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Montaje del código en volumen se hace en docker-compose
# COPY app ./app  # ya no necesario para desarrollo

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
