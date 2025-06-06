import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import os
import sys
import ctypes


def elevate_to_admin():
    """Request administrator privileges to run the program."""
    if not ctypes.windll.shell32.IsUserAnAdmin():
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
        except Exception as e:
            print(f"Error: Unable to elevate to administrator privileges. {e}")
            sys.exit(1)
        sys.exit()


def get_base_path():
    """Get the base path for the application, works both in development and when compiled to EXE."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))


def list_disks():
    try:
        # Get physical disks with partition and volume info
        physical_disks = subprocess.check_output(
            ['powershell', '-command', 
             """
             $disks = Get-PhysicalDisk | ForEach-Object {
                 $disk = $_
                 # Get all partitions for this disk
                 $parts = Get-Partition | Where-Object { $_.DiskNumber -eq $disk.DeviceId }
                 # Get volume info for each partition
                 $volumes = $parts | ForEach-Object {
                     try {
                         Get-Volume -Partition $_ | Select-Object DriveLetter, FileSystemType
                     } catch {
                         [PSCustomObject]@{DriveLetter = $null; FileSystemType = $null}
                     }
                 }
                 [PSCustomObject]@{
                     DeviceId = $disk.DeviceId
                     FriendlyName = $disk.FriendlyName
                     Size = $disk.Size
                     DriveLetter = if($volumes) { ($volumes | Select-Object -First 1).DriveLetter } else { $null }
                     FileSystem = if($volumes) { ($volumes | Select-Object -First 1).FileSystemType } else { $null }
                 }
             } | Format-List
             $disks
             """],
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        ).split('\n')

        # Process physical disks
        disk_map = {}
        current_disk = None
        
        for line in physical_disks:
            if line.strip():
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'DeviceId':
                        current_disk = value
                        disk_map[current_disk] = {'name': '', 'size': 0, 'letter': 'N/A', 'fs': 'N/A'}
                    elif key == 'FriendlyName' and current_disk:
                        disk_map[current_disk]['name'] = value
                    elif key == 'Size' and current_disk:
                        try:
                            size_gb = round(float(value) / (1024**3), 2)
                            disk_map[current_disk]['size'] = size_gb
                        except (ValueError, TypeError):
                            disk_map[current_disk]['size'] = 0
                    elif key == 'DriveLetter' and current_disk:
                        disk_map[current_disk]['letter'] = value if value else 'N/A'
                    elif key == 'FileSystem' and current_disk:
                        disk_map[current_disk]['fs'] = value if value else 'N/A'

        # Format output
        result = f"{'Device ID':<10}{'Model':<35}{'Size':<15}{'Drive Letter':<15}{'File System':<15}\n"
        result += "-" * 90 + "\n"
        
        if not disk_map:
            result += "No physical disks found.\n"
        else:
            for disk_id, info in sorted(disk_map.items()):
                size_str = f"{info['size']:<7.2f}GB"
                result += f"{disk_id:<10}{info['name']:<35}{size_str:<15}{info['letter']:<15}{info['fs']:<15}\n"

        return result
    except subprocess.CalledProcessError as e:
        return f"Error while listing disks (PowerShell error): {str(e)}"
    except Exception as e:
        return f"Error while listing disks: {str(e)}"


def format_disk(disk_id, file_system="NTFS", volume_label="NewVolume"):
    try:
        if not disk_id.strip():
            messagebox.showerror("Error", "Please enter a disk ID.")
            return
            
        if not disk_id.isdigit():
            messagebox.showerror("Error", "Please enter the numeric ID of the disk (e.g., 0, 1, 2, etc.).")
            return

        # Confirm the operation
        result = messagebox.askyesno(
            "Confirm Format", 
            f"WARNING: This will completely erase all data on disk {disk_id}.\n\n"
            f"Are you sure you want to format disk {disk_id} with {file_system} file system?"
        )
        
        if not result:
            return

        # Create the diskpart script file in temp directory
        temp_dir = os.environ.get('TEMP', os.getcwd())
        script_path = os.path.join(temp_dir, "format_disk.txt")
        log_path = os.path.join(temp_dir, "diskpart_log.txt")
        
        script_content = f"""select disk {disk_id}
clean
create partition primary
select partition 1
active
assign
format fs={file_system} label="{volume_label}" quick
exit
"""
        
        with open(script_path, "w") as file:
            file.write(script_content)

        # Execute diskpart
        try:
            with open(log_path, "w") as log_file:
                result = subprocess.run(
                    f'diskpart /s "{script_path}"', 
                    shell=True, 
                    check=True, 
                    stdout=log_file, 
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            
            messagebox.showinfo("Success", f"Disk {disk_id} has been successfully formatted to {file_system}.")
            refresh_disk_list()
            
        except subprocess.CalledProcessError as e:
            # Read the log file to get more details
            try:
                with open(log_path, "r") as log_file:
                    log_content = log_file.read()
                messagebox.showerror("Error", f"Error while formatting the disk:\n{log_content}")
            except:
                messagebox.showerror("Error", f"Error while formatting the disk: {e}")
        
        # Clean up temporary files
        try:
            os.remove(script_path)
            os.remove(log_path)
        except:
            pass
            
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error: {e}")


def clone_disk(source_disk, target_disk):
    """Note: This function uses dd command which is not available on Windows by default."""
    try:
        if not source_disk.strip() or not target_disk.strip():
            messagebox.showerror("Error", "Please enter both source and target disk paths.")
            return
            
        # Warning about dd not being available on Windows
        messagebox.showwarning(
            "Warning", 
            "The dd command is not available on Windows by default.\n"
            "Consider using tools like Clonezilla, AOMEI Backupper, or similar software for disk cloning."
        )
        return
        
        # This would work on Linux/Unix systems:
        # subprocess.run(f"dd if={source_disk} of={target_disk} bs=4M conv=sync", shell=True, check=True)
        # messagebox.showinfo("Success", "Disk cloning completed successfully!")
        
    except Exception as e:
        messagebox.showerror("Error", f"Error while cloning the disk: {e}")


def backup_disk(source_disk):
    """Note: This function uses dd command which is not available on Windows by default."""
    try:
        if not source_disk.strip():
            messagebox.showerror("Error", "Please enter a source disk path.")
            return
            
        # Warning about dd not being available on Windows
        messagebox.showwarning(
            "Warning", 
            "The dd command is not available on Windows by default.\n"
            "Consider using tools like AOMEI Backupper, Macrium Reflect, or Windows built-in backup tools."
        )
        return
        
        # This would work on Linux/Unix systems:
        # output_file = filedialog.asksaveasfilename(defaultextension=".backup", filetypes=[("Backup Files", "*.backup")])
        # if output_file:
        #     subprocess.run(f"dd if={source_disk} of={output_file} bs=4M conv=sync", shell=True, check=True)
        #     messagebox.showinfo("Success", "Disk backup completed successfully!")
            
    except Exception as e:
        messagebox.showerror("Error", f"Error while backing up the disk: {e}")


def refresh_disk_list():
    try:
        disks = list_disks()
        disk_list_text.delete(1.0, tk.END)
        disk_list_text.insert(tk.END, disks)
    except Exception as e:
        messagebox.showerror("Error", f"Error refreshing disk list: {e}")


def main():
    global disk_list_text, format_disk_entry, file_system_entry, volume_label_entry
    global source_disk_entry, target_disk_entry, backup_disk_entry
    
    # Main window creation
    root = tk.Tk()
    root.title("Disk Management Tool")
    root.geometry("800x600")
    
    # Try to set icon, but don't fail if it's not available
    try:
        base_path = get_base_path()
        icon_path = os.path.join(base_path, "iconw.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        # Ignore icon errors - the app will work without an icon
        pass

    # Section: Disk List
    tk.Label(root, text="Available Physical Disks:", font=('Arial', 12, 'bold')).pack(pady=(10, 5))
    
    disk_frame = tk.Frame(root)
    disk_frame.pack(fill='both', expand=True, padx=10)
    
    disk_list_text = tk.Text(disk_frame, height=12, width=100, font=('Courier', 9))
    scrollbar = tk.Scrollbar(disk_frame, orient='vertical', command=disk_list_text.yview)
    disk_list_text.configure(yscrollcommand=scrollbar.set)
    
    disk_list_text.pack(side='left', fill='both', expand=True)
    scrollbar.pack(side='right', fill='y')
    
    refresh_button = tk.Button(root, text="Refresh Disk List", command=refresh_disk_list, 
                              bg='lightblue', font=('Arial', 10))
    refresh_button.pack(pady=5)

    # Section: Disk Formatting
    format_frame = tk.LabelFrame(root, text="Disk Formatting", font=('Arial', 10, 'bold'))
    format_frame.pack(pady=10, padx=10, fill='x')
    
    tk.Label(format_frame, text="Disk ID to format:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
    format_disk_entry = tk.Entry(format_frame, width=20)
    format_disk_entry.grid(row=0, column=1, padx=5, pady=2)
    
    tk.Label(format_frame, text="File System:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
    file_system_entry = tk.Entry(format_frame, width=20)
    file_system_entry.insert(0, "NTFS")
    file_system_entry.grid(row=1, column=1, padx=5, pady=2)
    
    tk.Label(format_frame, text="Volume Label:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
    volume_label_entry = tk.Entry(format_frame, width=20)
    volume_label_entry.insert(0, "NewVolume")
    volume_label_entry.grid(row=2, column=1, padx=5, pady=2)
    
    format_button = tk.Button(format_frame, text="Format Disk", 
                             command=lambda: format_disk(
                                 format_disk_entry.get(),
                                 file_system_entry.get(),
                                 volume_label_entry.get()
                             ),
                             bg='red', fg='white', font=('Arial', 10, 'bold'))
    format_button.grid(row=3, column=0, columnspan=2, pady=10)

    # Section: Disk Cloning (disabled for Windows)
    clone_frame = tk.LabelFrame(root, text="Disk Cloning (Not yet available)", 
                               font=('Arial', 10, 'bold'))
    clone_frame.pack(pady=10, padx=10, fill='x')
    
    tk.Label(clone_frame, text="Source Disk:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
    source_disk_entry = tk.Entry(clone_frame, width=20, state='disabled')
    source_disk_entry.grid(row=0, column=1, padx=5, pady=2)
    
    tk.Label(clone_frame, text="Target Disk:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
    target_disk_entry = tk.Entry(clone_frame, width=20, state='disabled')
    target_disk_entry.grid(row=1, column=1, padx=5, pady=2)
    
    clone_button = tk.Button(clone_frame, text="Clone Disk (Use external tools)", 
                            command=lambda: clone_disk(source_disk_entry.get(), target_disk_entry.get()),
                            state='disabled')
    clone_button.grid(row=2, column=0, columnspan=2, pady=5)

    # Section: Disk Backup (disabled for Windows)
    backup_frame = tk.LabelFrame(root, text="Disk Backup (Not yet available)", 
                                font=('Arial', 10, 'bold'))
    backup_frame.pack(pady=10, padx=10, fill='x')
    
    tk.Label(backup_frame, text="Source Disk for Backup:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
    backup_disk_entry = tk.Entry(backup_frame, width=20, state='disabled')
    backup_disk_entry.grid(row=0, column=1, padx=5, pady=2)
    
    backup_button = tk.Button(backup_frame, text="Backup Disk (Use external tools)", 
                             command=lambda: backup_disk(backup_disk_entry.get()),
                             state='disabled')
    backup_button.grid(row=0, column=2, padx=5, pady=2)

    # Initialize the disk list
    refresh_disk_list()

    # Run the app
    root.mainloop()


if __name__ == "__main__": 
    elevate_to_admin()
    main()