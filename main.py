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
        self.root = self.screen.root
        print(f"CollectiveWM initialized on screen size: {self.screen.width_in_pixels}x{self.screen.height_in_pixels}")
        
        # Intercept window management requests on the root window
        mask = xproto.EventMask.SubstructureRedirect | xproto.EventMask.SubstructureNotify
        self.conn.core.ChangeWindowAttributes(self.root, xproto.CW.EventMask, [mask])
        
        # Cache atoms for checking window types (e.g., bars/dmenus)
        self.net_wm_window_type = self.get_atom("_NET_WM_WINDOW_TYPE")
        self.net_wm_window_type_dock = self.get_atom("_NET_WM_WINDOW_TYPE_DOCK")
        
        # Track managed windows
        self.windows = []
        self.current_window_count = 0
        self.conn.flush()

    def get_atom(self, name):
        """Helper to get or create an X11 Atom string identifier"""
        cookie = self.conn.core.InternAtom(False, len(name), name)
        return cookie.reply().atom

    def is_dock(self, window_id):
        """Check if a window is a status bar/dock (like i3bar)"""
        try:
            cookie = self.conn.core.GetProperty(
                False, window_id, self.net_wm_window_type, 
                xproto.Atom.ATOM, 0, 1024
            )
            reply = cookie.reply()
            if reply.value_len > 0:
                # Read the array of atoms returned in the property value
                value = reply.value.to_atoms()
                if self.net_wm_window_type_dock in value:
                    return True
        except Exception:
            pass
        return False

    def handle_new_window(self, window_id):
        """Handle a new window being created"""
        # Skip if it's a status bar or dock panel so it doesn't break the tiling grid
        if self.is_dock(window_id):
            print(f"Window {window_id} is a dock/bar. Allowing to map freely.")
            self.conn.core.MapWindow(window_id)
            self.conn.flush()
            return

        print(f"New window added to collective: {window_id}")
        
        # Configure the window to be monitored for crashes/unmaps
        self.conn.core.ChangeWindowAttributes(
            window=window_id,
            value_mask=xproto.CW.EventMask,
            value_list=[xproto.EventMask.StructureNotify]
        )
        
        # Store the window
        self.windows.append(window_id)
        self.current_window_count += 1
        
        # Map the window to the screen explicitly
        self.conn.core.MapWindow(window_id)
        
        # Re-tile current workspace layout
        if self.current_window_count > 1:
            self.split_screen_vertically()
        else:
            self.set_fullscreen(window_id)

    def split_screen_vertically(self):
        """Split the screen vertically and assign windows"""
        width = self.screen.width_in_pixels
        height = self.screen.height_in_pixels
        
        # Simple split layout math
        window_width = width // self.current_window_count
        window_height = height
        
        for i, window_id in enumerate(self.windows):
            x_pos = i * window_width
            y_pos = 0
            
            # Configure window position, size, and stack to top using XCB syntax
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

    def open_dmenu(self):
        """Open dmenu application launcher"""
        import subprocess
        try:
            # Start dmenu in the background
            subprocess.Popen(["dmenu_run"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("dmenu launched")
        except FileNotFoundError:
            print("Error: dmenu not found. Please install dmenu to use this feature.")
        except Exception as e:
            print(f"Error launching dmenu: {e}")

    def run(self):
        print("Starting the collective event loop...")
        try:
            while True:
                event = self.conn.wait_for_event()
                if event:
                    # MapRequestEvent is triggered when a client application wants to display its window
                    if isinstance(event, xproto.MapRequestEvent):
                        if event.window not in self.windows:
                            self.handle_new_window(event.window)
                    
                    # Track when windows close so we can adjust layout
                    elif isinstance(event, xproto.UnmapNotifyEvent):
                        if event.window in self.windows:
                            self.windows.remove(event.window)
                            self.current_window_count -= 1
                            if self.current_window_count > 0:
                                self.split_screen_vertically()
                    
                    # Handle key press events for window management
                    elif isinstance(event, xproto.KeyPressEvent):
                        # Check for Mod+Shift+q combination (close window)
                        if event.detail == 24:  # Q key (keycode 24)
                            # Check if Mod4 (Super/Windows) and Shift are pressed
                            # Mod4 = 0x40, Shift = 0x1
                            if event.state & 0x41 == 0x41:  # Mod4 + Shift
                                self.close_focused_window()
                            # Check if just Mod4 (Super/Windows) is pressed for dmenu
                            elif event.state & 0x40 == 0x40:  # Just Mod4
                                self.open_dmenu()
                                
        except (KeyboardInterrupt, SystemExit):
            print("\nShutting down CollectiveWM. Power to the users.")
        finally:
            self.conn.disconnect()

if __name__ == "__main__":
    wm = CollectiveWM()
    wm.run()
