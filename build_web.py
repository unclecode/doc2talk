#!/usr/bin/env python3
"""
Build script for Doc2Talk web interface
This script automates the process of building the React frontend and copying it to the correct location.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Get the root directory of the project
ROOT_DIR = Path(__file__).parent
WEB_DIR = ROOT_DIR / "web"
DIST_DIR = WEB_DIR / "build"
TARGET_DIR = ROOT_DIR / "src" / "doc2talk" / "web" / "dist"


def check_requirements():
    """Check if required tools are installed."""
    # Check npm and Node.js
    try:
        # Check if npm is installed
        subprocess.run(
            ["npm", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        print("✅ npm is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: npm is not installed or not in PATH.")
        print("Please install Node.js and npm: https://nodejs.org/")
        sys.exit(1)
    
    # Check Python dependencies
    required_packages = {
        "fastapi": "FastAPI for backend API",
        "uvicorn": "ASGI server for FastAPI",
        "websockets": "WebSocket support for streaming",
    }
    
    missing_packages = []
    
    print("\n📋 Checking Python dependencies...")
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            missing_packages.append((package, description))
            print(f"❌ {package} is not installed ({description})")
    
    # Install missing packages if any
    if missing_packages:
        print("\n📦 Installing missing Python dependencies...")
        for package, description in missing_packages:
            try:
                print(f"Installing {package}...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    check=True
                )
                print(f"✅ {package} installed successfully")
            except subprocess.CalledProcessError:
                print(f"❌ Error installing {package}. Please install it manually: pip install {package}")
                sys.exit(1)


def install_dependencies():
    """Install npm dependencies."""
    print("\n📦 Installing dependencies...")
    os.chdir(WEB_DIR)
    
    try:
        subprocess.run(["npm", "install"], check=True)
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError:
        print("❌ Error installing dependencies")
        sys.exit(1)


def build_frontend():
    """Build the React frontend."""
    print("\n🏗️ Building frontend...")
    os.chdir(WEB_DIR)
    
    try:
        subprocess.run(["npm", "run", "build"], check=True)
        print("✅ Frontend built successfully")
    except subprocess.CalledProcessError:
        print("❌ Error building frontend")
        sys.exit(1)


def copy_to_package():
    """Copy the built files to the package directory."""
    print("\n📋 Copying files to package...")
    
    # Create target directory if it doesn't exist
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    
    # Remove existing files in target directory
    for item in TARGET_DIR.glob("*"):
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    
    # Copy files from build to target
    for item in DIST_DIR.glob("*"):
        if item.is_file():
            shutil.copy2(item, TARGET_DIR)
        elif item.is_dir():
            shutil.copytree(item, TARGET_DIR / item.name)
    
    print("✅ Files copied successfully")


def start_dev_server():
    """Start the React development server."""
    print("\n🚀 Starting development server...")
    os.chdir(WEB_DIR)
    
    try:
        # This will block until the user terminates it
        subprocess.run(["npm", "start"], check=True)
    except subprocess.CalledProcessError:
        print("❌ Error starting development server")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n✨ Development server stopped")


def main():
    """Main build function."""
    # Check if in development mode
    if len(sys.argv) > 1 and sys.argv[1] == "--dev":
        print("🌐 Running Doc2Talk Web Interface in Development Mode\n" + "=" * 50)
        print("This will start the React development server.")
        print("Make sure to run 'doc2talk web --dev' in another terminal to start the API server.")
        
        check_requirements()
        install_dependencies()
        start_dev_server()
    else:
        print("🌐 Building Doc2Talk Web Interface\n" + "=" * 35)
        
        check_requirements()
        install_dependencies()
        build_frontend()
        copy_to_package()
        
        print("\n✨ Build completed successfully!")
        print("You can now run the web interface with: doc2talk web")
        print("\nFor development mode with hot-reloading:")
        print("1. Run 'python build_web.py --dev' in one terminal")
        print("2. Run 'doc2talk web --dev' in another terminal")


if __name__ == "__main__":
    main()