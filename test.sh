#!/bin/bash

# Test script for CollectiveWM with Xephyr
# This script launches Xephyr, starts CollectiveWM with dmenu and i3bar,
# and captures logs for debugging

set -e

# Configuration
LOG_DIR="./test_logs"
TEST_DISPLAY=":99"
WM_NAME="CollectiveWM"
WM_EXEC_NAME="collectivewm"
WRAPPER_SCRIPT_NAME="collectivewm-session"

# Create log directory
mkdir -p "$LOG_DIR"

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    pkill -f "Xephyr $TEST_DISPLAY" 2>/dev/null || true
    pkill -f "$WM_EXEC_NAME" 2>/dev/null || true
    pkill -f "dmenu" 2>/dev/null || true
    pkill -f "i3bar" 2>/dev/null || true
    rm -rf "$LOG_DIR"
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

# Start CollectiveWM with dmenu and i3bar
echo "Starting CollectiveWM with dmenu and i3bar..."
echo "Logging to $LOG_DIR"

# Start i3bar in background with proper DISPLAY
echo "Starting i3bar..."
DISPLAY=$TEST_DISPLAY i3bar > "$LOG_DIR/i3bar.log" 2>&1 &
IBAR_PID=$!

# Start dmenu in background with proper DISPLAY  
echo "Starting dmenu..."
DISPLAY=$TEST_DISPLAY dmenu_run > "$LOG_DIR/dmenu.log" 2>&1 &
DMENU_PID=$!

# Start CollectiveWM with proper DISPLAY
echo "Starting CollectiveWM..."
DISPLAY=$TEST_DISPLAY ./$WM_EXEC_NAME > "$LOG_DIR/collectivewm.log" 2>&1 &
WM_PID=$!

# Give everything time to initialize
sleep 3

# Verify that all processes are still running
if ! ps -p $WM_PID > /dev/null 2>&1; then
    echo "Error: CollectiveWM failed to start properly. Check logs in $LOG_DIR"
    exit 1
fi

if ! ps -p $IBAR_PID > /dev/null 2>&1; then
    echo "Error: i3bar failed to start properly. Check logs in $LOG_DIR"
    exit 1
fi

if ! ps -p $DMENU_PID > /dev/null 2>&1; then
    echo "Error: dmenu failed to start properly. Check logs in $LOG_DIR"
    exit 1
fi

echo "Test started successfully!"
echo "CollectiveWM PID: $WM_PID"
echo "i3bar PID: $IBAR_PID"
echo "dmenu PID: $DMENU_PID"
echo "Xephyr PID: $XEPHYR_PID"
echo ""
echo "Logs are being captured in $LOG_DIR/"
echo "Press Ctrl+C to stop the test"

# Keep the script running
wait
