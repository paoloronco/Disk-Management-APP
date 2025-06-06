# Disk Management Tool

![App Screenshot](/images/app.png)

**Disk Management Tool** is a desktop application currently under development for managing physical disks on Windows systems.

## 📦 Project Status

🚧 **Early Version**  
At the moment, only the **disk formatting** feature is functional. The **cloning** and **backup** sections are present in the interface but not yet implemented.

## 🛠 Technologies Used

- Language: **Python**
- GUI: **Tkinter**
- System Commands: **PowerShell**, **diskpart**
- EXE Conversion:  
  ```bash
  pyinstaller --onefile --noconsole --icon=iconw.ico app.py

## 🛠 Features

- ✔️ Display available physical disks
- ✔️ Format a selected disk (requires admin privileges)
- ❌ Disk cloning (coming soon)
- ❌ Disk backup (coming soon)

## Project Structure

```text
DiskManagement-APP/ 
├── images/
│ ├── App Icon/
│ │ ├── 1-nobackground-colored.png
│ │ ├── 1-nobackground-colored.ico
│ │ ├── 1-nobackground.png
│ │ └── 1.png
│ └── app.png 
├── PythonAPP/
│ ├── app.py 
│ ├── app.spec 
│ ├── iconw.ico 
│ ├── dist/
│ │ └── app.exe 
│ └── build/
│ └── app/ 
├── WindowsAPP-exe/
│ └── app.exe 
└── README.md 


