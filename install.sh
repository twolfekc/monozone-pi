#!/bin/bash
# MonoZone Pi Controller Installation Script

set -e

echo "=== MonoZone Pi Controller Setup ==="

# Update system
echo "Updating system packages..."
sudo apt update

# Install Python and pip if needed
echo "Installing Python dependencies..."
sudo apt install -y python3-pip python3-venv

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Created .env with default settings (iTach IP: 192.168.1.70)"
fi

# Install systemd service
echo "Installing systemd service..."
sudo cp monozone.service /etc/systemd/system/
sudo systemctl daemon-reload

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit .env with your iTach IP address"
echo "2. Start the service: sudo systemctl start monozone"
echo "3. Enable on boot: sudo systemctl enable monozone"
echo "4. Check status: sudo systemctl status monozone"
echo "5. View logs: journalctl -u monozone -f"
echo ""
echo "API will be available at http://$(hostname -I | awk '{print $1}'):8080"
