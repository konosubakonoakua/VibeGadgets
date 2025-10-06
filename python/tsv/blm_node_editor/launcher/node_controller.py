import os
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog
import threading
import time
import datetime
import paramiko
from paramiko.ssh_exception import SSHException
from .node_model import NodeModel
from .node_view import NodeView


class NodeController:
    def __init__(self, root):
        self.model = NodeModel()
        self.view = NodeView(root)
        self.root = root
        
        # Flag to track if main loop is active - Initialize early
        self.main_loop_active = True

        # Log related settings - Initialize first
        self.log_history = []  # Store all log entries for filtering
        self.log_file = None
        # self.setup_log_file()

        # Bind events and commands
        self._bind_events()

        # Store mapping of node names to Treeview item IDs
        self.node_item_map = {}

        # Status check thread control
        self.stop_status_check = False
        # Track nodes that consistently time out to avoid repeated errors
        self.timed_out_nodes = {}
        # Maximum allowed consecutive timeouts before temporarily skipping a node
        self.MAX_CONSECUTIVE_TIMEOUTS = 3
        # Time in seconds to wait before checking a problematic node again
        self.TIMEOUT_RETRY_INTERVAL = 300  # 5 minutes

        # Track unsaved changes
        self.has_unsaved_changes = False

        # Load data
        self.load_data()

        # Start status check thread
        self.start_status_check_thread()

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Bind log filter event
        self.view.log_filter_var.trace("w", self.filter_log_entries)

        # Bind Ctrl+S shortcut for saving
        self.root.bind("<Control-s>", self.save_changes)
        self.root.bind("<Control-S>", self.save_changes)

        # Flag to track if main loop is active
        self.main_loop_active = True

    def _bind_events(self):
        # Bind events and commands
        self.view.tree.bind("<Double-1>", self.on_double_click)
        self.view.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Bind context menu callbacks to controller methods
        self.view.start_service_callback = self.start_service
        self.view.stop_service_callback = self.stop_service
        self.view.restart_service_callback = self.restart_service
        self.view.deploy_service_callback = self.deploy_service
        self.view.edit_config_callback = self.edit_node_config
        self.view.edit_nodes_callback = self.edit_nodes_tsv
        self.view.add_tsv_item_callback = self.add_tsv_item
        self.view.delete_tsv_item_callback = self.delete_tsv_item
        self.view.launch_bdblm_callback = self.launch_bdblm
        self.view.connect_via_putty_callback = self.connect_via_putty
        self.view.open_filedb_callback = self.open_filedb
        self.view.save_changes_callback = self.save_changes
        self.view.load_service_parameter_callback = self.load_service_parameter
        self.view.update_shared_lib_callback = self.update_shared_lib
        self.view.update_shared_lib_all_callback = self.update_shared_lib_all
        self.view.stop_service_all_callback = self.stop_service_all

        # Bind authentication apply button
        self.view.apply_auth_button.config(command=self.apply_authentication)

        # Bind parameters apply button
        self.view.apply_params_button.config(command=self.apply_parameters)

        # Bind log button commands
        for child in self.view.log_text.master.winfo_children():
            if isinstance(child, ttk.Frame):
                for btn in child.winfo_children():
                    if isinstance(btn, ttk.Button):
                        if btn["text"] == "Clear Log":
                            btn.config(command=self.clear_log)
                        elif btn["text"] == "Refresh Status":
                            btn.config(command=self.force_refresh_status)

    def open_filedb(self):
        """Allow user to select a new NODES.tsv file and reload data"""
        # Ask user if they want to save current changes
        if self.has_unsaved_changes:
            if messagebox.askyesnocancel(
                "Save Changes",
                "You have unsaved changes. Would you like to save them before opening a new file?",
            ):
                if not self.save_changes():
                    return  # User canceled save operation
            elif messagebox.NO == messagebox.askyesnocancel(
                "Discard Changes", "Would you like to discard your unsaved changes?"
            ):
                return  # User decided not to discard changes

        # Allow user to select external file, passing the main window as parent
        success_select, select_message = self.model.select_external_nodes_file(
            parent=self.root
        )
        if success_select:
            self.log_message(select_message)
            # Try to load data again with the selected file
            self.load_data()
        else:
            self.log_message(select_message)

    def launch_bdblm(self):
        """Launch BDBLM.exe with parameters from the selected node"""
        # Get selected node information
        selected_items = self.view.tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "No node selected")
            return

        item = selected_items[0]
        node_name = self.view.tree.item(item, "values")[0]

        # Get node parameters
        params = self.model.get_node_params(node_name)

        # Construct the command
        cmd = f'.\\BDBLM.exe "" {{node_name}}={params["node_name"]},{{device_name}}={params["device_name"]},'
        cmd += f'{{ch00}}={params["ch00"]},{{ch01}}={params["ch01"]},'
        cmd += f'{{ch02}}={params["ch02"]},{{ch03}}={params["ch03"]},'
        cmd += f'{{ch04}}={params["ch04"]},{{ch05}}={params["ch05"]} false'

        # Log the command
        self.log_message(
            f"Launching BDBLM.exe for node {node_name} with command: {cmd}"
        )

        try:
            # Start the process using cmd.exe
            import subprocess

            subprocess.Popen(f'cmd /k "{cmd}"', shell=True)
            messagebox.showinfo(
                "Success", f"BDBLM.exe has been launched for node {node_name}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch BDBLM.exe: {str(e)}")
            self.log_message(f"ERROR: Failed to launch BDBLM.exe: {str(e)}")

    def load_data(self):
        success, message = self.model.load_node_data(parent=self.root)
        if not success:
            # If file not found, ask user to select external file
            if (
                "no such file" in message.lower()
                or "not found" in message.lower()
                or "errno 2" in message.lower()
            ):
                self.log_message(f"ERROR: {message}")
                # Ask user if they want to select an external file
                if messagebox.askyesno(
                    "File Not Found",
                    f"Could not find {self.model.tsv_file}\n"
                    "Would you like to select a different NODES.tsv file?",
                ):
                    # Allow user to select external file, passing the main window as parent
                    success_select, select_message = (
                        self.model.select_external_nodes_file(parent=self.root)
                    )
                    if success_select:
                        self.log_message(select_message)
                        # Try to load data again with the selected file
                        success_retry, retry_message = self.model.load_node_data(
                            parent=self.root
                        )
                        if not success_retry:
                            messagebox.showerror("Error", retry_message)
                            self.log_message(f"ERROR: {retry_message}")
                            return
                    else:
                        self.log_message(select_message)
                        return
            else:
                messagebox.showerror("Error", message)
                self.log_message(f"ERROR: {message}")
                return

        self.view.tree["columns"] = self.model.headers
        for col in self.model.headers:
            self.view.tree.heading(col, text=col)
            self.view.tree.column(col, width=100, anchor=tk.CENTER)

        for item in self.view.tree.get_children():
            self.view.tree.delete(item)

        self.node_item_map = {}
        for row in self.model.node_data:
            item_id = self.view.tree.insert("", tk.END, values=row)
            if row:
                node_name = row[0]
                self.node_item_map[node_name] = item_id

        self.log_message(message)

        self.update_node_list()

    def update_node_list(self):
        tree_items = []
        for item in self.view.tree.get_children():
            tree_items.append(self.view.tree.item(item, "values"))

        success, message = self.model.update_non_local_nodes(
            self.model.headers, tree_items
        )
        if not success:
            self.log_message(message)
            return

        self.log_message(message)

        self._initialize_status_tree()

    def _initialize_status_tree(self):
        for item in self.view.status_tree.get_children():
            self.view.status_tree.delete(item)

        for node_name in self.node_item_map.keys():
            status = self.model.get_node_status(node_name)
            node_ip = None
            for name, ip in self.model.non_local_nodes:
                if name == node_name:
                    node_ip = ip
                    break
            item_id = self.view.status_tree.insert(
                "", tk.END, values=(node_name, node_ip or "N/A", status)
            )

            if status.lower() == "running":
                self.view.status_tree.item(item_id, tags=("status_ok",))
            elif status.lower() == "stopped":
                self.view.status_tree.item(item_id, tags=("status_stopped",))
            elif status.lower() == "error":
                self.view.status_tree.item(item_id, tags=("status_error",))
            else:
                self.view.status_tree.item(item_id, tags=("status_unknown",))

    def _add_save_button(self):
        """Add a save button to the view"""
        # Create button frame inside main_frame to avoid layout conflicts
        button_frame = ttk.Frame(self.view.main_frame)
        button_frame.grid(
            row=1, column=0, sticky="ew", padx=10, pady=(5, 0), columnspan=2
        )
        button_frame.grid_columnconfigure(0, weight=1)

        # Add a label to indicate unsaved changes
        self.unsaved_label = ttk.Label(button_frame, text="", foreground="red")
        self.unsaved_label.grid(row=0, column=0, sticky="e", padx=5)

        save_button = ttk.Button(
            button_frame, text="Save Changes", command=self.save_changes
        )
        save_button.grid(row=0, column=1, sticky="e", padx=5)

    def set_unsaved_changes(self, has_changes=True):
        """Set the unsaved changes flag and update the UI"""
        self.has_unsaved_changes = has_changes
        if has_changes:
            self.unsaved_label.config(text="* Unsaved changes")
            # Update window title to indicate unsaved changes
            self.root.title("LACCS - Node Manager *")
        else:
            self.unsaved_label.config(text="")
            # Restore original window title
            self.root.title("LACCS - Node Manager")

    def load_service_parameter(self):
        """Load service parameters from BDMap.json file and update all nodes' parameters"""
        try:
            # Get the directory of the executable
            import sys
            exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            default_file_path = os.path.join(exe_dir, "BDMap.json")
            
            file_path = None
            
            # Check if default BDMap.json exists
            if os.path.exists(default_file_path):
                file_path = default_file_path
            else:
                # Show message and ask user if they want to select another file
                response = messagebox.askyesno(
                    "File Not Found",
                    "BDMap.json not found in executable directory.\nDo you want to select another file?"
                )
                
                if response:
                    # Open file dialog for JSON files
                    file_path = filedialog.askopenfilename(
                        title="Select BDMap.json File",
                        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                        initialdir=exe_dir,
                        parent=self.root
                    )
                else:
                    return  # User chose not to select a file

            if not file_path:
                return  # User canceled file selection

            # Read and parse JSON file
            import json
            with open(file_path, 'r', encoding='utf-8') as file:
                bd_map = json.load(file)

            # Now update all nodes in the Treeview with matching parameters
            updated_count = 0
            for item in self.view.tree.get_children():
                node_name = self.view.tree.item(item, "values")[0]
                
                # First get existing params to preserve default values
                existing_params = self.model.get_node_params(node_name)
                matching_found = False
                
                # Find matching parameter in bd_map
                for key, value in bd_map.items():
                    # Check if BDMap key starts with BD and contains BLMER and the node name
                    if key.startswith('BD') and 'BLMER' in key and node_name in key:
                        # Split value by |
                        parts = value.split('|')
                        if len(parts) >= 3:
                            # Extract the macro part (third part)
                            macro_part = parts[2]
                            
                            # Parse macro_part into params dictionary
                            new_params = {}
                            # The key is also the macro {node_name}
                            new_params['node_name'] = key
                            
                            # Parse each parameter in macro_part
                            param_pairs = macro_part.split(',')
                            for pair in param_pairs:
                                if '=' in pair:
                                    param_key, param_value = pair.split('=', 1)
                                    # Remove { and } from param_key if present
                                    param_key = param_key.strip('{}')
                                    new_params[param_key] = param_value
                            
                            # Update the existing params with new params
                            existing_params.update(new_params)
                            # Set laccs_path to '/opt/LACCS' after loading JSON
                            existing_params['laccs_path'] = '/opt/LACCS'
                            
                            # Update node parameters in the model
                            self.model.set_node_params(node_name, existing_params)
                            updated_count += 1
                            matching_found = True
                            break  # Stop searching once a match is found
                
                # If no match found, keep existing params but ensure laccs_path exists
                if not matching_found and 'laccs_path' not in existing_params:
                    existing_params['laccs_path'] = '/opt/LACCS#'
                    self.model.set_node_params(node_name, existing_params)

            # Show success message
            messagebox.showinfo("Success", f"Updated {updated_count} nodes with service parameters")
            self.log_message(f"Successfully loaded service parameters from {file_path}")
            self.log_message(f"Updated parameters for {updated_count} nodes")
            
        except Exception as e:
            error_msg = f"Failed to load service parameters: {str(e)}"
            messagebox.showerror("Error", error_msg)
            self.log_message(f"ERROR: {error_msg}")

    def save_changes(self, event=None):
        """Save all changes to the file"""
        if not self.has_unsaved_changes:
            messagebox.showinfo("Info", "No changes to save.")
            return

        try:
            data = []

            for item in self.view.tree.get_children():
                data.append(self.view.tree.item(item, "values"))

            success, message = self.model.save_node_data(data)
            if success:
                messagebox.showinfo("Success", message)
                self.log_message(message)
                self.update_node_list()
                self.set_unsaved_changes(False)
            else:
                messagebox.showerror("Error", message)
                self.log_message(f"ERROR: {message}")
        except Exception as e:
            error_msg = f"Failed to save file: {str(e)}"
            messagebox.showerror("Error", error_msg)
            self.log_message(f"ERROR: {error_msg}")

    def start_status_check_thread(self):
        self.status_check_thread = threading.Thread(target=self.check_all_nodes_status)
        self.status_check_thread.daemon = True
        self.status_check_thread.start()

    def on_double_click(self, event):
        region = self.view.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.view.tree.identify_column(event.x)
            col_index = int(column.replace("#", "")) - 1
            item = self.view.tree.identify_row(event.y)

            if item and 0 <= col_index < len(self.view.tree["columns"]):
                current_value = self.view.tree.item(item, "values")[col_index]
                col_name = self.view.tree["columns"][col_index]

                new_value = simpledialog.askstring(
                    "Edit",
                    f"Please enter new value for {col_name}:",
                    initialvalue=current_value,
                )

                if new_value is not None and new_value != current_value:
                    values = list(self.view.tree.item(item, "values"))
                    values[col_index] = new_value
                    self.view.tree.item(item, values=values)

                    # Update node_item_map if node name was changed
                    if col_index == 0:
                        old_node_name = current_value
                        new_node_name = new_value
                        if old_node_name in self.node_item_map:
                            del self.node_item_map[old_node_name]
                            self.node_item_map[new_node_name] = item

                    # Set unsaved changes flag instead of saving immediately
                    self.set_unsaved_changes()

    def on_tree_select(self, event):
        selected_items = self.view.tree.selection()
        if selected_items:
            item = selected_items[0]
            node_name = self.view.tree.item(item, "values")[0]

            self.view.auth_node_name.set(f"Node: {node_name}")

            # Load authentication info
            username, password = self.model.get_node_credentials(node_name)
            self.view.username_var.set(username)
            self.view.password_var.set(password)

            # Load node parameters
            params = self.model.get_node_params(node_name)
            self.view.laccs_path_var.set(params["laccs_path"])
            self.view.node_name_var.set(params["node_name"])
            self.view.device_name_var.set(params["device_name"])
            self.view.ch00_var.set(params["ch00"])
            self.view.ch01_var.set(params["ch01"])
            self.view.ch02_var.set(params["ch02"])
            self.view.ch03_var.set(params["ch03"])
            self.view.ch04_var.set(params["ch04"])
            self.view.ch05_var.set(params["ch05"])

    def get_selected_node_info(self):
        selected_items = self.view.tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "No node selected")
            return None, None

        item = selected_items[0]
        node_name = self.view.tree.item(item, "values")[0]

        for name, ip in self.model.non_local_nodes:
            if name == node_name:
                return node_name, ip

        messagebox.showerror("Error", f"Cannot find IP for node {node_name}")
        return None, None

    def start_service(self):
        node_name, ip = self.get_selected_node_info()
        if not node_name or not ip:
            return

        # Get current status to determine if it's running in screen or standalone
        current_status = self._get_node_status(node_name, ip)

        # Get node parameters
        params = self.model.get_node_params(node_name)

        # Generate the screen command with dynamic parameters
        screen_command = f"screen -wipe; screen -L -dmS LACCS bash -lc \"cd {params['laccs_path']} && ulimit -n 204800 && ulimit -s 81920 && ./LACCS --user_name=guest --password=guest_password --data_id=uptodate --D:node_name={params['node_name']} --D:device_name={params['device_name']} --D:ch00={params['ch00']} --D:ch01={params['ch01']} --D:ch02={params['ch02']} --D:ch03={params['ch03']} --D:ch04={params['ch04']} --D:ch05={params['ch05']}; exec bash\""

        if current_status == "Running" or current_status == "standalone":
            # Service is running (either in screen or standalone), ask user whether to kill current process and continue
            response = messagebox.askyesno(
                "Service Running",
                f"Service on node {node_name} ({ip}) is already running (mode: {current_status}).\n\n"
                + f"Command to be executed:\n1. Stop current service\n2. {screen_command}\n\n"
                + "Do you want to proceed with starting new service?",
            )

            if not response:
                # User canceled
                self.log_message(
                    f"User aborted starting new service on node {node_name} ({ip})"
                )
                return
            else:
                # User chose to proceed
                self.log_message(
                    f"User chose to kill current process and start new service on node {node_name} ({ip})"
                )

                # Use different commands to stop based on service type
                if current_status == "Running":
                    # Stop screen session
                    stop_command = "screen -S LACCS -X quit"
                    self.execute_ssh_command(ip, stop_command)
                    self.log_message(
                        f"Sent stop command for screen session to node {node_name} ({ip})"
                    )
                else:
                    # Kill standalone process
                    stop_command = "pkill -f LACCS"
                    self.execute_ssh_command(ip, stop_command)
                    self.log_message(
                        f"Sent stop command for standalone process to node {node_name} ({ip})"
                    )

                # Wait a moment to ensure service has stopped
                time.sleep(1)
        else:
            # First time start, show confirmation dialog
            response = messagebox.askyesno(
                "Start Service",
                f"Starting service on node {node_name} ({ip}).\n\n"
                + f"Command to be executed:\n{screen_command}\n\n" 
                + "Do you want to proceed?",
            )

            if not response:
                # User canceled
                self.log_message(
                    f"User aborted starting service on node {node_name} ({ip})"
                )
                return

        self.log_message(
            f"Starting service on {node_name} ({ip}) with command: {screen_command}"
        )

        # Execute the command via SSH
        result = self.execute_ssh_command(ip, screen_command)

        if result == "success":
            self.root.after(1000, lambda: self.update_node_status(node_name, "Running"))
        else:
            self.root.after(1000, lambda: self.update_node_status(node_name, "Stopped"))

    def _check_service_running(self, node_name, ip):
        """
        Check if the service is running on the specified node (simplified version for backward compatibility)
        Returns True if service is running, False if service is not running or status cannot be determined
        """
        try:
            status = self._get_node_status(node_name, ip)
            return status == "Running" or status == "standalone"
        except Exception:
            return False

    def _get_node_status(self, node_name, ip):
        """
        Get the detailed status of the node service
        Returns "Running", "standalone", or "Stopped"
        """
        try:
            # Skip status check for localhost
            if ip == "127.0.0.1":
                return "Localhost"

            # First check if the screen session named LACCS exists
            screen_status_command = 'screen -list | grep -q "LACCS"'

            # Command to check for any LACCS process running outside of screen
            standalone_status_command = (
                'ps -ef | grep -v grep | grep -v screen | grep -q "LACCS"'
            )

            # Use a low timeout for status checks
            try:
                # Get authentication credentials
                username, password = self.model.get_node_credentials(node_name)

                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(ip, username=username, password=password, timeout=5)

                # First check for screen session
                stdin, stdout, stderr = client.exec_command(screen_status_command)
                screen_exit_code = stdout.channel.recv_exit_status()

                if screen_exit_code == 0:
                    status = "Running"
                else:
                    # If not in screen, check for standalone process
                    stdin, stdout, stderr = client.exec_command(
                        standalone_status_command
                    )
                    standalone_exit_code = stdout.channel.recv_exit_status()

                    if standalone_exit_code == 0:
                        status = "standalone"
                    else:
                        status = "Stopped"

                # Ensure client is closed properly
                try:
                    client.close()
                except Exception:
                    pass

                return status
            except Exception:
                # Exception occurred, cannot determine status, assume service is not running
                return "Stopped"
        except Exception:
            # Exception occurred, cannot determine status, assume service is not running
            return "Stopped"

    def stop_service(self):
        node_name, ip = self.get_selected_node_info()
        if not node_name or not ip:
            return

        # Command to terminate the screen session named LACCS
        stop_command = "screen -S LACCS -X quit"

        # Show confirmation dialog
        response = messagebox.askyesno(
            "Stop Service",
            f"Stopping service on node {node_name} ({ip}).\n\n"
            + f"Command to be executed:\n{stop_command}\n\n" 
            + "Do you want to proceed?",
        )

        if not response:
            # User canceled
            self.log_message(
                f"User aborted stopping service on node {node_name} ({ip})"
            )
            return

        self.log_message(
            f"Stopping service on {node_name} ({ip}) with command: {stop_command}"
        )

        # Execute the command via SSH
        result = self.execute_ssh_command(ip, stop_command)

        if result == "success":
            self.root.after(1000, lambda: self.update_node_status(node_name, "Stopped"))

    def stop_service_all(self):
        """Stop service on all nodes using thread pool - UI-safe version"""
        # Show confirmation dialog
        from tkinter import messagebox
        confirm_message = "Stopping service on ALL nodes.\n\n"
        confirm_message += "This operation will:\n"
        confirm_message += "1. Stop service on each node\n\n"
        confirm_message += "This operation will run without further confirmation.\n"
        confirm_message += f"Are you sure you want to stop services on all {len(self.model.non_local_nodes)} nodes?"

        response = messagebox.askyesno("Batch Stop Service", confirm_message)
        if not response:
            self.log_message("Batch stop service operation cancelled by user")
            return

        # Create and start a new thread to run the actual stop process
        # This keeps the UI responsive
        stop_thread = threading.Thread(
            target=self._stop_service_all_async,
            daemon=True
        )
        stop_thread.start()

    def _stop_service_all_async(self):
        """Helper method to perform the actual stop process in a background thread"""
        # Log message in the main thread
        if self.main_loop_active:
            self.root.after(
                0,
                lambda: self.log_message(f"Starting batch stop of services on all nodes...")
            )
        
        # Use thread pool to process all nodes
        import concurrent.futures
        
        # Create a thread pool with a maximum of 10 worker threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all node stop tasks as concurrent tasks
            future_to_node = {
                executor.submit(self._stop_service_node, node_name, ip): 
                node_name 
                for node_name, ip in self.model.non_local_nodes
            }

            # Process completed tasks
            for future in concurrent.futures.as_completed(future_to_node):
                node_name = future_to_node[future]
                try:
                    future.result()  # This will raise exceptions if any occurred during execution
                except Exception as e:
                    # Log the error
                    if self.main_loop_active:
                        try:
                            self.log_message(f"ERROR stopping service on {node_name}: {str(e)}")
                            # Update status in main thread
                            self.root.after(
                                0,
                                lambda name=node_name: self.update_node_status(name, "Error"),
                            )
                        except Exception:
                            # Prevent thread from crashing if main loop has terminated
                            print(f"ERROR stopping service on {node_name}: {str(e)}")

        # Log completion message in the main thread
        if self.main_loop_active:
            self.root.after(
                0,
                lambda: self.log_message("Batch stop of services completed for all nodes")
            )

    def _stop_service_node(self, node_name, ip):
        """Helper method to stop service on a single node"""
        # Command to terminate the screen session named LACCS
        stop_command = "screen -S LACCS -X quit"
        
        # Log message in the main thread
        if self.main_loop_active:
            self.root.after(
                0,
                lambda name=node_name, ip=ip, cmd=stop_command: self.log_message(f"Stopping service on {name} ({ip}) with command: {cmd}")
            )
        
        # Execute the command via SSH
        result = self.execute_ssh_command(ip, stop_command)
        
        if result == "success" and self.main_loop_active:
            self.root.after(
                1000,
                lambda name=node_name: self.update_node_status(name, "Stopped")
            )

    def restart_service(self):
        node_name, ip = self.get_selected_node_info()
        if not node_name or not ip:
            return

        # Get node parameters
        params = self.model.get_node_params(node_name)

        # Stop command (terminate screen session)
        stop_command = "screen -S LACCS -X quit"

        # Start command with dynamic parameters
        start_command = f"screen -wipe; screen -L -dmS LACCS bash -lc \"cd {params['laccs_path']} && ulimit -n 204800 && ulimit -s 81920 && ./LACCS --user_name=guest --password=guest_password --data_id=uptodate --D:node_name={params['node_name']} --D:device_name={params['device_name']} --D:ch00={params['ch00']} --D:ch01={params['ch01']} --D:ch02={params['ch02']} --D:ch03={params['ch03']} --D:ch04={params['ch04']} --D:ch05={params['ch05']}; exec bash\""

        # Show confirmation dialog
        response = messagebox.askyesno(
            "Restart Service",
            f"Restarting service on node {node_name} ({ip}).\n\n"
            + f"Commands to be executed:\n1. {stop_command}\n2. {start_command}\n\n" 
            + "Do you want to proceed?",
        )

        if not response:
            # User canceled
            self.log_message(
                f"User aborted restarting service on node {node_name} ({ip})"
            )
            return

        self.log_message(f"Restarting service on {node_name} ({ip})")

        # Execute the commands via SSH
        stop_result = self.execute_ssh_command(ip, stop_command)

        if stop_result == "success":
            self.log_message("Waiting for service to stop...")
            time.sleep(1)  # Wait for the service to stop
            start_result = self.execute_ssh_command(ip, start_command)

            if start_result == "success":
                self.root.after(
                    500, lambda: self.update_node_status(node_name, "Stopped")
                )
                self.root.after(
                    1500, lambda: self.update_node_status(node_name, "Running")
                )
            else:
                self.root.after(
                    500, lambda: self.update_node_status(node_name, "Stopped")
                )

    def execute_ssh_command(self, ip, command):
        try:
            # Get node name from IP
            node_name = None
            for name, node_ip in self.model.non_local_nodes:
                if node_ip == ip:
                    node_name = name
                    break

            if not node_name:
                self.log_message(f"ERROR: Cannot find node name for IP {ip}")
                return None

            # Get authentication credentials
            username, password = self.model.get_node_credentials(node_name)

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username=username, password=password)
            stdin, stdout, stderr = client.exec_command(command)
            output = stdout.read().decode("utf-8")
            error = stderr.read().decode("utf-8")

            # Ensure client is closed properly
            try:
                client.close()
            except Exception:
                pass

            self.log_message(f"Command executed on {ip}")
            self.log_message(f"SSH command executed on {ip}: {command}")

            if output or error:
                self.log_message(f"SSH output for {ip}: {output}")
                if error:
                    self.log_message(f"SSH error for {ip}: {error}")
                    messagebox.showwarning(
                        "SSH Command Warning",
                        f"Command executed but with errors:\n{error}",
                    )

            if "status" in command.lower():
                return "running"

            return "success"
        except SSHException as e:
            error_msg = f"SSH error: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            messagebox.showerror("SSH Error", f"Failed to connect to {ip}: {str(e)}")
            return None
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            messagebox.showerror(
                "Error", f"Unexpected error executing command on {ip}: {str(e)}"
            )
            return None

    def apply_authentication(self):
        """Update node authentication information"""
        selected_items = self.view.tree.selection()
        if selected_items:
            item = selected_items[0]
            node_name = self.view.tree.item(item, "values")[0]

            new_username = self.view.username_var.get().strip()
            new_password = self.view.password_var.get().strip()

            if not new_username:
                messagebox.showerror("Error", "Username cannot be empty!")
                return

            self.model.set_node_credentials(node_name, new_username, new_password)

            messagebox.showinfo(
                "Success", f"Authentication info for node {node_name} has been updated."
            )
            self.log_message(f"Updated authentication info for node {node_name}")
        else:
            messagebox.showerror("Error", "Please select a node first!")

    def apply_parameters(self):
        """Apply node parameters for service startup"""
        selected_items = self.view.tree.selection()
        if selected_items:
            item = selected_items[0]
            node_name = self.view.tree.item(item, "values")[0]

            # Get parameters from UI
            params = {
                "laccs_path": self.view.laccs_path_var.get().strip(),
                "node_name": self.view.node_name_var.get().strip(),
                "device_name": self.view.device_name_var.get().strip(),
                "ch00": self.view.ch00_var.get().strip(),
                "ch01": self.view.ch01_var.get().strip(),
                "ch02": self.view.ch02_var.get().strip(),
                "ch03": self.view.ch03_var.get().strip(),
                "ch04": self.view.ch04_var.get().strip(),
                "ch05": self.view.ch05_var.get().strip(),
            }

            # Validate laccs_path parameter
            if not params["laccs_path"]:
                messagebox.showerror(
                    "Error", "LACCS Installation Path cannot be empty!"
                )
                return

            # Validate required parameters
            if not params["node_name"]:
                messagebox.showerror("Error", "Node Name cannot be empty!")
                return

            # Save parameters
            self.model.set_node_params(node_name, params)

            messagebox.showinfo(
                "Success", f"Parameters for node {node_name} have been updated."
            )
            self.log_message(f"Updated parameters for node {node_name}")
        else:
            messagebox.showerror("Error", "Please select a node first!")

    def edit_node_config(self):
        """Edit the config file of the selected node"""
        # Get selected node info
        node_name, ip = self.get_selected_node_info()
        if not node_name or not ip:
            return

        # Get authentication info
        username, password = self.model.get_node_credentials(node_name)

        # Create a temporary directory to store config files
        import os, tempfile

        temp_dir = os.path.join(tempfile.gettempdir(), f"node_config_{node_name}")
        os.makedirs(temp_dir, exist_ok=True)

        # Define local config file path
        local_config_path = os.path.join(temp_dir, "node.config")

        # Read config file from remote node
        self.log_message(f"Reading config file from node {node_name} ({ip})...")
        try:
            # Use paramiko to read the file
            import paramiko

            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=username, password=password)

            # Use SFTP to download the config file
            sftp = ssh.open_sftp()
            remote_config_path = "/opt/LACCS#/configs/node.config"
            sftp.get(remote_config_path, local_config_path)

            # Ensure connections are closed properly
            try:
                sftp.close()
            except Exception:
                pass

            try:
                ssh.close()
            except Exception:
                pass

            self.log_message(
                f"Config file downloaded successfully to {local_config_path}"
            )
        except Exception as e:
            error_msg = f"Failed to read config file from node {node_name}: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            messagebox.showerror("Error", error_msg)
            return

        # Parse the config file
        config_entries = []
        with open(local_config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:  # Skip empty lines
                    config_entries.append((True, "", "", True))  # Empty line
                    continue
                if line.startswith("#"):
                    # Commented line
                    parts = line[1:].strip().split("=", 1)
                    if len(parts) == 1:
                        config_entries.append((True, parts[0].strip(), "", False))
                    else:
                        config_entries.append(
                            (True, parts[0].strip(), parts[1].strip(), False)
                        )
                else:
                    # Active line
                    parts = line.split("=", 1)
                    if len(parts) == 1:
                        config_entries.append((False, parts[0].strip(), "", False))
                    else:
                        config_entries.append(
                            (False, parts[0].strip(), parts[1].strip(), False)
                        )

        # Create edit window
        config_window = tk.Toplevel(self.root)
        config_window.title(f"Edit Config - {node_name}")
        config_window.geometry("600x700")
        config_window.resizable(True, True)

        # Create a frame with scrollbar
        frame = ttk.Frame(config_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create canvas and scrollbar
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create content frame inside canvas
        content_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")

        # Update scroll region when content changes
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        content_frame.bind("<Configure>", on_frame_configure)

        # Store checkbox and entry variables
        config_vars = []

        # Create UI elements for each config entry
        for index, (is_commented, key, value, is_empty) in enumerate(config_entries):
            if is_empty:
                # Empty line
                ttk.Label(content_frame, text="").pack(pady=2, fill=tk.X)
                config_vars.append((None, None, None))
            else:
                entry_frame = ttk.Frame(content_frame)
                entry_frame.pack(fill=tk.X, pady=2)

                # Checkbox for commenting/uncommenting
                comment_var = tk.BooleanVar(value=is_commented)
                comment_cb = ttk.Checkbutton(
                    entry_frame, text="#", variable=comment_var, width=2
                )
                comment_cb.pack(side=tk.LEFT, padx=5)

                # Key entry
                key_var = tk.StringVar(value=key)
                key_entry = ttk.Entry(entry_frame, textvariable=key_var, width=20)
                key_entry.pack(side=tk.LEFT, padx=5)

                # Equal sign label
                ttk.Label(entry_frame, text="=").pack(side=tk.LEFT)

                # Value entry
                value_var = tk.StringVar(value=value)
                value_entry = ttk.Entry(entry_frame, textvariable=value_var, width=40)
                value_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

                config_vars.append((comment_var, key_var, value_var))

        # Save button
        def save_config():
            # Save to local file
            try:
                with open(local_config_path, "w", encoding="utf-8") as f:
                    for (comment_var, key_var, value_var), (
                        is_commented,
                        key,
                        value,
                        is_empty,
                    ) in zip(config_vars, config_entries):
                        if is_empty:
                            f.write("\n")
                        else:
                            comment = "#" if comment_var.get() else ""
                            key = key_var.get().strip()
                            value = value_var.get().strip()
                            if key and value:
                                f.write(f"{comment}{key} = {value}\n")
                            elif key:
                                f.write(f"{comment}{key}\n")

                self.log_message(f"Config file saved locally: {local_config_path}")

                # Ask user if they want to sync to SSH
                if messagebox.askyesno(
                    "Sync Config",
                    f"Do you want to sync the updated config file to node {node_name}?",
                ):
                    try:
                        # Use paramiko to upload the file
                        ssh = paramiko.SSHClient()
                        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        ssh.connect(ip, username=username, password=password)

                        sftp = ssh.open_sftp()
                        sftp.put(local_config_path, remote_config_path)
                        sftp.close()
                        ssh.close()

                        self.log_message(
                            f"Config file synced to node {node_name} successfully"
                        )
                        messagebox.showinfo(
                            "Success",
                            f"Config file has been updated and synced to node {node_name}",
                        )
                        config_window.destroy()
                    except Exception as e:
                        error_msg = (
                            f"Failed to sync config file to node {node_name}: {str(e)}"
                        )
                        self.log_message(f"ERROR: {error_msg}")
                        messagebox.showerror("Error", error_msg)
                else:
                    messagebox.showinfo(
                        "Saved",
                        "Config file has been saved locally but not synced to the node.",
                    )
            except Exception as e:
                error_msg = f"Failed to save config file: {str(e)}"
                self.log_message(f"ERROR: {error_msg}")
                messagebox.showerror("Error", error_msg)

        # Cancel button
        def cancel_edit():
            config_window.destroy()

        # Add buttons at the bottom
        button_frame = ttk.Frame(config_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        cancel_button = ttk.Button(button_frame, text="Cancel", command=cancel_edit)
        cancel_button.pack(side=tk.RIGHT, padx=5)

        save_button = ttk.Button(button_frame, text="Save", command=save_config)
        save_button.pack(side=tk.RIGHT, padx=5)

        # Make the window modal
        config_window.transient(self.root)
        config_window.grab_set()
        self.root.wait_window(config_window)

    def edit_nodes_tsv(self):
        """Edit FileDB/NODES.tsv file on remote machine with full CRUD operations"""
        # Get selected node info
        node_name, ip = self.get_selected_node_info()
        if not node_name or not ip:
            return

        # Get authentication info
        username, password = self.model.get_node_credentials(node_name)

        # Create a temporary directory to store files
        import os
        import tempfile
        import csv

        temp_dir = os.path.join(tempfile.gettempdir(), f"nodes_tsv_{node_name}")
        os.makedirs(temp_dir, exist_ok=True)

        # Define local NODES.tsv file path
        local_nodes_path = os.path.join(temp_dir, "NODES.tsv")

        # Read NODES.tsv file from remote node
        self.log_message(f"Reading NODES.tsv from node {node_name} ({ip})...")
        try:
            # Use paramiko to read the file
            import paramiko

            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=username, password=password)

            # Use SFTP to download the NODES.tsv file
            sftp = ssh.open_sftp()
            remote_nodes_path = "/opt/LACCS#/FileDB/NODES.tsv"
            sftp.get(remote_nodes_path, local_nodes_path)

            # Ensure connections are closed properly
            try:
                sftp.close()
            except Exception:
                pass

            try:
                ssh.close()
            except Exception:
                pass

            self.log_message(f"NODES.tsv downloaded successfully to {local_nodes_path}")
        except Exception as e:
            error_msg = f"Failed to read NODES.tsv from node {node_name}: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            messagebox.showerror("Error", error_msg)
            return

        # Read the content of NODES.tsv into headers and rows
        headers = []
        rows = []
        try:
            with open(local_nodes_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter="\t")
                lines = list(reader)

                if lines:
                    # First line is headers (remove # sign)
                    headers = [h.lstrip("#") for h in lines[0]]
                    # Load data rows (skip header and empty rows)
                    for row in lines[1:]:
                        if any(row):  # Skip empty rows
                            rows.append(row)
        except Exception as e:
            error_msg = f"Failed to parse NODES.tsv: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            messagebox.showerror("Error", error_msg)
            return

        # Create edit window
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Edit NODES.tsv - {node_name}")
        edit_window.geometry("900x600")
        edit_window.resizable(True, True)

        # Create a frame with scrollbars
        tree_frame = ttk.Frame(edit_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        # Create Treeview
        tree = ttk.Treeview(
            tree_frame,
            columns=headers,
            show="headings",
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set,
        )

        # Configure scrollbars
        v_scroll.config(command=tree.yview)
        h_scroll.config(command=tree.xview)

        # Pack the widgets
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure columns
        for col in headers:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor=tk.CENTER)

        # Insert data into treeview
        for row in rows:
            tree.insert("", tk.END, values=row)

        # Function to handle double click on cell for editing
        def on_tree_double_click(event):
            column = tree.identify_column(event.x)
            col_index = int(column.replace("#", "")) - 1
            item = tree.identify_row(event.y)

            if item and 0 <= col_index < len(headers):
                current_value = tree.item(item, "values")[col_index]
                col_name = headers[col_index]

                # Create a popup dialog for editing
                new_value = simpledialog.askstring(
                    "Edit Cell",
                    f"Please enter new value for {col_name}:",
                    initialvalue=current_value,
                )

                if new_value is not None:
                    # Update the treeview
                    values = list(tree.item(item, "values"))
                    values[col_index] = new_value
                    tree.item(item, values=values)

        # Bind double click event
        tree.bind("<Double-1>", on_tree_double_click)

        # Function to add a new row
        def add_new_row():
            # Create a new row with empty values
            new_row = ["" for _ in headers]
            # Insert at the end
            tree.insert("", tk.END, values=new_row)
            # Automatically select the new row
            items = tree.get_children()
            if items:
                last_item = items[-1]
                tree.selection_set(last_item)
                tree.focus(last_item)
                messagebox.showinfo(
                    "Add Row", "New row added. Double-click on cells to edit values."
                )

        # Function to delete selected rows
        def delete_selected_rows():
            selected_items = tree.selection()
            if not selected_items:
                messagebox.showwarning("Warning", "No rows selected for deletion")
                return

            # Confirm deletion
            confirm = messagebox.askyesno(
                "Confirm Deletion",
                f"Are you sure you want to delete {len(selected_items)} selected row(s)?",
            )

            if confirm:
                for item in selected_items:
                    tree.delete(item)
                messagebox.showinfo("Success", f"{len(selected_items)} row(s) deleted")

        # Function to save the NODES.tsv
        def save_nodes_tsv():
            # Get all data from treeview
            all_rows = []
            for item in tree.get_children():
                all_rows.append(tree.item(item, "values"))

            # Save to local temporary file
            try:
                with open(local_nodes_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f, delimiter="\t")
                    # Write header row (add # sign)
                    writer.writerow(["#" + h for h in headers])
                    # Write data rows
                    for row in all_rows:
                        writer.writerow(row)

                self.log_message(f"NODES.tsv saved locally: {local_nodes_path}")

                # Ask user if they want to sync to SSH
                if messagebox.askyesno(
                    "Sync NODES.tsv",
                    f"Do you want to sync the updated NODES.tsv to node {node_name}?",
                ):
                    try:
                        # Reconnect and upload the file
                        ssh_sync = paramiko.SSHClient()
                        ssh_sync.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        ssh_sync.connect(ip, username=username, password=password)

                        sftp_sync = ssh_sync.open_sftp()
                        sftp_sync.put(local_nodes_path, remote_nodes_path)
                        sftp_sync.close()
                        ssh_sync.close()

                        self.log_message(
                            f"NODES.tsv synced to node {node_name} successfully"
                        )
                        messagebox.showinfo(
                            "Success",
                            f"NODES.tsv has been updated and synced to node {node_name}",
                        )
                        edit_window.destroy()
                    except Exception as e:
                        error_msg = (
                            f"Failed to sync NODES.tsv to node {node_name}: {str(e)}"
                        )
                        self.log_message(f"ERROR: {error_msg}")
                        messagebox.showerror("Error", error_msg)
                else:
                    messagebox.showinfo(
                        "Saved",
                        "NODES.tsv has been saved locally but not synced to the node.",
                    )
            except Exception as e:
                error_msg = f"Failed to save NODES.tsv: {str(e)}"
                self.log_message(f"ERROR: {error_msg}")
                messagebox.showerror("Error", error_msg)

        # Function to cancel editing
        def cancel_edit():
            edit_window.destroy()

        # Add buttons at the bottom
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # Add CRUD operation buttons
        add_button = ttk.Button(button_frame, text="Add Row", command=add_new_row)
        add_button.pack(side=tk.LEFT, padx=5)

        delete_button = ttk.Button(
            button_frame, text="Delete Selected", command=delete_selected_rows
        )
        delete_button.pack(side=tk.LEFT, padx=5)

        cancel_button = ttk.Button(button_frame, text="Cancel", command=cancel_edit)
        cancel_button.pack(side=tk.RIGHT, padx=5)

        save_button = ttk.Button(button_frame, text="Save", command=save_nodes_tsv)
        save_button.pack(side=tk.RIGHT, padx=5)

        # Make the window modal
        edit_window.transient(self.root)
        edit_window.grab_set()
        self.root.wait_window(edit_window)

    def deploy_service(self):
        node_name, ip = self.get_selected_node_info()
        if not node_name or not ip:
            return

        self.log_message(f"Preparing to deploy to {node_name} ({ip})")
        self.log_message(f"Preparing deployment to {node_name}")

        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Select tgz file",
            filetypes=[("TGZ files", "*.tgz"), ("All files", "*")],
        )

        if not file_path:
            self.log_message("Deployment cancelled by user")
            self.log_message("Ready")
            return

        target_path = simpledialog.askstring(
            "Target Path",
            "Enter target path (e.g., /opt/LACCS#):",
            initialvalue="/opt/LACCS#",
        )

        if not target_path:
            self.log_message("Deployment cancelled by user")
            self.log_message("Ready")
            return

        if not target_path.endswith("/"):
            target_path += "/"

        import os

        filename = os.path.basename(file_path)
        remote_tmp_path = f"/tmp/{filename}"

        self.log_message(
            f"Starting deployment of {filename} to {node_name} ({ip}) target: {target_path}"
        )

        progress_window = tk.Toplevel(self.root)
        progress_window.title(f"Deploying to {node_name}")
        progress_window.geometry("400x150")
        progress_window.transient(self.root)
        progress_window.grab_set()

        progress_label = ttk.Label(progress_window, text="Starting deployment...")
        progress_label.pack(pady=20)

        progress_bar = ttk.Progressbar(
            progress_window, orient=tk.HORIZONTAL, length=300, mode="determinate"
        )
        progress_bar.pack(pady=10)

        self.root.update()

        try:
            # Get authentication credentials
            username, password = self.model.get_node_credentials(node_name)

            progress_label.config(text="Connecting to server...")
            self.root.update()

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username=username, password=password)

            progress_label.config(text="Transferring file...")
            self.root.update()

            # Use SFTP to upload the file with error handling
            sftp = client.open_sftp()

            try:
                # Get file size for progress tracking
                file_size = os.path.getsize(file_path)
                transferred = 0

                # Open local and remote files
                with open(file_path, "rb") as local_file:
                    with sftp.open(remote_tmp_path, "wb") as remote_file:
                        # Transfer in chunks
                        chunk_size = 32768  # 32KB chunks
                        while True:
                            data = local_file.read(chunk_size)
                            if not data:
                                break
                            remote_file.write(data)
                            transferred += len(data)
                            progress = int((transferred / file_size) * 100)
                            progress_bar["value"] = progress
                            self.root.update()
            finally:
                # Ensure SFTP connection is closed properly
                try:
                    sftp.close()
                except Exception:
                    pass

            progress_label.config(text="Checking target directory...")
            self.root.update()

            # Check if target directory exists
            check_dir_command = (
                f"test -d {target_path} && echo 'exists' || echo 'not exists'"
            )
            stdin, stdout, stderr = client.exec_command(check_dir_command)
            dir_exists = stdout.read().decode("utf-8").strip() == "exists"

            # Create target directory if it doesn't exist
            if not dir_exists:
                progress_label.config(text="Creating target directory...")
                self.root.update()

                create_dir_command = f"mkdir -p {target_path}"
                stdin, stdout, stderr = client.exec_command(create_dir_command)
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    error = stderr.read().decode("utf-8")
                    raise Exception(f"Failed to create target directory: {error}")

                self.log_message(
                    f"Created target directory {target_path} on {node_name}"
                )

            if dir_exists:
                progress_label.config(text="Target directory exists, asking user...")
                self.root.update()

                # Create a dialog to ask user what to do
                result = messagebox.askyesnocancel(
                    "Directory Exists",
                    f"The directory {target_path} already exists on {node_name}.\n\n"
                    + "Choose 'Yes' to delete existing content and deploy,\n"
                    + "'No' to deploy without deleting existing content,\n"
                    + "or 'Cancel' to abort deployment.",
                )

                if result is None:  # User cancelled
                    self.log_message(f"Deployment cancelled by user for {node_name}")
                    progress_window.destroy()
                    self.log_message("Ready")
                    client.close()
                    return
                elif result is True:  # User wants to delete existing content
                    progress_label.config(text="Deleting existing content...")
                    self.root.update()

                    # Delete existing content
                    delete_command = f"rm -rf {target_path}/*"
                    stdin, stdout, stderr = client.exec_command(delete_command)
                    exit_code = stdout.channel.recv_exit_status()
                    if exit_code != 0:
                        error = stderr.read().decode("utf-8")
                        raise Exception(f"Failed to delete existing content: {error}")

                    self.log_message(
                        f"Deleted existing content in {target_path} on {node_name}"
                    )

            progress_label.config(text="Extracting files...")
            progress_bar["value"] = 75
            self.root.update()

            # Extract the archive
            command = f"tar -xzf {remote_tmp_path} -C {target_path}"
            stdin, stdout, stderr = client.exec_command(command)

            # Wait for extraction to complete
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode("utf-8")
            error = stderr.read().decode("utf-8")

            if exit_code != 0:
                raise Exception(f"Failed to extract files: {error}")

            progress_label.config(text="Cleaning up...")
            progress_bar["value"] = 90
            self.root.update()

            # Clean up temporary file
            client.exec_command(f"rm {remote_tmp_path}")

            # Ensure client is closed properly
            try:
                client.close()
            except Exception:
                pass

            progress_bar["value"] = 100
            self.root.update()

            self.log_message(
                f"Successfully deployed {filename} to {target_path} on {node_name} ({ip})"
            )
            self.log_message(f"Deployed to {node_name}")

        except Exception as e:
            error_msg = f"Deployment failed: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            self.log_message("Deployment failed")
            progress_window.destroy()

            messagebox.showerror(
                "Deployment Error", f"Failed to deploy to {node_name} ({ip}):\n{str(e)}"
            )

    def check_all_nodes_status(self):
        import concurrent.futures

        while not self.stop_status_check and self.main_loop_active:
            # Create a thread pool with a maximum of 5 worker threads
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all node status checks as concurrent tasks
                future_to_node = {
                    executor.submit(self._check_node_status_async, node_name, ip): (
                        node_name,
                        ip,
                    )
                    for node_name, ip in self.model.non_local_nodes
                }

                # Process completed tasks
                for future in concurrent.futures.as_completed(future_to_node):
                    node_name, ip = future_to_node[future]
                    try:
                        future.result()  # This will raise exceptions if any occurred during execution
                    except Exception as e:
                        # Check if main loop is still active before updating UI
                        if self.main_loop_active:
                            try:
                                self.log_message(
                                    f"ERROR in status check for {node_name}: {str(e)}"
                                )
                                # Update status in main thread
                                self.root.after(
                                    0,
                                    lambda name=node_name: self.update_node_status(
                                        name, "Error"
                                    ),
                                )
                            except Exception:
                                # Prevent thread from crashing if main loop has terminated
                                print(f"ERROR in status check for {node_name}: {str(e)}")

            # Responsive sleep - check stop flag every second
            sleep_time = 30
            while sleep_time > 0 and not self.stop_status_check and self.main_loop_active:
                time.sleep(1)
                sleep_time -= 1

    def _check_node_status_async(self, node_name, ip):
        """
        Async version of _check_node_status that performs the status check
        in a worker thread and then updates the UI in the main thread.
        Modified to skip nodes that have failed once (no retry)
        """
        # Check if we should skip this node due to previous failures
        # If node has failed before, skip it completely (no retry)
        if node_name in self.timed_out_nodes:
            return

        current_time = time.time()
        try:
            # Skip status check for localhost
            if ip == "127.0.0.1":
                if self.main_loop_active:
                    self.root.after(
                        0,
                        lambda name=node_name: (
                            self.log_message_ignore(
                                f"Skipping status check for localhost node {name}"
                            ),
                            self.update_node_status(name, "Localhost"),
                        ),
                    )
                return

            if self.main_loop_active:
                self.root.after(
                    0,
                    lambda name=node_name, addr=ip: self.log_message_ignore(
                        f"Checking status for {name} ({addr})..."
                    ),
                )

            # First check if the screen session named LACCS exists
            # This command returns 0 if the session exists, 1 otherwise
            screen_status_command = 'screen -list | grep -q "LACCS"'

            # Command to check for any LACCS process running outside of screen
            standalone_status_command = (
                'ps -ef | grep -v grep | grep -v screen | grep -q "LACCS"'
            )

            # Use a low timeout for status checks
            try:
                # Get authentication credentials
                username, password = self.model.get_node_credentials(node_name)

                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(ip, username=username, password=password, timeout=5)

                # First check for screen session
                stdin, stdout, stderr = client.exec_command(screen_status_command)
                screen_exit_code = stdout.channel.recv_exit_status()

                if screen_exit_code == 0:
                    status = "Running"
                else:
                    # If not in screen, check for standalone process
                    stdin, stdout, stderr = client.exec_command(
                        standalone_status_command
                    )
                    standalone_exit_code = stdout.channel.recv_exit_status()

                    if standalone_exit_code == 0:
                        status = "standalone"
                    else:
                        status = "Stopped"

                # Ensure client is closed properly
                try:
                    client.close()
                except Exception:
                    pass

                # Leave timeout tracking in place even after successful connection
                # This ensures that once a node fails once, it will be skipped in future checks

            except paramiko.AuthenticationException:
                if self.main_loop_active:
                    self.root.after(
                        0,
                        lambda name=node_name, addr=ip: self.log_message(
                            f"Authentication failed for {name} ({addr})"
                        ),
                    )
                status = "Error"
            except paramiko.SSHException as e:
                # Handle timeout specifically
                if "timed out" in str(e):
                    # Mark node as failed - will be skipped in future checks
                    self.timed_out_nodes[node_name] = (current_time, 1)
                
                if self.main_loop_active:
                    self.root.after(
                        0,
                        lambda name=node_name, err=str(e): self.log_message(
                            f"SSH error checking status for {name}: {err}"
                        ),
                    )
                status = "Error"
            except Exception as e:
                # Handle timeout specifically
                if "timed out" in str(e):
                    # Mark node as failed - will be skipped in future checks
                    self.timed_out_nodes[node_name] = (current_time, 1)
                
                if self.main_loop_active:
                    self.root.after(
                        0,
                        lambda name=node_name, err=str(e): self.log_message(
                            f"Error checking status for {name}: {err}"
                        ),
                    )
                status = "Error"

            # Update status in main thread if main loop is still active
            if self.main_loop_active:
                try:
                    self.root.after(
                        0, lambda name=node_name, s=status: self.update_node_status(name, s)
                    )
                except Exception:
                    # Prevent thread from crashing if main loop has terminated
                    pass
        except Exception as e:
            # Log error without attempting UI updates if main loop is inactive
            if self.main_loop_active:
                try:
                    self.root.after(
                        0,
                        lambda name=node_name, err=str(e): self.log_message(
                            f"ERROR checking status for {name}: {err}"
                        ),
                    )
                    # Update status in main thread
                    self.root.after(
                        0, lambda name=node_name: self.update_node_status(name, "Error")
                    )
                except Exception:
                    # Prevent thread from crashing if main loop has terminated
                    pass
            else:
                # Just print to console if main loop is inactive
                print(f"ERROR checking status for {node_name}: {str(e)}")

    def _check_node_status(self, node_name, ip):
        try:
            # Skip status check for localhost
            if ip == "127.0.0.1":
                self.log_message(
                    f"Skipping status check for localhost node {node_name}"
                )
                self.update_node_status(node_name, "Localhost")
                return

            self.log_message(f"Checking status for {node_name} ({ip})...")

            # First check if the screen session named LACCS exists
            # This command returns 0 if the session exists, 1 otherwise
            screen_status_command = 'screen -list | grep -q "LACCS"'

            # Command to check for any LACCS process running outside of screen
            standalone_status_command = (
                'ps -ef | grep -v grep | grep -v screen | grep -q "LACCS"'
            )

            # Use a low timeout for status checks
            try:
                # Get authentication credentials
                username, password = self.model.get_node_credentials(node_name)

                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(ip, username=username, password=password, timeout=5)

                # First check for screen session
                stdin, stdout, stderr = client.exec_command(screen_status_command)
                screen_exit_code = stdout.channel.recv_exit_status()

                if screen_exit_code == 0:
                    status = "Running"
                else:
                    # If not in screen, check for standalone process
                    stdin, stdout, stderr = client.exec_command(
                        standalone_status_command
                    )
                    standalone_exit_code = stdout.channel.recv_exit_status()

                    if standalone_exit_code == 0:
                        status = "standalone"
                    else:
                        status = "Stopped"

                # Ensure client is closed properly
                try:
                    client.close()
                except Exception:
                    pass
            except paramiko.AuthenticationException:
                self.log_message(f"Authentication failed for {node_name} ({ip})")
                status = "Error"
            except paramiko.SSHException as e:
                self.log_message(f"SSH error checking status for {node_name}: {str(e)}")
                status = "Error"
            except Exception as e:
                self.log_message(f"Error checking status for {node_name}: {str(e)}")
                status = "Error"

            self.update_node_status(node_name, status)
        except Exception as e:
            self.log_message(f"ERROR checking status for {node_name}: {str(e)}")
            self.update_node_status(node_name, "Error")

    def update_node_status(self, node_name, status):
        self.model.update_node_status(node_name, status)

        # Check if main loop is still active before updating UI
        if self.main_loop_active:
            try:
                for item in self.view.status_tree.get_children():
                    item_values = self.view.status_tree.item(item, "values")
                    if item_values and item_values[0] == node_name:
                        # Update existing item instead of creating a new one
                        self.view.status_tree.item(
                            item,
                            values=(
                                node_name,
                                item_values[1] if len(item_values) > 1 else "N/A",
                                status,
                            ),
                        )

                        if status.lower() == "running":
                            self.view.status_tree.item(item, tags=("status_ok",))
                        elif status.lower() == "stopped":
                            self.view.status_tree.item(item, tags=("status_stopped",))
                        elif status.lower() == "error":
                            self.view.status_tree.item(item, tags=("status_error",))
                        elif status.lower() == "standalone":
                            self.view.status_tree.item(item, tags=("status_standalone",))
                        else:
                            self.view.status_tree.item(item, tags=("status_unknown",))
                        break

                # Log the status update if main loop is active
                try:
                    self.log_message_ignore(f"Status updated for {node_name}: {status}")
                except Exception:
                    pass
            except Exception:
                # Prevent thread from crashing if UI has been destroyed
                pass
        else:
            # Just log to console if main loop is inactive
            print(f"Status updated for {node_name}: {status}")

    def setup_log_file(self):
        """Create log file with timestamp"""
        # Create logs directory if it doesn't exist
        import os

        log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Logs"
        )
        os.makedirs(log_dir, exist_ok=True)

        # Generate log file name with timestamp
        timestamp = datetime.datetime.now().strftime("%Y.%m.%d-%H.%M.%S.%f")[:-3]
        log_file_path = os.path.join(log_dir, f"log-{timestamp}.tsv")

        try:
            # Open log file for writing
            self.log_file = open(log_file_path, "w", encoding="utf-8")
            # Write header
            self.log_file.write("Timestamp\tMessage\n")
            self.log_file.flush()
        except Exception as e:
            print(f"Failed to create log file: {str(e)}")

    def log_message_ignore(self, message):
        return

    def log_message(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        # Determine log level and color
        level = "INFO"
        if message.startswith("ERROR"):
            level = "ERROR"
            tag = "error"
        elif message.startswith("WARNING"):
            level = "WARNING"
            tag = "warning"
        else:
            tag = "info"

        # Add to log history with level information
        self.log_history.append((timestamp, message, tag))

        # Write to log file if it's open
        try:
            if self.log_file and not self.log_file.closed:
                self.log_file.write(f"{timestamp}\t{message}\n")
                self.log_file.flush()
        except Exception as e:
            print(f"Failed to write to log file: {str(e)}")

        # Print to console for debugging
        print(log_entry.strip())

        # Update log display with filtering if main loop is still active
        if self.main_loop_active:
            try:
                # Use after to ensure UI updates happen in the main thread
                self.root.after(0, self.filter_log_entries)
            except Exception:
                pass

    def filter_log_entries(self, *args):
        """Filter log entries based on search term with fuzzy matching"""
        filter_text = self.view.log_filter_var.get().lower()

        self.view.log_text.config(state=tk.NORMAL)
        self.view.log_text.delete(1.0, tk.END)

        # Configure text tags for coloring
        self.view.log_text.tag_configure("error", foreground="red")
        self.view.log_text.tag_configure("warning", foreground="orange")
        self.view.log_text.tag_configure("info", foreground="black")

        # Add filtered log entries
        for timestamp, message, tag in self.log_history:
            log_entry = f"[{timestamp}] {message}\n"

            # Check if entry matches filter (fuzzy matching)
            if not filter_text or self.fuzzy_match(log_entry.lower(), filter_text):
                self.view.log_text.insert(tk.END, log_entry, tag)

        self.view.log_text.see(tk.END)
        self.view.log_text.config(state=tk.DISABLED)

    def fuzzy_match(self, text, pattern):
        """Simple fuzzy matching implementation"""
        if not pattern:
            return True

        pattern_index = 0
        for char in text:
            if char == pattern[pattern_index]:
                pattern_index += 1
                if pattern_index == len(pattern):
                    return True
        return False

    def clear_log(self):
        # Clear log history
        self.log_history = []

        # Clear log display
        self.view.log_text.config(state=tk.NORMAL)
        self.view.log_text.delete(1.0, tk.END)
        self.view.log_text.config(state=tk.DISABLED)

        # Log the clearing event
        self.log_message("Log cleared")

    def force_refresh_status(self):
        self.log_message("Forcing status refresh for all nodes...")
        refresh_thread = threading.Thread(target=self._force_refresh_all)
        refresh_thread.daemon = True
        refresh_thread.start()

    def _force_refresh_all(self):
        for node_name, ip in self.model.non_local_nodes:
            self.root.after(
                0, lambda name=node_name, addr=ip: self._check_node_status(name, addr)
            )

    def update_shared_lib(self):
        """Update shared library for a selected node"""
        node_name, ip = self.get_selected_node_info()
        if not node_name or not ip:
            return

        # Step 1: Ask user to select SO file
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Shared Library File",
            filetypes=[("SO files", "*.so"), ("All files", "*")],
        )

        if not file_path:
            self.log_message("Library update cancelled by user")
            return

        # Get filename
        import os
        filename = os.path.basename(file_path)
        target_path = "/opt/LACCS/Controls/"
        remote_file_path = target_path + filename
        backup_command = "mv /opt/LACCS/Controls/libBeamLossMonitor.so* /tmp"

        # Step 2: Show confirmation dialog with commands
        from tkinter import messagebox
        confirm_message = f"Updating shared library on node {node_name} ({ip}).\n\n"
        confirm_message += "Commands to be executed:\n"
        confirm_message += "1. Stop service\n"
        confirm_message += f"2. {backup_command}\n"
        confirm_message += f"3. Upload {filename} to {target_path}\n"
        confirm_message += "4. Restart service (optional)\n\n"
        confirm_message += "Do you want to proceed?"

        response = messagebox.askyesno("Update Shared Library", confirm_message)
        if not response:
            self.log_message(f"User cancelled library update on node {node_name}")
            return

        try:
            # Step 3: Stop service
            self.log_message(f"Stopping service on node {node_name}...")
            # Get authentication credentials
            username, password = self.model.get_node_credentials(node_name)
            # Stop screen session
            stop_command = "screen -S LACCS -X quit"
            result = self.execute_ssh_command(ip, stop_command)
            if result != "success":
                # Also try to kill standalone process
                kill_command = "pkill -f LACCS"
                self.execute_ssh_command(ip, kill_command)
            self.log_message(f"Service stopped on node {node_name}")

            # Step 4: Execute backup command
            self.log_message(f"Backing up existing library files on node {node_name}...")
            result = self.execute_ssh_command(ip, backup_command)
            if result is None:
                raise Exception("Failed to backup existing library files")
            self.log_message(f"Existing library files backed up to /tmp on node {node_name}")

            # Step 5: Upload new SO file
            self.log_message(f"Uploading {filename} to node {node_name}...")
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username=username, password=password)
            
            # Use SFTP to upload the file
            sftp = client.open_sftp()
            try:
                sftp.put(file_path, remote_file_path)
            finally:
                try:
                    sftp.close()
                except Exception:
                    pass
                try:
                    client.close()
                except Exception:
                    pass
            
            self.log_message(f"Library file {filename} uploaded successfully to node {node_name}")

            # Step 6: Ask if user wants to restart service
            restart_response = messagebox.askyesno(
                "Restart Service",
                f"Library update completed on node {node_name}.\n\nDo you want to restart the service?"
            )
            
            if restart_response:
                self.log_message(f"Restarting service on node {node_name}...")
                # Start service using screen with node-specific path and parameters
                node_params = self.model.get_node_params(node_name)
                laccs_path = node_params["laccs_path"].replace("#", "")  # Remove # if present
                if not laccs_path.endswith("/"):
                    laccs_path += "/"
                screen_command = f"screen -wipe; screen -L -dmS LACCS bash -lc \"cd {laccs_path} && ulimit -n 204800 && ulimit -s 81920 && ./LACCS --user_name=guest --password=guest_password --data_id=uptodate --D:node_name={node_params['node_name']} --D:device_name={node_params['device_name']} --D:ch00={node_params['ch00']} --D:ch01={node_params['ch01']} --D:ch02={node_params['ch02']} --D:ch03={node_params['ch03']} --D:ch04={node_params['ch04']} --D:ch05={node_params['ch05']}; exec bash\""
                result = self.execute_ssh_command(ip, screen_command)
                if result == "success":
                    self.root.after(1000, lambda: self.update_node_status(node_name, "Running"))
                    self.log_message(f"Service restarted successfully on node {node_name}")
                else:
                    self.root.after(1000, lambda: self.update_node_status(node_name, "Stopped"))
                    self.log_message(f"Failed to restart service on node {node_name}")
            else:
                self.log_message(f"Service restart skipped on node {node_name}")

        except Exception as e:
            error_msg = f"Failed to update shared library on node {node_name}: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            messagebox.showerror("Update Error", error_msg)
            return

        self.log_message(f"Shared library update completed successfully on node {node_name}")

    def update_shared_lib_all(self):
        """Update shared library for all nodes using thread pool - UI-safe version"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Shared Library File",
            filetypes=[("SO files", "*.so"), ("All files", "*")],
        )

        if not file_path:
            self.log_message("Batch library update cancelled by user")
            return

        # Get filename
        import os
        filename = os.path.basename(file_path)
        
        # Show confirmation dialog
        from tkinter import messagebox
        confirm_message = "Updating shared library on ALL nodes.\n\n"
        confirm_message += f"Library file: {filename}\n\n"
        confirm_message += "This operation will:\n"
        confirm_message += "1. Stop service on each node\n"
        confirm_message += "2. Backup existing library files to /tmp\n"
        confirm_message += "3. Upload new library file\n"
        confirm_message += "4. Restart service\n\n"
        confirm_message += "This operation will run without further confirmation.\n"
        confirm_message += f"Are you sure you want to update all {len(self.model.non_local_nodes)} nodes?"

        response = messagebox.askyesno("Batch Update Shared Library", confirm_message)
        if not response:
            self.log_message("Batch library update cancelled by user")
            return

        # Create and start a new thread to run the actual update process
        # This keeps the UI responsive
        update_thread = threading.Thread(
            target=self._update_shared_lib_all_async, 
            args=(file_path, filename),
            daemon=True
        )
        update_thread.start()

    def _update_shared_lib_all_async(self, file_path, filename):
        """Helper method to perform the actual update process in a background thread"""
        # Log message in the main thread
        if self.main_loop_active:
            self.root.after(
                0,
                lambda: self.log_message(f"Starting batch update of shared library {filename} on all nodes...")
            )
        
        # Read the file content once to avoid multiple reads
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
        except Exception as e:
            if self.main_loop_active:
                self.root.after(
                    0,
                    lambda e: self.log_message(f"ERROR reading library file: {str(e)}")
                )
            return
        
        # Use thread pool to process all nodes
        import concurrent.futures
        
        # Create a thread pool with a maximum of 20 worker threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Submit all node update tasks as concurrent tasks
            future_to_node = {
                executor.submit(self._update_shared_lib_node, node_name, ip, filename, file_content): 
                node_name 
                for node_name, ip in self.model.non_local_nodes
            }

            # Process completed tasks
            for future in concurrent.futures.as_completed(future_to_node):
                node_name = future_to_node[future]
                try:
                    future.result()  # This will raise exceptions if any occurred during execution
                except Exception as e:
                    # Log the error
                    if self.main_loop_active:
                        try:
                            self.log_message(f"ERROR updating library on {node_name}: {str(e)}")
                            # Update status in main thread
                            self.root.after(
                                0,
                                lambda name=node_name: self.update_node_status(name, "Error"),
                            )
                        except Exception:
                            # Prevent thread from crashing if main loop has terminated
                            print(f"ERROR updating library on {node_name}: {str(e)}")

        # Log completion message in the main thread
        if self.main_loop_active:
            self.root.after(
                0,
                lambda: self.log_message("Batch update of shared library completed for all nodes")
            )

    def _update_shared_lib_node(self, node_name, ip, filename, file_content):
        """Helper method to update shared library on a single node"""
        try:
            # Get authentication credentials
            username, password = self.model.get_node_credentials(node_name)
            
            # Step 1: Stop service
            if self.main_loop_active:
                self.root.after(
                    0,
                    lambda name=node_name, status="Updating...": 
                    self.update_node_status(name, status),
                )
                self.root.after(
                    0,
                    lambda msg=f"Stopping service on node {node_name}...": 
                    self.log_message(msg),
                )
            
            # Stop screen session and standalone process
            stop_command = "screen -S LACCS -X quit"
            self.execute_ssh_command(ip, stop_command)
            kill_command = "pkill -f LACCS"
            self.execute_ssh_command(ip, kill_command)
            
            # Wait a moment to ensure service has stopped
            import time
            time.sleep(1)

            # Step 2: Execute backup command
            backup_command = "mv /opt/LACCS/Controls/libBeamLossMonitor.so* /tmp"
            self.execute_ssh_command(ip, backup_command)

            # Step 3: Upload new SO file
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username=username, password=password)
            
            # Use SFTP to upload the file
            sftp = client.open_sftp()
            try:
                # Create a file-like object from the content
                from io import BytesIO
                file_obj = BytesIO(file_content)
                sftp.putfo(file_obj, f"/opt/LACCS/Controls/{filename}")
            finally:
                try:
                    sftp.close()
                except Exception:
                    pass
                try:
                    client.close()
                except Exception:
                    pass

            # Step 4: Restart service with node-specific path and parameters
            node_params = self.model.get_node_params(node_name)
            laccs_path = node_params["laccs_path"].replace("#", "")  # Remove # if present
            if not laccs_path.endswith("/"):
                laccs_path += "/"
            start_command = f"screen -wipe; screen -L -dmS LACCS bash -lc \"cd {laccs_path} && ulimit -n 204800 && ulimit -s 81920 && ./LACCS --user_name=guest --password=guest_password --data_id=uptodate --D:node_name={node_params['node_name']} --D:device_name={node_params['device_name']} --D:ch00={node_params['ch00']} --D:ch01={node_params['ch01']} --D:ch02={node_params['ch02']} --D:ch03={node_params['ch03']} --D:ch04={node_params['ch04']} --D:ch05={node_params['ch05']}; exec bash\""
            self.execute_ssh_command(ip, start_command)

            # Update status
            if self.main_loop_active:
                self.root.after(
                    0,
                    lambda name=node_name: self.update_node_status(name, "Running"),
                )
                self.root.after(
                    0,
                    lambda msg=f"Library update completed successfully on node {node_name}": 
                    self.log_message(msg),
                )

        except Exception as e:
            error_msg = f"Failed to update shared library on node {node_name}: {str(e)}"
            if self.main_loop_active:
                self.root.after(
                    0,
                    lambda msg=f"ERROR: {error_msg}": 
                    self.log_message(msg),
                )
            raise

    def on_closing(self):
        # Set flag to stop main loop activities
        self.main_loop_active = False
        
        # Set flag to stop status check thread
        self.stop_status_check = True

        # Check for unsaved changes
        if self.has_unsaved_changes:
            try:
                response = messagebox.askyesnocancel(
                    "Unsaved Changes",
                    "You have unsaved changes.\n"
                    + "Do you want to save them before exiting?",
                )

                if response is None:  # User canceled
                    # Restore flags if user cancels exit
                    self.main_loop_active = True
                    self.stop_status_check = False
                    return
                elif response is True:  # User wants to save
                    self.save_changes()
            except Exception:
                # If messagebox fails, proceed with closing
                pass

        # Give threads a chance to terminate gracefully
        import time
        time.sleep(1)  # Short delay to allow threads to see the stop flags

        # Close log file if open and not already closed
        try:
            if self.log_file and not self.log_file.closed:
                self.log_file.close()
        except Exception as e:
            print(f"Failed to close log file: {str(e)}")

        # Exit application
        try:
            self.root.destroy()
        except Exception:
            # Handle case where root window is already destroyed
            pass

    def save_data(self):
        try:
            data = []

            for item in self.view.tree.get_children():
                data.append(self.view.tree.item(item, "values"))

            success, message = self.model.save_node_data(data)
            if success:
                messagebox.showinfo("Success", message)
                self.log_message(message)
                self.update_node_list()
            else:
                messagebox.showerror("Error", message)
                self.log_message(f"ERROR: {message}")
        except Exception as e:
            error_msg = f"Failed to save file: {str(e)}"
            messagebox.showerror("Error", error_msg)
            self.log_message(f"ERROR: {error_msg}")


class NodeEditor(NodeController):
    def __init__(self, root):
        # Call parent constructor to initialize all attributes
        super().__init__(root)
        
        # Ensure main_loop_active is accessible
        # This is a safeguard to ensure the attribute exists regardless of inheritance order
        if not hasattr(self, 'main_loop_active'):
            self.main_loop_active = True
        
        # Create main menu bar with help option
        self.create_main_menu()
    
    def create_main_menu(self):
        """Create main menu bar with File and Help options"""
        # Create menu bar
        self.menu_bar = tk.Menu(self.root)
        
        # Create File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Save Changes", command=self.save_changes, accelerator="Ctrl+S")
        file_menu.add_command(label="Open FileDB", command=self.open_filedb)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Create Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="Help", command=self.show_help)
        
        # Add menus to menu bar
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        
        # Attach menu bar to the root window
        self.root.config(menu=self.menu_bar)
    
    def show_help(self):
        """Show the help window"""
        from launcher.help_window import HelpWindow
        help_window = HelpWindow(self.root)
        help_window.show()

    def add_tsv_item(self):
        node_name, ip = self.get_selected_node_info()
        if not node_name or not ip:
            return

        # Create a new row with empty values
        headers = self.view.tree["columns"]
        if not headers:
            messagebox.showerror("Error", "No headers found in the TSV file.")
            return

        new_row = ["" for _ in headers]

        # Create a dialog to edit the new row
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Add TSV Item - {node_name}")
        edit_window.geometry("600x400")
        edit_window.transient(self.root)
        edit_window.grab_set()

        # Create a frame with scrollbar
        frame = ttk.Frame(edit_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create canvas and scrollbar
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create content frame inside canvas
        content_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")

        # Update scroll region when content changes
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        content_frame.bind("<Configure>", on_frame_configure)

        # Store entry variables
        entry_vars = []

        # Create entry fields for each header
        for col_name in headers:
            entry_frame = ttk.Frame(content_frame)
            entry_frame.pack(fill=tk.X, pady=5)

            ttk.Label(entry_frame, text=col_name, width=20).pack(side=tk.LEFT, padx=5)
            var = tk.StringVar()
            entry = ttk.Entry(entry_frame, textvariable=var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            entry_vars.append((col_name, var))

        # Function to save the new row
        def save_new_row():
            # Collect values from entry fields
            for i, (col_name, var) in enumerate(entry_vars):
                new_row[i] = var.get().strip()

            # Validate that at least the first column has a value
            if not new_row[0]:
                messagebox.showerror("Error", "The first column cannot be empty.")
                return

            # Insert the new row into the treeview
            item_id = self.view.tree.insert("", tk.END, values=new_row)

            # Update node_item_map for the new item
            if new_row:
                new_node_name = new_row[0]
                self.node_item_map[new_node_name] = item_id

            # Set unsaved changes flag instead of saving immediately
            self.set_unsaved_changes()

            self.log_message(f"Added new TSV item to node {node_name}")
            messagebox.showinfo(
                "Info", "New TSV item has been added. Remember to save changes."
            )
            edit_window.destroy()

        # Add buttons at the bottom
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        cancel_button = ttk.Button(
            button_frame, text="Cancel", command=edit_window.destroy
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)

        save_button = ttk.Button(button_frame, text="Save", command=save_new_row)
        save_button.pack(side=tk.RIGHT, padx=5)

        # Make the window modal
        self.root.wait_window(edit_window)

    def delete_tsv_item(self):
        selected_items = self.view.tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "No items selected for deletion")
            return

        node_name, ip = self.get_selected_node_info()
        if not node_name:
            return

        # Add confirmation dialog
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete {len(selected_items)} selected item(s)?",
        )

        if not confirm:
            return

        # Store node names to be deleted for log message and map update
        deleted_node_names = []
        for item in selected_items:
            row_values = self.view.tree.item(item, "values")
            if row_values:
                deleted_node_names.append(row_values[0])
            self.view.tree.delete(item)

        # Update node_item_map to remove deleted items
        for name in deleted_node_names:
            if name in self.node_item_map:
                del self.node_item_map[name]

        # Set unsaved changes flag instead of saving immediately
        self.set_unsaved_changes()

        self.log_message(
            f"Deleted {len(selected_items)} TSV item(s) from node {node_name}"
        )
        messagebox.showinfo(
            "Info",
            f"{len(selected_items)} TSV item(s) have been deleted. Remember to save changes.",
        )

    def save_treeview_data(self):
        """Save the current treeview data to the TSV file"""
        # Get all data from treeview
        headers = self.view.tree["columns"]
        all_rows = []

        for item in self.view.tree.get_children():
            row = self.view.tree.item(item, "values")
            all_rows.append(row)

        # Save data using model
        success, message = self.model.save_node_data(all_rows)

        if not success:
            messagebox.showerror("Error", message)
            self.log_message(f"ERROR: {message}")
        else:
            self.log_message(message)
            # After saving, update the node list and status tree to reflect changes
            self.update_node_list()
            # Force refresh status for all nodes to ensure status synchronization
            self.force_refresh_status()

    def connect_via_putty(self):
        """Connect to the selected node via Putty"""
        # Check if Putty is installed
        if not self._check_putty_installed():
            # Check if winget is available
            if self._check_winget_installed():
                # Offer to install Putty via winget
                reply = messagebox.askquestion(
                    "Putty Not Installed",
                    "Putty is not installed. Would you like to install it via winget?",
                    icon="question",
                    type=messagebox.YESNO,
                )

                if reply == "yes":
                    try:
                        import subprocess

                        # Run winget install command
                        subprocess.Popen(["powershell", "winget install PuTTY.PuTTY"])
                        messagebox.information(
                            self.view,
                            "Installation Started",
                            "Putty installation has started. Please wait for it to complete and try again.",
                        )
                        return
                    except Exception as e:
                        messagebox.showerror(
                            "Error", f"Failed to start winget installation: {str(e)}"
                        )
                        self.log_message(
                            f"ERROR: Failed to start winget installation: {str(e)}"
                        )
                        return
            else:
                # Offer to download Putty
                reply = messagebox.askquestion(
                    "Putty Not Installed",
                    "Putty is not installed and winget is not available. Would you like to download Putty from the official website?",
                    icon="question",
                    type=messagebox.YESNO,
                )

                if reply == "yes":
                    import os
                    import tempfile

                    # Create a temporary directory for Putty
                    temp_dir = os.path.join(tempfile.gettempdir(), "putty")
                    putty_path = os.path.join(temp_dir, "putty.exe")

                    # Download Putty
                    if self._download_putty(putty_path):
                        # Save the downloaded path in a class variable
                        self.putty_path = putty_path
                        messagebox.information(
                            self.view,
                            "Download Complete",
                            f"Putty has been downloaded to {putty_path}. You can now connect to the node.",
                        )
                    else:
                        messagebox.showerror(
                            "Error",
                            "Failed to download Putty. Please try manually downloading from https://www.putty.org",
                        )
                        self.log_message("ERROR: Failed to download Putty")
                        return
                else:
                    return

        # Get selected node information
        selected_items = self.view.tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "No node selected")
            return

        item = selected_items[0]
        node_name = self.view.tree.item(item, "values")[0]

        # Get node IP and credentials
        username, password = self.model.get_node_credentials(node_name)

        # Get node IP
        node_ip = None
        for name, ip in self.model.non_local_nodes:
            if name == node_name:
                node_ip = ip
                break

        if not node_ip:
            messagebox.showerror(
                "Error", f"Could not find IP address for node {node_name}"
            )
            return

        # Log the connection attempt
        self.log_message(f"Connecting to node {node_name} ({node_ip}) via Putty")

        try:
            # Start Putty process
            import subprocess

            # Use the downloaded Putty if available, otherwise use system Putty
            putty_exe = getattr(self, "putty_path", "putty.exe")

            # Use -ssh for SSH connection, -l for username, -pw for password
            subprocess.Popen(
                [putty_exe, "-ssh", f"{username}@{node_ip}", "-pw", password]
            )
            self.log_message(
                f"Successfully launched Putty for node {node_name} ({node_ip})"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch Putty: {str(e)}")
            self.log_message(f"ERROR: Failed to launch Putty: {str(e)}")

    def _check_putty_installed(self):
        """Check if Putty is installed using both cmd's 'where' and PowerShell's 'Get-Command'"""
        try:
            import subprocess

            # First try using cmd's 'where' command
            self.log_message(
                "DEBUG: Checking Putty installation using cmd 'where' command"
            )
            cmd_where_result = subprocess.run(
                ["cmd.exe", "/c", "where", "putty.exe"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            if cmd_where_result.returncode == 0 and cmd_where_result.stdout:
                putty_path = cmd_where_result.stdout.decode("utf-8").strip()
                self.log_message(f"DEBUG: Found Putty using 'where' at: {putty_path}")
                return True

            # If 'where' command fails, try using PowerShell's 'Get-Command'
            self.log_message(
                "DEBUG: 'where' command failed, trying PowerShell 'Get-Command'"
            )
            powershell_result = subprocess.run(
                [
                    "powershell.exe",
                    "-Command",
                    "Get-Command putty.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            if powershell_result.returncode == 0 and powershell_result.stdout:
                putty_path = powershell_result.stdout.decode("utf-8").strip()
                self.log_message(
                    f"DEBUG: Found Putty using 'Get-Command' at: {putty_path}"
                )
                return True

            # Both commands failed to find Putty
            self.log_message("DEBUG: Putty not found by both 'where' and 'Get-Command'")
            return False
        except Exception as e:
            # Log any unexpected errors
            self.log_message(f"DEBUG: Error checking Putty installation: {str(e)}")
            return False

    def _check_winget_installed(self):
        """Check if winget package manager is available on the system"""
        try:
            import subprocess

            # Try to run 'winget --version' to check if it exists
            result = subprocess.run(
                ["winget", "--version"],
                capture_output=True,
                text=True,
                check=False,
                shell=True,
            )
            return result.returncode == 0
        except Exception:
            # If any error occurs, winget is not available
            return False

    def _download_putty(self, target_path):
        """Download putty.exe from official website"""
        import requests
        import os

        putty_url = "https://the.earth.li/~sgtatham/putty/latest/w64/putty.exe"

        try:
            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # Download the file
            self.log_message(f"Downloading Putty from {putty_url}...")
            response = requests.get(putty_url, stream=True)
            response.raise_for_status()

            # Write the file to disk
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            self.log_message(f"Putty successfully downloaded to {target_path}")
            return True
        except Exception as e:
            self.log_message(f"ERROR: Failed to download Putty: {str(e)}")
            return False
