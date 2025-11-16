import PyInstaller.__main__
import os
import shutil

def build_exe():
    # Remove previous build directories
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # PyInstaller configuration
    params = [
        'main.py',  # Your main script
        '--name=NinjaSageBot',
        '--onefile',  # Single executable
        '--windowed',  # No console window (use --console if you want console)
        # '--icon=ninja_icon.ico',  # Optional: add an icon file
        '--add-data=data;data',  # Include data folder
        '--add-data=quick_login.json;.',  # Include config files
        '--hidden-import=config',
        '--hidden-import=amf_req',
        '--hidden-import=leveling',
        '--hidden-import=eudemon',
        '--hidden-import=event',
        '--hidden-import=event_finisher',
        '--hidden-import=shadow_war',
        '--hidden-import=resources',
        '--hidden-import=utils',
        '--collect-all=tkinter',
        '--noconfirm',
        '--clean'
    ]
    
    PyInstaller.__main__.run(params)

if __name__ == '__main__':
    build_exe()