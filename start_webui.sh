#!/bin/bash
# Bus Display Web UI Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚌 Starting Bus Display Web UI..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Install web UI dependencies if needed
echo "📦 Installing web UI dependencies..."
pip install -q -r webui_requirements.txt

# Ensure config directory exists
mkdir -p ~/.config/busdisplay

# Check if main config exists, create minimal one if not
CONFIG_FILE="$HOME/.config/busdisplay/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚙️  Creating default configuration..."
    cat > "$CONFIG_FILE" << 'EOF'
{
  "stops": [],
  "max_departures": 8,
  "fetch_interval": 60,
  "max_minutes": 120,
  "show_clock": true,
  "show_weather": true,
  "http_timeout": 10
}
EOF
fi

echo "🌐 Starting web interface..."
echo "📱 Access the configuration at: http://localhost:5000"
echo "🔧 Use this interface to configure your bus display"
echo ""
echo "Press Ctrl+C to stop the web interface"
echo ""

# Start the web UI
python webui.py