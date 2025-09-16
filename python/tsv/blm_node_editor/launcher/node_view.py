import tkinter as tk
from tkinter import ttk, scrolledtext, Menu


class NodeView:
    def __init__(self, root):
        self.root = root
        self.root.title("BLM Node Manger")
        self.root.geometry("1200x700")

        # Configure font support
        self.style = ttk.Style()
        self.style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        self.style.configure("Treeview", font=("Arial", 10))

        # Create main frame, split into left and right parts
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create left data editor area
        self.left_frame = ttk.Frame(self.main_frame, width=600)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Create right status display area
        self.right_frame = ttk.LabelFrame(
            self.main_frame, text="Node Service Status", width=200
        )
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # Create SSH operation buttons
        self.create_ssh_buttons()

        # Create Treeview component (left side)
        self.create_treeview()

        # Create node status display (right side)
        self.create_status_display()

        # Create log display area (bottom)
        self.create_log_display()

    def create_ssh_buttons(self):
        # SSH operation buttons have been removed, functionality is available in right-click context menu
        pass

    def create_treeview(self):
        # Create Treeview and scrollbars
        frame = ttk.Frame(self.left_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

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

            if hasattr(self, "refresh_status_callback"):
                blank_menu.add_command(
                    label="Refresh Status",
                    command=lambda: self.refresh_status_callback(),
                )

            blank_menu.post(event.x_root, event.y_root)

            self.root.blank_menu = blank_menu

    def create_status_display(self):
        # Create status display area (right side)
        # Status treeview
        frame = ttk.Frame(self.right_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

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

        # Set column headings and widths
        self.status_tree.heading("node_name", text="Node Name")
        self.status_tree.heading("ip", text="IP Address")
        self.status_tree.heading("status", text="Service Status")
        self.status_tree.column("node_name", width=120, anchor=tk.CENTER)
        self.status_tree.column("ip", width=120, anchor=tk.CENTER)
        self.status_tree.column("status", width=120, anchor=tk.CENTER)

        self.status_tree.pack(fill=tk.BOTH, expand=True)

        # Configure status tag colors
        self.status_tree.tag_configure("status_ok", foreground="green")
        self.status_tree.tag_configure("status_error", foreground="red")
        self.status_tree.tag_configure("status_stopped", foreground="gray")
        self.status_tree.tag_configure("status_unknown", foreground="orange")
        # Add standalone status with purple color
        self.status_tree.tag_configure("status_standalone", foreground="purple")

        # Create authentication info area
        auth_frame = ttk.LabelFrame(self.right_frame, text="Node Authentication")
        auth_frame.pack(fill=tk.X, padx=10, pady=10)

        # Node name label
        self.auth_node_name = tk.StringVar()
        self.auth_node_name.set("No node selected")
        ttk.Label(auth_frame, textvariable=self.auth_node_name).pack(
            pady=5, anchor=tk.W
        )

        # Username field
        ttk.Label(auth_frame, text="Username:").pack(pady=2, anchor=tk.W)
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(
            auth_frame, textvariable=self.username_var, width=20
        )
        self.username_entry.pack(pady=2, fill=tk.X)

        # Password field
        ttk.Label(auth_frame, text="Password:").pack(pady=2, anchor=tk.W)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            auth_frame, textvariable=self.password_var, show="*", width=20
        )
        self.password_entry.pack(pady=2, fill=tk.X)

        # Apply button
        self.apply_auth_button = ttk.Button(auth_frame, text="Apply Changes")
        self.apply_auth_button.pack(pady=10)

        # Create parameters configuration area
        params_frame = ttk.LabelFrame(self.right_frame, text="Node Service Parameters")
        params_frame.pack(fill=tk.X, padx=10, pady=10)

        # LACCS Path parameter
        ttk.Label(params_frame, text="LACCS Installation Path:").pack(
            pady=2, anchor=tk.W
        )
        self.laccs_path_var = tk.StringVar()
        self.laccs_path_entry = ttk.Entry(
            params_frame, textvariable=self.laccs_path_var, width=30
        )
        self.laccs_path_entry.pack(pady=2, fill=tk.X)

        # Node Name parameter
        ttk.Label(params_frame, text="Node Name (--D:node_name):").pack(
            pady=2, anchor=tk.W
        )
        self.node_name_var = tk.StringVar()
        self.node_name_entry = ttk.Entry(
            params_frame, textvariable=self.node_name_var, width=30
        )
        self.node_name_entry.pack(pady=2, fill=tk.X)

        # Device Name parameter
        ttk.Label(params_frame, text="Device Name (--D:device_name):").pack(
            pady=2, anchor=tk.W
        )
        self.device_name_var = tk.StringVar()
        self.device_name_entry = ttk.Entry(
            params_frame, textvariable=self.device_name_var, width=30
        )
        self.device_name_entry.pack(pady=2, fill=tk.X)

        # Channel parameters
        ttk.Label(params_frame, text="Channels (--D:ch00~ch05):").pack(
            pady=5, anchor=tk.W
        )

        # Create a frame for channel entries
        channels_frame = ttk.Frame(params_frame)
        channels_frame.pack(fill=tk.X, padx=5)

        # CH00-CH02 in first row
        row1_frame = ttk.Frame(channels_frame)
        row1_frame.pack(fill=tk.X)

        ttk.Label(row1_frame, text="CH00:").pack(side=tk.LEFT, padx=(0, 5))
        self.ch00_var = tk.StringVar()
        self.ch00_entry = ttk.Entry(row1_frame, textvariable=self.ch00_var, width=15)
        self.ch00_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(row1_frame, text="CH01:").pack(side=tk.LEFT, padx=(10, 5))
        self.ch01_var = tk.StringVar()
        self.ch01_entry = ttk.Entry(row1_frame, textvariable=self.ch01_var, width=15)
        self.ch01_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(row1_frame, text="CH02:").pack(side=tk.LEFT, padx=(10, 5))
        self.ch02_var = tk.StringVar()
        self.ch02_entry = ttk.Entry(row1_frame, textvariable=self.ch02_var, width=15)
        self.ch02_entry.pack(side=tk.LEFT, padx=5)

        # CH03-CH05 in second row
        row2_frame = ttk.Frame(channels_frame)
        row2_frame.pack(fill=tk.X, pady=5)

        ttk.Label(row2_frame, text="CH03:").pack(side=tk.LEFT, padx=(0, 5))
        self.ch03_var = tk.StringVar()
        self.ch03_entry = ttk.Entry(row2_frame, textvariable=self.ch03_var, width=15)
        self.ch03_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(row2_frame, text="CH04:").pack(side=tk.LEFT, padx=(10, 5))
        self.ch04_var = tk.StringVar()
        self.ch04_entry = ttk.Entry(row2_frame, textvariable=self.ch04_var, width=15)
        self.ch04_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(row2_frame, text="CH05:").pack(side=tk.LEFT, padx=(10, 5))
        self.ch05_var = tk.StringVar()
        self.ch05_entry = ttk.Entry(row2_frame, textvariable=self.ch05_var, width=15)
        self.ch05_entry.pack(side=tk.LEFT, padx=5)

        # Apply parameters button
        self.apply_params_button = ttk.Button(params_frame, text="Apply Parameters")
        self.apply_params_button.pack(pady=10)

    def create_log_display(self):
        # Create log display area at the bottom
        log_frame = ttk.LabelFrame(self.root, text="Real-time Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create search/filter frame
        filter_frame = ttk.Frame(log_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=2)

        # Search label
        ttk.Label(filter_frame, text="Search Log:", anchor=tk.W).pack(
            side=tk.LEFT, padx=5
        )

        # Search entry
        self.log_filter_var = tk.StringVar()
        self.log_filter_entry = ttk.Entry(
            filter_frame, textvariable=self.log_filter_var, width=30
        )
        self.log_filter_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Create scrolled text widget for log
        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Arial", 9), state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add clear log button
        button_frame = ttk.Frame(log_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=2)

        clear_button = ttk.Button(button_frame, text="Clear Log")
        clear_button.pack(side=tk.RIGHT, padx=5)

        # Add refresh status button
        refresh_button = ttk.Button(button_frame, text="Refresh Status")
        refresh_button.pack(side=tk.RIGHT, padx=5)
