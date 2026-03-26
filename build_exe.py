import PyInstaller.__main__
import os

def build_app():
    PyInstaller.__main__.run([
        'main.py',
        '--onefile',
        '--windowed',
        '--name', 'DHM_Manager',
        '--add-data', 'app;app', # Include app module
        '--icon', 'NONE', # Can add .ico here
        '--clean'
    ])

if __name__ == "__main__":
    build_app()
    print("Build complete. Look for 'DHM_Manager.exe' in the 'dist' folder.")
