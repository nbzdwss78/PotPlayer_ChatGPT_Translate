# -*- coding: utf-8 -*-
"""PyQt6 based installer for PotPlayer ChatGPT Translate — FINAL (OpenAI SDK, Dark Theme)"""

import ctypes
import hashlib
import json
import os
import re
import shutil
import sys
import winreg
import webbrowser

# OPENAI SDK 替换 requests
from openai import OpenAI
import win32com.client
from PyQt6 import QtWidgets, QtCore, QtGui

PLUGIN_VERSION = "1.9.4"

# ========= Helpers for bundled resources =========

def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def load_json_resource(filename: str):
    path = resource_path(filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_json_text(filename: str) -> str:
    path = resource_path(filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _format_language_strings(strings):
    for lang_dict in strings.values():
        if isinstance(lang_dict, dict):
            for key, value in list(lang_dict.items()):
                if isinstance(value, str):
                    lang_dict[key] = value.replace("{VERSION}", PLUGIN_VERSION)


# ========= Per-model provider dict (model → api_base endpoint & purchase link) =========
# 重要：预设使用完整 chat/completions 端点（例如 https://api.openai.com/v1/chat/completions）
API_PROVIDERS = {
    # Official OpenAI presets
    "gpt-5": {
        "model": "gpt-5",
        "api_base": "https://api.openai.com/v1/chat/completions",
        "purchase_page": "https://platform.openai.com/account/billing"
    },
    "gpt-5-mini": {
        "model": "gpt-5-mini",
        "api_base": "https://api.openai.com/v1/chat/completions",
        "purchase_page": "https://platform.openai.com/account/billing"
    },
    "gpt-5-nano": {
        "model": "gpt-5-nano",
        "api_base": "https://api.openai.com/v1/chat/completions",
        "purchase_page": "https://platform.openai.com/account/billing"
    },
    "gpt-4o": {
        "model": "gpt-4o",
        "api_base": "https://api.openai.com/v1/chat/completions",
        "purchase_page": "https://platform.openai.com/account/billing"
    },
    "gpt-4.1": {
        "model": "gpt-4.1",
        "api_base": "https://api.openai.com/v1/chat/completions",
        "purchase_page": "https://platform.openai.com/account/billing"
    },
    "gpt-4.1-mini": {
        "model": "gpt-4.1-mini",
        "api_base": "https://api.openai.com/v1/chat/completions",
        "purchase_page": "https://platform.openai.com/account/billing"
    },
    # 示例第三方：需 OpenAI-兼容接口（路径中一般包含 /v1/chat/completions）
    # 如你有网关给的是完整 endpoint（.../chat/completions），也能用，代码会自动规范化
    "ollama": {
        "model": "glm-4",
        "api_base": "http://xxx.xxx.xxx.xxx:11434/v1/chat/completions",  # 假设兼容 /chat/completions
        "purchase_page": "pass",
        "allow_custom_model": True
    },
    "gemini-flash": {
        "model": "gemini-3-flash-preview",
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "purchase_page": "https://aistudio.google.com/app/apikey"
    },
    # Sentinel for custom entry (user-defined)
    "__CUSTOM__": {
        "model": "",
        "api_base": "",
        "purchase_page": ""
    }
}

LANGUAGE_STRINGS = load_json_resource("language_strings.json")
_format_language_strings(LANGUAGE_STRINGS)
MODEL_TOKEN_LIMITS_JSON = load_json_text("model_token_limits.json")

OFFLINE_FILES = {
    "with_context": [
        ("SubtitleTranslate - ChatGPT.as", "SubtitleTranslate - ChatGPT.as"),
        ("SubtitleTranslate - ChatGPT.ico", "SubtitleTranslate - ChatGPT.ico"),
    ],
    "without_context": [
        ("SubtitleTranslate - ChatGPT - Without Context.as", "SubtitleTranslate - ChatGPT - Without Context.as"),
        ("SubtitleTranslate - ChatGPT - Without Context.ico", "SubtitleTranslate - ChatGPT - Without Context.ico"),
    ]
}

# ========= Utils =========

def merge_bilingual(key):
    return LANGUAGE_STRINGS["en"][key] + "\n\n" + LANGUAGE_STRINGS["zh"][key]

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def restart_as_admin():
    params = " ".join([f'"{arg}"' for arg in sys.argv])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit()

def get_path_from_shortcut(shortcut_path):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(shortcut_path)
        return shortcut.TargetPath
    except Exception:
        return None

def scan_shortcuts():
    search_dirs = [
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        r"C:\Users\Public\Desktop",
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]
    for base in search_dirs:
        if os.path.exists(base):
            for root, _, files in os.walk(base):
                for file in files:
                    if file.lower().endswith(".lnk") and "potplayer" in file.lower():
                        shortcut_path = os.path.join(root, file)
                        target = get_path_from_shortcut(shortcut_path)
                        if target and os.path.exists(target):
                            translate_dir = os.path.join(os.path.dirname(target), "Extension", "Subtitle", "Translate")
                            if os.path.exists(translate_dir):
                                return translate_dir
    return None

def get_path_from_installation_dir():
    base_dirs = [r"C:\Program Files\DAUM\PotPlayer", r"C:\Program Files (x86)\DAUM\PotPlayer"]
    for drive in [f"{chr(x)}:\\" for x in range(65, 91) if os.path.exists(f"{chr(x)}:\\")]:
        base_dirs.append(os.path.join(drive, "DAUM", "PotPlayer"))
        base_dirs.append(os.path.join(drive, "Program Files", "DAUM", "PotPlayer"))
        base_dirs.append(os.path.join(drive, "Program Files (x86)", "DAUM", "PotPlayer"))
    for d in base_dirs:
        if os.path.exists(d):
            translate_dir = os.path.join(d, "Extension", "Subtitle", "Translate")
            if os.path.exists(translate_dir):
                return translate_dir
    return None

def scan_drives():
    for drive in [f"{chr(x)}:\\" for x in range(65, 91) if os.path.exists(f"{chr(x)}:\\")]:
        for pf in ("Program Files", "Program Files (x86)"):
            path = os.path.join(drive, pf, "DAUM", "PotPlayer", "Extension", "Subtitle", "Translate")
            if os.path.exists(path):
                return path
    return None

def auto_detect_directory():
    detected = scan_shortcuts()
    if detected:
        return detected
    detected = get_path_from_installation_dir()
    if detected:
        return detected
    return scan_drives()

def read_license():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    license_path = os.path.join(script_dir, "LICENSE")
    if os.path.exists(license_path):
        with open(license_path, "r", encoding="utf-8") as f:
            return f.read()
    return "LICENSE file not found."

def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _escape_for_as_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")


# —— OpenAI SDK 验证：把“可能是完整 endpoint”的 api_url 规范化为 base_url 根路径
def _normalize_api_url_for_config(api_url: str) -> str:
    """
    Normalize user/preset API URL to a chat/completions endpoint.
    - If为空，默认写入官方 chat/completions。
    - 如果以 /v1 或 /v4 结尾，补上 /chat/completions。
    - 已经是 chat/completions 或 responses 结尾，则保持不变。
    """
    u = (api_url or "").strip()
    if not u:
        return "https://api.openai.com/v1/chat/completions"
    u = u.rstrip("/")
    for tail in ("/chat/completions", "/responses"):
        if u.endswith(tail):
            return u
    if re.search(r"/v[14]$", u):
        return u + "/chat/completions"
    return u


def _normalize_base_url_for_openai(api_url: str) -> str:
    """
    Normalize to base_url for OpenAI SDK (strip resource suffix).
    """
    u = (api_url or "").strip().rstrip("/")
    if not u:
        return "https://api.openai.com/v1"
    for tail in ("/chat/completions", "/responses"):
        if u.endswith(tail):
            return u[: -len(tail)]
    return u

def verify_api_settings(model, api_url, api_key):
    """
    使用 OpenAI SDK 做最小化验证。
    - 支持 base_url 为根或完整 endpoint（自动规范化）。
    - 仅请求 1 token，失败时返回异常信息。
    """
    api_url_for_config = _normalize_api_url_for_config(api_url)
    base_url = _normalize_base_url_for_openai(api_url_for_config)
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Hello"}
            ],
        )
        # 成功只需有 choices 即可
        if getattr(resp, "choices", None):
            return True, ""
        return False, "Empty response"
    except Exception as e:
        return False, str(e)

def reg_key_name(install_dir, context_type):
    id_base = os.path.abspath(install_dir).lower() + "|" + context_type
    id_hash = hashlib.md5(id_base.encode("utf-8")).hexdigest()[:8]
    return f"PotPlayer_ChatGPT_Translate_{id_hash}"

def find_existing_reg_info(install_dir, context_type):
    regname = reg_key_name(install_dir, context_type)
    try:
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\\" + regname
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
        version, _ = winreg.QueryValueEx(key, "DisplayVersion")
        uninstall_str, _ = winreg.QueryValueEx(key, "UninstallString")
        context_type_val, _ = winreg.QueryValueEx(key, "ContextType")
        key.Close()
        return {"key": regname, "version": version, "uninstall": uninstall_str, "context": context_type_val}
    except Exception:
        return None

def register_software(display_name, uninstall_path, install_dir, key_name, version, context_type):
    reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\\" + key_name
    key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
    winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, display_name)
    winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninstall_path)
    winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
    winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Felix3322")
    winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, uninstall_path)
    winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
    winreg.SetValueEx(key, "ContextType", 0, winreg.REG_SZ, context_type)
    key.Close()

def generate_uninstaller(uninstall_bat_path, files_to_delete, reg_key):
    with open(uninstall_bat_path, "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write("REM PotPlayer ChatGPT Translate uninstall script\n\n")
        for file in files_to_delete:
            if os.path.isdir(file):
                f.write(f'rmdir /s /q "{file}"\n')
            else:
                f.write(f'del "{file}" /f /q\n')
        f.write('del "%~f0" /f /q\n')
        f.write(f'reg delete "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{reg_key}" /f\n')
        popup_message = "卸载完成，所有文件均已清理，如果Geek Uninstaller或其他卸载工具提示有残留，请仔细甄别，避免误删PotPlayer本体文件"
        f.write(
            'powershell -NoProfile -Command '
            '"Add-Type -AssemblyName PresentationFramework;'
            f"[System.Windows.MessageBox]::Show('{popup_message}','PotPlayer ChatGPT Translate')\"\n"
        )
        f.write("\nexit\n")

def apply_preconfig(file_path, api_key, model, api_base, delay_ms, retry_mode, debug_mode,
                    check_hallucination=None, context_subtitle_count=None, context_cache_mode=None,
                    prompt_cache_retention=None, gemini_cached_content=None,
                    small_model=False, token_limits_json=None):
    try:
        api_base = _normalize_api_url_for_config(api_base)
        with open(file_path, "r", encoding="utf-8") as f:
            data = f.read()
        data = re.sub(r'pre_api_key\s*=\s*".*?"', f'pre_api_key = "{api_key}"', data)
        data = re.sub(r'pre_selected_model\s*=\s*".*?"', f'pre_selected_model = "{model}"', data)
        data = re.sub(r'pre_apiUrl\s*=\s*".*?"', f'pre_apiUrl = "{api_base}"', data)
        data = re.sub(r'pre_delay_ms\s*=\s*".*?"', f'pre_delay_ms = "{delay_ms}"', data)
        data = re.sub(r'pre_retry_mode\s*=\s*".*?"', f'pre_retry_mode = "{retry_mode}"', data)
        if small_model is not None:
            val = "1" if small_model else "0"
            data = re.sub(r'pre_small_model\s*=\s*".*?"', f'pre_small_model = "{val}"', data)
        if check_hallucination is not None:
            retry_value = "1" if str(check_hallucination) in ("1", "true", "True", "on", "yes") else "0"
            data = re.sub(r'pre_check_hallucination\s*=\s*".*?"', f'pre_check_hallucination = "{retry_value}"', data)
        if context_subtitle_count is not None:
            data = re.sub(r'pre_context_subtitle_count\s*=\s*".*?"', f'pre_context_subtitle_count = "{context_subtitle_count}"', data)
        if context_cache_mode is not None:
            cache_value = str(context_cache_mode)
            data = re.sub(r'pre_context_cache_mode\s*=\s*".*?"',
                          f'pre_context_cache_mode = "{cache_value}"', data)
        if prompt_cache_retention is not None:
            retention_value = str(prompt_cache_retention)
            data = re.sub(r'pre_prompt_cache_retention\s*=\s*".*?"',
                          f'pre_prompt_cache_retention = "{retention_value}"', data)
        if gemini_cached_content is not None:
            gemini_cache_value = str(gemini_cached_content)
            data = re.sub(r'pre_gemini_cached_content\s*=\s*".*?"',
                          f'pre_gemini_cached_content = "{gemini_cache_value}"', data)
        if token_limits_json is not None:
            escaped_json = _escape_for_as_string(token_limits_json)
            data = re.sub(r'pre_model_token_limits_json\s*=\s*".*?"',
                          f'pre_model_token_limits_json = "{escaped_json}"', data)
        if debug_mode and "HostOpenConsole();" not in data:
            inserted = False
            m = re.search(r'(void\s+OnInitialize\(\)\s*\{\s*\n)([ \t]*)', data)
            if m:
                insert_pos = m.end(1)
                indent = m.group(2) or "    "
                data = data[:insert_pos] + indent + "HostOpenConsole();\n" + data[insert_pos:]
                inserted = True
            if not inserted:
                idx = data.find("*/")
                if idx != -1:
                    idx += 2
                    data = data[:idx] + "\nHostOpenConsole();\n" + data[idx:]
                else:
                    data = "HostOpenConsole();\n" + data
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(data)
    except Exception:
        pass

def set_wizard_button_texts(wizard):
    s = wizard.strings
    wizard.setWindowTitle(s["app_title"])
    wizard.setButtonText(QtWidgets.QWizard.WizardButton.NextButton, s["next"])
    wizard.setButtonText(QtWidgets.QWizard.WizardButton.BackButton, s["back"])
    wizard.setButtonText(QtWidgets.QWizard.WizardButton.CancelButton, s["cancel"])
    wizard.setButtonText(QtWidgets.QWizard.WizardButton.FinishButton, s["finish"])

# ========= Theme helpers (Force Fusion Dark Palette) =========

def apply_fusion_dark_palette(app: QtWidgets.QApplication):
    app.setStyle("Fusion")
    p = QtGui.QPalette()

    bg  = QtGui.QColor(30, 30, 30)
    base= QtGui.QColor(25, 25, 25)
    text= QtGui.QColor(220, 220, 220)
    btn = QtGui.QColor(45, 45, 45)
    link= QtGui.QColor(100, 160, 255)
    hl  = QtGui.QColor(53, 132, 228)

    p.setColor(QtGui.QPalette.ColorRole.Window, bg)
    p.setColor(QtGui.QPalette.ColorRole.WindowText, text)
    p.setColor(QtGui.QPalette.ColorRole.Base, base)
    p.setColor(QtGui.QPalette.ColorRole.AlternateBase, bg)
    p.setColor(QtGui.QPalette.ColorRole.ToolTipBase, base)
    p.setColor(QtGui.QPalette.ColorRole.ToolTipText, text)
    p.setColor(QtGui.QPalette.ColorRole.Text, text)
    p.setColor(QtGui.QPalette.ColorRole.Button, btn)
    p.setColor(QtGui.QPalette.ColorRole.ButtonText, text)
    p.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor(255, 0, 0))
    p.setColor(QtGui.QPalette.ColorRole.Link, link)
    p.setColor(QtGui.QPalette.ColorRole.Highlight, hl)
    p.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(255, 255, 255))

    app.setPalette(p)
    app.setStyleSheet("""
        QLabel { color: palette(WindowText); }
        QLabel a { color: palette(Link); text-decoration: none; }
        QLabel a:hover { text-decoration: underline; }
    """)

# ========= Installation Thread  (NO UI inside thread) =========

class InstallThread(QtCore.QThread):
    progress = QtCore.pyqtSignal(str)

    ask_file_exists = QtCore.pyqtSignal(str, str)     # title, message
    ask_yesno       = QtCore.pyqtSignal(str, str)     # title, message
    ask_text        = QtCore.pyqtSignal(str, str)     # title, prompt

    @QtCore.pyqtSlot(object)
    def receive_answer(self, value):
        self._answer = value
        if self._loop is not None:
            self._loop.quit()

    def _ask_main(self, signal, *args):
        self._answer = None
        self._loop = QtCore.QEventLoop()
        signal.emit(*args)
        self._loop.exec()
        ans = self._answer
        self._loop = None
        return ans

    def __init__(self, install_dir, versions, script_dir, language, api_key, model, api_base, delay_ms, retry_mode, debug_mode, check_hallucination, context_subtitle_count, context_cache_mode, prompt_cache_retention, gemini_cached_content, small_model):
        super().__init__()
        self.install_dir = install_dir
        self.versions = list(versions) if versions else []
        self.script_dir = script_dir
        self.language = language
        self.api_key = api_key
        self.model = model
        self.api_base = api_base
        self.delay_ms = delay_ms
        self.retry_mode = retry_mode
        self.debug_mode = debug_mode
        self.check_hallucination = check_hallucination
        self.context_subtitle_count = context_subtitle_count
        self.context_cache_mode = context_cache_mode
        self.prompt_cache_retention = prompt_cache_retention
        self.gemini_cached_content = gemini_cached_content
        self.small_model = small_model
        self.files_installed = []
        self._loop = None
        self._answer = None

    def run(self):
        s = LANGUAGE_STRINGS[self.language]
        try:
            ensure_dir_exists(self.install_dir)
            if not self.versions:
                self.progress.emit(s["installation_failed"].format("No variant selected"))
                self.progress.emit("DONE")
                return
            for variant in self.versions:
                self._install_variant(variant, s)
            self.progress.emit(LANGUAGE_STRINGS["en"]["installation_complete"] + "\n" +
                               LANGUAGE_STRINGS["zh"]["installation_complete"])
            self.progress.emit("DONE")
        except Exception as e:
            self.progress.emit(merge_bilingual("installation_failed").format(str(e)))
            return

    def _install_variant(self, variant, strings):
        files_for_variant = []
        reg_write = False
        context_type = variant
        key_name = reg_key_name(self.install_dir, context_type)
        variant_label = strings.get("with_context_short", "With context") if variant == "with_context" else strings.get("without_context_short", "Without context")
        self.progress.emit(strings["installing_variant"].format(variant_label))
        display_suffix = LANGUAGE_STRINGS["en"]["with_context_short"] if variant == "with_context" else LANGUAGE_STRINGS["en"]["without_context_short"]
        display_name = f"PotPlayer ChatGPT Translate v{PLUGIN_VERSION} [{display_suffix}]"
        reginfo = find_existing_reg_info(self.install_dir, context_type)

        for src_file, dest_name in OFFLINE_FILES.get(variant, []):
            src_path = os.path.join(self.script_dir, src_file)
            dest_path = os.path.join(self.install_dir, dest_name)
            self.progress.emit(f"Copying {src_file} ...")
            if not os.path.exists(src_path):
                self.progress.emit(strings["installation_failed"].format(f"Missing file {src_file}"))
                return
            if os.path.exists(dest_path):
                choice = self._ask_main(self.ask_file_exists, strings["app_title"], strings["file_exists_3choice"].format(dest_name))
                if choice is None:
                    self.progress.emit(merge_bilingual("installation_cancelled"))
                    return
                elif choice == "overwrite":
                    shutil.copy(src_path, dest_path)
                    if dest_name.lower().endswith(".as"):
                        apply_preconfig(dest_path, self.api_key, self.model, self.api_base, self.delay_ms, self.retry_mode, self.debug_mode,
                                        self.check_hallucination,
                                        str(self.context_subtitle_count) if variant == "with_context" else None,
                                        self.context_cache_mode if variant == "with_context" else None,
                                        self.prompt_cache_retention if variant == "with_context" else None,
                                        self.gemini_cached_content if variant == "with_context" else None,
                                        self.small_model,
                                        MODEL_TOKEN_LIMITS_JSON)
                    self.progress.emit(f"Installed {dest_name} (Overwritten).")
                    self.files_installed.append(dest_path)
                    files_for_variant.append(dest_path)
                    if reginfo:
                        if self._ask_main(self.ask_yesno, strings["app_title"], strings["ask_reg_upgrade"]):
                            reg_write = True
                    else:
                        if self._ask_main(self.ask_yesno, strings["app_title"], strings["ask_reg_write"]):
                            reg_write = True
                elif choice == "rename":
                    while True:
                        new_name = self._ask_main(self.ask_text, strings["app_title"], strings["rename"])
                        if new_name is None:
                            self.progress.emit(merge_bilingual("installation_cancelled"))
                            return
                        new_name = new_name.strip()
                        if not new_name:
                            continue
                        if not os.path.splitext(new_name)[1]:
                            new_name += os.path.splitext(dest_name)[1]
                        new_dest_path = os.path.join(self.install_dir, new_name)
                        if os.path.exists(new_dest_path):
                            _ = self._ask_main(self.ask_file_exists, strings["app_title"], strings["file_exists_3choice"].format(new_name))
                            continue
                        shutil.copy(src_path, new_dest_path)
                        if new_name.lower().endswith(".as"):
                            apply_preconfig(new_dest_path, self.api_key, self.model, self.api_base, self.delay_ms, self.retry_mode, self.debug_mode,
                                            self.check_hallucination,
                                            str(self.context_subtitle_count) if variant == "with_context" else None,
                                            self.context_cache_mode if variant == "with_context" else None,
                                            self.prompt_cache_retention if variant == "with_context" else None,
                                            self.gemini_cached_content if variant == "with_context" else None,
                                            self.small_model,
                                            MODEL_TOKEN_LIMITS_JSON)
                        self.progress.emit(f"Installed {new_name}.")
                        self.files_installed.append(new_dest_path)
                        files_for_variant.append(new_dest_path)
                        if self._ask_main(self.ask_yesno, strings["app_title"], strings["ask_reg_new"]):
                            reg_write = True
                        break
            else:
                shutil.copy(src_path, dest_path)
                if dest_name.lower().endswith(".as"):
                    apply_preconfig(dest_path, self.api_key, self.model, self.api_base, self.delay_ms, self.retry_mode, self.debug_mode,
                                    self.check_hallucination,
                                    str(self.context_subtitle_count) if variant == "with_context" else None,
                                    self.context_cache_mode if variant == "with_context" else None,
                                    self.prompt_cache_retention if variant == "with_context" else None,
                                    self.gemini_cached_content if variant == "with_context" else None,
                                    self.small_model,
                                    MODEL_TOKEN_LIMITS_JSON)
                self.progress.emit(f"Installed {dest_name}.")
                self.files_installed.append(dest_path)
                files_for_variant.append(dest_path)
                if self._ask_main(self.ask_yesno, strings["app_title"], strings["ask_reg_new"]):
                    reg_write = True

        if reg_write:
            tools_dir = os.path.join(self.install_dir, "tools")
            ensure_dir_exists(tools_dir)
            uninstaller_path = os.path.join(tools_dir, f"uninstaller_{key_name}.bat")
            files_to_delete = list(files_for_variant)
            files_to_delete.append(uninstaller_path)
            generate_uninstaller(uninstaller_path, files_to_delete, key_name)
            register_software(
                display_name=display_name,
                uninstall_path=uninstaller_path,
                install_dir=self.install_dir,
                key_name=key_name,
                version=PLUGIN_VERSION,
                context_type=context_type
            )

# ========= Wizard Pages & UI =========

def set_button_texts_for(wizard):
    set_wizard_button_texts(wizard)

class LanguagePage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        layout = QtWidgets.QVBoxLayout()
        self.title_label = QtWidgets.QLabel()
        self.rb_en = QtWidgets.QRadioButton()
        self.rb_zh = QtWidgets.QRadioButton()
        self.rb_en.setChecked(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.rb_en)
        layout.addWidget(self.rb_zh)
        self.setLayout(layout)

    def initializePage(self):
        self.setTitle(LANGUAGE_STRINGS["en"]["choose_language"] + " / " + LANGUAGE_STRINGS["zh"]["choose_language"])
        self.title_label.setText(LANGUAGE_STRINGS["en"]["choose_language"] + " / " + LANGUAGE_STRINGS["zh"]["choose_language"])
        self.rb_en.setText(LANGUAGE_STRINGS["en"]["language_english"])
        self.rb_zh.setText(LANGUAGE_STRINGS["zh"]["language_chinese"])
        set_button_texts_for(self.wizard)

    def validatePage(self):
        self.wizard.language = 'zh' if self.rb_zh.isChecked() else 'en'
        self.wizard.strings = LANGUAGE_STRINGS[self.wizard.language]
        set_button_texts_for(self.wizard)
        return True

class WelcomePage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel()
        self.label.setWordWrap(True)
        self.author = QtWidgets.QLabel()
        self.author.setOpenExternalLinks(True)
        layout.addWidget(self.label)
        layout.addWidget(self.author)
        self.setLayout(layout)

    def initializePage(self):
        s = self.wizard.strings
        self.setTitle(s["welcome_title"])
        self.label.setText(s["welcome_message"])
        self.author.setText(f"<a href='https://github.com/Felix3322/PotPlayer_ChatGPT_Translate'>{s['author_info']}</a>")
        set_button_texts_for(self.wizard)

class LicensePage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        layout = QtWidgets.QVBoxLayout()
        self.intro = QtWidgets.QLabel()
        self.intro.setWordWrap(True)
        self.intro.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.intro.setOpenExternalLinks(True)
        self.intro.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.intro.setOpenExternalLinks(True)
        self.text = QtWidgets.QTextEdit()
        self.text.setReadOnly(True)
        self.chk = QtWidgets.QCheckBox()
        layout.addWidget(self.intro)
        layout.addWidget(self.text)
        layout.addWidget(self.chk)
        self.setLayout(layout)

    def initializePage(self):
        s = self.wizard.strings
        self.setTitle(s["license_title"])
        self.intro.setText(s["license_intro"])
        self.chk.setText(s["license_agree"])
        self.text.setPlainText(read_license())
        set_button_texts_for(self.wizard)

    def validatePage(self):
        if not self.chk.isChecked():
            QtWidgets.QMessageBox.warning(self, self.wizard.strings["app_title"], self.wizard.strings["license_reject"])
            return False
        return True

class DirectoryPage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        layout = QtWidgets.QVBoxLayout()
        self.info = QtWidgets.QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        h = QtWidgets.QHBoxLayout()
        self.edit = QtWidgets.QLineEdit()
        self.browse = QtWidgets.QPushButton()
        self.browse.clicked.connect(self.on_browse)
        h.addWidget(self.edit)
        h.addWidget(self.browse)
        layout.addLayout(h)
        self.setLayout(layout)

    def initializePage(self):
        s = self.wizard.strings
        self.setTitle(s["select_install_dir_title"])
        self.info.setText(s["select_install_dir_explain"])
        self.browse.setText(s["browse"])
        set_button_texts_for(self.wizard)

        detected = auto_detect_directory()
        if detected:
            if QtWidgets.QMessageBox.question(
                self, s["app_title"],
                s["confirm_path"].format(detected),
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            ) == QtWidgets.QMessageBox.StandardButton.Yes:
                self.edit.setText(detected)
        else:
            QtWidgets.QMessageBox.information(self, s["app_title"], s["not_detected"])

    def on_browse(self):
        s = self.wizard.strings
        d = QtWidgets.QFileDialog.getExistingDirectory(self, s["select_directory"])
        if d:
            self.edit.setText(d)

    def validatePage(self):
        s = self.wizard.strings
        if not self.edit.text():
            QtWidgets.QMessageBox.warning(self, s["app_title"], s["select_directory"])
            return False
        self.wizard.install_dir = self.edit.text().strip()
        return True

class VersionPage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        layout = QtWidgets.QVBoxLayout()
        self.prompt = QtWidgets.QLabel()
        self.prompt.setWordWrap(True)
        self.cb_with = QtWidgets.QCheckBox()
        self.cb_without = QtWidgets.QCheckBox()
        self.desc1 = QtWidgets.QLabel()
        self.desc1.setWordWrap(True)
        self.desc2 = QtWidgets.QLabel()
        self.desc2.setWordWrap(True)
        self.explain = QtWidgets.QLabel()
        self.explain.setWordWrap(True)
        layout.addWidget(self.prompt)
        layout.addWidget(self.cb_with)
        layout.addWidget(self.desc1)
        layout.addWidget(self.cb_without)
        layout.addWidget(self.desc2)
        layout.addWidget(self.explain)
        self.setLayout(layout)

    def initializePage(self):
        s = self.wizard.strings
        self.setTitle(s["choose_version_title"])
        self.prompt.setText(s["choose_version"])
        self.cb_with.setText(s["with_context"])
        self.cb_without.setText(s["without_context"])
        self.desc1.setText(s["with_context_description"])
        self.desc2.setText(s["without_context_description"])
        self.explain.setText(s["version_explain"])
        selections = set(self.wizard.versions)
        self.cb_with.setChecked('with_context' in selections or not selections)
        self.cb_without.setChecked('without_context' in selections)
        set_button_texts_for(self.wizard)

    def validatePage(self):
        s = self.wizard.strings
        selections = []
        if self.cb_with.isChecked():
            selections.append('with_context')
        if self.cb_without.isChecked():
            selections.append('without_context')
        if not selections:
            QtWidgets.QMessageBox.warning(self, s["app_title"], s["version_select_warning"])
            return False
        self.wizard.versions = selections
        self.wizard.has_context_variant = ('with_context' in selections)
        return True

class ConfigPage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard

        self.intro = QtWidgets.QLabel()
        self.intro.setWordWrap(True)

        self.form = QtWidgets.QFormLayout()
        self.model_combo = QtWidgets.QComboBox()
        self.model_edit = QtWidgets.QLineEdit()
        self.api_edit = QtWidgets.QLineEdit()
        self.key_edit = QtWidgets.QLineEdit()
        self.key_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.small_model_cb = QtWidgets.QCheckBox()

        self.purchase_btn = QtWidgets.QPushButton()
        self.verify_btn = QtWidgets.QPushButton()
        self.skip_btn = QtWidgets.QPushButton()
        self.purchase_btn.clicked.connect(self.open_purchase_page)
        self.verify_btn.clicked.connect(self.verify)
        self.skip_btn.clicked.connect(self.on_skip)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.purchase_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.verify_btn)
        btn_row.addWidget(self.skip_btn)

        self.status = QtWidgets.QLabel("")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.intro)
        layout.addLayout(self.form)
        layout.addLayout(btn_row)
        layout.addWidget(self.status)
        self.setLayout(layout)

        self.purchase_link = ""
        self.skip = False
        self._empty_key_verified = False

    def initializePage(self):
        s = self.wizard.strings
        self.setTitle(s["config_title"])
        self.intro.setText(s["config_intro"])
        set_button_texts_for(self.wizard)

        while self.form.rowCount():
            self.form.removeRow(0)

        try:
            self.model_combo.currentTextChanged.disconnect(self.on_model_change)
        except TypeError:
            pass
        self.model_combo.clear()
        preset_names = [k for k in API_PROVIDERS.keys() if k != "__CUSTOM__"]
        self.model_combo.addItems(preset_names + ["Custom..."])
        self.model_combo.currentTextChanged.connect(self.on_model_change)

        self.form.addRow(s["config_model_preset"], self.model_combo)
        self.form.addRow(s["config_model"], self.model_edit)
        self.form.addRow(s["config_api"], self.api_edit)
        self.form.addRow(s["config_key"], self.key_edit)
        self.key_edit.setPlaceholderText(s["config_key_placeholder"])
        self.form.addRow(s["smallmodel_label"], self.small_model_cb)
        self.small_model_cb.setToolTip(s["smallmodel_hint"])
        self.small_model_cb.setChecked(self.wizard.small_model)

        self.purchase_btn.setText(s["purchase_button"])
        self.purchase_btn.setToolTip(s["purchase_hint"])
        self.verify_btn.setText(s["verify"])
        self.skip_btn.setText(s["skip"])

        stored_model = self.wizard.model or ""
        stored_api = self.wizard.api_base or ""
        stored_key = self.wizard.api_key or ""
        normalized_api = _normalize_api_url_for_config(stored_api)

        target_index = -1
        for idx, preset in enumerate(preset_names):
            provider = API_PROVIDERS.get(preset, API_PROVIDERS["__CUSTOM__"])
            provider_api = _normalize_api_url_for_config(provider.get("api_base", ""))
            if provider.get("model", "") == stored_model and provider_api == normalized_api:
                target_index = idx
                break
            if provider.get("allow_custom_model", False) and provider_api == normalized_api:
                target_index = idx

        self.model_combo.blockSignals(True)
        if target_index >= 0:
            self.model_combo.setCurrentIndex(target_index)
        else:
            custom_index = self.model_combo.count() - 1
            if custom_index < 0:
                custom_index = 0
            self.model_combo.setCurrentIndex(custom_index)
        self.model_combo.blockSignals(False)

        if target_index >= 0:
            current_text = self.model_combo.itemText(target_index)
            self.on_model_change(current_text, initializing=True)
            self.api_edit.setText(normalized_api)
            if stored_model:
                self.model_edit.setText(stored_model)
        else:
            self.on_model_change("Custom...", initializing=True)
            self.model_edit.setText(stored_model)
            self.api_edit.setText(normalized_api)

        self.key_edit.setText(stored_key)
        self.status.setText("")
        self.skip = False
        self._empty_key_verified = False

    def on_model_change(self, name, initializing=False):
        if name == "Custom...":
            self.model_edit.setReadOnly(False)
            self.api_edit.setReadOnly(False)
            if not initializing:
                self.model_edit.setText("")
                self.api_edit.setText("")
            self.purchase_link = ""
        else:
            provider = API_PROVIDERS.get(name, API_PROVIDERS["__CUSTOM__"])
            self.model_edit.setReadOnly(not provider.get("allow_custom_model", False))
            self.api_edit.setReadOnly(False)
            self.model_edit.setText(provider.get("model", ""))
            self.api_edit.setText(_normalize_api_url_for_config(provider.get("api_base", "")))
            self.purchase_link = provider.get("purchase_page", "")
        if not initializing:
            self.status.setText("")

    def open_purchase_page(self):
        if self.purchase_link:
            webbrowser.open(self.purchase_link)

    def verify(self):
        s = self.wizard.strings
        api_key = self.key_edit.text().strip()
        self.status.setText(s["verifying"])
        QtWidgets.QApplication.processEvents()
        if not api_key:
            ok, msg = verify_api_settings(
                self.model_edit.text().strip(),
                self.api_edit.text().strip(),
                "",
            )
            if ok:
                self._empty_key_verified = True
                self.status.setText(s["verify_empty_success"])
                return True
            self._empty_key_verified = False
            self.status.setText(s["verify_fail"].format(msg))
            return False
        ok, msg = verify_api_settings(
            self.model_edit.text().strip(),
            self.api_edit.text().strip(),
            api_key,
        )
        if ok:
            self._empty_key_verified = False
            self.status.setText(msg or s["verify_success"])
            return True
        else:
            self._empty_key_verified = False
            self.status.setText(s["verify_fail"].format(msg))
            return False

    def on_skip(self):
        self.skip = True
        self.wizard.next()

    def validatePage(self):
        self.wizard.model = self.model_edit.text().strip()
        self.wizard.api_base = _normalize_api_url_for_config(self.api_edit.text().strip())
        self.wizard.api_key = self.key_edit.text().strip()
        self.wizard.small_model = self.small_model_cb.isChecked()
        if self.skip:
            return True
        if not self.verify():
            return False
        if not self.wizard.api_key and self._empty_key_verified:
            self.wizard.api_key = "nullkey"
        return True

class DelayPage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        self.intro = QtWidgets.QLabel()
        self.intro.setWordWrap(True)
        self.intro.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.intro.setOpenExternalLinks(True)
        self.spin = QtWidgets.QSpinBox()
        self.spin.setRange(0, 60000)
        self.spin.setSuffix(" ms")
        self.form = QtWidgets.QFormLayout()
        self.form.addRow("", self.spin)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.intro)
        layout.addLayout(self.form)
        self.setLayout(layout)

    def initializePage(self):
        s = self.wizard.strings
        self.setTitle(s["delay_title"])
        self.intro.setText(s["delay_intro"])
        self.form.setItem(0, QtWidgets.QFormLayout.ItemRole.LabelRole, QtWidgets.QLabel(s["delay_label"]))
        self.spin.setValue(self.wizard.delay_ms)
        set_button_texts_for(self.wizard)

    def validatePage(self):
        self.wizard.delay_ms = self.spin.value()
        return True

class RetryPage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        self.intro = QtWidgets.QLabel()
        self.intro.setWordWrap(True)
        self.combo = QtWidgets.QComboBox()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.intro)
        layout.addWidget(self.combo)
        self.setLayout(layout)

    def initializePage(self):
        s = self.wizard.strings
        self.setTitle(s["retry_title"])
        self.intro.setText(s["retry_intro"])
        self.combo.clear()
        self.combo.addItem(s["retry_off"], 0)
        self.combo.addItem(s["retry_once"], 1)
        self.combo.addItem(s["retry_until"], 2)
        self.combo.addItem(s["retry_until_delay"], 3)
        self.combo.setCurrentIndex(self.wizard.retry_mode)
        set_button_texts_for(self.wizard)

    def validatePage(self):
        self.wizard.retry_mode = self.combo.currentIndex()
        return True

class HallucinationPage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        self.intro = QtWidgets.QLabel()
        self.intro.setWordWrap(True)
        self.checkbox = QtWidgets.QCheckBox()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.intro)
        layout.addWidget(self.checkbox)
        self.setLayout(layout)

    def initializePage(self):
        s = self.wizard.strings
        self.setTitle(s["hallucination_title"])
        self.intro.setText(s["hallucination_intro"])
        self.checkbox.setText(s["hallucination_label"])
        self.checkbox.setChecked(self.wizard.check_hallucination)
        set_button_texts_for(self.wizard)

    def validatePage(self):
        self.wizard.check_hallucination = self.checkbox.isChecked()
        return True

class ContextPage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        self.intro = QtWidgets.QLabel()
        self.intro.setWordWrap(True)
        self.count_label = QtWidgets.QLabel()
        self.count_spin = QtWidgets.QSpinBox()
        self.count_spin.setRange(0, 20)
        self.count_spin.setSingleStep(1)
        self.count_hint = QtWidgets.QLabel()
        self.count_hint.setWordWrap(True)
        self.cache_label = QtWidgets.QLabel()
        self.cache_combo = QtWidgets.QComboBox()
        self.cache_hint = QtWidgets.QLabel()
        self.cache_hint.setWordWrap(True)
        form = QtWidgets.QFormLayout()
        form.addRow(self.count_label, self.count_spin)
        form.addRow(self.cache_label, self.cache_combo)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.intro)
        layout.addLayout(form)
        layout.addWidget(self.count_hint)
        layout.addWidget(self.cache_hint)
        self.setLayout(layout)

    def initializePage(self):
        s = self.wizard.strings
        set_button_texts_for(self.wizard)
        if not self.wizard.has_context_variant:
            QtCore.QTimer.singleShot(0, self.wizard.next)
            return
        self.setTitle(s["context_title"])
        self.intro.setText(s["context_intro"])
        self.count_label.setText(s["context_count_label"])
        suffix = s.get("context_count_suffix", "")
        if suffix:
            self.count_spin.setSuffix(f" {suffix}")
        else:
            self.count_spin.setSuffix("")
        self.count_spin.setSpecialValueText(s.get("context_count_zero", "No context"))
        self.count_spin.setValue(int(self.wizard.context_subtitle_count))
        self.count_hint.setText(s["context_count_hint"])
        self.cache_label.setText(s["context_cache_label"])
        self.cache_combo.clear()
        self.cache_combo.addItem(s["context_cache_auto"], "auto")
        self.cache_combo.addItem(s["context_cache_off"], "off")
        cache_mode = getattr(self.wizard, "context_cache_mode", "off") or "off"
        cache_index = self.cache_combo.findData(cache_mode)
        if cache_index != -1:
            self.cache_combo.setCurrentIndex(cache_index)
        else:
            self.cache_combo.setCurrentIndex(1) # Default to Off
        self.cache_hint.setText(s["context_cache_hint"])

    def validatePage(self):
        if not self.wizard.has_context_variant:
            return True
        self.wizard.context_subtitle_count = self.count_spin.value()
        cache_data = self.cache_combo.currentData()
        if cache_data:
            self.wizard.context_cache_mode = cache_data
        return True

class DebugPage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        self.checkbox = QtWidgets.QCheckBox()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.checkbox)
        self.setLayout(layout)

    def initializePage(self):
        s = self.wizard.strings
        self.setTitle(s["debug_title"])
        self.checkbox.setText(s["debug_label"])
        self.checkbox.setChecked(self.wizard.debug_mode)
        set_button_texts_for(self.wizard)

    def validatePage(self):
        self.wizard.debug_mode = self.checkbox.isChecked()
        return True

class ProgressPage(QtWidgets.QWizardPage):
    class UIProxy(QtCore.QObject):
        answer = QtCore.pyqtSignal(object)
        def __init__(self, parent=None):
            super().__init__(parent)

    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        self.header = QtWidgets.QLabel()
        self.text = QtWidgets.QTextEdit()
        self.text.setReadOnly(True)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.header)
        layout.addWidget(self.text)
        self.setLayout(layout)
        self.thread = None
        self.proxy = ProgressPage.UIProxy(self)
        self.s = None

    def initializePage(self):
        s = self.wizard.strings
        self.s = s
        self.setTitle(s["install_progress_title"])
        self.header.setText(s["install_progress"])
        set_button_texts_for(self.wizard)

        self.text.clear()
        self.thread = InstallThread(
            self.wizard.install_dir,
            self.wizard.versions,
            os.path.dirname(os.path.abspath(__file__)),
            self.wizard.language,
            self.wizard.api_key,
            self.wizard.model,
            self.wizard.api_base,
            self.wizard.delay_ms,
            self.wizard.retry_mode,
            self.wizard.debug_mode,
            self.wizard.check_hallucination,
            self.wizard.context_subtitle_count,
            self.wizard.context_cache_mode,
            self.wizard.prompt_cache_retention,
            self.wizard.gemini_cached_content,
            self.wizard.small_model,
        )
        self.thread.progress.connect(self.append_text)
        self.thread.ask_file_exists.connect(self.on_ask_file_exists)
        self.thread.ask_yesno.connect(self.on_ask_yesno)
        self.thread.ask_text.connect(self.on_ask_text)
        self.proxy.answer.connect(self.thread.receive_answer)
        self.thread.start()

    @QtCore.pyqtSlot(str)
    def append_text(self, msg):
        self.text.append(msg)
        if msg == "DONE":
            self.wizard.next()

    @QtCore.pyqtSlot(str, str)
    def on_ask_file_exists(self, title, message):
        s = self.s
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        overwrite = box.addButton(s["overwrite"], QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        rename = box.addButton(s["rename"], QtWidgets.QMessageBox.ButtonRole.ActionRole)
        cancel = box.addButton(s["cancel"], QtWidgets.QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == overwrite:
            self.proxy.answer.emit("overwrite")
        elif box.clickedButton() == rename:
            self.proxy.answer.emit("rename")
        else:
            self.proxy.answer.emit(None)

    @QtCore.pyqtSlot(str, str)
    def on_ask_yesno(self, title, message):
        ret = QtWidgets.QMessageBox.question(
            self, title, message,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        self.proxy.answer.emit(ret == QtWidgets.QMessageBox.StandardButton.Yes)

    @QtCore.pyqtSlot(str, str)
    def on_ask_text(self, title, prompt):
        s = self.s
        while True:
            text, ok = QtWidgets.QInputDialog.getText(self, title, prompt)
            if not ok:
                self.proxy.answer.emit(None)
                return
            text = text.strip()
            if text:
                self.proxy.answer.emit(text)
                return
            QtWidgets.QMessageBox.warning(self, title, s["rename"])

class FinishPage(QtWidgets.QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self.wizard = wizard
        self.label = QtWidgets.QLabel()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def initializePage(self):
        s = self.wizard.strings
        self.setTitle(s["finish_title"])
        self.label.setText(s["installation_complete"])
        set_button_texts_for(self.wizard)

# ========= Wizard =========

class InstallerWizard(QtWidgets.QWizard):
    def __init__(self):
        super().__init__()
        self.language = 'en'
        self.strings = LANGUAGE_STRINGS[self.language]
        self.install_dir = ''
        self.versions = ['with_context']
        self.api_key = ''
        self.model = API_PROVIDERS["gpt-5-nano"]["model"]
        self.api_base = API_PROVIDERS["gpt-5-nano"]["api_base"]
        # Recommended default profile for highest cache hit probability on official OpenAI.
        self.delay_ms = 500
        self.retry_mode = 1
        self.debug_mode = False
        self.check_hallucination = False
        self.context_subtitle_count = 3
        self.context_cache_mode = "auto"
        self.prompt_cache_retention = "24h"
        self.gemini_cached_content = ""
        self.small_model = False
        self.has_context_variant = True

        self.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)
        set_wizard_button_texts(self)

        self.addPage(LanguagePage(self))
        self.addPage(WelcomePage(self))
        self.addPage(LicensePage(self))
        self.addPage(DirectoryPage(self))
        self.addPage(VersionPage(self))
        self.addPage(ConfigPage(self))
        self.addPage(DelayPage(self))
        self.addPage(RetryPage(self))
        self.addPage(HallucinationPage(self))
        self.addPage(ContextPage(self))
        self.addPage(DebugPage(self))
        self.addPage(ProgressPage(self))
        self.addPage(FinishPage(self))

# ========= main =========

def set_high_dpi_attrs_if_available():
    # Qt6 默认开启 HiDPI；仅当属性存在时设置，避免 AttributeError
    try:
        AA = QtCore.Qt.ApplicationAttribute
        if hasattr(AA, "AA_UseHighDpiPixmaps"):
            QtWidgets.QApplication.setAttribute(AA.AA_UseHighDpiPixmaps)
        if hasattr(AA, "AA_EnableHighDpiScaling"):
            QtWidgets.QApplication.setAttribute(AA.AA_EnableHighDpiScaling)
    except Exception:
        pass

def main():
    set_high_dpi_attrs_if_available()
    app = QtWidgets.QApplication(sys.argv)

    # 强制深色配色
    apply_fusion_dark_palette(app)

    if not is_admin():
        QtWidgets.QMessageBox.warning(None, LANGUAGE_STRINGS["en"]["app_title"], merge_bilingual("admin_required"))
        restart_as_admin()
        return
    wizard = InstallerWizard()
    wizard.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
