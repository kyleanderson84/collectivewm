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
    pkill -f "i3bar" 2>/dev/null || true
    pkill -f "dmenu" 2>/dev/null || true
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

# ==============================================================================
# 1. Start CollectiveWM FIRST to lock down Substructure Interception
# ==============================================================================
echo "Starting CollectiveWM..."
# We use python3 -u to eliminate output buffering inside redirected log targets
DISPLAY=$TEST_DISPLAY python3 -u ./$WM_EXEC_NAME > "$LOG_DIR/collectivewm.log" 2>&1 &
WM_PID=$!

# Give the Python window manager loop a clean second to bind to X11
sleep 1

# ==============================================================================
# 2. Spawn Associated Desktop Tools Into the Active WM Environment
# ==============================================================================
echo "Starting i3bar..."
DISPLAY=$TEST_DISPLAY i3bar > "$LOG_DIR/i3bar.log" 2>&1 &
IBAR_PID=$!

echo "Starting dmenu..."
# Use an open standard input frame path so dmenu doesn't immediately exit
DISPLAY=$TEST_DISPLAY dmenu -p "The Collective:" < /dev/null > "$LOG_DIR/dmenu.log" 2>&1 &
DMENU_PID=$!

# Give everything final initialization time
sleep 2

# Verify that primary environments are still running
if ! ps -p $WM_PID > /dev/null 2>&1; then
    echo "Error: CollectiveWM failed to start properly. Check logs in $LOG_DIR"
    exit 1
fi

echo "Test started successfully!"
echo "CollectiveWM PID: $WM_PID"
echo "Xephyr PID: $XEPHYR_PID"
echo ""
echo "Logs are being captured in $LOG_DIR/"
echo "Press Ctrl+C to stop the test"

# Keep the script running to allow testing
while true; do
    sleep 1
done
