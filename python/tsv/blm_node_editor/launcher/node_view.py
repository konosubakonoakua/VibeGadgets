import tkinter as tk
from tkinter import ttk, scrolledtext, Menu


class NodeView:
    def __init__(self, root):
        self.root = root
        self.root.title("BLM Node Manager")
        self.root.geometry("1200x700")

        # Configure font support
        self.style = ttk.Style()
        self.style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        self.style.configure("Treeview", font=("Arial", 10))

        self.root.grid_columnconfigure(0, weight=1)

        # Create main vertical paned window for all three rows with adjustable dividers
        self.main_vertical_paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.main_vertical_paned.grid(row=0, column=0, sticky="nsew")

        self.nodes_table_frame = ttk.Frame(self.main_vertical_paned)
        self.main_vertical_paned.add(self.nodes_table_frame, weight=7)
        self.nodes_table_frame.grid_rowconfigure(0, weight=1)
        self.nodes_table_frame.grid_columnconfigure(0, weight=1)

        self.left_frame = ttk.LabelFrame(self.nodes_table_frame, text="Nodes Table")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.second_row_frame = ttk.Frame(self.main_vertical_paned)
        self.main_vertical_paned.add(self.second_row_frame, weight=4)
        self.second_row_frame.grid_rowconfigure(0, weight=1)
        self.second_row_frame.grid_columnconfigure(0, weight=1)

        self.second_row_paned = ttk.PanedWindow(
            self.second_row_frame, orient=tk.HORIZONTAL
        )
        self.second_row_paned.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

        self.status_frame = ttk.LabelFrame(
            self.second_row_paned, text="Node Service Status"
        )
        self.status_frame.grid_propagate(True)
        self.second_row_paned.add(self.status_frame, weight=1)

        self.auth_frame = ttk.LabelFrame(
            self.second_row_paned, text="Node Authentication", width=160, height=180
        )
        self.auth_frame.grid_propagate(
            False
        )  # Prevent frame from resizing based on content
        self.second_row_paned.add(self.auth_frame, weight=1)

        self.params_frame = ttk.LabelFrame(
            self.second_row_paned, text="Node Service Parameters", width=300, height=300
        )
        self.params_frame.grid_propagate(
            False
        )  # Prevent frame from resizing based on content
        self.second_row_paned.add(self.params_frame, weight=2)

        self.create_ssh_buttons()

        self.create_treeview()

        self.create_status_display()

        self.log_frame_container = ttk.Frame(self.main_vertical_paned)
        self.main_vertical_paned.add(self.log_frame_container, weight=1)
        self.log_frame_container.grid_rowconfigure(0, weight=1)
        self.log_frame_container.grid_columnconfigure(0, weight=1)

        self.create_log_display()

    def create_ssh_buttons(self):
        # SSH operation buttons have been removed, functionality is available in right-click context menu
        pass

    def create_treeview(self):
        # Create Treeview and scrollbars
        frame = ttk.Frame(self.left_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure internal grid for better layout management
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        # Horizontal scrollbar
        h_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Vertical scrollbar
        v_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Create Treeview
        self.tree = ttk.Treeview(
            frame,
            columns=[],
            show="headings",
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set,
        )

        h_scroll.config(command=self.tree.xview)
        v_scroll.config(command=self.tree.yview)

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Create right-click menu for the treeview
        self.create_treeview_context_menu()

    def create_treeview_context_menu(self):
        # Create context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)

        # Add menu items corresponding to the buttons
        self.context_menu.add_command(
            label="Start Service", command=lambda: self.start_service_callback()
        )
        self.context_menu.add_command(
            label="Stop Service", command=lambda: self.stop_service_callback()
        )
        self.context_menu.add_command(
            label="Restart Service", command=lambda: self.restart_service_callback()
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Deploy", command=lambda: self.deploy_service_callback()
        )
        self.context_menu.add_command(
            label="Launch BDBLM", command=lambda: self.launch_bdblm_callback()
        )
        self.context_menu.add_command(
            label="Connect via Putty", command=lambda: self.connect_via_putty_callback()
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Add TSV Item", command=lambda: self.add_tsv_item_callback()
        )
        self.context_menu.add_command(
            label="Delete TSV Item", command=lambda: self.delete_tsv_item_callback()
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Edit Config", command=lambda: self.edit_config_callback()
        )
        self.context_menu.add_command(
            label="Edit NODES", command=lambda: self.edit_nodes_callback()
        )
        self.context_menu.add_command(
            label="Open FileDB", command=lambda: self.open_filedb_callback()
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Save Changes", command=lambda: self.save_changes_callback()
        )

        # Bind right-click event to show menu
        self.tree.bind("<Button-3>", self.show_context_menu)

    # Callback methods that will be bound by the controller
    def start_service_callback(self):
        pass

    def stop_service_callback(self):
        pass

    def restart_service_callback(self):
        pass

    def deploy_service_callback(self):
        pass

    def add_tsv_item_callback(self):
        pass

    def delete_tsv_item_callback(self):
        pass

    def edit_config_callback(self):
        pass

    def edit_nodes_callback(self):
        pass

    def launch_bdblm_callback(self):
        pass

    def connect_via_putty_callback(self):
        pass

    def open_filedb_callback(self):
        pass

    def save_changes_callback(self):
        pass

    def show_context_menu(self, event):
        row = self.tree.identify_row(event.y)

        if row:
            self.tree.selection_set(row)
            self.tree.focus(row)
            self.context_menu.post(event.x_root, event.y_root)
        else:
            blank_menu = tk.Menu(self.root, tearoff=0)
            blank_menu.add_command(
                label="Add TSV Item", command=lambda: self.add_tsv_item_callback()
            )
            blank_menu.add_command(
                label="Open FileDB", command=lambda: self.open_filedb_callback()
            )
            blank_menu.add_command(
                label="Save Changes", command=lambda: self.save_changes_callback()
            )

            if hasattr(self, "refresh_status_callback"):
                blank_menu.add_command(
                    label="Refresh Status",
                    command=lambda: self.refresh_status_callback(),
                )

            blank_menu.post(event.x_root, event.y_root)

            self.root.blank_menu = blank_menu

    def create_status_display(self):
        # Configure status_frame grid layout
        self.status_frame.grid_columnconfigure(0, weight=1)
        self.status_frame.grid_rowconfigure(0, weight=1)
        self.status_frame.grid_propagate(True)

        # Create status treeview
        frame = ttk.Frame(self.status_frame)
        frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Vertical scrollbar
        v_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Create status treeview with IP column
        self.status_tree = ttk.Treeview(
            frame,
            columns=["node_name", "ip", "status"],
            show="headings",
            yscrollcommand=v_scroll.set,
        )

        v_scroll.config(command=self.status_tree.yview)

        # Set column headings and increased widths
        self.status_tree.heading("node_name", text="Node Name")
        self.status_tree.heading("ip", text="IP Address")
        self.status_tree.heading("status", text="Service Status")
        self.status_tree.column("node_name", width=140, anchor=tk.CENTER)
        self.status_tree.column("ip", width=140, anchor=tk.CENTER)
        self.status_tree.column("status", width=140, anchor=tk.CENTER)

        self.status_tree.pack(fill=tk.BOTH, expand=True)

        # Configure status tag colors
        self.status_tree.tag_configure("status_ok", foreground="green")
        self.status_tree.tag_configure("status_error", foreground="red")
        self.status_tree.tag_configure("status_stopped", foreground="gray")
        self.status_tree.tag_configure("status_unknown", foreground="orange")
        # Add standalone status with purple color
        self.status_tree.tag_configure("status_standalone", foreground="purple")

        # Create authentication fields directly in auth_frame
        self.auth_frame.grid_columnconfigure(0, weight=1)

        # Node name label
        self.auth_node_name = tk.StringVar()
        self.auth_node_name.set("No node selected")
        ttk.Label(self.auth_frame, textvariable=self.auth_node_name).grid(
            row=0, column=0, sticky="w", padx=10, pady=5
        )

        # Username field
        ttk.Label(self.auth_frame, text="Username:").grid(
            row=1, column=0, sticky="w", padx=10, pady=2
        )
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(self.auth_frame, textvariable=self.username_var)
        self.username_entry.grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        # Password field
        ttk.Label(self.auth_frame, text="Password:").grid(
            row=3, column=0, sticky="w", padx=10, pady=2
        )
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            self.auth_frame, textvariable=self.password_var, show="*"
        )
        self.password_entry.grid(row=4, column=0, sticky="ew", padx=10, pady=2)

        # Apply button
        self.apply_auth_button = ttk.Button(self.auth_frame, text="Apply Changes")
        self.apply_auth_button.grid(row=5, column=0, pady=10, padx=10)

        # Create parameters fields directly in params_frame
        self.params_frame.grid_columnconfigure(0, weight=1)

        # LACCS Path parameter
        ttk.Label(self.params_frame, text="LACCS Installation Path:").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.laccs_path_var = tk.StringVar()
        self.laccs_path_entry = ttk.Entry(
            self.params_frame, textvariable=self.laccs_path_var
        )
        self.laccs_path_entry.grid(row=1, column=0, sticky="ew", pady=2)

        # Node Name parameter
        ttk.Label(self.params_frame, text="Node Name (--D:node_name):").grid(
            row=2, column=0, sticky="w", pady=2
        )
        self.node_name_var = tk.StringVar()
        self.node_name_entry = ttk.Entry(
            self.params_frame, textvariable=self.node_name_var
        )
        self.node_name_entry.grid(row=3, column=0, sticky="ew", pady=2)

        # Device Name parameter
        ttk.Label(self.params_frame, text="Device Name (--D:device_name):").grid(
            row=4, column=0, sticky="w", pady=2
        )
        self.device_name_var = tk.StringVar()
        self.device_name_entry = ttk.Entry(
            self.params_frame, textvariable=self.device_name_var
        )
        self.device_name_entry.grid(row=5, column=0, sticky="ew", pady=2)

        # Channel parameters
        ttk.Label(self.params_frame, text="Channels (--D:ch00~ch05):").grid(
            row=6, column=0, sticky="w", pady=5
        )

        # Create a frame for channel entries
        channels_frame = ttk.Frame(self.params_frame)
        channels_frame.grid(row=7, column=0, sticky="ew", padx=5)

        # Configure channel frame layout
        channels_frame.grid_columnconfigure(0, weight=1)
        channels_frame.grid_columnconfigure(1, weight=1)
        channels_frame.grid_columnconfigure(2, weight=1)

        # CH00-CH02 in first row
        ttk.Label(channels_frame, text="CH00:").grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        self.ch00_var = tk.StringVar()
        self.ch00_entry = ttk.Entry(channels_frame, textvariable=self.ch00_var)
        self.ch00_entry.grid(row=0, column=0, sticky="ew", padx=(40, 5))

        ttk.Label(channels_frame, text="CH01:").grid(
            row=0, column=1, sticky="w", padx=(0, 5)
        )
        self.ch01_var = tk.StringVar()
        self.ch01_entry = ttk.Entry(channels_frame, textvariable=self.ch01_var)
        self.ch01_entry.grid(row=0, column=1, sticky="ew", padx=(40, 5))

        ttk.Label(channels_frame, text="CH02:").grid(
            row=0, column=2, sticky="w", padx=(0, 5)
        )
        self.ch02_var = tk.StringVar()
        self.ch02_entry = ttk.Entry(channels_frame, textvariable=self.ch02_var)
        self.ch02_entry.grid(row=0, column=2, sticky="ew", padx=(40, 5))

        # CH03-CH05 in second row
        ttk.Label(channels_frame, text="CH03:").grid(
            row=1, column=0, sticky="w", padx=(0, 5), pady=5
        )
        self.ch03_var = tk.StringVar()
        self.ch03_entry = ttk.Entry(channels_frame, textvariable=self.ch03_var)
        self.ch03_entry.grid(row=1, column=0, sticky="ew", padx=(40, 5), pady=5)

        ttk.Label(channels_frame, text="CH04:").grid(
            row=1, column=1, sticky="w", padx=(0, 5), pady=5
        )
        self.ch04_var = tk.StringVar()
        self.ch04_entry = ttk.Entry(channels_frame, textvariable=self.ch04_var)
        self.ch04_entry.grid(row=1, column=1, sticky="ew", padx=(40, 5), pady=5)

        ttk.Label(channels_frame, text="CH05:").grid(
            row=1, column=2, sticky="w", padx=(0, 5), pady=5
        )
        self.ch05_var = tk.StringVar()
        self.ch05_entry = ttk.Entry(channels_frame, textvariable=self.ch05_var)
        self.ch05_entry.grid(row=1, column=2, sticky="ew", padx=(40, 5), pady=5)

        # Apply parameters button
        self.apply_params_button = ttk.Button(
            self.params_frame, text="Apply Parameters"
        )
        self.apply_params_button.grid(row=8, column=0, pady=10)

    def create_log_display(self):
        # Create log display area inside the log_frame_container
        log_frame = ttk.LabelFrame(self.log_frame_container, text="Real-time Log")
        log_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(5, 10))

        # Configure log_frame grid layout with proper weight distribution
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_rowconfigure(0, weight=0)
        log_frame.grid_rowconfigure(2, weight=0)

        # Set height for log_frame but allow it to expand vertically
        log_frame.grid_propagate(True)

        # Create search/filter frame
        filter_frame = ttk.Frame(log_frame)
        filter_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        filter_frame.grid_columnconfigure(1, weight=1)

        # Search label
        ttk.Label(filter_frame, text="Search Log:", anchor=tk.W).grid(
            row=0, column=0, sticky="w", padx=5
        )

        # Search entry
        self.log_filter_var = tk.StringVar()
        self.log_filter_entry = ttk.Entry(
            filter_frame, textvariable=self.log_filter_var
        )
        self.log_filter_entry.grid(row=0, column=1, sticky="ew", padx=5)

        # Create scrolled text widget for log with resizable properties
        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Arial", 9), state=tk.DISABLED, height=8
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.log_text.configure(width=1)
        log_frame.bind("<Configure>", lambda event: self.log_text.update_idletasks())

        # Add buttons frame
        button_frame = ttk.Frame(log_frame)
        button_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=2)
        button_frame.grid_columnconfigure(0, weight=1)

        # Add refresh status button
        refresh_button = ttk.Button(button_frame, text="Refresh Status")
        refresh_button.grid(row=0, column=1, padx=5)

        # Add clear log button
        clear_button = ttk.Button(button_frame, text="Clear Log")
        clear_button.grid(row=0, column=2, padx=5)
