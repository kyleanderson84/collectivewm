#!/usr/bin/env python3
import os
import sys
import shutil
from pathlib import Path

# Configuration
WM_NAME = "CollectiveWM"
WM_EXEC_NAME = "collectivewm"  # The name of your main executable/script
TARGET_BIN_DIR = Path("/usr/local/bin")
XSESSION_DIR = Path("/usr/share/xsessions")
WRAPPER_SCRIPT_NAME = "collectivewm-session"

def check_root():
    """Ensure the script is run with sudo/root privileges."""
    if os.geteuid() != 0:
        print(f"Error: This install script requires root privileges to write to {XSESSION_DIR}.", file=sys.stderr)
        print("Please run with: sudo python3 install.py", file=sys.stderr)
        sys.exit(1)

def create_wrapper_script():
    """Creates a wrapper script that starts CollectiveWM with dmenu and i3bar."""
    wrapper_content = f"""#!/bin/bash
# CollectiveWM session launcher with dmenu and i3bar

# Start i3bar in the background
i3bar &

# Start dmenu for application launching
dmenu_run &

# Start CollectiveWM
{TARGET_BIN_DIR}/{WM_EXEC_NAME}
"""
    
    wrapper_path = TARGET_BIN_DIR / WRAPPER_SCRIPT_NAME
    
    print(f"Creating wrapper script at: {wrapper_path}")
    try:
        wrapper_path.write_text(wrapper_content)
        wrapper_path.chmod(0o755)  # rwxr-xr-x
        return wrapper_path
    except Exception as e:
        print(f"Failed to create wrapper script: {e}", file=sys.stderr)
        sys.exit(1)

def create_desktop_entry(exec_path):
    """Generates the XSession .desktop entry so the WM appears at login."""
    desktop_content = f"""[Desktop Entry]
Name={WM_NAME}
Comment=A custom Python-based tiling window manager using xcffib
Exec={exec_path}
Type=Application
DesktopNames={WM_NAME}
"""
    session_file = XSESSION_DIR / f"{WM_EXEC_NAME}.desktop"
    
    print(f"Creating XSession entry at: {session_file}")
    try:
        session_file.write_text(desktop_content)
        session_file.chmod(0o644)
    except Exception as e:
        print(f"Failed to write desktop session file: {e}", file=sys.stderr)
        sys.exit(1)

def install_binary():
    """Finds the main entry point, copies it to /usr/local/bin, and makes it executable."""
    # Assumes your entry script is in the same directory as install.py
    current_dir = Path(__file__).parent.resolve()
    source_exec = current_dir / WM_EXEC_NAME
    
    # Fallback/Check if it's named something like main.py instead
    if not source_exec.exists():
        if (current_dir / "main.py").exists():
            source_exec = current_dir / "main.py"
        else:
            print(f"Error: Could not find executable source file (expected {WM_EXEC_NAME} or main.py)", file=sys.stderr)
            sys.exit(1)

    target_exec = TARGET_BIN_DIR / WM_EXEC_NAME
    
    print(f"Copying executable to {target_exec}...")
    try:
        shutil.copy2(source_exec, target_exec)
        target_exec.chmod(0o755)  # rwxr-xr-x
        return target_exec
    except Exception as e:
        print(f"Failed to install executable binary: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    check_root()
    
    # Ensure directories exist
    TARGET_BIN_DIR.mkdir(parents=True, exist_ok=True)
    XSESSION_DIR.mkdir(parents=True, exist_ok=True)
    
    # Run installation steps
    installed_path = install_binary()
    create_wrapper_script()
    create_desktop_entry(f"{TARGET_BIN_DIR}/{WRAPPER_SCRIPT_NAME}")
    
    print(f"\nSuccessfully installed {WM_NAME}!")
    print("Log out or restart your display manager to see it in your login options.")

if __name__ == "__main__":
    main()
