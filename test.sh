#!/bin/bash

# Test script for CollectiveWM with Xephyr
# This script launches Xephyr, starts CollectiveWM,
# and captures logs for debugging

set -e

# Configuration
LOG_DIR="./test_logs"
TEST_DISPLAY=":99"
WM_NAME="CollectiveWM"
WM_EXEC_NAME="main.py"

# Create log directory
mkdir -p "$LOG_DIR"

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    pkill -f "Xephyr $TEST_DISPLAY" 2>/dev/null || true
    pkill -f "$WM_EXEC_NAME" 2>/dev/null || true
}
trap cleanup EXIT

echo "Starting CollectiveWM test with Xephyr..."

# ==============================================================================
# 1. Launch Xephyr (With Disabled Host-Grab & Disables Access Control)
# ==============================================================================
echo "Starting Xephyr on display $TEST_DISPLAY..."
# Added -ac and -no-host-grab to ensure local clients can connect seamlessly
Xephyr -br -ac -no-host-grab -screen 1024x768 $TEST_DISPLAY > "$LOG_DIR/xephyr.log" 2>&1 &
XEPHYR_PID=$!

# ==============================================================================
# FIX: Dynamic Socket Polling (Eliminates the Race Condition)
# ==============================================================================
sleep 5
echo "Waiting for Xephyr socket to initialize..."

# Strip the leading colon from ":99" to get "99" for the filename
SOCKET_FILE="/tmp/.X11-unix/X${TEST_DISPLAY#:}"
MAX_ATTEMPTS=30
ATTEMPT=0

# Loop until the socket file exists on the filesystem
while [ ! -e "$SOCKET_FILE" ]; do
    sleep 0.1
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
        echo "Error: Xephyr failed to create X11 socket. Check $LOG_DIR/xephyr.log"
        exit 1
    fi
done

echo "Xephyr socket detected! Proceeding..."
# ==============================================================================

# ==============================================================================
# 2. Robust Guard: Wait explicitly for X-Server Socket to exist
#!/bin/bash
# ==============================================================================
# Check if Xephyr process is actually still alive
if ! kill -0 $XEPHYR_PID 2>/dev/null; then
    echo "Error: Xephyr process died immediately after socket creation. Check logs in $LOG_DIR"
    exit 1
fi

# ==============================================================================
# 3. Establish Global Display Scope for all child processes
# ==============================================================================
export DISPLAY=$TEST_DISPLAY

# ==============================================================================
# 4. Start CollectiveWM FIRST to lock down Substructure Interception
# ==============================================================================
echo "Starting CollectiveWM..."
# We use python3 -u to eliminate output buffering inside redirected log targets
python3 -u "./$WM_EXEC_NAME" > "$LOG_DIR/collectivewm.log" 2>&1 &
WM_PID=$!

# Give the Python window manager loop a clean moment to bind to X11 events
sleep 0.5

# Verify that CollectiveWM didn't instantly drop its connection
if ! kill -0 $WM_PID 2>/dev/null; then
    echo "Error: CollectiveWM failed to start properly. Check $LOG_DIR/collectivewm.log"
    exit 1
fi

# Final stabilization wait
sleep 1

echo "Test started successfully!"
echo "CollectiveWM PID: $WM_PID"
echo "Xephyr PID:       $XEPHYR_PID"
echo ""
echo "Logs are being captured in $LOG_DIR/"
echo "Press Ctrl+C to stop the test"

# Keep the script running to allow testing
while true; do
    sleep 1
done
