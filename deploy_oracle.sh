#!/usr/bin/env bash
set -e

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

echo "=========================================================================="
echo "🚀 Operational Intelligence Platform — Oracle Cloud Deployer"
echo "=========================================================================="

# 1. Update system packages non-interactively
echo "📦 [1/5] Updating system packages..."
sudo DEBIAN_FRONTEND=noninteractive apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get upgrade -y -o Dpkg::Options::="--force-confold"

# 2. Configure Ubuntu iptables firewall
echo "🔓 [2/5] Opening firewall ports (80, 443, 3000, 15672)..."
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 3000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 15672 -j ACCEPT

# Persist rules
echo "iptables-persistent iptables-persistent/autosave_v4 boolean true" | sudo debconf-set-selections
echo "iptables-persistent iptables-persistent/autosave_v6 boolean true" | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
sudo netfilter-persistent save

# 3. Install Docker & Docker Compose
echo "🐳 [3/5] Installing Docker & Docker Compose..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates gnupg lsb-release docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker $USER || true

# 4. Clone or pull repo
echo "📥 [4/5] Checking out repository..."
if [ ! -d "operational-intelligence-platform" ] && [ ! -f "docker-compose.yml" ]; then
    git clone https://github.com/adhish1478/operational-intelligence-platform.git
    cd operational-intelligence-platform
fi

# 5. Create backend/.env if missing
echo "📝 [5/5] Checking environment configuration..."
if [ ! -f "backend/.env" ]; then
    cat << 'EOF' > backend/.env
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=super-secret-key-change-in-production

# Replace with your actual OpenAI API Key for DAG Multi-Agent Forensics
OPENAI_API_KEY=sk-proj-your-key-here

POSTGRES_USER=postgres
POSTGRES_PASSWORD=securepassword
POSTGRES_DB=oip_db
MONGO_URI=mongodb://mongodb:27017
MONGO_DB_NAME=evidence_store
RABBITMQ_USER=guest
RABBITMQ_PASS=guest
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
EOF
    echo "⚠️  Created backend/.env — please update OPENAI_API_KEY with your actual API key!"
fi

echo "=========================================================================="
echo "✅ Setup script completed successfully!"
echo "--------------------------------------------------------------------------"
echo "To start all 9 containers now, run:"
echo "   sg docker -c 'docker compose up -d --build'"
echo "=========================================================================="
