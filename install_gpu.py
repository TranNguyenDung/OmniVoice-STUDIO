import platform
import subprocess
import sys
import os


def is_git_installed():
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except:
        return False


def install_git(os_name):
    print("\n" + "=" * 50)
    print("Git not found. Installing Git...")
    print("=" * 50)

    if os_name == "Windows":
        print("Installing Git for Windows...")
        try:
            subprocess.run(
                [
                    "winget",
                    "install",
                    "--id",
                    "Git.Git",
                    "--source",
                    "winget",
                    "--silent",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
                check=False,
            )
        except:
            try:
                subprocess.run(["choco", "install", "git", "-y"], check=False)
            except:
                print("Could not auto-install.")
                print("Download: https://git-scm.com/download/win")
                print("Run as Administrator, enable 'Git Bash' and 'Add to PATH'")

    elif os_name == "Linux":
        print("Installing Git for Linux...")
        try:
            subprocess.run(["sudo", "apt", "update"], check=False)
            subprocess.run(["sudo", "apt", "install", "-y", "git"], check=False)
        except:
            try:
                subprocess.run(["sudo", "yum", "install", "-y", "git"], check=False)
            except:
                subprocess.run(["sudo", "dnf", "install", "-y", "git"], check=False)

    elif os_name == "Darwin":
        print("Installing Git for macOS...")
        try:
            subprocess.run(["brew", "install", "git"], check=False)
        except:
            print("Installing Homebrew...")
            subprocess.run(
                [
                    "/bin/bash",
                    "-c",
                    "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)",
                ],
                check=False,
            )
            subprocess.run(["brew", "install", "git"], check=False)


def get_gpu_info():
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda", f"GPU: {torch.cuda.get_device_name(0)}"
        elif (
            platform.system() == "Darwin"
            and hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        ):
            return "mps", "Apple Metal (M1/M2/M3)"
    except ImportError:
        pass
    return None, "CPU"


def install_python_deps(os_name):
    print("\n" + "=" * 50)
    print("Installing Python dependencies...")
    print("=" * 50)

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
        )
    except Exception as e:
        print(f"Could not install requirements.txt: {e}")
        print("Installing packages individually...")

        if os_name == "Windows":
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "torch",
                    "torchvision",
                    "torchaudio",
                    "--index-url",
                    "https://download.pytorch.org/whl/cu121",
                ],
                check=False,
            )
        else:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "torch",
                    "torchvision",
                    "torchaudio",
                ],
                check=False,
            )

        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "git+https://github.com/k2-fsa/omnivoice.git",
                ],
                check=False,
            )
        except:
            pass


def show_gpu_instructions(os_name):
    print("\n" + "=" * 50)
    print("GPU Setup Instructions")
    print("=" * 50)

    if os_name == "Windows":
        print("""
=== Windows GPU Setup (NVIDIA) ===
1. Download CUDA Toolkit 12.1:
   https://developer.nvidia.com/cuda-12-1-0-download-archive
2. Install CUDA
3. Install cuDNN (extract to CUDA folder)
4. Run: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
        """)
    elif os_name == "Linux":
        print("""
=== Linux GPU Setup (NVIDIA) ===
1. sudo apt update && sudo apt install nvidia-driver-535
2. Install CUDA 12.1 from NVIDIA website
3. Add to ~/.bashrc:
   export PATH=/usr/local/cuda-12.1/bin:$PATH
4. pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
        """)
    elif os_name == "Darwin":
        print("""
=== macOS GPU Setup ===
- PyTorch uses Metal (MPS) on Apple Silicon
- pip install torch torchvision torchaudio
- Code automatically uses MPS if available
        """)


def main():
    os_name = platform.system()
    print(f"Detected OS: {os_name}")
    print(f"Python: {sys.version.split()[0]}")

    if not is_git_installed():
        install_git(os_name)

    install_python_deps(os_name)
    show_gpu_instructions(os_name)

    print("\n" + "=" * 50)
    print("Verifying GPU availability...")
    print("=" * 50)

    backend, info = get_gpu_info()
    if backend:
        print(f"OK! {backend.upper()} available - {info}")
    else:
        print("No GPU detected, will use CPU (slower)")

    print("\n" + "=" * 50)
    print("Done! Run: python main.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
