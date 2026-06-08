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
        
        # Intercept window management mapping requests on the root window
        mask = xproto.EventMask.SubstructureRedirect | xproto.EventMask.SubstructureNotify
        self.conn.core.ChangeWindowAttributes(self.root, xproto.CW.EventMask, [mask])
        
        # Cache atoms for checking window types (e.g., status bars)
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
            print(f"Window {window_id} is a dock/bar. Mapping freely.")
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
        
        # Split screen vertically if we have more than one window
        if self.current_window_count > 1:
            self.split_screen_vertically()
        else:
            self.set_fullscreen(window_id)

    def split_screen_vertically(self):
        """Split the screen vertically and assign windows"""
        width = self.screen.width_in_pixels
        height = self.screen.height_in_pixels
        
        # Simple dynamic dynamic split layout math
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

    def run(self):
        print("Starting the collective event loop...")
        try:
            while True:
                event = self.conn.wait_for_event()
                if event:
                    # MapRequestEvent is triggered when an application wants to open its window
                    if isinstance(event, xproto.MapRequestEvent):
                        if event.window not in self.windows:
                            self.handle_new_window(event.window)
                    
                    # Track when windows close so we can recalculate layouts
                    elif isinstance(event, xproto.UnmapNotifyEvent):
                        if event.window in self.windows:
                            self.windows.remove(event.window)
                            self.current_window_count -= 1
                            if self.current_window_count > 0:
                                self.split_screen_vertically()
                                
        except (KeyboardInterrupt, SystemExit):
            print("\nShutting down CollectiveWM. Power to the users.")
        finally:
            self.conn.disconnect()

if __name__ == "__main__":
    wm = CollectiveWM()
    wm.run()
