import os
import json
from cryptography.fernet import Fernet

KEY_PATH = 'secret.key'

def get_or_create_key():
    """Generates a key or loads the existing one."""
    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        with open(KEY_PATH, 'wb') as f:
            f.write(key)
        return key
    else:
        with open(KEY_PATH, 'rb') as f:
            return f.read()

def encrypt_data(data: dict) -> str:
    """Encrypts a dictionary into a string."""
    key = get_or_create_key()
    fernet = Fernet(key)
    json_data = json.dumps(data)
    return fernet.encrypt(json_data.encode()).decode()

def decrypt_data(token: str) -> dict:
    """Decrypts a string into a dictionary."""
    if not token:
        return {}
    key = get_or_create_key()
    fernet = Fernet(key)
    try:
        decrypted = fernet.decrypt(token.encode()).decode()
        return json.loads(decrypted)
    except Exception as e:
        print(f"Decryption failed: {e}")
        return {}

def backup_db(db_path, target_dir):
    """Simple sqlite backup by file copy."""
    import shutil
    import datetime
    filename = f"dhm_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    dest = os.path.join(target_dir, filename)
    shutil.copy2(db_path, dest)
    return dest

def restore_db(backup_path, db_path):
    """Restore database by replacing the current one with a backup."""
    import shutil
    if os.path.exists(backup_path):
        # Backup the current one just in case before overwriting
        if os.path.exists(db_path):
            os.rename(db_path, f"{db_path}.pre_restore")
        shutil.copy2(backup_path, db_path)
        return True
    return False
