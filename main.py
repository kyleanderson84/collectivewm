#!/usr/bin/env python3
import sys
import xcffib
from xcffib import xproto

class CollectiveWM:
    def __init__(self):
        # Connect to the X server (uses $DISPLAY environment variable automatically)
        try:
            self.conn = xcffib.connect()
        except xcffib.ConnectionException:
            print("Error: Could not connect to the X server. Is X running?", file=sys.stderr)
            sys.exit(1)
            
        # Get the setup data and the primary screen
        self.setup = self.conn.get_setup()
        self.screen = self.setup.roots[0]
        self.root = self.screen.root  # Reference to the root window
        print(f"CollectiveWM initialized on screen size: {self.screen.width_in_pixels}x{self.screen.height_in_pixels}")
        
        # Track managed windows
        self.windows = []
        self.current_window_count = 0

        # Become the Window Manager by subbing to SubstructureRedirect
        try:
            mask = xproto.EventMask.SubstructureRedirect | xproto.EventMask.SubstructureNotify
            self.conn.core.ChangeWindowAttributes(self.root, xproto.CW.EventMask, [mask])
            self.conn.flush()
        except xcffib.AccessError:
            print("Error: Another window manager is already running.", file=sys.stderr)
            sys.exit(1)

    def handle_new_window(self, window_id):
        """Handle a new window being created"""
        print(f"New window created: {window_id}")
        
        # Configure the window to be managed
        self.conn.core.ChangeWindowAttributes(
            window=window_id,
            value_mask=xproto.CW.EventMask,
            value_list=[xproto.EventMask.SubstructureNotify | xproto.EventMask.StructureNotify]
        )
        
        # Store the window
        self.windows.append(window_id)
        self.current_window_count += 1
        
        # Split screen vertically if we have more than one window
        if self.current_window_count > 1:
            self.split_screen_vertically()
        else:
            # For the first window, make it full screen
            self.set_fullscreen(window_id)

    def split_screen_vertically(self):
        """Split the screen vertically and assign windows"""
        width = self.screen.width_in_pixels
        height = self.screen.height_in_pixels
        
        # Calculate window sizes - split screen equally among all windows
        window_width = width // self.current_window_count
        window_height = height
        
        # Position windows side by side
        for i, window_id in enumerate(self.windows):
            x_pos = i * window_width
            y_pos = 0
            
            # Configure window position, size, AND bring it to the top (Above)
            self.conn.core.ConfigureWindow(
                window=window_id,
                value_mask=(
                    xproto.ConfigWindow.X | 
                    xproto.ConfigWindow.Y | 
                    xproto.ConfigWindow.Width | 
                    xproto.ConfigWindow.Height |
                    xproto.ConfigWindow.StackMode
                ),
                value_list=[x_pos, y_pos, window_width, window_height, xproto.StackMode.Above]
            )
            
        self.conn.flush()

    def set_fullscreen(self, window_id):
        """Set a window to fullscreen"""
        width = self.screen.width_in_pixels
        height = self.screen.height_in_pixels
        
        # Configure window size and restack it above others
        self.conn.core.ConfigureWindow(
            window=window_id,
            value_mask=(
                xproto.ConfigWindow.X | 
                xproto.ConfigWindow.Y | 
                xproto.ConfigWindow.Width | 
                xproto.ConfigWindow.Height |
                xproto.ConfigWindow.StackMode
            ),
            value_list=[0, 0, width, height, xproto.StackMode.Above]
        )
        
        self.conn.flush()

    def close_focused_window(self):
        """Close the currently focused window"""
        if not self.windows:
            return
            
        # Get the currently focused window (last window in list for simplicity)
        # In a real implementation, you'd track focus more accurately
        focused_window = self.windows[-1] if self.windows else None
        
        if focused_window:
            # Send a delete window request to close the window gracefully
            self.conn.core.DeleteWindow(focused_window)
            self.conn.flush()
            
            # Remove from our tracking
            if focused_window in self.windows:
                self.windows.remove(focused_window)
                self.current_window_count -= 1
                
                # Re-layout remaining windows
                if self.current_window_count > 0:
                    self.split_screen_vertically()
                else:
                    # If no windows left, make the first window fullscreen again
                    if self.windows:
                        self.set_fullscreen(self.windows[0])

    def run(self):
        # This is where your main X event loop will live
        print("Starting the collective event loop...")
        try:
            while True:
                # Wait for events sent by the X server (keystrokes, new windows, mouse clicks)
                event = self.conn.wait_for_event()
                
                # Handle key press events for window closing
                if isinstance(event, xproto.KeyPressEvent):
                    # Check for Mod+Shift+q combination
                    # Note: This is a simplified implementation - in practice you'd need to 
                    # properly detect modifier keys (Mod1, Mod4, etc.)
                    if event.detail == 24:  # Q key (keycode 24)
                        # This is a placeholder - in a real implementation you'd check modifiers
                        self.close_focused_window()
                
                # Use MapRequest instead of CreateNotify for tiling
                if isinstance(event, xproto.MapRequestEvent):
                    wid = event.window
                    
                    # Only manage the window if we aren't already
                    if wid not in self.windows:
                        # 1. Map the window so it's visible
                        self.conn.core.MapWindow(wid)
                        # 2. Add to our collective and trigger the layout
                        self.handle_new_window(wid)
                        
                elif isinstance(event, xproto.UnmapNotifyEvent):
                    # Handle windows closing so the layout shrinks back
                    if event.window in self.windows:
                        self.windows.remove(event.window)
                        self.current_window_count -= 1
                        if self.current_window_count > 0:
                            self.split_screen_vertically()
                        else:
                            # If no windows left, make the first window fullscreen again
                            if self.windows:
                                self.set_fullscreen(self.windows[0])

        except (KeyboardInterrupt, SystemExit):
            print("\nShutting down CollectiveWM. Power to the users.")
        finally:
            self.conn.disconnect()

if __name__ == "__main__":
    wm = CollectiveWM()
    wm.run()
