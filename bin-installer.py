#!/usr/bin/env python3

import os
import sys
import shutil
import subprocess
import importlib.util
from pathlib import Path
from time import sleep
from select import select  # For input timeout on Unix-based systems

APP_NAME = "NordVPN"
BIN_NAME = f"{APP_NAME}-GUI"
READ_NAME = f"{APP_NAME} GUI"
INSTALL_DIR = Path.home() / ".local/share" / APP_NAME
BIN_PATH = INSTALL_DIR / BIN_NAME
ICON_PATH = INSTALL_DIR / "icon.jpg"
INSTALLED_FILE = INSTALL_DIR / f"Installed-{BIN_NAME}"
DESKTOP_FILE = INSTALL_DIR / f"{APP_NAME}.desktop"
UNINSTALLER = INSTALL_DIR / "uninstall.sh"
INSTALLER = INSTALL_DIR / "install.sh"
MENU_DESKTOP_FILE = Path.home() / ".local/share/applications" / f"{APP_NAME}.desktop"

def is_compiled():
    """Check if running as a compiled binary."""
    return getattr(sys, '_MEIPASS', None) is not None

def error_exit(message, delay=4):
    """Display an error message and exit."""
    print(message)
    sleep(delay)
    sys.exit(1)

def timed_input(prompt, timeout=10):
    """Get input from the user with a timeout."""
    print(f"{prompt} (y/n) [default: n]: ", end="", flush=True)
    ready, _, _ = select([sys.stdin], [], [], timeout)
    if ready:
        return sys.stdin.readline().strip()
    print("\nTimed out.")  # Timeout message
    return "n"  # Default to "n" on timeout

def create_installation_directory():
    """Create the installation directory."""
    if not INSTALL_DIR.exists():
        os.makedirs(INSTALL_DIR, exist_ok=True)
    print(f"Created installation directory: {INSTALL_DIR}")

def copy_files():
    """Copy required files to the installation directory."""
    base_dir = Path(sys._MEIPASS)  # Base directory for compiled files
    icon = base_dir / ICON_PATH.name
    icond = INSTALL_DIR / ICON_PATH.name
    if icond.is_file():
        icond.unlink()
    shutil.copy(icon, icond)
    if BIN_PATH.is_file():
        BIN_PATH.unlink()
    shutil.copy(sys.executable, BIN_PATH)
    os.chmod(BIN_PATH, 0o755)
    print("Copied files to installation directory.")

def create_desktop_file():
    """Create and place the .desktop shortcut."""
    content = f"""[Desktop Entry]
Version=1.0
Type=Application
Terminal=false
Exec={BIN_PATH}
Path={INSTALL_DIR}
Name=NordVPN GUI
Icon={ICON_PATH}
X-Desktop-File-Install-Version=0.24
"""
    DESKTOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DESKTOP_FILE, "w") as f:
        f.write(content)
    MENU_DESKTOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MENU_DESKTOP_FILE, "w") as f:
        f.write(content)

    print(f"Created desktop file: {DESKTOP_FILE}")

def create_un_installer():
    content = f"""#!/bin/bash
echo {DESKTOP_FILE}
touch {DESKTOP_FILE}
cat > $FILE_NAME <<EOF
#!/usr/bin/env xdg-open

[Desktop Entry]
Version=1.0
Type=Application
Terminal=false
Exec={BIN_PATH}
Path={INSTALL_DIR}
Name={READ_NAME}
Icon={ICON_PATH}
X-Desktop-File-Install-Version=0.24

EOF

echo {MENU_DESKTOP_FILE}
cp "{DESKTOP_FILE}" "{MENU_DESKTOP_FILE}"

chmod 755 "{DESKTOP_FILE}"
chmod 755 "{MENU_DESKTOP_FILE}"

if [ ! -f "{INSTALLED_FILE}" ]; then
    ./NordVPN-GUI
fi
    """ # Restore github syntax highlighting: """   
    INSTALLER.parent.mkdir(parents=True, exist_ok=True)
    with open(INSTALLER, "w") as f:
        f.write(content)
    os.chmod(INSTALLER, 0o755)

    content = f"""#!/bin/bash
echo {DESKTOP_FILE}
rm "{DESKTOP_FILE}"
echo {MENU_DESKTOP_FILE}
rm "{MENU_DESKTOP_FILE}"
echo {INSTALLED_FILE}
rm "{INSTALLED_FILE}"
    """ # Restore github syntax highlighting: """
    UNINSTALLER.parent.mkdir(parents=True, exist_ok=True)
    with open(UNINSTALLER, "w") as f:
        f.write(content)
    os.chmod(UNINSTALLER, 0o755)

def save_installed_file():
    INSTALLED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INSTALLED_FILE, "w") as f:
        f.write("True")

def finalize_installation():
    """Finalize installation by notifying the user."""
    print("Installation complete!")
    print(f"The app was installed to '{INSTALL_DIR}'")
    print("To launch the app, find 'NordVPN GUI' in your applications menu.")
    print("If the desktop icon doesn't work, enable launching by right-clicking on it and selecting 'Allow Launching'.")
    if "noopen" not in sys.argv[1:]:
        print("Opening the install folder")
        subprocess.run(["xdg-open", f"{INSTALL_DIR}"])
    else:
        print("The keyword 'noopen' was in the argument list, skipping opening of install dir")

def check_required_files(required_files):
    """Check if all required files exist."""
    missing_files = [file for file in required_files if not Path(file).exists()]
    if missing_files:
        print(f"The following files are missing: {', '.join(missing_files)}")
        error_exit("Compilation cannot proceed due to missing files.")

def create_virtual_environment(venv_dir):
    """Create the virtual environment if it's missing."""
    if not venv_dir.exists():
        print("Virtual environment is missing. Creating...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        print("Virtual environment created.")

def install_pyinstaller(venv_dir):
    """Ensure PyInstaller is installed in the virtual environment."""
    print("Installing PyInstaller...")
    subprocess.run([str(venv_dir / "bin/python"), "-m", "pip", "install", "pip", "setuptools", "wheel", "pyinstaller"], check=True)
    print("PyInstaller installed.")


def get_installed_version(package_name, python_executable):
    """Check the installed version of a package using pip."""
    try:
        result = subprocess.run(
            [python_executable, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
        return None  # Package exists, but version could not be determined
    except subprocess.CalledProcessError:
        return None  # Package is not installed

def install_dependencies(venv_dir, requirements_path):
    """Install dependencies from requirements.txt one by one, checking if already installed."""
    if requirements_path.exists():
        print("Installing dependencies from requirements.txt one by one...")
        python_executable = str(venv_dir / "bin/python")

        # Read each line from requirements.txt
        with requirements_path.open("r") as f:
            dependencies = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        for dependency in dependencies:
            base_package = dependency.split("==")[0]  # Extract base package name
            specified_version = dependency.split("==")[1] if "==" in dependency else None

            # Check if the package is already installed
            installed_version = get_installed_version(base_package, python_executable)
            if installed_version:
                if specified_version:
                    if installed_version == specified_version:
                        print(f"{base_package} {specified_version} is already installed. Skipping.")
                        continue
                    else:
                        print(f"{base_package} installed version ({installed_version}) differs from {specified_version}. Reinstalling.")
                else:
                    print(f"{base_package} is already installed (version {installed_version}). Skipping.")
                    continue
            else:
                print(f"{base_package} is not installed. Installing.")

            # Try to install the dependency
            print(f"Installing {dependency}...")
            result = subprocess.run(
                [python_executable, "-m", "pip", "install", dependency],
                capture_output=True,  # Captures both stdout and stderr
                text=True,            # Decodes output to strings
                check=False           # Avoid automatic exception on failure
            )

            # Print the captured stdout and stderr
            print("Output:", result.stdout)
            print("Error:", result.stderr)

            if result.returncode != 0:
                print(f"Failed to install {dependency}. Attempting to install the latest version.")
                latest_result = subprocess.run(
                    [python_executable, "-m", "pip", "install", base_package],
                    capture_output=True,
                    text=True,
                    check=False
                )

                print("Latest version output:", latest_result.stdout)
                print("Latest version error:", latest_result.stderr)

                if latest_result.returncode != 0:
                    print(f"Failed to install the latest version of {base_package}. Continuing with the next dependency...")
                else:
                    print(f"Successfully installed the latest version of {base_package}.")
            else:
                print(f"Successfully installed {dependency}.")

        print("All dependencies processed.")
    else:
        error_exit("requirements.txt is missing.")


def compile_application(venv_dir):
    """Compile the application using PyInstaller."""
    print("Compiling the application using PyInstaller...")
    os.chdir(Path(__file__).parent)
    pyinstaller_command = [
        str(venv_dir / "bin/pyinstaller"),
        "--onefile",
        "--noconfirm",
        "--add-data=icon.jpg:.",
        "--exclude-module=tkinter",
        "--strip",
        "--optimize=2",
        "--clean",
        "--name",
        BIN_NAME,
        Path(__file__).name,
    ]

    do_compile = 3
    while do_compile > 1:
        print(f"Running: {pyinstaller_command}")
        result = subprocess.run(
            pyinstaller_command,
            capture_output=True,
            text=True,
            check=False
        )
            
        # Print the captured stdout and stderr
        print("Output: " + str(result.stdout) + "")
        print("Error: " + str(result.stderr) + "")

        if result.returncode != 0:
            do_compile -= 1
            if do_compile > 1:
                print(f"Retrying compile {do_compile} times, on compile errror")
            else:
                print("Could not compile after the attempts")
        else:
            do_compile = 0
            print("Compilation was finished")

    if result.returncode != 0:
        print("Exitting for Pyinstaller, because of error")
        sys.exit(1)
    
    result_file = Path("dist") / BIN_NAME
    dest_file = Path(BIN_NAME)
    if dest_file.is_file():
        dest_file.unlink()
    if result_file.is_file() and not dest_file.exists():
        shutil.move(result_file, dest_file)
    print("Compilation complete. Run the compiled binary to proceed.")


def check_and_compile():
    """Main function to check files, set up the environment, and compile the app."""
    # Define required files
    required_files = [
        "nord_vpn_api/nord_client.py",
        "main.py",
        "icon.jpg",
        "requirements.txt",
    ]
    venv_dir = Path("venv")
    requirements_path = Path("requirements.txt")

    # Step-by-step checks and actions
    check_required_files(required_files)
    create_virtual_environment(venv_dir)
    install_pyinstaller(venv_dir)
    install_dependencies(venv_dir, requirements_path)
    compile_application(venv_dir)

    # After compile the app has to be reinstalled
    if INSTALLED_FILE.is_file():
        INSTALLED_FILE.unlink()

    # Enable exit it install not wanted
    # sys.exit()

    cmd=[Path(__file__).parent / BIN_NAME]
    # After copile install the app
    if "noopen" in sys.argv[1:]:
        cmd.append("noopen")
    subprocess.run(cmd, check=True)
    sys.exit()


def start_app_and_close():
    print("App was installed. Starting...")
    import main
    import binreqs
    sys.exit()


def main():
    """Main installation process."""
    if not is_compiled():
        if "compile" in sys.argv[1:]:
            print("The keyword 'compile' was added as argument. Compiling now!")
            response = "y"
        else:
            response = timed_input("This installer must be run from a compiled binary. Compile now?")
        if response.lower() != "y":
            error_exit("Exiting. Please compile the script to run the installer.")

        check_and_compile()

    elif INSTALLED_FILE.is_file():
        start_app_and_close()

    create_installation_directory()
    copy_files()
    create_desktop_file()
    create_un_installer()
    save_installed_file()
    finalize_installation()

if __name__ == "__main__":
    main()
