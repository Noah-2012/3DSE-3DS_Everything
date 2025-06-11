import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import _3dse_core # Import our logic script
import threading
import os

class _3DSE_App:
    def __init__(self, root):
        self.root = root
        self.root.title("3DSE - 3DS Everything Tool")
        self.root.geometry("500x600") # Slightly taller for more space
        self.root.resizable(False, False)

        # Common variables
        self.latest_luma_download_url = None
        self.latest_gm9_download_url = None
        self.current_sd_drive = None
        self.dump_target_folder = os.path.join(os.path.expanduser("~"), "3DSE_Dumps")

        self.create_widgets()
        self.dump_files_to_copy = [] # List of selected dump files

    def create_widgets(self):
        # Global drive letter input area (top)
        drive_frame = ttk.LabelFrame(self.root, text="SD Card Drive")
        drive_frame.pack(pady=5, padx=10, fill="x")

        self.drive_label = ttk.Label(drive_frame, text="Drive Letter (e.g., E:):")
        self.drive_label.pack(side="left", padx=5, pady=5)

        self.drive_entry = ttk.Entry(drive_frame, width=10)
        self.drive_entry.pack(side="left", padx=5, pady=5)
        self.drive_entry.insert(0, "E:") # Suggested value

        # A button to check all statuses in one go
        self.global_check_button = ttk.Button(drive_frame, text="Check Status", command=self.check_all_statuses)
        self.global_check_button.pack(side="right", padx=5, pady=5)

        # Notebook (Tabbed view)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        # Update Tab (contains Luma and GodMode9)
        self.update_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.update_tab, text="Update")
        self.create_update_widgets(self.update_tab)

        # Dump Tab
        self.dump_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.dump_tab, text="Dump Files")
        self.create_dump_widgets(self.dump_tab)

    def create_update_widgets(self, parent_frame):
        # Luma3DS Section
        luma_frame = ttk.LabelFrame(parent_frame, text="Luma3DS Update")
        luma_frame.pack(pady=10, padx=10, fill="x")

        self.luma_local_version_label = ttk.Label(luma_frame, text="Local Version: N/A")
        self.luma_local_version_label.pack(anchor="w", padx=5, pady=2)

        self.luma_latest_version_label = ttk.Label(luma_frame, text="Latest Version (GitHub): N/A")
        self.luma_latest_version_label.pack(anchor="w", padx=5, pady=2)
        
        self.luma_status_label = ttk.Label(luma_frame, text="Status: Ready", foreground="blue")
        self.luma_status_label.pack(anchor="w", padx=5, pady=5)

        self.luma_progress_bar = ttk.Progressbar(luma_frame, orient="horizontal", length=200, mode="determinate")
        self.luma_progress_bar.pack(pady=5, padx=5, fill="x")
        self.luma_progress_text = ttk.Label(luma_frame, text="Waiting to start...")
        self.luma_progress_text.pack(pady=2, padx=5)

        self.luma_update_button = ttk.Button(luma_frame, text="Update Luma3DS", command=self.start_luma_update_process, state=tk.DISABLED)
        self.luma_update_button.pack(pady=10)

        # GodMode9 Section
        gm9_frame = ttk.LabelFrame(parent_frame, text="GodMode9 Update")
        gm9_frame.pack(pady=20, padx=10, fill="x") # More space between Luma and GM9

        self.gm9_local_status_label = ttk.Label(gm9_frame, text="Local Files: N/A")
        self.gm9_local_status_label.pack(anchor="w", padx=5, pady=2)

        self.gm9_latest_version_label = ttk.Label(gm9_frame, text="Latest Version (GitHub): N/A")
        self.gm9_latest_version_label.pack(anchor="w", padx=5, pady=2)
        
        self.gm9_status_label = ttk.Label(gm9_frame, text="Status: Ready", foreground="blue")
        self.gm9_status_label.pack(anchor="w", padx=5, pady=5)

        self.gm9_progress_bar = ttk.Progressbar(gm9_frame, orient="horizontal", length=200, mode="determinate")
        self.gm9_progress_bar.pack(pady=5, padx=5, fill="x")
        self.gm9_progress_text = ttk.Label(gm9_frame, text="Waiting to start...")
        self.gm9_progress_text.pack(pady=2, padx=5)

        self.gm9_update_button = ttk.Button(gm9_frame, text="Update GodMode9", command=self.start_gm9_update_process, state=tk.DISABLED)
        self.gm9_update_button.pack(pady=10)


    def create_dump_widgets(self, parent_frame):
        # Dump Destination Folder
        dump_dest_frame = ttk.LabelFrame(parent_frame, text="Dump Destination Folder")
        dump_dest_frame.pack(pady=10, padx=10, fill="x")

        self.dump_folder_label = ttk.Label(dump_dest_frame, text=f"Destination Folder: {self.dump_target_folder}")
        self.dump_folder_label.pack(anchor="w", padx=5, pady=2)

        self.change_dump_folder_button = ttk.Button(dump_dest_frame, text="Change Destination Folder", command=self.change_dump_folder)
        self.change_dump_folder_button.pack(pady=5)

        # Dump Options
        dump_options_frame = ttk.LabelFrame(parent_frame, text="Select Files to Dump")
        dump_options_frame.pack(pady=10, padx=10, fill="x", expand=True)

        self.dump_options_data = {
            "firm0_enc.bak": {"path": "boot9strap/firm0_enc.bak", "name": "firm0_enc.bak (Boot9Strap)"},
            "firm1_enc.bak": {"path": "boot9strap/firm1_enc.bak", "name": "firm1_enc.bak (Boot9Strap)"},
            "bios7i_part1.bin": {"path": "_nds/bios7i_part1.bin", "name": "bios7i_part1.bin (_nds)"},
            "bios9i_part1.bin": {"path": "_nds/bios9i_part1.bin", "name": "bios9i_part1.bin (_nds)"},
            "boot9.bin": {"path": "3ds/boot9.bin", "name": "boot9.bin (3ds)"},
            "boot11.bin": {"path": "3ds/boot11.bin", "name": "boot11.bin (3ds)"},
        }
        self.dump_checkbox_vars = {}

        row = 0
        col = 0
        for key, info in self.dump_options_data.items():
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(dump_options_frame, text=info['name'], variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=5, pady=2)
            self.dump_checkbox_vars[key] = var
            col += 1
            if col > 1: # Two column layout
                col = 0
                row += 1
        
        # Select All / Deselect All
        select_all_button = ttk.Button(dump_options_frame, text="Select All", command=self.select_all_dump_files)
        select_all_button.grid(row=row + 1, column=0, pady=5, padx=5, sticky="w")
        deselect_all_button = ttk.Button(dump_options_frame, text="Deselect All", command=self.deselect_all_dump_files)
        deselect_all_button.grid(row=row + 1, column=1, pady=5, padx=5, sticky="w")


        # Progress bar for Dump
        self.dump_progress_frame = ttk.LabelFrame(parent_frame, text="Dump Progress")
        self.dump_progress_frame.pack(pady=10, padx=10, fill="x")

        self.dump_progress_bar = ttk.Progressbar(self.dump_progress_frame, orient="horizontal", length=300, mode="determinate")
        self.dump_progress_bar.pack(pady=5, padx=5)

        self.dump_progress_text = ttk.Label(self.dump_progress_frame, text="Waiting to start...")
        self.dump_progress_text.pack(pady=2, padx=5)

        self.dump_button = ttk.Button(parent_frame, text="Dump Files", command=self.start_dump_process)
        self.dump_button.pack(pady=10)

    def change_dump_folder(self):
        new_folder = filedialog.askdirectory(title="Select a destination folder for dumps")
        if new_folder:
            self.dump_target_folder = new_folder
            self.dump_folder_label.config(text=f"Destination Folder: {self.dump_target_folder}")

    def select_all_dump_files(self):
        for var in self.dump_checkbox_vars.values():
            var.set(True)

    def deselect_all_dump_files(self):
        for var in self.dump_checkbox_vars.values():
            var.set(False)

    def update_progress_ui(self, target, message, progress_value, status_type):
        """Callback function to update the GUI from the thread."""
        # Local variable must always be assigned before it is used
        label_to_update = None # Initialize to avoid UnboundLocalError

        if target == "luma":
            self.luma_progress_text.config(text=message)
            self.luma_progress_bar['value'] = progress_value
            label_to_update = self.luma_status_label
        elif target == "gm9":
            self.gm9_progress_text.config(text=message)
            self.gm9_progress_bar['value'] = progress_value
            label_to_update = self.gm9_status_label
        elif target == "dump":
            self.dump_progress_text.config(text=message)
            self.dump_progress_bar['value'] = progress_value
            # For dump, the "status" is displayed directly in the progress text,
            # there is no separate status_label for it.
            # Hence, no assignment to label_to_update here.
        
        # Only try to call config if label_to_update has been assigned
        if label_to_update:
            if status_type == "info":
                label_to_update.config(foreground="blue")
            elif status_type == "warning":
                label_to_update.config(foreground="orange")
            elif status_type == "error":
                label_to_update.config(foreground="red")
            elif status_type == "success":
                label_to_update.config(foreground="green")
            
            # For Update/GM9, update the status label
            label_to_update.config(text=f"Status: {message}")


    def check_all_statuses(self):
        sd_card_drive = self.drive_entry.get().strip().upper()
        if not sd_card_drive:
            messagebox.showwarning("Input Missing", "Please enter a drive letter.")
            return

        if not sd_card_drive.endswith(':'):
            sd_card_drive += ':'
        
        self.current_sd_drive = sd_card_drive

        # Reset Luma UI
        self.luma_status_label.config(text="Status: Checking...", foreground="orange")
        self.luma_local_version_label.config(text="Local Version: Detecting...")
        self.luma_latest_version_label.config(text="Latest Version (GitHub): Detecting...")
        self.luma_update_button.config(state=tk.DISABLED)
        self.luma_progress_bar['value'] = 0
        self.luma_progress_text.config(text="Checking in progress...")

        # Reset GM9 UI
        self.gm9_status_label.config(text="Status: Checking...", foreground="orange")
        self.gm9_local_status_label.config(text="Local Files: Detecting...")
        self.gm9_latest_version_label.config(text="Latest Version (GitHub): Detecting...")
        self.gm9_update_button.config(state=tk.DISABLED)
        self.gm9_progress_bar['value'] = 0
        self.gm9_progress_text.config(text="Checking in progress...")
        
        # Reset Dump UI (optional, but good for consistency)
        self.dump_progress_bar['value'] = 0
        self.dump_progress_text.config(text="Ready to dump.")


        # Run the check in a separate thread
        thread = threading.Thread(target=self._run_all_status_checks, args=(sd_card_drive,))
        thread.start()

    def _run_all_status_checks(self, sd_card_drive):
        # --- Luma3DS Check ---
        local_luma_version, local_luma_error = _3dse_core.get_local_luma_version(sd_card_drive)
        luma_release_info, latest_luma_error = _3dse_core.get_latest_luma_release_info()
        latest_luma_version = luma_release_info['version'] if luma_release_info else None
        self.latest_luma_download_url = luma_release_info['download_url'] if luma_release_info else None
        
        # --- GodMode9 Check ---
        local_gm9_status, local_gm9_error = _3dse_core.get_local_gm9_version(sd_card_drive)
        gm9_release_info, latest_gm9_error = _3dse_core.get_latest_gm9_release_info()
        latest_gm9_version = gm9_release_info['version'] if gm9_release_info else None
        self.latest_gm9_download_url = gm9_release_info['download_url'] if gm9_release_info else None


        # Update GUI in the main thread
        self.root.after(0, self._update_all_gui_after_check,
                         local_luma_version, local_luma_error, latest_luma_version, latest_luma_error,
                         local_gm9_status, local_gm9_error, latest_gm9_version, latest_gm9_error)

    def _update_all_gui_after_check(self, local_luma_version, local_luma_error, latest_luma_version, latest_luma_error,
                                    local_gm9_status, local_gm9_error, latest_gm9_version, latest_gm9_error):
        # --- Update Luma3DS UI ---
        self.luma_progress_bar['value'] = 0
        self.luma_progress_text.config(text="Check completed.")
        if local_luma_error:
            self.luma_local_version_label.config(text=f"Local Version: {local_luma_error}", foreground="red")
        else:
            self.luma_local_version_label.config(text=f"Local Version: {local_luma_version}", foreground="black")
        if latest_luma_error:
            self.luma_latest_version_label.config(text=f"Latest Version (GitHub): {latest_luma_error}", foreground="red")
        else:
            self.luma_latest_version_label.config(text=f"Latest Version (GitHub): {latest_luma_version}", foreground="black")

        if local_luma_version and latest_luma_version:
            luma_comparison_result = _3dse_core.compare_versions(local_luma_version, latest_luma_version)
            if luma_comparison_result == -1:
                self.luma_status_label.config(text=f"Status: Update available! ({local_luma_version} -> {latest_luma_version})", foreground="green")
                self.luma_update_button.config(state=tk.NORMAL)
            elif luma_comparison_result == 0:
                self.luma_status_label.config(text=f"Status: Up to date ({local_luma_version})", foreground="blue")
                self.luma_update_button.config(state=tk.DISABLED)
            else:
                self.luma_status_label.config(text=f"Status: Your version is newer ({local_luma_version} vs. {latest_luma_version})", foreground="purple")
                self.luma_update_button.config(state=tk.DISABLED)
        else:
            self.luma_status_label.config(text="Status: Version comparison not possible.", foreground="red")
            self.luma_update_button.config(state=tk.DISABLED)

        # --- Update GodMode9 UI ---
        self.gm9_progress_bar['value'] = 0
        self.gm9_progress_text.config(text="Check completed.")
        if local_gm9_error:
            self.gm9_local_status_label.config(text=f"Local Files: {local_gm9_error}", foreground="red")
        else:
            self.gm9_local_status_label.config(text=f"Local GodMode9: {local_gm9_status}", foreground="black")

        if latest_gm9_error:
            self.gm9_latest_version_label.config(text=f"Latest Version (GitHub): {latest_gm9_error}", foreground="red")
        else:
            self.gm9_latest_version_label.config(text=f"Latest Version (GitHub): {latest_gm9_version}", foreground="black")

        if latest_gm9_version:
            if local_gm9_status == "Not found" or \
               (_3dse_core.compare_versions("0.0.0", latest_gm9_version) == -1): # Assumption that 'Not found' or 'Installed' is an old version
                self.gm9_status_label.config(text=f"Status: Update/Installation recommended! (Latest: {latest_gm9_version})", foreground="green")
                self.gm9_update_button.config(state=tk.NORMAL)
            else:
                self.gm9_status_label.config(text="Status: Appears to be up to date.", foreground="blue")
                self.gm9_update_button.config(state=tk.DISABLED)
        else:
            self.gm9_status_label.config(text="Status: Version check not possible.", foreground="red")
            self.gm9_update_button.config(state=tk.DISABLED)


    def start_luma_update_process(self):
        if not self.latest_luma_download_url or not self.current_sd_drive:
            messagebox.showerror("Error", "No Luma download URL or drive available for update. Please re-run the version check.")
            return

        response = messagebox.askyesno("Confirm Luma3DS Update",
                                       f"Do you want to update Luma3DS to the SD card ({self.current_sd_drive}) now?\n\n"
                                       "This will update boot.firm, boot.3dsx, and the contents of the luma/config folder.\n"
                                       "Please ensure your SD card is properly inserted and no other programs are accessing it.\n\n"
                                       "**CREATE A BACKUP OF YOUR SD CARD BEFORE PROCEEDING!**")
        
        if response:
            self.luma_update_button.config(state=tk.DISABLED)
            self.global_check_button.config(state=tk.DISABLED)
            self.drive_entry.config(state=tk.DISABLED)
            self.luma_status_label.config(text="Status: Starting Luma3DS Update...", foreground="orange")
            self.luma_progress_bar['value'] = 0
            self.luma_progress_text.config(text="Preparing...")

            update_thread = threading.Thread(target=self._run_luma_update_in_thread,
                                             args=(self.current_sd_drive, self.latest_luma_download_url))
            update_thread.start()
        else:
            messagebox.showinfo("Update Cancelled", "The Luma3DS update was cancelled.")

    def _run_luma_update_in_thread(self, sd_card_drive, download_url):
        success, message = _3dse_core.download_and_inject_luma_update(
            sd_card_drive, download_url,
            progress_callback=lambda msg, prog, status: self.root.after(0, self.update_progress_ui, "luma", msg, prog, status)
        )
        self.root.after(0, self._after_luma_update_finished, success, message)

    def _after_luma_update_finished(self, success, message):
        self.global_check_button.config(state=tk.NORMAL)
        self.drive_entry.config(state=tk.NORMAL)
        if success:
            messagebox.showinfo("Luma3DS Update Complete", message + "\n\nPlease safely remove the SD card and insert it into your 3DS.")
            self.luma_status_label.config(text="Status: Luma3DS Update successful!", foreground="green")
            self.check_all_statuses() # Re-check status after update
        else:
            messagebox.showerror("Luma3DS Update Failed", message + "\n\nPlease check the error message and restart if necessary or restore your backup.")
            self.luma_status_label.config(text="Status: Luma3DS Update failed!", foreground="red")
        self.luma_update_button.config(state=tk.DISABLED)
        self.luma_progress_bar['value'] = 0
        self.luma_progress_text.config(text="Luma3DS update process finished.")


    def start_gm9_update_process(self):
        if not self.latest_gm9_download_url or not self.current_sd_drive:
            messagebox.showerror("Error", "No GodMode9 download URL or drive available for update. Please re-run the version check.")
            return

        response = messagebox.askyesno("Confirm GodMode9 Update",
                                       f"Do you want to update GodMode9 to the SD card ({self.current_sd_drive}) now?\n\n"
                                       "This will copy GodMode9.firm to the /luma/payloads/ folder and update the gm9/ folder, while PRESERVING your gm9/scripts/ folder.\n"
                                       "Please ensure your SD card is properly inserted and no other programs are accessing it.\n\n"
                                       "**CREATE A BACKUP OF YOUR SD CARD BEFORE PROCEEDING!**")
        
        if response:
            self.gm9_update_button.config(state=tk.DISABLED)
            self.global_check_button.config(state=tk.DISABLED)
            self.drive_entry.config(state=tk.DISABLED)
            self.gm9_status_label.config(text="Status: Starting GodMode9 Update...", foreground="orange")
            self.gm9_progress_bar['value'] = 0
            self.gm9_progress_text.config(text="Preparing...")

            update_thread = threading.Thread(target=self._run_gm9_update_in_thread,
                                             args=(self.current_sd_drive, self.latest_gm9_download_url))
            update_thread.start()
        else:
            messagebox.showinfo("Update Cancelled", "The GodMode9 update was cancelled.")

    def _run_gm9_update_in_thread(self, sd_card_drive, download_url):
        success, message = _3dse_core.download_and_inject_gm9_update(
            sd_card_drive, download_url,
            progress_callback=lambda msg, prog, status: self.root.after(0, self.update_progress_ui, "gm9", msg, prog, status)
        )
        self.root.after(0, self._after_gm9_update_finished, success, message)

    def _after_gm9_update_finished(self, success, message):
        self.global_check_button.config(state=tk.NORMAL)
        self.drive_entry.config(state=tk.NORMAL)
        if success:
            messagebox.showinfo("GodMode9 Update Complete", message + "\n\nPlease safely remove the SD card and insert it into your 3DS.")
            self.gm9_status_label.config(text="Status: GodMode9 Update successful!", foreground="green")
            self.check_all_statuses() # Re-check status after update
        else:
            messagebox.showerror("GodMode9 Update Failed", message + "\n\nPlease check the error message and restart if necessary or restore your backup.")
            self.gm9_status_label.config(text="Status: GodMode9 Update failed!", foreground="red")
        self.gm9_update_button.config(state=tk.DISABLED)
        self.gm9_progress_bar['value'] = 0
        self.gm9_progress_text.config(text="GodMode9 update process finished.")

    def start_dump_process(self):
        if not self.current_sd_drive:
            messagebox.showwarning("Drive Missing", "Please enter the SD card drive letter first and check its status.")
            return

        self.dump_files_to_copy = []
        for key, var in self.dump_checkbox_vars.items():
            if var.get():
                self.dump_files_to_copy.append(self.dump_options_data[key])
        
        if not self.dump_files_to_copy:
            messagebox.showwarning("No Selection", "Please select at least one file to dump.")
            return
        
        response = messagebox.askyesno("Confirm Dump",
                                       f"Do you want to dump the {len(self.dump_files_to_copy)} selected file(s) to '{self.dump_target_folder}' now?\n\n"
                                       "Please ensure your SD card is properly inserted.")
        
        if response:
            self.dump_button.config(state=tk.DISABLED)
            self.global_check_button.config(state=tk.DISABLED)
            self.drive_entry.config(state=tk.DISABLED)
            self.dump_progress_bar['value'] = 0
            self.dump_progress_text.config(text="Starting dump...")

            dump_thread = threading.Thread(target=self._run_dump_in_thread,
                                           args=(self.current_sd_drive, self.dump_target_folder, self.dump_files_to_copy))
            dump_thread.start()
        else:
            messagebox.showinfo("Dump Cancelled", "The dump process was cancelled.")

    def _run_dump_in_thread(self, sd_card_drive, target_folder, files_to_dump):
        total_files = len(files_to_dump)
        successful_dumps = 0
        all_messages = []

        for i, file_info in enumerate(files_to_dump):
            file_path_on_sd = file_info['path']
            file_display_name = file_info['name']
            
            # Update GUI for current file dump
            self.root.after(0, self.update_progress_ui, "dump", 
                            f"Dumping '{file_display_name}' ({i+1}/{total_files})...", 
                            int(((i + 0.5) / total_files) * 100), "info")

            success, message = _3dse_core.dump_file(sd_card_drive, file_path_on_sd, target_folder)
            all_messages.append(f"{file_display_name}: {message}")
            if success:
                successful_dumps += 1
                self.root.after(0, self.update_progress_ui, "dump", 
                                f"Dump of '{file_display_name}' successful.", 
                                int(((i + 1) / total_files) * 100), "info")
            else:
                self.root.after(0, self.update_progress_ui, "dump", 
                                f"Dump of '{file_display_name}' failed.", 
                                int(((i + 1) / total_files) * 100), "error")

        final_status_type = "success" if successful_dumps == total_files else ("warning" if successful_dumps > 0 else "error")
        final_message = f"{successful_dumps} of {total_files} files successfully dumped."
        self.root.after(0, self.update_progress_ui, "dump", final_message, 100, final_status_type)
        self.root.after(0, self._after_dump_finished, successful_dumps, total_files, all_messages)


    def _after_dump_finished(self, successful_dumps, total_files, all_messages):
        self.dump_button.config(state=tk.NORMAL)
        self.global_check_button.config(state=tk.NORMAL)
        self.drive_entry.config(state=tk.NORMAL)
        
        detail_message = "\n".join(all_messages)

        if successful_dumps == total_files:
            messagebox.showinfo("Dump Complete", f"All {successful_dumps} files successfully dumped!\n\nDetails:\n{detail_message}")
        elif successful_dumps > 0:
            messagebox.showwarning("Dump with Warnings", f"{successful_dumps} of {total_files} files successfully dumped. There were errors with some files.\n\nDetails:\n{detail_message}")
        else:
            messagebox.showerror("Dump Failed", f"No files could be dumped.\n\nDetails:\n{detail_message}")
        
        self.dump_progress_bar['value'] = 0
        self.dump_progress_text.config(text="Dump process finished.")

if __name__ == "__main__":
    root = tk.Tk()
    app = _3DSE_App(root)
    root.mainloop()