#!/usr/bin/env python
"""
OmniVoice Studio - One-click Setup & Run Script
"""

import subprocess
import sys
import os
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"

def install_package(package):
    """Install a package using pip."""
    print(f"[INSTALL] {package}")
    result = subprocess.run([sys.executable, "-m", "pip", "install", package], capture_output=False)
    return result.returncode == 0

def main():
    print("=" * 60)
    print("OMNIVOICE STUDIO - SETTING UP...")
    print("=" * 60)

    base_dir = Path(__file__).parent
    os.chdir(base_dir)

    dependencies = [
        "torch>=2.0.0",
        "torchaudio>=2.0.0",
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.22.0",
        "python-multipart>=0.0.6",
        "jinja2>=3.1.2",
        "soundfile",
        "pillow",
        "moviepy>=2.0.0",
    ]

    print("\n[Step 1] Installing Python packages...")
    for dep in dependencies:
        install_package(dep)

    print("\n[Step 2] Installing OmniVoice...")
    install_package("git+https://github.com/k2-fsa/omnivoice.git")

    print("\n[Step 3] Creating directories...")
    for folder in ["input", "output", "media_uploads", "output_videos", "temp_debug"]:
        Path(folder).mkdir(parents=True, exist_ok=True)
        print(f"  - {folder}/")

    print("\n[Step 4] Starting web server...")
    print("=" * 60)
    print("Running at: http://localhost:8000")
    print("=" * 60)

    import uvicorn
    from web_api import app
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()