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
    users[username] = {
        'psw': hashlib.sha256(password.encode('utf-8')).hexdigest(),
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

    psw = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return user['psw'] == psw


def is_admin(username):
    user = users[username]
    return user['is_admin']


def client_login(username, password):
    return auth(username, password, False)


def admin_login(username, password):
    return auth(username, password, True)


if __name__ == '__main__':
    webui_config = load_configs(WEBUI_CONFIG)
    theme_path = os.path.join(THEME_FOLDER, webui_config["settings"].get("theme", "theme_blue.json"))
    os.environ["GRADIO_TEMP_DIR"] = os.path.abspath("E:/MSSTcache/")

    interface = gr.Blocks(
        theme=gr.Theme.load(theme_path),
        title='MSST 客户端'
    )
    with interface:
        create_ui()

    interface.launch(share=False,
                     server_name='0.0.0.0',
                     server_port=7861,
                     auth=client_login)
