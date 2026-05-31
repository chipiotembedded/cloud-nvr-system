#!/bin/bash
# install.sh — set up the AI module on the GCP VM.
# Run as the `cloud` user (NOT root). Will sudo where needed.
set -e

NVR_ROOT=/home/cloud/cloud-nvr-system
AI_DIR=$NVR_ROOT/ai
TEMPLATES=$NVR_ROOT/templates

echo "=== NVR AI install ==="

# 1. Sanity check
if [ ! -d "$NVR_ROOT" ]; then
    echo "ERROR: $NVR_ROOT not found. Run this on the cloud-server-1 VM."
    exit 1
fi
if [ ! -d "$AI_DIR" ]; then
    echo "ERROR: $AI_DIR not found. Copy the ai/ folder there first."
    exit 1
fi

# 2. System packages
echo ">>> Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-venv \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 ffmpeg

# 3. Python packages (system-wide; matches your existing Flask setup)
echo ">>> Installing Python packages (this downloads PyTorch CPU ~200MB, takes a while)..."
sudo pip3 install --break-system-packages -r "$AI_DIR/requirements.txt"

# 4. Pre-download YOLOv8n weights so first run doesn't need internet
echo ">>> Pre-downloading YOLOv8n weights..."
cd "$AI_DIR"
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 5. Storage dirs
echo ">>> Creating storage directories..."
sudo mkdir -p /var/www/ai/snapshots
sudo chown -R cloud:cloud /var/www/ai
sudo chmod -R 755 /var/www/ai

# 6. Move dashboard template into place
echo ">>> Installing dashboard template..."
cp "$AI_DIR/ai_dashboard.html" "$TEMPLATES/ai_dashboard.html"

# 7. Initialise SQLite database
echo ">>> Initialising alerts database..."
python3 -c "
import sys; sys.path.insert(0, '$AI_DIR')
from alerts import init_db
init_db('/var/www/ai/alerts.db')
print('  db ready at /var/www/ai/alerts.db')
"

# 8. Install systemd service
echo ">>> Installing systemd service..."
sudo cp "$AI_DIR/nvr-ai.service" /etc/systemd/system/nvr-ai.service
sudo systemctl daemon-reload
sudo systemctl enable nvr-ai.service

# 9. Reminder for Flask wire-up
echo ""
echo "=== Install done. ==="
echo ""
echo "MANUAL STEP — wire the dashboard into your existing Flask server."
echo "Edit /home/cloud/cloud-nvr-system/server/playback_server.py and"
echo "add these 3 lines near the top (after 'app = Flask(...)'):"
echo ""
echo "    import sys"
echo "    sys.path.insert(0, '/home/cloud/cloud-nvr-system/ai')"
echo "    from ai_routes import ai_bp"
echo "    app.register_blueprint(ai_bp)"
echo ""
echo "Then:"
echo "    1. Run zone calibration:    python3 $AI_DIR/calibrate.py"
echo "    2. Edit zone coords in:     $AI_DIR/config.yaml"
echo "    3. Restart Flask:           sudo systemctl restart nvr-playback"
echo "    4. Start the detector:      sudo systemctl start nvr-ai"
echo "    5. Tail the log:            tail -f /home/cloud/ai_detector.log"
echo "    6. Open the dashboard:      http://34.93.38.200:5000/ai"
echo ""
