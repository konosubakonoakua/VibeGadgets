import os
import csv
import json
import os
import tempfile
import platform
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from fuzzywuzzy import fuzz, process


class FileTab:
    """Class to represent each file tab with its own data and UI components"""
    def __init__(self, parent, notebook, tab_name):
        self.parent = parent
        self.notebook = notebook
        self.tab_frame = ttk.Frame(notebook)
        self.filename = ""
        self.data = []
        self.headers = [
            "node_name",
            "local_ip",
            "cluster",
            "remote_ip",
            "connect_to_nodes",
            "node_type",
            "data_save_switch",
        ]
        self.tab_name = tab_name
        self.modified = False

        self.sort_column = None
        self.sort_direction = True
        
        # Initialize lazy loading properties
        self.is_large_file = False
        self.file_size_threshold = 10 * 1024 * 1024  # Default 10MB threshold
        self.total_rows = 0
        self.loaded_chunks = {}
        self.chunk_size = 100000  # Load 100000 rows per chunk
        self.currently_visible_range = (0, 0)
        
        # Default template data
        self.template = {
            "node_name": "none",
            "local_ip": "192.168.138.138",
            "cluster": "cluster_huizhou",
            "remote_ip": "none",
            "connect_to_nodes": "none",
            "node_type": "compute",
            "data_save_switch": "off",
        }
        
        # Format templates for different file types
        self.format_templates = {
            # PV (Process Variable) format template
            "pv": {
                "node_name": "",
                "pv_name": "",
                "pv_type": "c",
                "cv_name": "",
                "action": "publish",
                "is_readonly": "1",
                "pv_length": "512000",
                "pv_scan_period": "2",
                "precision": "12",
                "unit": "none"
            },
            # Command format template
            "command": {
                "node_name": "",
                "command_name": "",
                "module": "control",
                "command": "call",
                "parameters": "",
                "input_cvs": "none",
                "output_cvs": "none",
                "is_sync": "1",
                "is_check": "1"
            },
            # CV (Control Variable) format template
            "cv": {
                "node_name": "",
                "cv_name": "",
                "cv_type": "d",
                "cv_max_length": "1",
                "set_events": "none",
                "sync_events": "none",
                "update_events": "none",
                "update_period": "-1",
                "cv_code_type": "0"
            },
            # Event format template
            "event": {
                "node_name": "",
                "event_name": "",
                "commands": "",
                "is_lock": "0"
            },
            # Ion format template
            "ion": {
                "ion_name": "",
                "ion_mass_num": "",
                "ion_proton_num": "",
                "ion_charge_num": "1",
                "mass_in_MeV": ""
            }
        }
        
    def load_data(self):
        """Load data file with lazy loading support"""
        try:
            # Initialize lazy loading properties
            # Use the threshold from parent TableManager instance
            self.file_size_threshold = self.parent.lazy_load_threshold * 1024 * 1024
            
            # Check file size to determine if lazy loading is needed
            file_size = os.path.getsize(self.filename)
            if file_size > self.file_size_threshold:
                self.is_large_file = True
                
                # Just read headers and count total rows without loading all data
                with open(self.filename, "r") as f:
                    reader = csv.reader(f, delimiter="\t")
                    # First row is always treated as headers
                    self.headers = next(reader)
                    
                    # Count total rows
                    for _ in reader:
                        self.total_rows += 1
                        
                    # Detect file format based on headers
                    self.detect_format_and_set_template()
                
                messagebox.showinfo("Info", f"Loading large file: {self.filename}\n" \
                                   f"Size: {file_size/1024/1024:.2f}MB, Total rows: {self.total_rows}\n" \
                                   f"Using lazy loading to improve performance.")
            else:
                # For small files, load all data as before
                with open(self.filename, "r") as f:
                    reader = csv.reader(f, delimiter="\t")
                    # First row is always treated as headers
                    self.headers = next(reader)
                    
                    # Read all remaining rows as data
                    self.data = [row for row in reader if row]  # Filter empty rows
                    self.total_rows = len(self.data)
                    
                    # Detect file format and set appropriate template
                    self.detect_format_and_set_template()
        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {self.filename}")
            self.data = []
            self.total_rows = 0
        except Exception as e:
            messagebox.showerror("Error", f"Error loading file: {str(e)}")
            self.data = []
            self.total_rows = 0
    
    def load_chunk(self, start_row, end_row):
        """Load a specific chunk of the file"""
        if not self.is_large_file:
            return self.data[start_row:end_row] if start_row < len(self.data) else []
        
        # Calculate chunk key
        chunk_start = (start_row // self.chunk_size) * self.chunk_size
        chunk_end = chunk_start + self.chunk_size - 1
        chunk_key = (chunk_start, chunk_end)
        
        # Check if chunk is already loaded
        if chunk_key in self.loaded_chunks:
            # Return the requested portion from the loaded chunk
            chunk_offset_start = start_row - chunk_start
            chunk_offset_end = end_row - chunk_start
            return self.loaded_chunks[chunk_key][chunk_offset_start:chunk_offset_end]
        
        # Load the chunk from file
        try:
            chunk_data = []
            with open(self.filename, "r") as f:
                reader = csv.reader(f, delimiter="\t")
                # Skip header
                next(reader)
                
                # Skip rows until chunk start
                for _ in range(chunk_start):
                    try:
                        next(reader)
                    except StopIteration:
                        break
                
                # Read chunk_size rows
                for _ in range(self.chunk_size):
                    try:
                        row = next(reader)
                        if row:  # Filter empty rows
                            chunk_data.append(row)
                    except StopIteration:
                        break
            
            # Store the loaded chunk
            self.loaded_chunks[chunk_key] = chunk_data
            
            # Return the requested portion
            chunk_offset_start = start_row - chunk_start
            chunk_offset_end = end_row - chunk_start
            return chunk_data[chunk_offset_start:chunk_offset_end]
        except Exception as e:
            print(f"Error loading chunk: {str(e)}")
            return []
            
        
    def detect_format_and_set_template(self):
        """Detect file format based on headers and set appropriate template"""
        # Get headers in lowercase for case-insensitive comparison
        headers_lower = [h.lower().strip() for h in self.headers]
        
        # Check for PV format
        if "pv_name" in headers_lower and "pv_type" in headers_lower:
            self.template = self.format_templates["pv"].copy()
        # Check for Command format
        elif "command_name" in headers_lower and "module" in headers_lower:
            self.template = self.format_templates["command"].copy()
        # Check for CV format
        elif "cv_name" in headers_lower and "cv_type" in headers_lower:
            self.template = self.format_templates["cv"].copy()
        # Check for Event format
        elif "event_name" in headers_lower and "commands" in headers_lower:
            self.template = self.format_templates["event"].copy()
        # Check for Ion format
        elif "ion_name" in headers_lower and "ion_mass_num" in headers_lower:
            self.template = self.format_templates["ion"].copy()
        # Otherwise, keep the default template
        else:
            # Ensure template has all headers
            for header in self.headers:
                if header not in self.template:
                    self.template[header] = ""
        
    def create_tab_widgets(self):
        # Search frame
        search_frame = tk.Frame(self.tab_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        # Search label and entry
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        # Create a helper method to handle search
        def handle_search(event=None):
            self.parent.real_time_search(self)
            return "break"  # Prevent default behavior
        
        # Always bind Enter key for explicit search
        self.search_entry.bind("<Return>", handle_search)
        
        # Add a custom trace for the search_var that checks is_large_file dynamically
        def custom_trace(*args):
            # Only do real-time search if not a large file
            if not self.is_large_file:
                self.parent.real_time_search(self)
        
        # Set up the trace
        self.search_var.trace_add("write", custom_trace)
        
        # Bind ESC key to exit search
        self.search_entry.bind("<Escape>", lambda event: self.cancel_operation())

        # Column selection dropdown
        tk.Label(search_frame, text="Column:").pack(side=tk.LEFT, padx=(10, 0))
        self.search_column_var = tk.StringVar(value="All Columns")
        column_options = ["All Columns"] + self.headers
        column_menu = tk.OptionMenu(search_frame, self.search_column_var, *column_options)
        column_menu.pack(side=tk.LEFT, padx=5)
        self.search_column_var.trace_add("write", lambda *args: self.parent.real_time_search(self))

        # Fuzzy search threshold slider
        self.threshold_var = tk.IntVar(value=70)
        tk.Label(search_frame, text="Threshold:").pack(side=tk.LEFT, padx=(10, 0))
        tk.Scale(
            search_frame, 
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.threshold_var,
            showvalue=True,
        ).pack(side=tk.LEFT)
        
        # Data operations frame
        
        # Tab operations buttons
        tab_ops_frame = tk.Frame(search_frame)
        tab_ops_frame.pack(side=tk.RIGHT, padx=10)
        tk.Button(tab_ops_frame, text="New Tab", command=self.parent.new_tab).pack(side=tk.LEFT, padx=5)
        tk.Button(tab_ops_frame, text="Close Tab", command=self.parent.close_tab).pack(side=tk.LEFT, padx=5)
        data_ops_frame = tk.Frame(search_frame)
        data_ops_frame.pack(side=tk.RIGHT, padx=10)
        
        # Data operations buttons
        tk.Button(data_ops_frame, text="Add", command=self.add_row, width=8).pack(
            side=tk.LEFT, padx=2
        )
        tk.Button(data_ops_frame, text="Edit", command=self.edit_row, width=8).pack(
            side=tk.LEFT, padx=2
        )
        tk.Button(data_ops_frame, text="Delete", command=self.delete_row, width=8).pack(
            side=tk.LEFT, padx=2
        )
        tk.Button(data_ops_frame, text="Refresh", command=self.refresh_table, width=8).pack(
            side=tk.LEFT, padx=2
        )

        # Table frame
        table_frame = tk.Frame(self.tab_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add row number column to headers
        self.headers_with_index = ["#"] + self.headers
        
        # Table with index column
        self.tree = ttk.Treeview(table_frame, columns=self.headers_with_index, show="headings")

        # Set column headings with sorting functionality
        for col in self.headers_with_index:
            if col == "#":
                self.tree.heading(col, text="#")
                self.tree.column(col, width=50, anchor=tk.CENTER, stretch=tk.NO)
            else:
                self.tree.heading(col, text=col, command=lambda _col=col: self.sort_by_column(_col))
                self.tree.column(col, width=100, anchor=tk.W, stretch=tk.YES)

        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        h_scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.HORIZONTAL, command=self.tree.xview
        )
        self.tree.configure(yscroll=v_scrollbar.set, xscroll=h_scrollbar.set)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Initialize selection mode flag and global selection set
        self.selection_mode = False
        self.selected_items = set()
        
        # Bind double-click for editing
        self.tree.bind("<Double-1>", lambda event: self.parent.edit_row(self, event))
        
        # Bind left click with Ctrl for multiple selection in normal mode
        self.tree.bind("<Button-1>", self._handle_mouse_click)
        
        # Bind Vim-style keyboard shortcuts
        self.bind_vim_shortcuts()
        
        # Make the treeview focusable
        self.tree.focus_set()
        
        style = ttk.Style()
        style.configure("Treeview",
                       background="#ffffff",
                       foreground="#000000",
                       rowheight=25,
                       fieldbackground="#ffffff",
                       borderwidth=1,
                       relief="solid")
        style.map("Treeview",
                  background=[('selected', '#31869b')],
                  foreground=[('selected', '#ffffff')])
        style.configure("Treeview.Heading",
                       background="#d0d0d0",
                       foreground="#000000",
                       font=('Arial', 10, 'bold'),
                       borderwidth=1,
                       relief="solid")
        style.configure("OddRow.Treeitem", background="#ffffff")
        style.configure("EvenRow.Treeitem", background="#f0f0f0")
        style.configure("CurrentRow.Treeitem", background="#ffcc00", foreground="#000000")
        # 添加选择模式专用样式
        style.configure("SelectionRangeEnd.Treeitem", background="#9933ff", foreground="#ffffff")
        style.configure("SelectionRangeMiddle.Treeitem", background="#33cc33", foreground="#ffffff")
        
    def bind_vim_shortcuts(self):
        """Bind Vim-style keyboard shortcuts to the treeview"""
        # Navigation
        self.tree.bind("h", lambda event: self.scroll_left())
        self.tree.bind("j", lambda event: self.move_down())
        self.tree.bind("k", lambda event: self.move_up())
        self.tree.bind("l", lambda event: self.scroll_right())
        
        # Editing and file operations
        self.tree.bind("o", lambda event: self.add_row())
        self.tree.bind("O", lambda event: self.add_row_above())
        self.tree.bind("a", lambda event: self.add_row())
        self.tree.bind("i", lambda event: self.edit_row(event))
        self.tree.bind("e", lambda event: self.edit_row(event))  # e key to edit selected row
        self.tree.bind("<Return>", lambda event: self.edit_row(event))
        
        # Delete
        self.tree.bind("d", lambda event: self.handle_delete(event))
        
        # Selection mode
        self.tree.bind("v", lambda event: self.toggle_selection_mode())
        self.tree.bind("V", lambda event: self.toggle_selection_mode())
        
        # Page navigation
        self.tree.bind("<Control-u>", lambda event: self.page_up())
        self.tree.bind("<Control-d>", lambda event: self.page_down())
        
        # Search
        self.tree.bind("<Control-f>", lambda event: self.activate_search())
        self.tree.bind("/", lambda event: self.activate_search())
        self.tree.bind("f", lambda event: self.activate_search())
        
        # Close tab when Ctrl+W is pressed while focus is on treeview
        self.tree.bind("<Control-w>", lambda event: self.parent.close_tab())
        
        # ESC key to cancel operations and refocus on tab
        self.tree.bind("<Escape>", lambda event: self.cancel_operation())
        
        # Prevent default behavior for these keys
        for key in "hjklovaideVf" + "/":
            self.tree.bind(f"<Key-{key}>", lambda event: "break", add="+")
    
    def _handle_mouse_click(self, event):
        """Handle mouse click events, entering selection mode with Ctrl+click and managing selection state"""
        # Get the item under the mouse cursor
        region = self.tree.identify_region(event.x, event.y)
        item = self.tree.identify_row(event.y)
        
        # Only handle clicks on actual items
        if region != "cell" or not item:
            return
        
        # Check if Ctrl key is pressed
        is_control_down = event.state & 0x4  # CTRL key mask
        
        # Set focus to the clicked item
        event.widget.focus(item)
        
        # In normal mode with Ctrl key pressed: enter selection mode
        if not self.selection_mode and is_control_down:
            # Enter selection mode
            self.toggle_selection_mode()
            
            # Add the clicked item to selection
            self.selected_items = set([item])
            self.tree.selection_set(item)
            self.update_current_row_style(item)
            print(f"Mouse click: entered selection mode with {item}")
            
            # Prevent default selection behavior
            return "break"
        
        # In selection mode: toggle selection of clicked item
        elif self.selection_mode:
            if item in self.selected_items:
                # Remove from selection
                self.selected_items.remove(item)
                self.tree.selection_remove(item)
                print(f"Mouse click: removed {item} from selected_items")
            else:
                # Add to selection
                self.selected_items.add(item)
                self.tree.selection_add(item)
                print(f"Mouse click: added {item} to selected_items")
            
            # Prevent default selection behavior
            return "break"
            
    def scroll_left(self):
        """Scroll horizontally to the left"""
        x, y = self.tree.xview()
        if x > 0:
            self.tree.xview_moveto(max(0, x - 0.1))
    
    def scroll_right(self):
        """Scroll horizontally to the right"""
        x, y = self.tree.xview()
        if y < 1:
            self.tree.xview_moveto(min(1, x + 0.1))
    
    def move_down(self):
        """Move down to the next row"""
        print(f"move_down called, selection_mode={self.selection_mode}, current selected_items: {self.selected_items}")
        
        items = self.tree.get_children()
        
        if not items:
            print("No items available")
            return
        
        # Get current focused item or select first item
        focused_item = self.tree.focus()
        if not focused_item:
            focused_item = items[0]
            self.tree.focus(focused_item)
            print(f"No focused item, setting focus to: {focused_item}")
        
        current_index = self.tree.index(focused_item)
        print(f"Current focused item: {focused_item} at index {current_index}")
        
        # Move to the next item if available
        if current_index < len(items) - 1:
            next_item = items[current_index + 1]
            print(f"Next item: {next_item} at index {current_index + 1}")
            
            if self.selection_mode:
                print(f"In selection mode, current selected_items: {self.selected_items}")
                if self.selected_items:
                    # Get all selected items and their indices
                    selected_indices = [self.tree.index(item) for item in self.selected_items]
                    min_index = min(selected_indices)
                    max_index = max(selected_indices)
                    
                    print(f"Selected indices: {selected_indices}, min: {min_index}, max: {max_index}")
                    
                    # Check if we're at the start of the selection range
                    if current_index == min_index:
                        print(f"At start of selection range")
                        # Special case: if there's only one item selected, don't remove it
                        # This fixes the bug where first down selection would clear the only selection
                        if len(self.selected_items) == 1:
                            print(f"Only one item selected, adding next item")
                            if next_item not in self.selected_items:
                                self.selected_items.add(next_item)
                                self.tree.selection_add(next_item)
                                print(f"Selection added: {next_item}, new selected_items: {self.selected_items}")
                        else:
                            # When moving down from start of selection range with multiple items, remove current item
                            if focused_item in self.selected_items:
                                self.selected_items.remove(focused_item)
                                self.tree.selection_remove(focused_item)
                                print(f"Selection removed: {focused_item}, new selected_items: {self.selected_items}")
                    # Check if we're at the end of the selection range
                    elif current_index == max_index:
                        print(f"At end of selection range")
                        # When moving down from end of selection range, add next item
                        if next_item not in self.selected_items:
                            self.selected_items.add(next_item)
                            self.tree.selection_add(next_item)
                            print(f"Selection added: {next_item}, new selected_items: {self.selected_items}")
                    else:
                        print(f"In middle of selection range")
                        # Normal case: toggle selection of next item
                        if next_item in self.selected_items:
                            self.selected_items.remove(next_item)
                            self.tree.selection_remove(next_item)
                            print(f"Selection removed: {next_item}, new selected_items: {self.selected_items}")
                        else:
                            self.selected_items.add(next_item)
                            self.tree.selection_add(next_item)
                            print(f"Selection added: {next_item}, new selected_items: {self.selected_items}")
                else:
                    print(f"No items selected yet, adding next item")
                    # If no items selected, add next item to selection
                    self.selected_items.add(next_item)
                    self.tree.selection_add(next_item)
                    print(f"Selection added: {next_item}, new selected_items: {self.selected_items}")
            else:
                # Otherwise, select only the next item
                self.tree.selection_set(next_item)
            
            self.tree.focus(next_item)
            self.tree.see(next_item)
            if self.selection_mode:
                self.update_current_row_style(next_item)

    def move_up(self):
        """Move up to the previous row"""
        items = self.tree.get_children()
        
        if not items:
            return
        
        # Get current focused item or select first item
        focused_item = self.tree.focus()
        if not focused_item:
            focused_item = items[0]
            self.tree.focus(focused_item)
        
        current_index = self.tree.index(focused_item)
        
        # Move to the previous item if available
        if current_index > 0:
            prev_item = items[current_index - 1]
            
            if self.selection_mode:
                if self.selected_items:
                    # Get all selected items and their indices
                    selected_indices = [self.tree.index(item) for item in self.selected_items]
                    min_index = min(selected_indices)
                    max_index = max(selected_indices)
                    
                    # Check if we're at the start of the selection range
                    if current_index == min_index:
                        # When moving up from start of selection range, add previous item
                        if prev_item not in self.selected_items:
                            self.selected_items.add(prev_item)
                            self.tree.selection_add(prev_item)
                            print(f"Selection added: {prev_item}")
                    # Check if we're at the end of the selection range
                    elif current_index == max_index:
                        # When moving up from end of selection range, remove current item
                        if focused_item in self.selected_items:
                            self.selected_items.remove(focused_item)
                            self.tree.selection_remove(focused_item)
                            print(f"Selection removed: {focused_item}")
                    else:
                        # Normal case: toggle selection of previous item
                        if prev_item in self.selected_items:
                            self.selected_items.remove(prev_item)
                            self.tree.selection_remove(prev_item)
                            print(f"Selection removed: {prev_item}")
                        else:
                            self.selected_items.add(prev_item)
                            self.tree.selection_add(prev_item)
                            print(f"Selection added: {prev_item}")
                else:
                    # If no items selected, add previous item to selection
                    self.selected_items.add(prev_item)
                    self.tree.selection_add(prev_item)
                    print(f"Selection added: {prev_item}")
            else:
                # Otherwise, select only the previous item
                self.tree.selection_set(prev_item)
            
            self.tree.focus(prev_item)
            self.tree.see(prev_item)
            if self.selection_mode:
                self.update_current_row_style(prev_item)
    
    def handle_delete(self, event):
        """Handle delete operations (dd)"""
        if not hasattr(self, 'last_key') or self.last_key != 'd':
            self.last_key = 'd'
        else:
            # Double d pressed - perform delete
            self.delete_row()
            self.last_key = None
    
    def add_row(self):
        """Add new row below current row using template in this tab"""
        # Create edit window
        edit_window = tk.Toplevel(self.parent.root)
        edit_window.title("Add New Node")
        
        # Position the window next to the main window
        root_x = self.parent.root.winfo_x()
        root_y = self.parent.root.winfo_y()
        root_width = self.parent.root.winfo_width()
        edit_window.geometry(f"+{root_x + root_width + 10}+{root_y}")
        
        self.parent.active_popups.append(edit_window)
        
        # Bind ESC and Ctrl+W to close only this window
        edit_window.bind("<Escape>", lambda event, popup=edit_window: self.parent._remove_popup(popup))
        edit_window.bind("<Control-w>", lambda event, popup=edit_window: self.parent._remove_popup(popup))
        # Bind Ctrl+Y to confirm
        edit_window.bind("<Control-y>", lambda event: confirm_add())
        
        # Auto-focus the new window
        edit_window.focus_force()

        # Create input fields
        entries = {}
        for i, header in enumerate(self.headers):
            tk.Label(edit_window, text=header).grid(
                row=i, column=0, padx=5, pady=2, sticky=tk.E
            )
            entry = tk.Entry(edit_window, width=40)
            # Fill with template value if available
            entry.insert(0, self.template.get(header, ""))
            entry.grid(row=i, column=1, padx=5, pady=2)
            entries[header] = entry

        # Confirm button
        def confirm_add():
            new_row = [entries[header].get() for header in self.headers]
            
            # Get current focused item's index
            focused_item = self.tree.focus()
            if focused_item:
                current_index = self.tree.index(focused_item) + 1  # Add after current row
            else:
                current_index = len(self.data)  # Add at the end
                
            self.data.insert(current_index, new_row)
            self.populate_table()
            
            # Restore focus to the new row
            if current_index < len(self.tree.get_children()):
                new_item = self.tree.get_children()[current_index]
                self.tree.focus(new_item)
                self.tree.see(new_item)
                
            self.modified = True
            self.parent._remove_popup(edit_window)

        tk.Button(edit_window, text="Confirm", command=confirm_add).grid(
            row=len(self.headers), column=1, pady=5
        )
    
    def add_row_above(self):
        """Add new row above current row using template in this tab"""
        # Create edit window
        edit_window = tk.Toplevel(self.parent.root)
        edit_window.title("Add New Node")
        
        # Position the window next to the main window
        root_x = self.parent.root.winfo_x()
        root_y = self.parent.root.winfo_y()
        root_width = self.parent.root.winfo_width()
        edit_window.geometry(f"+{root_x + root_width + 10}+{root_y}")
        
        self.parent.active_popups.append(edit_window)
        
        # Bind ESC and Ctrl+W to close only this window
        edit_window.bind("<Escape>", lambda event, popup=edit_window: self.parent._remove_popup(popup))
        edit_window.bind("<Control-w>", lambda event, popup=edit_window: self.parent._remove_popup(popup))
        # Bind Ctrl+Y to confirm
        edit_window.bind("<Control-y>", lambda event: confirm_add())
        
        # Auto-focus the new window
        edit_window.focus_force()

        # Create input fields
        entries = {}
        for i, header in enumerate(self.headers):
            tk.Label(edit_window, text=header).grid(
                row=i, column=0, padx=5, pady=2, sticky=tk.E
            )
            entry = tk.Entry(edit_window, width=40)
            # Fill with template value if available
            entry.insert(0, self.template.get(header, ""))
            entry.grid(row=i, column=1, padx=5, pady=2)
            entries[header] = entry

        # Confirm button
        def confirm_add():
            new_row = [entries[header].get() for header in self.headers]
            
            # Get current focused item's index
            focused_item = self.tree.focus()
            if focused_item:
                current_index = self.tree.index(focused_item)  # Add before current row
            else:
                current_index = 0  # Add at the beginning
                
            self.data.insert(current_index, new_row)
            self.populate_table()
            
            # Restore focus to the new row
            if current_index < len(self.tree.get_children()):
                new_item = self.tree.get_children()[current_index]
                self.tree.focus(new_item)
                self.tree.see(new_item)
                
            self.modified = True
            self.parent._remove_popup(edit_window)

        tk.Button(edit_window, text="Confirm", command=confirm_add).grid(
            row=len(self.headers), column=1, pady=5
        )
        
    def edit_row(self, event=None):
        """Edit row(s) in this tab, open separate window for each selected item"""
        # Debug: Print current selection status
        print(f"Edit row called with selection_mode={self.selection_mode}")
        print(f"Number of selected items: {len(self.selected_items)}")
        print(f"Selected items: {self.selected_items}")
        
        # Get selected items
        selected_items = []
        if self.selection_mode or (self.selected_items and len(self.selected_items) > 1):
            # In selection mode or normal mode with multiple items selected via Ctrl+click, use all selected items
            selected_items = list(self.selected_items)
            print(f"Using all selected items: {selected_items}")
        else:
            # In normal mode with single selection, use focused item
            selected_item = self.tree.focus()
            if not selected_item:
                print("No item focused, returning")
                return
            selected_items = [selected_item]
            print(f"Using focused item: {selected_item}")

        # Create edit window for each selected item
        print(f"Creating {len(selected_items)} edit windows")
        for i, item_id in enumerate(selected_items):
            print(f"Creating edit window for item {i}: {item_id}")
            self._create_edit_window_for_item(item_id, i)
    
    def _create_edit_window_for_item(self, item_id, window_offset=0):
        """Create an edit window for a specific item"""
        # Get row data and save row index immediately
        item_data = self.tree.item(item_id)["values"]
        row_index = self.tree.index(item_id)
        
        # Get item name or identifier for window title
        item_name = item_data[0] if item_data else f"Item {row_index}"
        
        # Create edit window
        edit_window = tk.Toplevel(self.parent.root)
        edit_window.title(f"Edit Node: {item_name}")
        
        # Position the window next to the main window with offset for multiple windows
        root_x = self.parent.root.winfo_x()
        root_y = self.parent.root.winfo_y()
        root_width = self.parent.root.winfo_width()
        window_x = root_x + root_width + 10 + (window_offset * 20)  # Offset windows horizontally
        window_y = root_y + (window_offset * 20)  # Offset windows vertically
        edit_window.geometry(f"+{window_x}+{window_y}")
        
        self.parent.active_popups.append(edit_window)
        
        # Bind ESC and Ctrl+W to close only this window
        edit_window.bind("<Escape>", lambda event, popup=edit_window: self.parent._remove_popup(popup))
        edit_window.bind("<Control-w>", lambda event, popup=edit_window: self.parent._remove_popup(popup))
        # Bind Ctrl+Y to confirm
        edit_window.bind("<Control-y>", lambda event: confirm_edit())
        
        edit_window.protocol("WM_DELETE_WINDOW", lambda: self.parent._remove_popup(edit_window))
        
        # Auto-focus the new window
        edit_window.focus_force()

        # Create input fields
        entries = {}
        for i, header in enumerate(self.headers):
            tk.Label(edit_window, text=header).grid(
                row=i, column=0, padx=5, pady=2, sticky=tk.E
            )
            entry = tk.Entry(edit_window, width=40)
            entry.insert(0, item_data[i])
            entry.grid(row=i, column=1, padx=5, pady=2)
            entries[header] = entry

        # Confirm button
        def confirm_edit():
            # Update data for this specific row
            self.data[row_index] = [entries[header].get() for header in self.headers]
            self.populate_table()
            self.modified = True
            self.parent._remove_popup(edit_window)
            
        # Update window position when parent window moves
        def on_parent_move(event=None):
            try:
                # Check if edit_window still exists
                if edit_window.winfo_exists():
                    new_root_x = self.parent.root.winfo_x()
                    new_root_y = self.parent.root.winfo_y()
                    new_root_width = self.parent.root.winfo_width()
                    new_window_x = new_root_x + new_root_width + 10 + (window_offset * 20)
                    new_window_y = new_root_y + (window_offset * 20)
                    edit_window.geometry(f"+{new_window_x}+{new_window_y}")
            except tk.TclError:
                # Window has been destroyed, do nothing
                pass
        
        # Bind to parent window configure event to track movement
        bind_id = self.parent.root.bind("<Configure>", on_parent_move)
        
        # Store bind_id for later unbinding
        edit_window._parent_bind_id = bind_id
        
        # Unbind when window is closed
        edit_window.protocol("WM_DELETE_WINDOW", lambda: self._cleanup_edit_window(edit_window))
        
        tk.Button(edit_window, text="Confirm", command=confirm_edit).grid(
            row=len(self.headers), column=1, pady=5
        )
        
    def _cleanup_edit_window(self, edit_window):
        """Cleanup resources when edit window is closed"""
        # Unbind parent window configure event if bind_id exists
        if hasattr(edit_window, '_parent_bind_id'):
            try:
                self.parent.root.unbind("<Configure>", edit_window._parent_bind_id)
            except tk.TclError:
                # Already unbound or invalid, do nothing
                pass
        # Remove from active popups
        self.parent._remove_popup(edit_window)
        
    def refresh_table(self):
        """Refresh the table data"""
        if self.filename:
            self.load_data()
            self.populate_table()
        else:
            messagebox.showwarning("Warning", "No file opened in this tab")
    
    def delete_row(self):
        """Delete selected row(s) in this tab"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select rows to delete")
            return

        # Create custom confirmation dialog with ESC support
        confirm_window = tk.Toplevel(self.parent.root)
        confirm_window.title("Confirm")
        confirm_window.geometry("300x120")
        confirm_window.resizable(False, False)
        confirm_window.transient(self.parent.root)
        
        # Add to active popups and set protocol for window deletion
        self.parent.active_popups.append(confirm_window)
        confirm_window.protocol("WM_DELETE_WINDOW", lambda: confirm_window.destroy())
        
        # Position dialog in center of main window
        root_x = self.parent.root.winfo_x()
        root_y = self.parent.root.winfo_y()
        root_width = self.parent.root.winfo_width()
        root_height = self.parent.root.winfo_height()
        confirm_width = 300
        confirm_height = 120
        confirm_x = root_x + (root_width // 2) - (confirm_width // 2)
        confirm_y = root_y + (root_height // 2) - (confirm_height // 2)
        confirm_window.geometry(f"{confirm_width}x{confirm_height}+{confirm_x}+{confirm_y}")
        
        # Auto-focus the confirmation window
        confirm_window.focus_force()
        
        # Add message
        msg = "Are you sure you want to delete the selected rows?"
        tk.Label(confirm_window, text=msg, wraplength=280, padx=10, pady=10).pack()
        
        # Add buttons frame
        buttons_frame = tk.Frame(confirm_window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add buttons
        def on_yes():
            # Delete from end to avoid index issues
            for item in reversed(selected_items):
                row_index = self.tree.index(item)
                del self.data[row_index]

            self.populate_table()
            self.modified = True
            
            # If in selection mode or normal mode with multiple selections, clear selections after deletion
            if self.selection_mode or (self.selected_items and len(self.selected_items) > 1):
                if self.selection_mode:
                    print("Exiting selection mode after deletion")
                    self.selection_mode = False
                    # Reset bindings if in selection mode
                    self.tree.bind("i", lambda event: self.parent.edit_row(self, event))
                    self.tree.bind("o", lambda event: self.parent.add_row())
                
                # Clear selections regardless of mode
                self.selected_items.clear()
                self.clear_current_row_style()
                
                # Reset j/k key bindings when exiting selection mode
                self.tree.bind("j", lambda event: "break")
                self.tree.bind("k", lambda event: "break")
            
            confirm_window.destroy()
            
        def on_no():
            confirm_window.destroy()
            
        tk.Button(buttons_frame, text="Yes", command=on_yes, width=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(buttons_frame, text="No", command=on_no, width=10).pack(side=tk.RIGHT, padx=5)
        
        # Bind ESC and Ctrl+W to cancel
        confirm_window.bind("<Escape>", lambda event: on_no())
        confirm_window.bind("<Control-w>", lambda event: on_no())
        # Bind Ctrl+Y to confirm
        confirm_window.bind("<Control-y>", lambda event: on_yes())
        # Bind Ctrl+N to cancel
        confirm_window.bind("<Control-n>", lambda event: on_no())
        
        # Focus on No button by default
        buttons_frame.after(100, lambda: buttons_frame.winfo_children()[0].focus())
    
    def toggle_selection_mode(self):
        """Toggle selection mode"""
        self.selection_mode = not self.selection_mode
        
        if self.selection_mode:
            print("Selection mode activated")
            # In selection mode, bind additional keys
            self.tree.bind("i", lambda event: self.jump_to_selection_start())
            self.tree.bind("o", lambda event: self.jump_to_selection_end())
            self.tree.bind("e", lambda event: self.edit_row(event))
            # Bind j/k keys for navigation with multi-select capability
            self.tree.bind("j", lambda event: self.move_down())
            self.tree.bind("k", lambda event: self.move_up())
            
            # Ensure there is a focused item when entering selection mode
            focused_item = self.tree.focus()
            if not focused_item:
                items = self.tree.get_children()
                if items:
                    focused_item = items[0]
                    self.tree.focus(focused_item)
            
            # Explicitly select the focused item when entering selection mode only if not already set by mouse click
            if focused_item and not self.selected_items:
                self.selected_items = set([focused_item])
                self.tree.selection_set(focused_item)
                self.update_current_row_style(focused_item)
        else:
            print("Selection mode deactivated")
            self.clear_current_row_style()
            # Reset bindings when exiting selection mode
            self.tree.bind("i", lambda event: self.parent.edit_row(self, event))
            self.tree.bind("o", lambda event: self.parent.add_row())
            # Clear selections when exiting selection mode
            self.selected_items.clear()
            # Re-render grid when exiting selection mode
            self.populate_table()

    def get_selected_items(self):
        """Get the list of currently selected items"""
        return list(self.selected_items)

    def is_full_document_selected(self):
        """Check if all items in the document are selected"""
        all_items = self.tree.get_children()
        return len(self.selected_items) == len(all_items)
        
    def update_current_row_style(self, current_item):
        # 清除所有特殊样式标签
        for item in self.tree.get_children():
            tags = self.tree.item(item, "tags")
            if tags:
                new_tags = [tag for tag in tags if tag not in ["SelectionRangeEnd", "SelectionRangeMiddle"]]
                self.tree.item(item, tags=new_tags)
                
        # 清除并重新设置当前行样式
        self.clear_current_row_style()
        
        if current_item:
            original_tags = self.tree.item(current_item, "tags")
            new_tags = list(original_tags) if original_tags else []
            if "CurrentRow" not in new_tags:
                new_tags.append("CurrentRow")
            self.tree.item(current_item, tags=new_tags)
        
        # 在选择模式下应用特殊样式
        if self.selection_mode:
            selected_items = self.selected_items
            if selected_items:
                # 获取所有项目和选中项目的索引
                all_items = self.tree.get_children()
                item_to_index = {item: idx for idx, item in enumerate(all_items)}
                selected_indices = [item_to_index[item] for item in selected_items]
                selected_indices.sort()
                
                # 为选中的项目应用样式
                for item in selected_items:
                    item_idx = item_to_index[item]
                    tags = list(self.tree.item(item, "tags")) if self.tree.item(item, "tags") else []
                    
                    # 首尾项使用紫色样式（如果是首尾项或当前项）
                    if (item_idx == selected_indices[0] or item_idx == selected_indices[-1] or item == current_item):
                        tags.append("SelectionRangeEnd")
                    # 中间选择项使用绿色样式
                    else:
                        tags.append("SelectionRangeMiddle")
                    
                    self.tree.item(item, tags=tags)
            
    def clear_current_row_style(self):
        for item in self.tree.get_children():
            tags = self.tree.item(item, "tags")
            if tags and "CurrentRow" in tags:
                new_tags = [tag for tag in tags if tag != "CurrentRow"]
                self.tree.item(item, tags=new_tags)
    
    def jump_to_selection_start(self):
        """Jump to the start of the selection"""
        selected = self.selected_items
        items = self.tree.get_children()
        
        if items:
            if selected and not self.is_full_document_selected():
                min_index = min([self.tree.index(item) for item in selected])
                first_selected_item = items[min_index]
                self.tree.focus(first_selected_item)
                self.tree.see(first_selected_item)
                if self.selection_mode:
                    self.update_current_row_style(first_selected_item)
            else:
                first_item = items[0]
                self.tree.focus(first_item)
                self.tree.see(first_item)
                if self.selection_mode:
                    self.update_current_row_style(first_item)
    
    def jump_to_selection_end(self):
        """Jump to the end of the selection"""
        selected = self.selected_items
        items = self.tree.get_children()
        
        if items:
            if selected and not self.is_full_document_selected():
                max_index = max([self.tree.index(item) for item in selected])
                last_selected_item = items[max_index]
                self.tree.focus(last_selected_item)
                self.tree.see(last_selected_item)
                if self.selection_mode:
                    self.update_current_row_style(last_selected_item)
            else:
                last_item = items[-1]
                self.tree.focus(last_item)
                self.tree.see(last_item)
                if self.selection_mode:
                    self.update_current_row_style(last_item)
    
    def page_up(self):
        """Page up"""
        y, _ = self.tree.yview()
        new_y = max(0, y - 0.2)
        self.tree.yview_moveto(new_y)
        
        # Update selection to the visible item at the top
        items = self.tree.get_children()
        if items:
            # Get the first visible item
            for item in items:
                bbox = self.tree.bbox(item)
                if bbox and bbox[1] >= 0:
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    self.tree.see(item)
                    break
    
    def page_down(self):
        """Page down"""
        y, _ = self.tree.yview()
        new_y = min(1, y + 0.2)
        self.tree.yview_moveto(new_y)
        
        # Update selection to the visible item at the top of the new page
        items = self.tree.get_children()
        if items:
            # Get the first visible item after scrolling
            for item in items:
                bbox = self.tree.bbox(item)
                if bbox and bbox[1] >= 0:
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    self.tree.see(item)
                    break
    
    def activate_search(self):
        """Activate the search field"""
        # Find the search entry widget
        for widget in self.tab_frame.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Entry):
                        child.focus_set()
                        child.select_range(0, tk.END)
                        return
    
    def cancel_operation(self):
        """Cancel current operation and refocus on the treeview"""
        # Always exit selection mode when ESC is pressed
        if self.selection_mode:
            print("ESC pressed - exiting selection mode")
            self.selection_mode = False
            self.clear_current_row_style()
            # Reset bindings
            self.tree.bind("i", lambda event: self.parent.edit_row(self, event))
            self.tree.bind("o", lambda event: self.parent.add_row())
            
            # Clear all selections
            current_focus = self.tree.focus()
            self.selected_items.clear()
            for item in self.tree.selection():
                self.tree.selection_remove(item)
            if current_focus:
                self.tree.selection_set(current_focus)
                self.selected_items = set([current_focus])
        else:
            # Exit selection mode if active (legacy behavior)
            self.selection_mode = False
            self.clear_current_row_style()
            # Reset bindings
            self.tree.bind("i", lambda event: self.parent.edit_row(self, event))
            self.tree.bind("o", lambda event: self.parent.add_row())
        
        self.parent.cancel_all_operations()
        
        # Refocus on the treeview
        self.tree.focus_set()
        
        # Clear any search text
        for widget in self.tab_frame.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Entry):
                        # Just clear the entry without checking variables
                        child.delete(0, tk.END)

    def populate_table(self, data=None):
        """Populate table with data, using lazy loading for large files"""
        # If search data is provided, use it directly
        if data is not None:
            # Clear existing data
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            # Save current lazy loading state and temporarily disable it for search results
            was_large_file = self.is_large_file
            self.is_large_file = False
            
            # Add search results with index
            for i, row in enumerate(data):
                tag = "EvenRow" if i % 2 == 0 else "OddRow"
                # Add row number as first column
                row_with_index = [str(i + 1)] + row
                self.tree.insert("", tk.END, values=row_with_index, tags=(tag,))
            
            self.tree.tag_configure("OddRow", background="#ffffff")
            self.tree.tag_configure("EvenRow", background="#f0f0f0")
            
            # Restore lazy loading state after search
            self.is_large_file = was_large_file
            return
            
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # If it's a small file or real-time search is active, load all data
        if not self.is_large_file:
            display_data = self.data
            for i, row in enumerate(display_data):
                tag = "EvenRow" if i % 2 == 0 else "OddRow"
                # Add row number as first column
                row_with_index = [str(i + 1)] + row
                self.tree.insert("", tk.END, values=row_with_index, tags=(tag,))
        else:
            # For large files, load initial visible portion
            # Get visible area info
            visible_height = self.tree.winfo_height()
            row_height = 25  # Approximate row height from style configuration
            visible_rows = max(10, visible_height // row_height)  # Load more than visible for smoother scrolling
            
            # Load initial chunk
            initial_data = self.load_chunk(0, visible_rows * 2)
            
            # Add data with virtual row IDs for tracking
            for i, row in enumerate(initial_data):
                tag = "EvenRow" if i % 2 == 0 else "OddRow"
                # Add row number as first column
                row_with_index = [str(i + 1)] + row
                self.tree.insert("", tk.END, iid=str(i), values=row_with_index, tags=(tag,))
                
            # Set virtual total rows for proper scrolling
            self.tree.configure(height=min(visible_rows, self.total_rows))
            
            # Bind to scroll events for lazy loading
            self.tree.bind("<Configure>", self.on_tree_configure)
            self.tree.bind("<MouseWheel>", self.on_mouse_wheel)
            self.tree.bind("<Button-4>", self.on_mouse_wheel)  # Linux scroll up
            self.tree.bind("<Button-5>", self.on_mouse_wheel)  # Linux scroll down
            self.tree.bind("<KeyPress>", self.on_key_press)
        
        self.tree.tag_configure("OddRow", background="#ffffff")
        self.tree.tag_configure("EvenRow", background="#f0f0f0")
        
    def on_tree_configure(self, event):
        """Handle treeview configuration changes"""
        if self.is_large_file:
            self.update_visible_rows()
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling for lazy loading"""
        if self.is_large_file:
            # Schedule visible row update after scrolling completes
            self.tree.after(10, self.update_visible_rows)
    
    def on_key_press(self, event):
        """Handle keyboard navigation for lazy loading"""
        if self.is_large_file and event.keysym in ('Up', 'Down', 'Prior', 'Next', 'Home', 'End'):
            # Schedule visible row update after key navigation
            self.tree.after(10, self.update_visible_rows)
    
    def update_visible_rows(self):
        """Update visible rows based on current scroll position"""
        if not self.is_large_file:
            return
        
        try:
            # Get current scroll position
            y, _ = self.tree.yview()
            visible_height = self.tree.winfo_height()
            row_height = 25  # Approximate row height
            visible_rows = max(10, visible_height // row_height)
            
            # Calculate current visible range
            start_row = int(y * self.total_rows)
            end_row = min(self.total_rows, start_row + visible_rows * 2)  # Load extra for smooth scrolling
            
            # Only update if the visible range has changed significantly
            if (abs(start_row - self.currently_visible_range[0]) > visible_rows // 2 or 
                abs(end_row - self.currently_visible_range[1]) > visible_rows // 2):
                
                self.currently_visible_range = (start_row, end_row)
                
                # Load the visible chunk
                visible_data = self.load_chunk(start_row, end_row)
                
                # Get existing items
                existing_items = set(self.tree.get_children())
                
                # Track which new items need to be added
                new_items_to_add = []
                for i, row in enumerate(visible_data):
                    actual_row = start_row + i
                    if str(actual_row) not in existing_items:
                        new_items_to_add.append((actual_row, row))
                
                # Track current displayed rows
                current_displayed_rows = len(self.tree.get_children())
                
                # Check if scrolled to bottom (near the end of current data)
                if end_row >= current_displayed_rows - visible_rows // 2:
                    # Calculate new load range with chunk size of row increments
                    new_load_start = current_displayed_rows
                    new_load_end = min(self.total_rows, current_displayed_rows + self.chunk_size)
                    
                    # Load new chunk
                    new_data = self.load_chunk(new_load_start, new_load_end)
                    
                    # Add new rows without clearing existing ones
                    if new_data:
                        for i, row in enumerate(new_data):
                            actual_row = new_load_start + i
                            tag = "EvenRow" if actual_row % 2 == 0 else "OddRow"
                            # Add row number as first column
                            row_with_index = [str(actual_row + 1)] + row
                            self.tree.insert("", tk.END, iid=str(actual_row), values=row_with_index, tags=(tag,))
                
                # Update visible range
                self.currently_visible_range = (start_row, end_row)
        except Exception as e:
            print(f"Error updating visible rows: {str(e)}")

    def update_tab_name(self, name):
        self.tab_name = name
        self.notebook.tab(self.tab_frame, text=name)
        
    def sort_by_column(self, col):
        items = self.tree.get_children()
        if not items:
            return
            
        if self.sort_column == col:
            self.sort_direction = not self.sort_direction  # 切换排序方向
        else:
            self.sort_column = col
            self.sort_direction = True  # 默认升序
            
        col_index = self.headers.index(col)
        
        def sort_key(item):
            value = self.tree.item(item, "values")[col_index]
            try:
                return float(value)
            except ValueError:
                return str(value).lower()
                
        sorted_items = sorted(items, key=sort_key, reverse=(not self.sort_direction))
        
        for index, item in enumerate(sorted_items):
            self.tree.move(item, "", index)

class TableManager:
    def __init__(self, root):
        self.root = root
        self.root.title("LACCS TSV Editor")
        self.root.geometry("1200x600")

        # Initialize data
        # Use system temp directory for backups
        self.backup_dir = os.path.join(tempfile.gettempdir(), "laccs_tsv_editor_backups")
        self.tabs = []
        self.current_tab = None
        self.active_popups = []
        self.backup_enabled = True  # Backup functionality toggle
        self.lazy_load_threshold = 10  # Default 10MB threshold for lazy loading
        
        # History configuration
        # Use system temp directory for cross-platform compatibility
        self.recent_files_path = os.path.join(tempfile.gettempdir(), "laccs_tsv_editor_recent_files.json")
        self.recent_files = []
        self.max_recent_files = 10

        # Create backup directory
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        # Load recent files
        self.load_recent_files()

        # Create UI
        self.create_widgets()

        # Show history dashboard or file dialog
        if self.recent_files:
            self.show_history_dashboard()
        else:
            self.open_file_dialog()

    def open_file_dialog(self, multi_select=True):
        """Open file selection dialog with multiple files support by default"""
        if multi_select:
            file_paths = filedialog.askopenfilenames(
                title="Select Table Files",
                filetypes=[("TSV Files", "*.tsv"), ("CSV Files", "*.csv"), ("Text Files", "*.txt"), ("All Files", "*.*")],
            )
            
            if file_paths:
                for file_path in file_paths:
                    self.open_file(file_path)
                return True
        else:
            file_path = filedialog.askopenfilename(
                title="Select Table File",
                filetypes=[("TSV Files", "*.tsv"), ("CSV Files", "*.csv"), ("Text Files", "*.txt"), ("All Files", "*.*")],
            )
            
            if file_path:
                self.open_file(file_path)
                return True
        
        return False
        
    def open_file(self, file_path):
        """Open a file in a new tab or switch to existing tab if file is already open"""
        # Convert to absolute path for consistent comparison
        file_path = os.path.abspath(file_path)
        
        # Check if file is already open in any tab
        for tab in self.tabs:
            if tab.filename and os.path.abspath(tab.filename) == file_path:
                # Switch to existing tab
                self.notebook.select(tab.tab_frame)
                self.current_tab = tab
                self.update_title()
                # Update recent files order (file remains in the list)
                self.add_to_recent_files(file_path)
                return
        
        # File is not open, create new tab
        tab_name = os.path.basename(file_path)
        new_tab = FileTab(self, self.notebook, tab_name)
        new_tab.filename = file_path
        new_tab.load_data()
        new_tab.create_tab_widgets()  # Ensure tree is initialized first
        new_tab.populate_table()
        
        self.notebook.add(new_tab.tab_frame, text=tab_name)
        self.notebook.select(new_tab.tab_frame)
        self.tabs.append(new_tab)
        self.current_tab = new_tab
        
        # Update recent files
        self.add_to_recent_files(file_path)
        
        # Update window title
        self.update_title()

    def update_title(self):
        """Update window title with current filename"""
        if self.current_tab and self.current_tab.filename:
            self.root.title(
                f"LACCS TSV Manager - {os.path.basename(self.current_tab.filename)}"
            )
        else:
            self.root.title("LACCS TSV Manager - No file selected")

    def load_data(self):
        """Load data file - This is now called from the FileTab class"""
        pass
        
    def bind_application_shortcuts(self):
        """Bind application-wide keyboard shortcuts"""
        # Save shortcut (Ctrl+S)
        self.root.bind("<Control-s>", lambda event: self.save_data())
        
        # Open file (Ctrl+O)
        self.root.bind("<Control-o>", lambda event: self.open_file_dialog())
        
        # Open folder (Ctrl+Shift+O)
        self.root.bind("<Control-O>", lambda event: self.open_folder_dialog())
        
        # Open restore interface (Ctrl+R)
        self.root.bind("<Control-r>", lambda event: self.restore_backup())
        
        # Open backups folder (Ctrl+B)
        self.root.bind("<Control-b>", lambda event: self.open_backup_folder())
        
        # Toggle auto backup (Ctrl+Shift+B)
        self.root.bind("<Control-B>", lambda event: self.toggle_auto_backup())
        
        # Close current tab with Ctrl+W only when focus is not on any tab's treeview
        def on_ctrl_w(event):
            # Get the widget that currently has focus
            focused_widget = event.widget
            # Check if the focused widget is not a Treeview
            if not isinstance(focused_widget, ttk.Treeview):
                self.close_tab()
        
        self.root.bind("<Control-w>", on_ctrl_w)

    def backup_file(self, filename):
        """Backup original file if backup is enabled"""
        # Check if backup is enabled
        if not self.backup_enabled:
            return

        if not filename:
            return

        # Create backup directory if it doesn't exist
        if not os.path.exists(self.backup_dir):
            try:
                os.makedirs(self.backup_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create backup directory: {str(e)}")
                return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = os.path.join(
            self.backup_dir, f"{os.path.basename(filename)}.bak_{timestamp}"
        )
        try:
            with open(filename, "r") as original, open(
                backup_filename, "w"
            ) as backup:
                backup.write(original.read())
        except Exception as e:
            messagebox.showerror("Error", f"Error backing up file: {str(e)}")

    def open_backup_folder(self):
        """Open the backup folder in the system file explorer"""
        if not os.path.exists(self.backup_dir):
            try:
                os.makedirs(self.backup_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create backup directory: {str(e)}")
                return
        
        try:
            # Open folder using the appropriate method for the current OS
            if platform.system() == "Windows":
                os.startfile(self.backup_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", self.backup_dir])
            else:  # Linux and other Unix-like
                subprocess.run(["xdg-open", self.backup_dir])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open backup folder: {str(e)}")

    def restore_backup(self):
        """Restore a backup file for the current tab"""
        if not self.current_tab or not self.current_tab.filename:
            messagebox.showwarning("Warning", "No file opened in current tab")
            return

        # Create backup directory if it doesn't exist
        if not os.path.exists(self.backup_dir):
            messagebox.showinfo("Info", "No backup directory found. No backups available.")
            return

        # Get the base filename of the current file
        current_filename = os.path.basename(self.current_tab.filename)
        
        # Find all backup files for this filename
        backup_files = []
        for file in os.listdir(self.backup_dir):
            if file.startswith(f"{current_filename}.bak_"):
                # Extract timestamp from filename
                timestamp_str = file.replace(f"{current_filename}.bak_", "")
                try:
                    # Parse timestamp for sorting
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    backup_files.append((file, timestamp))
                except ValueError:
                    # Skip files with invalid timestamp format
                    continue

        if not backup_files:
            messagebox.showinfo("Info", f"No backups found for {current_filename}")
            return

        # Sort backups by timestamp (newest first)
        backup_files.sort(key=lambda x: x[1], reverse=True)

        # Create restore dialog
        restore_window = tk.Toplevel(self.root)
        restore_window.title(f"Restore Backup - {current_filename}")
        restore_window.geometry("600x400")
        restore_window.resizable(True, True)
        restore_window.transient(self.root)
        
        # Center the window
        restore_window.update_idletasks()
        width = restore_window.winfo_width()
        height = restore_window.winfo_height()
        x = (restore_window.winfo_screenwidth() // 2) - (width // 2)
        y = (restore_window.winfo_screenheight() // 2) - (height // 2)
        restore_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Add to active popups
        self.active_popups.append(restore_window)
        restore_window.protocol("WM_DELETE_WINDOW", lambda: self._remove_popup(restore_window))
        
        # Bind ESC and Ctrl+W to close
        restore_window.bind("<Escape>", lambda event: self._remove_popup(restore_window))
        restore_window.bind("<Control-w>", lambda event: self._remove_popup(restore_window))
        # Bind Ctrl+Y to restore and Ctrl+N to cancel
        restore_window.bind("<Control-y>", lambda event: on_restore())
        restore_window.bind("<Control-n>", lambda event: self._remove_popup(restore_window))
        
        # Auto-focus the new window
        restore_window.focus_force()

        # Create a frame for scrolling
        frame = tk.Frame(restore_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a canvas and scrollbar
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create a frame inside the canvas
        content_frame = tk.Frame(canvas)
        canvas_frame = canvas.create_window((0, 0), window=content_frame, anchor="nw")

        # Title
        tk.Label(content_frame, text=f"Available Backups for {current_filename}", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Create listbox for backup selection
        backup_listbox = tk.Listbox(content_frame, width=70, height=15, font=('Arial', 10))
        backup_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Populate listbox with backup files and their timestamps
        backup_paths = []
        for file, timestamp in backup_files:
            display_text = f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {file}"
            backup_listbox.insert(tk.END, display_text)
            backup_paths.append(os.path.join(self.backup_dir, file))
        
        # Select the first item by default
        if backup_listbox.size() > 0:
            backup_listbox.selection_set(0)
        
        # Button frame
        button_frame = tk.Frame(content_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def on_restore():
            selection = backup_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a backup to restore")
                return
            
            # Confirm overwrite
            if not messagebox.askyesno("Confirm Restore", "This will replace the current file with the selected backup. Continue?"):
                return
            
            backup_path = backup_paths[selection[0]]
            try:
                # Create a backup of the current file before restoring
                self.backup_file(self.current_tab.filename)
                
                # Read the backup file
                with open(backup_path, "r") as f:
                    reader = csv.reader(f, delimiter="\t")
                    # First row is headers
                    self.current_tab.headers = next(reader)
                    # Read all remaining rows as data
                    self.current_tab.data = [row for row in reader if row]  # Filter empty rows
                
                # Repopulate the table
                self.current_tab.populate_table()
                self.current_tab.modified = True
                
                messagebox.showinfo("Success", f"File restored from backup")
                restore_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restore backup: {str(e)}")
        
        # Buttons
        tk.Button(button_frame, text="Restore", command=on_restore, width=15).pack(side=tk.RIGHT, padx=5)
        tk.Button(button_frame, text="Cancel", command=restore_window.destroy, width=15).pack(side=tk.RIGHT, padx=5)
        
        # Update scroll region when content changes
        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_frame, width=event.width)
        
        content_frame.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", on_configure)

    def save_data(self):
        """Save data to file"""
        if not self.current_tab:
            messagebox.showwarning("Warning", "No active tab")
            return
            
        if not self.current_tab.filename:
            self.save_as_data()
            return

        self.backup_file(self.current_tab.filename)
        try:
            with open(self.current_tab.filename, "w", newline="") as f:
                writer = csv.writer(f, delimiter="\t")
                writer.writerow(self.current_tab.headers)
                writer.writerows(self.current_tab.data)
            messagebox.showinfo("Success", "Data saved successfully")
            self.current_tab.modified = False
        except Exception as e:
            messagebox.showerror("Error", f"Error saving file: {str(e)}")

    def save_as_data(self):
        """Save As file"""
        if not self.current_tab:
            messagebox.showwarning("Warning", "No active tab")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )

        if file_path:
            self.current_tab.filename = file_path
            self.save_data()
            
            # Update tab name and window title
            tab_name = os.path.basename(file_path)
            self.current_tab.update_tab_name(tab_name)
            self.update_title()
            
            # Add to recent files
            self.add_to_recent_files(file_path)

    def show_help(self):
        """Show help dialog with keyboard shortcuts"""
        # Create help window
        help_window = tk.Toplevel(self.root)
        help_window.title("Keyboard Shortcuts")
        help_window.geometry("600x600")
        help_window.resizable(True, True)
        
        # Add to active popups
        self.active_popups.append(help_window)
        help_window.protocol("WM_DELETE_WINDOW", lambda: self._remove_popup(help_window))
        
        # Bind ESC and Ctrl+W to close
        help_window.bind("<Escape>", lambda event: self._remove_popup(help_window))
        help_window.bind("<Control-w>", lambda event: self._remove_popup(help_window))
        # Bind Ctrl+N to cancel
        help_window.bind("<Control-n>", lambda event: self._remove_popup(help_window))
        
        # Auto-focus the new window
        help_window.focus_force()
        
        # Create a frame for scrolling
        frame = tk.Frame(help_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a canvas and scrollbar
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create a frame inside the canvas
        content_frame = tk.Frame(canvas)
        canvas_frame = canvas.create_window((0, 0), window=content_frame, anchor="nw")
        
        # Title
        tk.Label(content_frame, text="Keyboard Shortcuts", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Navigation shortcuts
        tk.Label(content_frame, text="Navigation", font=('Arial', 12, 'bold')).pack(anchor="w", pady=5)
        shortcuts = [
            ("h", "Scroll left"),
            ("j", "Move down"),
            ("k", "Move up"),
            ("l", "Scroll right"),
            ("Ctrl+u", "Page up"),
            ("Ctrl+d", "Page down"),
            ("i", "Jump to selection start (in selection mode)"),
            ("o", "Jump to selection end (in selection mode)")
        ]
        self._create_shortcut_table(content_frame, shortcuts)
        
        # Editing shortcuts
        tk.Label(content_frame, text="\nEditing", font=('Arial', 12, 'bold')).pack(anchor="w", pady=5)
        shortcuts = [
            ("i", "Edit current row"),
            ("e", "Edit current row"),
            ("Enter", "Edit current row"),
            ("o", "Add new row below"),
            ("O", "Add new row above"),
            ("a", "Add new row below"),
            ("d", "Delete selected rows")
        ]
        self._create_shortcut_table(content_frame, shortcuts)
        
        # Selection shortcuts
        tk.Label(content_frame, text="\nSelection", font=('Arial', 12, 'bold')).pack(anchor="w", pady=5)
        shortcuts = [
            ("v", "Toggle selection mode"),
            ("V", "Toggle selection mode"),
            ("Ctrl+click", "Toggle item in selection"),
            ("j/k", "Navigate with selection (in selection mode)")
        ]
        self._create_shortcut_table(content_frame, shortcuts)
        
        # Search shortcuts
        tk.Label(content_frame, text="\nSearch", font=('Arial', 12, 'bold')).pack(anchor="w", pady=5)
        shortcuts = [
            ("f", "Activate search"),
            ("/", "Activate search"),
            ("Ctrl+f", "Activate search")
        ]
        self._create_shortcut_table(content_frame, shortcuts)
        
        # File operations
        tk.Label(content_frame, text="\nFile Operations", font=('Arial', 12, 'bold')).pack(anchor="w", pady=5)
        shortcuts = [
            ("Ctrl+s", "Save current file"),
            ("Ctrl+w", "Close current tab (only when focus is on tab)"),
            ("Ctrl+o", "Open file"),
            ("Ctrl+Shift+o", "Open folder"),
            ("Ctrl+r", "Open restore interface"),
            ("Ctrl+b", "Open backups folder"),
            ("Ctrl+Shift+b", "Toggle auto backup"),
            ("Restore Button", "Restore from backup"),
            ("Open Backups Button", "Open backup folder")
        ]
        self._create_shortcut_table(content_frame, shortcuts)
        
        # General shortcuts
        tk.Label(content_frame, text="\nGeneral", font=('Arial', 12, 'bold')).pack(anchor="w", pady=5)
        shortcuts = [
            ("ESC", "Cancel operation / Exit selection mode / Close popup")
        ]
        self._create_shortcut_table(content_frame, shortcuts)
        
        # Update scroll region when content changes
        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_frame, width=event.width)
            
        content_frame.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", on_configure)
        
        # Add close button
        tk.Button(help_window, text="Close", command=help_window.destroy).pack(pady=10)
        
        # Center the window
        help_window.update_idletasks()
        width = help_window.winfo_width()
        height = help_window.winfo_height()
        x = (help_window.winfo_screenwidth() // 2) - (width // 2)
        y = (help_window.winfo_screenheight() // 2) - (height // 2)
        help_window.geometry(f"{width}x{height}+{x}+{y}")
        
    def _create_shortcut_table(self, parent, shortcuts):
        """Create a table of shortcuts and their descriptions"""
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, anchor="w")
        
        for shortcut, description in shortcuts:
            # Create a frame for each row
            row_frame = tk.Frame(frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            # Shortcut (fixed width)
            shortcut_label = tk.Label(row_frame, text=shortcut, width=15, font=('Arial', 10, 'bold'))
            shortcut_label.pack(side=tk.LEFT, padx=5)
            
            # Description
            desc_label = tk.Label(row_frame, text=description, anchor="w", justify="left")
            desc_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def create_widgets(self):
        """Create UI components"""
        # Bind application-wide keyboard shortcuts
        self.bind_application_shortcuts()
        
        # Top button frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        # File operations group
        file_group_frame = tk.Frame(button_frame)
        file_group_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(file_group_frame, text="", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=0)
        
        file_buttons_frame = tk.Frame(file_group_frame)
        file_buttons_frame.pack(side=tk.LEFT)
        tk.Button(file_buttons_frame, text="Open", command=self.open_file_dialog).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(file_buttons_frame, text="Open Folder", command=self.open_folder_dialog).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(file_buttons_frame, text="Save", command=self.save_data).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(file_buttons_frame, text="Save As", command=self.save_as_data).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(file_buttons_frame, text="Restore", command=self.restore_backup).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(file_buttons_frame, text="Open Backups", command=self.open_backup_folder).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(file_buttons_frame, text="Help", command=self.show_help).pack(
            side=tk.LEFT, padx=5
        )
        
        # Backup toggle switch
        backup_toggle_frame = tk.Frame(button_frame)
        backup_toggle_frame.pack(side=tk.LEFT, padx=5)
        self.backup_var = tk.BooleanVar(value=self.backup_enabled)
        backup_checkbox = tk.Checkbutton(
            backup_toggle_frame,
            text="Auto Backup",
            variable=self.backup_var,
            command=lambda: setattr(self, 'backup_enabled', self.backup_var.get())
        )
        backup_checkbox.pack(side=tk.LEFT)

        # Lazy load threshold setting
        lazy_load_frame = tk.Frame(button_frame)
        lazy_load_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(lazy_load_frame, text="Lazy Load Threshold:").pack(side=tk.LEFT, padx=(0, 5))
        self.lazy_load_var = tk.StringVar(value=f"{self.lazy_load_threshold}M")
        threshold_options = ["1M", "5M", "10M", "20M", "50M", "100M"]
        threshold_menu = tk.OptionMenu(lazy_load_frame, self.lazy_load_var, *threshold_options)
        threshold_menu.pack(side=tk.LEFT, padx=5)
        self.lazy_load_var.trace_add("write", lambda *args: self._update_lazy_load_threshold())

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Bind double click on tab to close other tabs
        self.notebook.bind("<Double-1>", self.on_tab_double_click)
        
        # Bind middle mouse button click on tab to close current tab
        self.notebook.bind("<Button-2>", self.on_tab_middle_click)
        
    def _update_lazy_load_threshold(self):
        """Update the lazy load threshold when user changes the setting"""
        try:
            # Extract numeric value from the string (e.g., "10M" -> 10)
            value_str = self.lazy_load_var.get()
            if value_str.endswith('M'):
                self.lazy_load_threshold = int(value_str[:-1])
        except ValueError:
            # If parsing fails, default to 10MB
            self.lazy_load_threshold = 10
            self.lazy_load_var.set("10M")
        
    def new_tab(self):
        """Create a new blank tab"""
        new_tab = FileTab(self, self.notebook, "Untitled")
        new_tab.data = []
        new_tab.create_tab_widgets()  # Ensure tree is initialized first
        new_tab.populate_table()
        
        self.notebook.add(new_tab.tab_frame, text="Untitled")
        self.notebook.select(new_tab.tab_frame)
        self.tabs.append(new_tab)
        self.current_tab = new_tab
        
        self.update_title()
        
    def on_tab_double_click(self, event):
        """Handle double click on tab to close other tabs"""
        # Check if event is on a tab header
        try:
            # Get the clicked tab's index
            x, y = event.x, event.y
            tab_idx = self.notebook.index("@%d,%d" % (x, y))
            if tab_idx is not None:
                self.close_other_tabs(tab_idx)
        except tk.TclError:
            # Event not on a tab header, do nothing
            pass
            
    def on_tab_middle_click(self, event):
        """Handle middle mouse button click on tab to close current tab"""
        # Check if event is on a tab header
        try:
            # Get the clicked tab's index
            x, y = event.x, event.y
            tab_idx = self.notebook.index("@%d,%d" % (x, y))
            if tab_idx is not None and 0 <= tab_idx < len(self.tabs):
                # Save the current tab index
                current_idx = self.notebook.index(self.notebook.select())
                
                # If the clicked tab is the current tab, just close it
                if tab_idx == current_idx:
                    self.close_tab()
                else:
                    # If the clicked tab is not the current tab, select it first then close it
                    self.notebook.select(self.tabs[tab_idx].tab_frame)
                    self.current_tab = self.tabs[tab_idx]
                    self.close_tab()
        except tk.TclError:
            # Event not on a tab header, do nothing
            pass
            
    def close_other_tabs(self, keep_index):
        """Close all tabs except the one at the given index"""
        if len(self.tabs) <= 1:
            return
            
        # Check if there are unsaved changes in any tab
        unsaved_tabs = [i for i, tab in enumerate(self.tabs) if i != keep_index and tab.modified]
        
        if unsaved_tabs:
            response = messagebox.askyesnocancel(
                "Save Changes", 
                "There are unsaved changes in other tabs. Do you want to save before closing?"
            )
            if response is None:  # Cancel
                return
            if response:  # Yes
                for i in unsaved_tabs:
                    if self.tabs[i].filename:
                        # Temporarily set current_tab to save
                        old_current = self.current_tab
                        self.current_tab = self.tabs[i]
                        self.save_data()
                        self.current_tab = old_current
                    else:
                        # File has no name, can't save
                        if not messagebox.askyesno(
                            "Save As",
                            f"File '{self.tabs[i].tab_name}' has no name. Would you like to save it?"
                        ):
                            # User chose not to save, proceed with closing
                            pass
                        else:
                            # Temporarily set current_tab to save as
                            old_current = self.current_tab
                            self.current_tab = self.tabs[i]
                            if not self.save_as_data():
                                # Save as cancelled, abort closing other tabs
                                self.current_tab = old_current
                                return
                            self.current_tab = old_current
        
        # Close all tabs except the one to keep
        tabs_to_close = [i for i in range(len(self.tabs)) if i != keep_index]
        # Close from last to first to avoid index issues
        for i in reversed(tabs_to_close):
            self.notebook.forget(self.tabs[i].tab_frame)
            del self.tabs[i]
        
        # Update current tab
        self.current_tab = self.tabs[0]
        self.update_title()
        
    def open_folder_dialog(self, dashboard=None):
        """Open folder selection dialog and open all tsv/csv/txt files in the selected folder"""
        folder_path = filedialog.askdirectory(
            title="Select Folder containing TSV/CSV/TXT Files"
        )
        
        if folder_path:
            # Close dashboard if provided
            if dashboard:
                dashboard.destroy()
                
            # Define supported file extensions
            supported_extensions = ['.tsv', '.csv', '.txt']
            files_opened = False
            
            # Iterate through all files in the selected folder
            for filename in os.listdir(folder_path):
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in supported_extensions:
                    file_path = os.path.join(folder_path, filename)
                    self.open_file(file_path)
                    files_opened = True
            
            if not files_opened:
                messagebox.showinfo("Info", "No TSV/CSV/TXT files found in the selected folder.")
            
            return files_opened
        
        return False
        
    def close_tab(self):
        """Close the current tab"""
        if not self.current_tab:
            return
            
        # Check if there are unsaved changes
        if self.current_tab.modified:
            response = messagebox.askyesnocancel("Save Changes", 
                "Do you want to save changes to this file?")
            if response is None:  # Cancel
                return
            if response:  # Yes
                if self.current_tab.filename:
                    self.save_data()
                else:
                    if not self.save_as_data():
                        return
        
        # Remove the tab from the notebook and tabs list
        tab_to_close = self.current_tab
        self.notebook.forget(self.current_tab.tab_frame)
        self.tabs.remove(self.current_tab)
        
        # Update current tab
        if self.tabs:
            self.current_tab = self.tabs[0]
            self.notebook.select(self.current_tab.tab_frame)
        else:
            self.current_tab = None
            self.new_tab()  # Create a new blank tab if all are closed
        
        self.update_title()
        
    def on_tab_changed(self, event):
        """Handle tab change event"""
        if not self.notebook.tabs():
            self.current_tab = None
            return
            
        # Get the selected tab index
        current_index = self.notebook.index(self.notebook.select())
        # Update current_tab based on index
        if 0 <= current_index < len(self.tabs):
            self.current_tab = self.tabs[current_index]
            self.update_title()

    def populate_table(self, data=None):
        """Populate table with data - This is now called from the FileTab class"""
        pass

    def refresh_table(self):
        """Refresh table"""
        if not self.current_tab:
            messagebox.showwarning("Warning", "No active tab")
            return
            
        if self.current_tab.filename:
            self.current_tab.load_data()
            self.current_tab.populate_table()
        else:
            messagebox.showwarning("Warning", "No file opened in this tab")

    def add_row(self):
        """Delegate to current tab's add_row method"""
        if not self.current_tab:
            messagebox.showwarning("Warning", "No active tab")
            return
            
        self.current_tab.add_row()

    def edit_row(self, tab, event):
        """Delegate to tab's edit_row method"""
        if tab:
            tab.edit_row(event)

    def delete_row(self):
        """Delegate to current tab's delete_row method"""
        if not self.current_tab:
            messagebox.showwarning("Warning", "No active tab")
            return
            
        self.current_tab.delete_row()

    def real_time_search(self, tab=None):
        """Real-time fuzzy search with column selection"""
        if not tab:
            tab = self.current_tab
            if not tab:
                return
                
        search_term = tab.search_var.get().lower()
        threshold = tab.threshold_var.get()
        search_column = getattr(tab, 'search_column_var', None)
        if search_column:
            search_column = search_column.get()
        else:
            search_column = "All Columns"

        if not search_term:
            tab.populate_table()
            return

        # Prepare data for fuzzy search
        search_data = []
        
        # In lazy load mode, data might not be fully loaded, so we need to read from file
        if tab.is_large_file:
            try:
                with open(tab.filename, "r") as f:
                    reader = csv.reader(f, delimiter="\t")
                    # Skip header
                    next(reader)
                    
                    # Search through all rows in the file
                    for row in reader:
                        if not row:  # Skip empty rows
                            continue
                            
                        # Check if we're searching all columns or specific columns
                        if search_column == "All Columns":
                            # Combine all row values into one string for searching
                            row_text = " ".join(str(cell) for cell in row).lower()
                            score = fuzz.partial_ratio(search_term, row_text)
                        else:
                            # Search only in the selected column
                            if search_column in tab.headers:
                                column_index = tab.headers.index(search_column)
                                if column_index < len(row):
                                    cell_value = str(row[column_index]).lower()
                                    score = fuzz.partial_ratio(search_term, cell_value)
                                else:
                                    score = 0
                            else:
                                score = 0
                        
                        if score >= threshold:
                            search_data.append(row)
            except Exception as e:
                print(f"Error during search in lazy load mode: {str(e)}")
        else:
            # For normal mode, search in memory data
            for row in tab.data:
                # Check if we're searching all columns or specific columns
                if search_column == "All Columns":
                    # Combine all row values into one string for searching
                    row_text = " ".join(str(cell) for cell in row).lower()
                    score = fuzz.partial_ratio(search_term, row_text)
                else:
                    # Search only in the selected column
                    if search_column in tab.headers:
                        column_index = tab.headers.index(search_column)
                        if column_index < len(row):
                            cell_value = str(row[column_index]).lower()
                            score = fuzz.partial_ratio(search_term, cell_value)
                        else:
                            score = 0
                    else:
                        score = 0

                if score >= threshold:
                    search_data.append(row)

        tab.populate_table(search_data)
        
    def cancel_all_operations(self):
        """Cancel all operations and close all popups"""
        # Create a copy to iterate over to avoid modification during iteration
        popups_to_close = list(self.active_popups)
        for popup in popups_to_close:
            try:
                if popup.winfo_exists():
                    popup.destroy()
            except Exception as e:
                print(f"Error closing popup: {e}")
        # Clear the active popups list
        self.active_popups.clear()
        
    def _remove_popup(self, popup):
        if popup in self.active_popups:
            self.active_popups.remove(popup)
        
        # Destroy the popup window
        try:
            if popup.winfo_exists():
                popup.destroy()
        except Exception as e:
            print(f"Error destroying popup: {e}")
        
        # Focus next window after this one is removed
        if self.active_popups:
            # Focus the last remaining popup (most recently opened)
            next_popup = self.active_popups[-1]
            try:
                if next_popup.winfo_exists():
                    next_popup.focus_force()
            except Exception as e:
                print(f"Error focusing next popup: {e}")
        else:
            # If no popups left, focus on the current tab's treeview
            if hasattr(self, 'current_tab') and self.current_tab:
                try:
                    self.current_tab.tree.focus_force()
                except Exception as e:
                    print(f"Error focusing on tab: {e}")
                    # Fallback to main window focus if tab focusing fails
                    self.root.focus_force()
            else:
                # If no current tab, focus main window
                self.root.focus_force()
            
    def toggle_auto_backup(self):
        """Toggle auto backup functionality"""
        self.backup_enabled = not self.backup_enabled
        self.backup_var.set(self.backup_enabled)
        status = "enabled" if self.backup_enabled else "disabled"
        messagebox.showinfo("Auto Backup", f"Auto backup has been {status}")
        
    def load_recent_files(self):
        """Load recently opened files from configuration with deduplication"""
        if os.path.exists(self.recent_files_path):
            try:
                with open(self.recent_files_path, 'r') as f:
                    loaded_files = json.load(f)
                    
                    # Deduplicate while preserving LRU order (first occurrence keeps position)
                    seen = set()
                    self.recent_files = []
                    for file_path in loaded_files:
                        if file_path not in seen:
                            seen.add(file_path)
                            self.recent_files.append(file_path)
                    
                    # Ensure we don't exceed max_recent_files
                    if len(self.recent_files) > self.max_recent_files:
                        self.recent_files = self.recent_files[:self.max_recent_files]
            except Exception as e:
                print(f"Error loading recent files: {str(e)}")
                self.recent_files = []
        
    def save_recent_files(self):
        """Save recently opened files to configuration"""
        try:
            with open(self.recent_files_path, 'w') as f:
                json.dump(self.recent_files, f)
        except Exception as e:
            print(f"Error saving recent files: {str(e)}")
            
    def add_to_recent_files(self, file_path):
        """Add a file path to recent files list"""
        # Remove if already exists to keep only the most recent occurrence
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
            
        # Add to the beginning of the list
        self.recent_files.insert(0, file_path)
        
        # Keep only the max number of recent files
        if len(self.recent_files) > self.max_recent_files:
            self.recent_files = self.recent_files[:self.max_recent_files]
            
        # Save the updated list
        self.save_recent_files()
        
    def show_history_dashboard(self):
        """Show history dashboard with recently opened files"""
        # Create dashboard window
        dashboard = tk.Toplevel(self.root)
        dashboard.title("File History")
        dashboard.geometry("1035x500")  # Set default width to 900
        dashboard.resizable(True, True)  # Allow resizing to accommodate long file paths
        
        # Center the dashboard window
        dashboard.update_idletasks()
        width = dashboard.winfo_width()
        height = dashboard.winfo_height()
        x = (dashboard.winfo_screenwidth() // 2) - (width // 2)
        y = (dashboard.winfo_screenheight() // 2) - (height // 2)
        dashboard.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Make dashboard modal
        dashboard.transient(self.root)
        dashboard.grab_set()
        
        # Bind ESC and Ctrl+W to close the dashboard
        dashboard.bind("<Escape>", lambda event: dashboard.destroy())
        dashboard.bind("<Control-w>", lambda event: dashboard.destroy())
        
        # Add title label
        title_label = tk.Label(dashboard, text="Recent Files", font=('Arial', 14, 'bold'))
        title_label.pack(pady=15)
        
        # Create listbox with scrollbars
        frame = tk.Frame(dashboard)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create listbox with both scrollbars and adjusted width
        self.recent_files_listbox = tk.Listbox(
            frame, 
            yscrollcommand=v_scrollbar.set, 
            xscrollcommand=h_scrollbar.set,  # Add horizontal scroll support
            width=100,  # Increase default width for longer paths
            height=10, 
            font=('Arial', 10),
            selectmode=tk.EXTENDED,
            exportselection=False
        )
        self.recent_files_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        v_scrollbar.config(command=self.recent_files_listbox.yview)
        h_scrollbar.config(command=self.recent_files_listbox.xview)
        
        # Populate listbox with recent files
        for file_path in self.recent_files:
            display_name = f"{os.path.basename(file_path)} - {file_path}"
            self.recent_files_listbox.insert(tk.END, display_name)
        
        # Bind double click to open file
        self.recent_files_listbox.bind('<Double-1>', lambda event: self.open_selected_file(dashboard))
        
        # Add buttons frame
        buttons_frame = tk.Frame(dashboard)
        buttons_frame.pack(fill=tk.X, padx=20, pady=15)
        
        # File operations group
        file_group_frame = tk.Frame(buttons_frame)
        file_group_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(file_group_frame, text="File Operations:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=2)
        
        file_buttons_frame = tk.Frame(file_group_frame)
        file_buttons_frame.pack(side=tk.LEFT)
        # Open button
        open_button = tk.Button(
            file_buttons_frame, 
            text="Open Selected", 
            command=lambda: self.open_selected_file(dashboard),
            width=15
        )
        open_button.pack(side=tk.LEFT, padx=5)
        
        # New file button
        new_button = tk.Button(
            file_buttons_frame, 
            text="New File", 
            command=lambda: self.create_new_file(dashboard),
            width=15
        )
        new_button.pack(side=tk.LEFT, padx=5)
        
        # Navigation group
        nav_group_frame = tk.Frame(buttons_frame)
        nav_group_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(nav_group_frame, text="Navigation:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=2)
        
        nav_buttons_frame = tk.Frame(nav_group_frame)
        nav_buttons_frame.pack(side=tk.LEFT)
        # Browse button
        browse_button = tk.Button(
            nav_buttons_frame, 
            text="Browse Files", 
            command=lambda: self.browse_files(dashboard),
            width=15
        )
        browse_button.pack(side=tk.LEFT, padx=5)
        
        # Open Folder button
        open_folder_button = tk.Button(
            nav_buttons_frame, 
            text="Open Folder", 
            command=lambda: self.open_folder_dialog(dashboard),
            width=15
        )
        open_folder_button.pack(side=tk.LEFT, padx=5)
        
        # History management
        history_group_frame = tk.Frame(buttons_frame)
        history_group_frame.pack(side=tk.RIGHT, padx=5)
        tk.Label(history_group_frame, text="History Management:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=2)
        
        history_buttons_frame = tk.Frame(history_group_frame)
        history_buttons_frame.pack(side=tk.LEFT)
        # Clear history button
        clear_button = tk.Button(
            history_buttons_frame, 
            text="Clear History", 
            command=self.clear_history,
            width=15
        )
        clear_button.pack(side=tk.LEFT, padx=5)
        
    def open_selected_file(self, dashboard):
        """Open the selected files from the history dashboard"""
        selection = self.recent_files_listbox.curselection()
        if selection:
            dashboard.destroy()
            
            # Process selected files
            files_to_open = []
            invalid_files = []
            
            # First collect all valid files and identify invalid ones
            for index in selection:
                if 0 <= index < len(self.recent_files):
                    file_path = self.recent_files[index]
                    if os.path.exists(file_path):
                        files_to_open.append(file_path)
                    else:
                        invalid_files.append(file_path)
                        # Remove non-existent file from recent files
                        self.recent_files.pop(index)
            
            # Save updated recent files list if any invalid files were removed
            if invalid_files:
                self.save_recent_files()
                
                # Show error message for invalid files
                if len(invalid_files) == 1:
                    messagebox.showerror("Error", f"File not found: {invalid_files[0]}")
                else:
                    messagebox.showerror("Error", f"Files not found: {', '.join(invalid_files)}")
            
            # Open all valid files
            for file_path in files_to_open:
                self.open_file(file_path)
                self.add_to_recent_files(file_path)  # Update recent files order
            
            # If no files were opened and there are still recent files, show dashboard again
            if not files_to_open and self.recent_files:
                self.show_history_dashboard()
            elif not files_to_open and not self.recent_files:
                self.open_file_dialog()
            
    def create_new_file(self, dashboard):
        """Create a new file"""
        dashboard.destroy()
        self.new_tab()
        messagebox.showinfo("New File", "New file created. Use 'Save As' to save your work.")
        
    def browse_files(self, dashboard):
        """Browse for files"""
        dashboard.destroy()
        self.open_file_dialog()
        
    def clear_history(self):
        """Clear the recent files history"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all recent file history?"):
            self.recent_files = []
            self.save_recent_files()
            # Clear the listbox
            self.recent_files_listbox.delete(0, tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = TableManager(root)
    root.mainloop()
