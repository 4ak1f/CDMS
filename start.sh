#!/bin/bash
set -e
cd ~/Desktop/CDMS

echo "════════════════════════════════════════"
echo "  CDMS — Starting Services"
echo "════════════════════════════════════════"

# ── Kill existing processes ───────────────────────────────────
echo "🧹 Cleaning up old processes..."
pkill -f "uvicorn backend.main" 2>/dev/null || true
pkill -f "ngrok http"           2>/dev/null || true
pkill -f "vite"                 2>/dev/null || true
sleep 1

# ── Backend ───────────────────────────────────────────────────
echo "🔧 Starting backend..."
source venv/bin/activate
python -m uvicorn backend.main:app \
    --host 0.0.0.0 --port 8000 \
    --ssl-keyfile ./key.pem --ssl-certfile ./cert.pem \
    --log-level warning &
BACKEND_PID=$!

# Wait for backend to be healthy (up to 20 retries)
echo "⏳ Waiting for backend..."
for i in $(seq 1 20); do
    if curl -sk https://localhost:8000/stats > /dev/null 2>&1; then
        echo "✅ Backend ready (${i}s)"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "❌ Backend failed to start after 20s"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# ── ngrok ─────────────────────────────────────────────────────
echo "🌐 Starting ngrok tunnel..."
ngrok http https://localhost:8000 --scheme https > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!

NGROK_URL=""
for i in $(seq 1 15); do
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for t in data.get('tunnels', []):
        if t.get('proto') == 'https':
            print(t['public_url'])
            break
except: pass
" 2>/dev/null)
    if [ -n "$NGROK_URL" ]; then
        echo "$NGROK_URL" > /tmp/cdms_ngrok_url.txt
        echo "✅ ngrok ready: $NGROK_URL"
        break
    fi
    sleep 1
done

if [ -z "$NGROK_URL" ]; then
    echo "⚠️  ngrok tunnel not ready — multi-camera will use local URL"
    rm -f /tmp/cdms_ngrok_url.txt
fi

# ── Frontend ──────────────────────────────────────────────────
echo "⚛️  Starting React frontend..."
cd frontend-react && npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!
cd ..

# ── Summary ───────────────────────────────────────────────────
sleep 2
echo ""
echo "════════════════════════════════════════"
echo "  CDMS Running"
echo "  Dashboard: http://localhost:5173"
echo "  Backend:   https://localhost:8000"
if [ -n "$NGROK_URL" ]; then
    echo "  Public:    $NGROK_URL"
    echo ""
    echo "  📱 Camera Demo:"
    echo "  1. Open the Dashboard"
    echo "  2. Go to Multi-Camera panel"
    echo "  3. Click 'Start Camera Session'"
    echo "  4. Scan QR code with your phone"
    echo "     (uses public URL — works on any network)"
else
    echo ""
    echo "  📱 Camera Demo (local network only):"
    echo "  1. Open the Dashboard"
    echo "  2. Go to Multi-Camera panel"
    echo "  3. Click 'Start Camera Session'"
    echo "  4. Copy link and open on phone"
    echo "     (phone must be on same WiFi)"
fi
echo "════════════════════════════════════════"
echo "  Press Ctrl+C to stop all services"
echo "════════════════════════════════════════"

trap "echo ''; echo 'Stopping...'; kill $NGROK_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f /tmp/cdms_ngrok_url.txt; exit 0" INT TERM
wait $BACKEND_PID
