#!/usr/bin/env bash
set -e  # Exit on first error
set -o pipefail

echo "🚀 Bootstrapping ClaimSight-AI environment..."

# 1. Check prerequisites
command -v docker >/dev/null 2>&1 || { echo >&2 "❌ Docker is not installed. Install Docker Desktop first."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo >&2 "❌ docker-compose is not installed. Install it first."; exit 1; }

# 2. Create .env if missing
if [ ! -f .env ]; then
    echo "📄 Creating .env file..."
    cat <<EOF > .env
# Snowflake
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=CLAIMS
SNOWFLAKE_SCHEMA=PUBLIC

# API
API_HOST=0.0.0.0
API_PORT=8000

# RAG / Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EOF
else
    echo "✅ .env already exists, skipping..."
fi

# 3. Install Python deps locally (optional)
if command -v python3 >/dev/null 2>&1; then
    echo "🐍 Installing Python dependencies..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "⚠️ Python 3 not found, skipping local install."
fi

# 4. Build Docker images
echo "🐳 Building Docker images..."
docker-compose build

# 5. Seed synthetic data
echo "📊 Generating sample data..."
docker-compose run --rm api python scripts/make_synth_data.py
docker-compose run --rm api python scripts/make_fake_policies.py

# 6. Run tests
echo "🧪 Running tests..."
docker-compose run --rm api pytest --maxfail=1 --disable-warnings -q

# 7. Launch stack
echo "🌐 Starting services..."
docker-compose up -d

echo "✅ ClaimSight-AI is ready!"
echo "API available at: http://localhost:8000"
