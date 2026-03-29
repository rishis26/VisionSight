import os
import sys

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_app_data_dir():
    app_data = os.path.expanduser('~/Library/Application Support/VisionSight')
    os.makedirs(app_data, exist_ok=True)
    os.makedirs(os.path.join(app_data, 'assets', 'known_faces'), exist_ok=True)
    os.makedirs(os.path.join(app_data, 'logs'), exist_ok=True)
    return app_data

def get_env_path():
    return os.path.join(get_app_data_dir(), '.env')

def get_log_path():
    return os.path.join(get_app_data_dir(), 'logs', 'daemon.log')

def get_encodings_path():
    return os.path.join(get_app_data_dir(), 'assets', 'known_faces', 'encodings.pkl')

def get_known_faces_dir():
    return os.path.join(get_app_data_dir(), 'assets', 'known_faces')
    
def get_icon_path():
    return os.path.join(get_base_dir(), 'assets', 'icon.png')
