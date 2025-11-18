import gradio as gr
import hashlib
from pathlib import Path

from clientui.actions import add_user
from clientui.ui import create_ui

from utils.constant import *
from webui.utils import load_configs

user_lib = Path('./user.json').resolve()
if not user_lib.exists():
    users = {}
    add_user('admin',
             'ypd@123',
             True)
else:
    with open(user_lib, encoding='utf-8') as f:
        users = json.load(f)


def add_user(username, password, admin):
    if username in users:
        return False
    
    # 如果密码以 'TEMP_' 开头，说明是安装时设置的临时密码，需要去掉前缀并哈希
    if password.startswith('TEMP_'):
        actual_password = password[5:]  # 去掉 'TEMP_' 前缀
        password_hash = hashlib.sha256(actual_password.encode('utf-8')).hexdigest()
    else:
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    users[username] = {
        'psw': password_hash,
        'is_admin': admin,
    }

    with open(user_lib, mode='w', encoding='utf-8') as f:
        f.write(json.dumps(users, indent=4, ensure_ascii=False))

    return True


def auth(username, password, admin_only):
    if username not in users:
        return False
    user = users[username]
    admin = user['is_admin']
    if admin_only and not admin:
        return False

    stored_password = user['psw']
    
    # 如果存储的密码以 'TEMP_' 开头，说明还未哈希化
    if stored_password.startswith('TEMP_'):
        # 去掉 'TEMP_' 前缀并比较
        actual_stored_password = stored_password[5:]
        if password == actual_stored_password:
            # 密码正确，现在更新为哈希值
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            users[username]['psw'] = password_hash
            
            # 删除说明字段（如果存在）
            if '_note' in users[username]:
                del users[username]['_note']
            
            # 保存更新后的用户数据
            with open(user_lib, mode='w', encoding='utf-8') as f:
                f.write(json.dumps(users, indent=4, ensure_ascii=False))
            
            return True
        else:
            return False
    else:
        # 正常的哈希密码验证
        psw = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return stored_password == psw


def is_admin(username):
    user = users[username]
    return user['is_admin']


def client_login(username, password):
    return auth(username, password, False)


def admin_login(username, password):
    return auth(username, password, True)


def load_client_config():
    """加载客户端配置"""
    client_config_file = "client_config.json"
    default_config = {
        "client_port": 7861,
        "server_port": 7860,
        "server_address": "localhost",
        "user_dir": "E:/MSSTuser",  # 与clientui/actions.py中的设置保持一致
        "cache_dir": os.path.join(os.path.expanduser("~"), "AppData", "Local", "MSST_WebUI", "cache"),
        "temp_dir": os.path.join(os.path.expanduser("~"), "AppData", "Local", "MSST_WebUI", "temp"),
        "auto_clean_temp": True,
        "max_file_size": 100,
        "allowed_formats": ["wav", "mp3", "flac", "m4a", "ogg"]
    }
    
    try:
        with open(client_config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # 合并默认配置，确保所有必要的键都存在
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        return config
    except FileNotFoundError:
        # 如果配置文件不存在，创建默认配置
        with open(client_config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        return default_config
    except json.JSONDecodeError:
        print(f"警告: 客户端配置文件格式错误，使用默认配置")
        return default_config

if __name__ == '__main__':
    # 加载客户端配置
    client_config = load_client_config()
    
    # 加载WebUI配置
    webui_config = load_configs(WEBUI_CONFIG)
    theme_path = os.path.join(THEME_FOLDER, webui_config["settings"].get("theme", "theme_blue.json"))
    
    # 设置临时目录
    temp_dir = client_config.get("temp_dir", os.path.join(os.path.expanduser("~"), "AppData", "Local", "MSST_WebUI", "temp"))
    try:
        print(f"正在创建临时目录: {temp_dir}")
        print(f"临时目录类型: {type(temp_dir)}")
        print(f"临时目录长度: {len(temp_dir) if temp_dir else 'None'}")
        
        # 确保路径是字符串且格式正确
        temp_dir = str(temp_dir).strip()
        
        # 使用 Path 对象处理路径，避免路径问题
        temp_dir_path = Path(temp_dir)
        temp_dir_path.mkdir(parents=True, exist_ok=True)
        temp_dir = str(temp_dir_path.absolute())
        
        os.environ["GRADIO_TEMP_DIR"] = temp_dir
        print(f"临时目录创建成功: {temp_dir}")
    except Exception as e:
        print(f"创建临时目录失败: {e}")
        print(f"将使用当前目录下的 temp 文件夹")
        temp_dir = os.path.abspath("./temp")
        os.makedirs(temp_dir, exist_ok=True)
        os.environ["GRADIO_TEMP_DIR"] = temp_dir
    
    # 创建其他必要目录
    for dir_key in ["user_dir", "cache_dir"]:
        dir_path = client_config.get(dir_key)
        if dir_path:
            try:
                print(f"正在创建{dir_key}: {dir_path}")
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                print(f"{dir_key}创建成功")
            except Exception as e:
                print(f"创建{dir_key}失败: {e}")

    interface = gr.Blocks(
        theme=gr.Theme.load(theme_path),
        title='MSST 客户端'
    )
    with interface:
        create_ui()

    # 使用客户端配置中的端口
    client_port = client_config.get("client_port", 7861)
    
    interface.launch(share=False,
                     server_name='0.0.0.0',
                     server_port=client_port,
                     auth=client_login)
