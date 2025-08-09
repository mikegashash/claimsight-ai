FROM python:3.11-slim
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy API code
COPY . .

# Also copy RAG code into the image (relative to repo root via compose bind)
# In docker-compose we mount the repo as volume, but this ensures it builds standalone too.
# If running via compose with volumes, this line is optional.

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
