import os
import requests
import re
import configparser
import zipfile
import shutil
import tempfile
import json # For GitHub Releases API Parsing

# --- General Helper Functions ---

def compare_versions(local_version, latest_version):
    """
    Compares two version strings (e.g., '1.2.3' with '1.2.4').

    Returns:
        int: -1 if local version is older, 0 if same, 1 if local version is newer.
    """
    def parse_version(version_str):
        try:
            # Remove non-digit characters at the start/end if present (like 'v')
            version_str = re.sub(r'^[^\d.]*|[^\d.]*$', '', version_str)
            return [int(x) for x in version_str.split('.')]
        except ValueError:
            return []

    local_parts = parse_version(version_str=local_version)
    latest_parts = parse_version(version_str=latest_version)

    for i in range(max(len(local_parts), len(latest_parts))):
        local_part = local_parts[i] if i < len(local_parts) else 0
        latest_part = latest_parts[i] if i < len(latest_parts) else 0

        if local_part < latest_part:
            return -1
        elif local_part > latest_part:
            return 1
    return 0

# --- Luma3DS Specific Functions ---

def get_local_luma_version(drive_letter):
    """
    Attempts to read the Luma3DS version from the initial comment
    of the config.ini file on the SD card.
    """
    luma_config_path = os.path.join(drive_letter, 'luma', 'config.ini')

    if not os.path.exists(drive_letter):
        return None, f"Error: Drive letter '{drive_letter}' not found."
    if not os.path.isdir(os.path.join(drive_letter, 'luma')):
        return None, f"Error: The 'luma' directory was not found on '{drive_letter}'."
    if not os.path.exists(luma_config_path):
        return None, f"Error: The file '{luma_config_path}' (config.ini) was not found."

    try:
        with open(luma_config_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        match = re.search(r'v(\d+\.\d+\.\d+)', first_line)
        if match:
            return match.group(1), None
        else:
            return None, "Error: The first line of config.ini does not contain the expected Luma3DS version format."
    except Exception as e:
        return None, f"Error reading config.ini or parsing version: {e}"

def get_latest_luma_release_info():
    """
    Retrieves the latest Luma3DS release information from GitHub.
    """
    repo_owner = "LumaTeam"
    repo_name = "Luma3DS"
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        tag_name = data.get('tag_name')
        download_url = None
        luma_zip_pattern = re.compile(r"Luma3DSv\d+\.\d+\.\d+\.zip")

        for asset in data.get('assets', []):
            asset_name = asset.get('name')
            if asset_name and luma_zip_pattern.match(asset_name):
                download_url = asset.get('browser_download_url')
                break

        if tag_name and tag_name.startswith('v') and download_url:
            return {'version': tag_name[1:], 'download_url': download_url}, None
        elif not tag_name or not tag_name.startswith('v'):
            return None, "Error: Could not find the latest Luma3DS version number on GitHub (tag_name missing or invalid)."
        elif not download_url:
            return None, "Error: Could not find the Luma3DS ZIP file (pattern 'Luma3DSvX.Y.Z.zip') in the latest GitHub Release. The asset name might have changed."
        else:
            return None, "An unexpected error occurred while parsing GitHub release data."
    except requests.exceptions.RequestException as e:
        return None, f"Error connecting to GitHub: {e}. Please check your internet connection."
    except Exception as e:
        return None, f"An unexpected error occurred: {e}"

def download_and_inject_luma_update(drive_letter, download_url, progress_callback=None):
    """
    Performs the download and "injection" of Luma3DS files to the SD card.
    This function performs REAL FILE OPERATIONS!
    """
    if progress_callback:
        progress_callback("Starting Luma3DS update process...", 0, "info")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'Luma3DS_update.zip')

            if progress_callback:
                progress_callback("Downloading Luma3DS...", 10, "info")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = int((downloaded_size / total_size) * 50) + 10 # 10-60% for download
                            progress_callback(f"Downloaded: {downloaded_size / (1024*1024):.2f} MB of {total_size / (1024*1024):.2f} MB", progress, "info")
            
            if progress_callback:
                progress_callback("Luma3DS archive downloaded.", 60, "info")

            extract_path = os.path.join(temp_dir, 'extracted_luma')
            os.makedirs(extract_path, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            if progress_callback:
                progress_callback("Luma3DS archive extracted.", 70, "info")

            sd_card_root = drive_letter
            sd_card_luma_dir = os.path.join(drive_letter, 'luma')
            sd_card_luma_config_dir = os.path.join(drive_letter, 'luma', 'config')

            src_boot_firm = os.path.join(extract_path, 'boot.firm')
            dest_boot_firm = os.path.join(sd_card_root, 'boot.firm')
            if os.path.exists(src_boot_firm):
                if progress_callback: progress_callback("Copying boot.firm...", 75, "info")
                shutil.copy2(src_boot_firm, dest_boot_firm)
            else:
                if progress_callback: progress_callback("Warning: 'boot.firm' not found in extracted Luma archive.", 75, "warning")

            src_boot_3dsx = os.path.join(extract_path, 'boot.3dsx')
            dest_boot_3dsx = os.path.join(sd_card_root, 'boot.3dsx')
            if os.path.exists(src_boot_3dsx):
                if progress_callback: progress_callback("Copying boot.3dsx...", 80, "info")
                shutil.copy2(src_boot_3dsx, dest_boot_3dsx)
            else:
                if progress_callback: progress_callback("Warning: 'boot.3dsx' not found in extracted Luma archive.", 80, "warning")

            src_luma_config_dir = os.path.join(extract_path, 'luma', 'config')
            if os.path.isdir(src_luma_config_dir):
                if progress_callback: progress_callback("Updating luma/config folder...", 85, "info")
                os.makedirs(sd_card_luma_config_dir, exist_ok=True)
                for item in os.listdir(src_luma_config_dir):
                    s = os.path.join(src_luma_config_dir, item)
                    d = os.path.join(sd_card_luma_config_dir, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d)
            else:
                if progress_callback: progress_callback("Warning: Luma/config folder not found in release.", 85, "warning")

            if progress_callback:
                progress_callback("Luma3DS files successfully copied.", 100, "success")
            return True, "Luma3DS update successful."

    except requests.exceptions.RequestException as e:
        if progress_callback: progress_callback(f"Network error: {e}", 0, "error")
        return False, f"Network error downloading Luma3DS: {e}"
    except zipfile.BadZipFile:
        if progress_callback: progress_callback("Error: Downloaded Luma3DS ZIP is corrupted.", 0, "error")
        return False, "The downloaded Luma3DS ZIP file is corrupted."
    except Exception as e:
        if progress_callback: progress_callback(f"An unexpected Luma3DS error occurred: {e}", 0, "error")
        return False, f"An unexpected error during Luma3DS update: {e}"

# --- GodMode9 Specific Functions ---

def get_local_gm9_version(drive_letter):
    """
    Checks if GodMode9.firm exists. Returns "Installed" or an error.
    The exact version cannot be read directly from the firm file.
    """
    gm9_payload_path = os.path.join(drive_letter, 'luma', 'payloads', 'GodMode9.firm')

    if not os.path.exists(drive_letter):
        return None, f"Error: Drive letter '{drive_letter}' not found."
    if not os.path.exists(os.path.join(drive_letter, 'luma', 'payloads')):
        return None, f"Error: The 'luma/payloads' directory was not found on '{drive_letter}'."
    if not os.path.exists(gm9_payload_path):
        return "Not found", f"Error: The file '{gm9_payload_path}' (GodMode9.firm) was not found."

    return "Installed", None # Assumed if the file exists, it's "installed"

def get_latest_gm9_release_info():
    """
    Retrieves the latest GodMode9 release information from GitHub.
    Looks for the asset "GodMode9-vX.Y.Z-*.zip".
    """
    repo_owner = "d0k3"
    repo_name = "GodMode9"
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        tag_name = data.get('tag_name') # e.g. "v2.1.0"
        download_url = None
        
        # Pattern for the GodMode9 ZIP filename: GodMode9-vX.Y.Z-TAG.zip
        gm9_zip_pattern = re.compile(r"GodMode9-v\d+\.\d+\.\d+.*\.zip")

        for asset in data.get('assets', []):
            asset_name = asset.get('name')
            if asset_name and gm9_zip_pattern.match(asset_name):
                download_url = asset.get('browser_download_url')
                break

        if tag_name and tag_name.startswith('v') and download_url:
            return {'version': tag_name[1:], 'download_url': download_url}, None
        elif not tag_name or not tag_name.startswith('v'):
            return None, "Error: Could not find the latest GodMode9 version number on GitHub (tag_name missing or invalid)."
        elif not download_url:
            return None, "Error: Could not find the GodMode9 ZIP file (pattern 'GodMode9-vX.Y.Z-*.zip') in the latest GitHub Release. The asset name might have changed."
        else:
            return None, "An unexpected error occurred while parsing GitHub release data for GodMode9."
    except requests.exceptions.RequestException as e:
        return None, f"Error connecting to GitHub for GodMode9: {e}. Please check your internet connection."
    except Exception as e:
        return None, f"An unexpected error occurred: {e}"

def download_and_inject_gm9_update(drive_letter, download_url, progress_callback=None):
    """
    Performs the download and "injection" of GodMode9 files to the SD card.
    This function copies GodMode9.firm to the 'luma/payloads' directory
    and updates the 'gm9' folder without deleting the 'scripts' subfolder.
    """
    if progress_callback:
        progress_callback("Starting GodMode9 update process...", 0, "info")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'GodMode9_update.zip')

            if progress_callback:
                progress_callback("Downloading GodMode9...", 10, "info")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = int((downloaded_size / total_size) * 50) + 10 # 10-60% for download
                            progress_callback(f"Downloaded: {downloaded_size / (1024*1024):.2f} MB of {total_size / (1024*1024):.2f} MB", progress, "info")
            
            if progress_callback:
                progress_callback("GodMode9 archive downloaded.", 60, "info")

            extract_path = os.path.join(temp_dir, 'extracted_gm9')
            os.makedirs(extract_path, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            if progress_callback:
                progress_callback("GodMode9 archive extracted.", 70, "info")

            sd_card_root = drive_letter
            luma_payloads_dir = os.path.join(sd_card_root, 'luma', 'payloads')
            os.makedirs(luma_payloads_dir, exist_ok=True) # Ensure target directory exists

            # Search for GodMode9.firm in the extracted directory
            src_gm9_firm = None
            for root, _, files in os.walk(extract_path):
                if 'GodMode9.firm' in files:
                    src_gm9_firm = os.path.join(root, 'GodMode9.firm')
                    break
            
            if not src_gm9_firm:
                return False, "Error: 'GodMode9.firm' not found in the extracted GodMode9 archive."

            dest_gm9_firm = os.path.join(luma_payloads_dir, 'GodMode9.firm')

            if progress_callback:
                progress_callback("Copying GodMode9.firm...", 75, "info")
            
            shutil.copy2(src_gm9_firm, dest_gm9_firm)

            # Update the 'gm9/' folder selectively to preserve 'scripts'
            src_gm9_folder = os.path.join(extract_path, 'gm9')
            if os.path.isdir(src_gm9_folder):
                if progress_callback:
                    progress_callback("Updating gm9/ folder...", 80, "info")
                
                dest_gm9_folder = os.path.join(sd_card_root, 'gm9')
                os.makedirs(dest_gm9_folder, exist_ok=True) # Ensure target folder exists

                # Iterate through all items in the source gm9 folder
                for item_name in os.listdir(src_gm9_folder):
                    src_item_path = os.path.join(src_gm9_folder, item_name)
                    dest_item_path = os.path.join(dest_gm9_folder, item_name)

                    if item_name == 'scripts': # Skip the scripts folder
                        if progress_callback: progress_callback("Skipping gm9/scripts folder...", 85, "info")
                        continue
                    
                    if os.path.isdir(src_item_path):
                        # If it's another folder, clear and copy
                        if os.path.exists(dest_item_path):
                            shutil.rmtree(dest_item_path) # Delete existing folder (except scripts)
                        shutil.copytree(src_item_path, dest_item_path)
                    elif os.path.isfile(src_item_path):
                        # If it's a file, overwrite
                        shutil.copy2(src_item_path, dest_item_path)

            if progress_callback:
                progress_callback("GodMode9 files successfully copied.", 100, "success")
            return True, "GodMode9 update successful."

    except requests.exceptions.RequestException as e:
        if progress_callback: progress_callback(f"Network error: {e}", 0, "error")
        return False, f"Network error downloading GodMode9: {e}"
    except zipfile.BadZipFile:
        if progress_callback: progress_callback("Error: Downloaded GodMode9 ZIP is corrupted.", 0, "error")
        return False, "The downloaded GodMode9 ZIP file is corrupted."
    except Exception as e:
        if progress_callback: progress_callback(f"An unexpected GodMode9 error occurred: {e}", 0, "error")
        return False, f"An unexpected error during GodMode9 update: {e}"

# --- Dump Functions (NEW) ---

def dump_file(drive_letter, source_path_on_sd, destination_folder, progress_callback=None):
    """
    Copies a file from the SD card to a specified destination folder on the PC.
    """
    full_source_path = os.path.join(drive_letter, source_path_on_sd)
    
    # Ensure the destination folder exists
    os.makedirs(destination_folder, exist_ok=True)
    
    file_name = os.path.basename(source_path_on_sd)
    full_destination_path = os.path.join(destination_folder, file_name)

    if progress_callback:
        progress_callback(f"Starting dump of {file_name}...", 0, "info")

    if not os.path.exists(full_source_path):
        if progress_callback:
            progress_callback(f"Error: Source file '{file_name}' not found on SD card.", 0, "error")
        return False, f"Error: Source file '{full_source_path}' not found."
    
    try:
        shutil.copy2(full_source_path, full_destination_path)
        if progress_callback:
            progress_callback(f"File '{file_name}' successfully dumped.", 100, "success")
        return True, f"File '{file_name}' successfully dumped to '{full_destination_path}'."
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error dumping '{file_name}': {e}", 0, "error")
        return False, f"Error dumping '{file_name}': {e}"

# --- Main execution for CLI test (updated) ---

if __name__ == "__main__":
    print("--- 3DSE - 3DS Everything Tool ---")
    while True:
        sd_card_drive = input("Please enter the drive letter of your 3DS SD card (e.g., E: or F:). Type 'exit' to quit: ").strip().upper()

        if sd_card_drive == 'EXIT':
            break

        if not sd_card_drive.endswith(':'):
            sd_card_drive += ':'
        
        # --- Luma3DS Status ---
        print("\n--- Luma3DS Status ---")
        local_luma_version, local_luma_error = get_local_luma_version(sd_card_drive)
        if local_luma_error:
            print(local_luma_error)
        else:
            print(f"Local Luma3DS Version: {local_luma_version}")

        luma_release_info, latest_luma_error = get_latest_luma_release_info()
        latest_luma_version = luma_release_info['version'] if luma_release_info else None
        latest_luma_download_url = luma_release_info['download_url'] if luma_release_info else None

        if latest_luma_error:
            print(latest_luma_error)
        else:
            print(f"Latest Luma3DS Version (GitHub): {latest_luma_version}")

        if local_luma_version and latest_luma_version:
            luma_comparison_result = compare_versions(local_luma_version, latest_luma_version)
            if luma_comparison_result == -1:
                print(f"Luma3DS update available! Your version ({local_luma_version}) is older than the latest ({latest_luma_version}).")
                if latest_luma_download_url:
                    confirm = input("Would you like to update Luma3DS now? (y/n): ").strip().lower()
                    if confirm == 'y':
                        success, message = download_and_inject_luma_update(sd_card_drive, latest_luma_download_url, progress_callback=lambda msg, prog, status: print(f"Luma Progress: {msg} ({prog}%)"))
                        print(f"Luma3DS Update Result: {message}")
                    else:
                        print("Luma3DS update cancelled.")
                else:
                    print("No download URL available for Luma3DS.")
            elif luma_comparison_result == 0:
                print(f"Luma3DS is up to date ({local_luma_version}).")
            else:
                print(f"Your Luma3DS version ({local_luma_version}) is newer than on GitHub ({latest_luma_version}).")
        else:
            print("Luma3DS version comparison not possible.")


        # --- GodMode9 Status ---
        print("\n--- GodMode9 Status ---")
        local_gm9_status, local_gm9_error = get_local_gm9_version(sd_card_drive)
        if local_gm9_error:
            print(local_gm9_error)
        else:
            print(f"Local GodMode9: {local_gm9_status}")

        gm9_release_info, latest_gm9_error = get_latest_gm9_release_info()
        latest_gm9_version = gm9_release_info['version'] if gm9_release_info else None
        latest_gm9_download_url = gm9_release_info['download_url'] if gm9_release_info else None

        if latest_gm9_error:
            print(latest_gm9_error)
        else:
            print(f"Latest GodMode9 Version (GitHub): {latest_gm9_version}")
        
        # Logic for GodMode9: If the file is not found or a newer version is available
        if latest_gm9_version:
            if local_gm9_status == "Not found" or \
               (local_gm9_status == "Installed" and compare_versions("0.0.0", latest_gm9_version) == -1): # Assumption that 'Installed' is an old version if no specific version was read
                print(f"GodMode9 update/installation recommended! Latest Version: {latest_gm9_version}.")
                if latest_gm9_download_url:
                    confirm = input("Would you like to install/update GodMode9 now? (y/n): ").strip().lower()
                    if confirm == 'y':
                        success, message = download_and_inject_gm9_update(sd_card_drive, latest_gm9_download_url, progress_callback=lambda msg, prog, status: print(f"GM9 Progress: {msg} ({prog}%)"))
                        print(f"GodMode9 Update Result: {message}")
                    else:
                        print("GodMode9 installation/update cancelled.")
                else:
                    print("No download URL available for GodMode9.")
            else:
                print(f"GodMode9 appears to be up to date or a newer version is not available.")
        else:
            print("GodMode9 version check not possible.")
        
        # --- Dump Options (NEW) ---
        print("\n--- Dump Options ---")
        dump_target_folder = os.path.join(os.path.expanduser("~"), "3DSE_Dumps")
        print(f"Files will be dumped to the following folder: {dump_target_folder}")
        
        dump_options = {
            "1": {"path": "boot9strap/firm0_enc.bak", "name": "firm0_enc.bak (Boot9Strap)"},
            "2": {"path": "boot9strap/firm1_enc.bak", "name": "firm1_enc.bak (Boot9Strap)"},
            "3": {"path": "_nds/bios7i_part1.bin", "name": "bios7i_part1.bin (_nds)"},
            "4": {"path": "_nds/bios9i_part1.bin", "name": "bios9i_part1.bin (_nds)"},
            "5": {"path": "3ds/boot9.bin", "name": "boot9.bin (3ds)"},
            "6": {"path": "3ds/boot11.bin", "name": "boot11.bin (3ds)"},
            "all": {"name": "All of the above files"}
        }

        print("\nAvailable files to dump:")
        for key, info in dump_options.items():
            if key != "all":
                print(f"  {key}. {info['name']}")
        print(f"  all. {dump_options['all']['name']}")

        while True:
            dump_choice = input("Select a number to dump or 'all' for all, 'back' to go back, or 'exit' to quit: ").strip().lower()
            if dump_choice == 'exit':
                exit()
            if dump_choice == 'back':
                break

            files_to_dump = []
            if dump_choice == 'all':
                for key, info in dump_options.items():
                    if key != "all":
                        files_to_dump.append(info)
            elif dump_choice in dump_options and dump_choice != "all":
                files_to_dump.append(dump_options[dump_choice])
            else:
                print("Invalid selection. Please try again.")
                continue

            if not files_to_dump:
                print("No files selected or found to dump.")
                continue

            confirm_dump = input(f"Would you like to dump the selected files to '{dump_target_folder}'? (y/n): ").strip().lower()
            if confirm_dump == 'y':
                for file_info in files_to_dump:
                    source_path = file_info['path']
                    file_display_name = file_info['name']
                    print(f"\nStarting dump of: {file_display_name}")
                    success, message = dump_file(sd_card_drive, source_path, dump_target_folder, 
                                                 progress_callback=lambda msg, prog, status: print(f"Dump Progress ({file_display_name}): {msg} ({prog}%)"))
                    print(f"Dump result for {file_display_name}: {message}")
                print("\nDump process completed.")
            else:
                print("Dump process cancelled.")
            break # Break out of the inner loop after a successful dump or cancellation

        print("\n" + "-" * 30 + "\n")

    print("Script terminated.")