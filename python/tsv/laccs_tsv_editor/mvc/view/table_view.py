import tkinter as tk
from tkinter import ttk
import os
from .base_view import BaseView

class TableView(BaseView):
    """View for managing the main application window and table display"""
    
    def __init__(self, root):
        super().__init__(root)
        self.notebook = None
        self.current_tab = None
        self.tabs = []
        self.button_frame = None
        
        # Setup the main window
        self.setup_main_window()
        
    def setup_main_window(self):
        """Setup the main application window"""
        # Set minimum window size
        self.root.minsize(800, 600)
        
        # Create button frame
        self.create_button_frame()
        
        # Create notebook for tabs
        self.create_notebook()
    
    def create_button_frame(self):
        """Create the button frame with all control buttons"""
        self.button_frame = self.create_frame(self.root)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)
    
    def add_file_operations_buttons(self, new_callback, open_callback, save_callback, save_as_callback):
        """Add file operation buttons to the button frame"""
        file_frame = self.create_frame(self.button_frame)
        file_frame.pack(side=tk.LEFT, padx=5)
        
        # New button
        new_button = self.create_button(file_frame, "New", new_callback, width=10)
        new_button.pack(side=tk.LEFT, padx=2)
        
        # Open button
        open_button = self.create_button(file_frame, "Open", open_callback, width=10)
        open_button.pack(side=tk.LEFT, padx=2)
        
        # Save button
        save_button = self.create_button(file_frame, "Save", save_callback, width=10)
        save_button.pack(side=tk.LEFT, padx=2)
        
        # Save As button
        save_as_button = self.create_button(file_frame, "Save As", save_as_callback, width=10)
        save_as_button.pack(side=tk.LEFT, padx=2)
    
    def add_edit_operations_buttons(self, add_row_callback, delete_row_callback):
        """Add edit operation buttons to the button frame"""
        edit_frame = self.create_frame(self.button_frame)
        edit_frame.pack(side=tk.LEFT, padx=5)
        
        # Add Row button
        add_row_button = self.create_button(edit_frame, "Add Row", add_row_callback, width=10)
        add_row_button.pack(side=tk.LEFT, padx=2)
        
        # Delete Row button
        delete_row_button = self.create_button(edit_frame, "Delete Row", delete_row_callback, width=10)
        delete_row_button.pack(side=tk.LEFT, padx=2)
    
    def add_backup_checkbox(self, variable, command):
        """Add auto backup checkbox to the button frame"""
        backup_checkbox = self.create_checkbutton(
            self.button_frame,
            "Auto Backup",
            variable=variable,
            command=command
        )
        backup_checkbox.pack(side=tk.LEFT)
    
    def add_lazy_load_setting(self, variable, options, command):
        """Add lazy load threshold setting to the button frame"""
        lazy_load_frame = self.create_frame(self.button_frame)
        lazy_load_frame.pack(side=tk.LEFT, padx=5)
        
        # Label
        tk.Label(lazy_load_frame, text="Lazy Load Threshold:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Option menu
        threshold_menu = tk.OptionMenu(lazy_load_frame, variable, *options)
        threshold_menu.pack(side=tk.LEFT, padx=5)
        
        # Bind the command
        variable.trace_add("write", lambda *args: command())
    
    def create_notebook(self):
        """Create the notebook widget for tab management"""
        self.notebook = tk.ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_tab(self, title):
        """Create a new tab in the notebook"""
        tab_frame = self.create_frame(self.notebook)
        self.notebook.add(tab_frame, text=title)
        return tab_frame
    
    def select_tab(self, tab_frame):
        """Select a specific tab"""
        self.notebook.select(tab_frame)
    
    def update_tab_title(self, tab_frame, title):
        """Update the title of a specific tab"""
        tab_index = self.notebook.index(tab_frame)
        self.notebook.tab(tab_index, text=title)
    
    def close_tab(self, tab_frame):
        """Close a specific tab"""
        try:
            self.notebook.forget(tab_frame)
        except tk.TclError:
            pass
    
    def create_table_widgets(self, parent, columns):
        """Create the table widgets (treeview and scrollbars)"""
        # Create a frame for the table and scrollbars
        table_frame = self.create_frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview
        tree = self.create_treeview(table_frame, columns=columns)
        
        # Configure columns
        for col in columns:
            tree.heading(col, text=col, anchor=tk.W)
            tree.column(col, width=100, anchor=tk.W)
        
        # Create vertical scrollbar
        v_scrollbar = self.create_scrollbar(table_frame, tk.VERTICAL, tree.yview)
        tree.configure(yscrollcommand=v_scrollbar.set)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create horizontal scrollbar
        h_scrollbar = self.create_scrollbar(table_frame, tk.HORIZONTAL, tree.xview)
        tree.configure(xscrollcommand=h_scrollbar.set)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Pack treeview
        tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        return tree, table_frame
    
    def create_search_widgets(self, parent):
        """Create search widgets"""
        search_frame = self.create_frame(parent)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Search label
        search_label = self.create_label(search_frame, "Search:")
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Search entry
        search_var = tk.StringVar()
        search_entry = self.create_entry(search_frame, variable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Threshold label
        threshold_label = self.create_label(search_frame, "Threshold:")
        threshold_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Threshold entry
        threshold_var = tk.IntVar(value=70)
        threshold_entry = self.create_entry(search_frame, variable=threshold_var, width=5)
        threshold_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Column selection (optional for now)
        search_column_var = tk.StringVar(value="All Columns")
        
        return search_var, threshold_var, search_column_var, search_frame
    
    def populate_table(self, tree, data, columns):
        """Populate the table with data"""
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)
        
        # Insert new items
        for i, row in enumerate(data):
            # Ensure row has the same length as columns
            while len(row) < len(columns):
                row.append('')
            
            # Truncate long strings for display
            display_row = [str(cell)[:100] + '...' if len(str(cell)) > 100 else str(cell) for cell in row]
            
            tree.insert('', tk.END, iid=str(i), values=display_row)
    
    def create_edit_window(self, title, headers, row_data=None):
        """Create a window for editing rows"""
        # Create popup window
        edit_window = self.create_popup_window(title, width=600, height=400)
        
        # Create a frame with scrollbars for the editing fields
        main_frame = self.create_frame(edit_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create canvas for scrolling
        canvas = tk.Canvas(main_frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create scrollbars
        v_scrollbar = self.create_scrollbar(main_frame, tk.VERTICAL, canvas.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = self.create_scrollbar(main_frame, tk.HORIZONTAL, canvas.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Configure canvas
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Create frame inside canvas
        edit_frame = self.create_frame(canvas)
        canvas_frame = canvas.create_window((0, 0), window=edit_frame, anchor="nw")
        
        # Store entry variables
        entry_vars = []
        
        # Create labels and entries for each column
        for i, header in enumerate(headers):
            # Create a frame for each row
            row_frame = self.create_frame(edit_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            # Create label
            label = self.create_label(row_frame, f"{header}:", width=20, anchor=tk.W)
            label.pack(side=tk.LEFT, padx=5)
            
            # Create entry
            var = tk.StringVar()
            if row_data and i < len(row_data):
                var.set(str(row_data[i]))
            entry = self.create_entry(row_frame, variable=var, width=50)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            entry_vars.append(var)
        
        # Create button frame
        button_frame = self.create_frame(edit_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Create OK and Cancel buttons
        ok_button = self.create_button(button_frame, "OK", lambda: None, width=10)
        ok_button.pack(side=tk.RIGHT, padx=5)
        
        cancel_button = self.create_button(button_frame, "Cancel", edit_window.destroy, width=10)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Update scrollregion when the frame size changes
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        edit_frame.bind("<Configure>", on_frame_configure)
        
        # Make canvas expand with window
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_frame, width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)
        
        return edit_window, entry_vars, ok_button
    
    def create_history_dashboard(self, recent_files):
        """Create the recent files history dashboard"""
        dashboard = self.create_popup_window("File History", width=1035, height=500)
        
        # Add title label
        title_label = self.create_label(dashboard, "Recent Files", font=('Arial', 14, 'bold'))
        title_label.pack(pady=15)
        
        # Create listbox with scrollbars
        frame = self.create_frame(dashboard)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Vertical scrollbar
        v_scrollbar = self.create_scrollbar(frame, tk.VERTICAL, None)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Horizontal scrollbar
        h_scrollbar = self.create_scrollbar(frame, tk.HORIZONTAL, None)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create listbox with both scrollbars and adjusted width
        recent_files_listbox = tk.Listbox(
            frame,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            width=100,
            height=10,
            font=('Arial', 10),
            selectmode=tk.EXTENDED,
            exportselection=False
        )
        recent_files_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        v_scrollbar.config(command=recent_files_listbox.yview)
        h_scrollbar.config(command=recent_files_listbox.xview)
        
        # Populate listbox with recent files
        for file_path in recent_files:
            display_name = f"{os.path.basename(file_path)} - {file_path}"
            recent_files_listbox.insert(tk.END, display_name)
        
        # Add buttons frame
        buttons_frame = self.create_frame(dashboard)
        buttons_frame.pack(fill=tk.X, padx=20, pady=15)
        
        # Return dashboard and listbox for further configuration
        return dashboard, recent_files_listbox, buttons_frame
    
    def create_help_window(self):
        """Create the help window"""
        help_window = self.create_popup_window("Help", width=600, height=500)
        
        # Create text widget with scrollbar
        main_frame = self.create_frame(help_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Vertical scrollbar
        v_scrollbar = self.create_scrollbar(main_frame, tk.VERTICAL, None)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create text widget
        help_text = tk.Text(main_frame, wrap=tk.WORD, yscrollcommand=v_scrollbar.set)
        help_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        v_scrollbar.config(command=help_text.yview)
        
        # Make text widget read-only
        help_text.config(state=tk.DISABLED)
        
        return help_window, help_text