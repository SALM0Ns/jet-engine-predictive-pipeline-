FROM python:3.11-slim
WORKDIR /app

# Install dependencies before copying source for better Docker layer caching.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-u", "main.py"]
