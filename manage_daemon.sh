#!/bin/bash

# manage_daemon.sh - Utility to install and manage the VisionSight daemon

# Ensure correct base path
PROJECT_DIR="/Users/rishishah/Study/Project/VisionSight"
PLIST_NAME="com.visionsight.daemon.plist"
PLIST_SRC="$PROJECT_DIR/$PLIST_NAME"
PLIST_TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"

case "$1" in
    install)
        echo "Installing VisionSight daemon to LaunchAgents..."
        
        # Make the runner executable
        chmod +x "$PROJECT_DIR/run_daemon.sh"
        
        # Ensure logs dir exists
        mkdir -p "$PROJECT_DIR/logs"
        touch "$PROJECT_DIR/logs/daemon.log" "$PROJECT_DIR/logs/daemon.err"
        
        # Copy plist
        mkdir -p "$HOME/Library/LaunchAgents"
        cp "$PLIST_SRC" "$PLIST_TARGET"
        
        # Load into launchd
        echo "Loading daemon into launchctl..."
        launchctl load "$PLIST_TARGET"
        
        # Start immediately
        launchctl start com.visionsight.daemon
        
        echo "✅ Installed and started!"
        echo "View logs with: ./manage_daemon.sh logs"
        ;;
        
    uninstall)
        echo "Unpacking from LaunchAgents..."
        
        # Stop and unload
        launchctl stop com.visionsight.daemon
        launchctl unload "$PLIST_TARGET" 2>/dev/null
        
        # Remove original plist
        rm -f "$PLIST_TARGET"
        
        echo "✅ Uninstalled!"
        ;;
        
    start)
        echo "Starting daemon..."
        launchctl start com.visionsight.daemon
        echo "✅ Started!"
        ;;
        
    stop)
        echo "Stopping daemon..."
        launchctl stop com.visionsight.daemon
        echo "✅ Stopped!"
        ;;
        
    status)
        echo "Checking daemon status..."
        STATUS=$(launchctl list | grep com.visionsight.daemon)
        if [ -n "$STATUS" ]; then
            echo "🟢 Running: $STATUS"
        else
            echo "🔴 Not running (or not installed)."
        fi
        ;;
        
    logs)
        echo "Tailing daemon logs (Ctrl+C to exit)..."
        tail -f "$PROJECT_DIR/logs/daemon.log" "$PROJECT_DIR/logs/daemon.err"
        ;;
        
    reload)
        echo "Reloading daemon..."
        launchctl unload "$PLIST_TARGET" 2>/dev/null
        launchctl load "$PLIST_TARGET"
        launchctl start com.visionsight.daemon
        echo "✅ Reloaded!"
        ;;
        
    *)
        echo "Usage: ./manage_daemon.sh {install|uninstall|start|stop|reload|status|logs}"
        exit 1
        ;;
esac
