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
        print(f"CollectiveWM initialized on screen size: {self.screen.width_in_pixels}x{self.screen.height_in_pixels}")
        
        # Track managed windows
        self.windows = []
        self.current_window_count = 0

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
        
        # Calculate window sizes
        window_width = width // 2
        window_height = height
        
        # Position windows side by side
        for i, window_id in enumerate(self.windows):
            x_pos = i * window_width
            y_pos = 0
            
            # Configure window position and size
            self.conn.core.ConfigureWindow(
                window=window_id,
                value_mask=xproto.ConfigWindow.X | xproto.ConfigWindow.Y | xproto.ConfigWindow.Width | xproto.ConfigWindow.Height,
                value_list=[x_pos, y_pos, window_width, window_height]
            )
            
            # Raise window to top
            self.conn.core.RaiseWindow(window=window_id)
            
        self.conn.flush()

    def set_fullscreen(self, window_id):
        """Set a window to fullscreen"""
        width = self.screen.width_in_pixels
        height = self.screen.height_in_pixels
        
        self.conn.core.ConfigureWindow(
            window=window_id,
            value_mask=xproto.ConfigWindow.X | xproto.ConfigWindow.Y | xproto.ConfigWindow.Width | xproto.ConfigWindow.Height,
            value_list=[0, 0, width, height]
        )
        
        # Raise window to top
        self.conn.core.RaiseWindow(window=window_id)
        self.conn.flush()

    def run(self):
        # This is where your main X event loop will live
        print("Starting the collective event loop...")
        try:
            while True:
                # Wait for events sent by the X server (keystrokes, new windows, mouse clicks)
                event = self.conn.wait_for_event()
                if event:
                    # Handle different types of events
                    if isinstance(event, xproto.CreateNotifyEvent):
                        # New window created
                        self.handle_new_window(event.window)
                    elif isinstance(event, xproto.MapRequestEvent):
                        # Window mapping request
                        self.conn.core.MapWindow(window=event.window)
                    # Add more event handlers as needed
        except (KeyboardInterrupt, SystemExit):
            print("\nShutting down CollectiveWM. Power to the users.")
        finally:
            self.conn.disconnect()

if __name__ == "__main__":
    wm = CollectiveWM()
    wm.run()
