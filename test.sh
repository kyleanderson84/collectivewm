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
WRAPPER_SCRIPT_NAME="collectivewm-session"

# Create log directory
mkdir -p "$LOG_DIR"

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    pkill -f "Xephyr $TEST_DISPLAY" 2>/dev/null || true
    pkill -f "$WM_EXEC_NAME" 2>/dev/null || true
    pkill -f "i3bar" 2>/dev/null || true
}
trap cleanup EXIT

echo "Starting CollectiveWM test with Xephyr..."

# Launch Xephyr with 1024x768 screen
echo "Starting Xephyr on display $TEST_DISPLAY..."
Xephyr -screen 1024x768 $TEST_DISPLAY > "$LOG_DIR/xephyr.log" 2>&1 &
XEPHYR_PID=$!

# Wait for Xephyr to start
sleep 2

# Check if Xephyr is still running
if ! ps -p $XEPHYR_PID > /dev/null 2>&1; then
    echo "Error: Xephyr failed to start properly. Check logs in $LOG_DIR"
    exit 1
fi

# Set DISPLAY to our test display
export DISPLAY=$TEST_DISPLAY

# Start CollectiveWM with proper DISPLAY
echo "Starting CollectiveWM..."
DISPLAY=$TEST_DISPLAY ./$WM_EXEC_NAME > "$LOG_DIR/collectivewm.log" 2>&1 &
WM_PID=$!

# Give CollectiveWM time to initialize
sleep 3

# Verify that CollectiveWM is still running
if ! ps -p $WM_PID > /dev/null 2>&1; then
    echo "Error: CollectiveWM failed to start properly. Check logs in $LOG_DIR"
    exit 1
fi

echo "Test started successfully!"
echo "CollectiveWM PID: $WM_PID"
echo "Xephyr PID: $XEPHYR_PID"
echo ""
echo "Logs are being captured in $LOG_DIR/"
echo "To test dmenu, press Mod+d (usually Super/Windows key + d)"
echo "To test window closing, press Mod+Shift+q (usually Super/Windows key + Shift + q)"
echo "Press Ctrl+C to stop the test"

# Keep the script running
wait
