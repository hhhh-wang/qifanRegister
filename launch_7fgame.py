import os
import subprocess
import sys
import ctypes
import time
import pyautogui
import ctypes
from ctypes import wintypes
import slide_solver
import uuid
import msvcrt
import tempfile
import random
import subprocess
# 让 pyautogui 更稳定（可按需修改）
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

def get_base_dir():
    """
    获取程序运行根目录：
    - 开发环境：py 文件所在目录
    - PyInstaller 打包后：exe 解包临时目录
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 环境
        return sys._MEIPASS
    else:
        # 普通 python 运行
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

PIC_DIR = os.path.join(BASE_DIR, "pic")
EXE_PATH  = r"D:\Game\7fgame\7FGame.exe"

PIC_DIR = os.path.join(BASE_DIR, "pic")

LOGIN_IMAGE = os.path.join(PIC_DIR, "login.png")
TONGYI_IMAGE = os.path.join(PIC_DIR, "tongyi.png")
WANCHENG_IMAGE = os.path.join(PIC_DIR, "wancheng.png")

USER_INPUT_IMAGE = os.path.join(PIC_DIR, "user_input.png")
PSD_INPUT_IMAGE = os.path.join(PIC_DIR, "psd_input.png")
CONFIRM_PSD_IMAGE = os.path.join(PIC_DIR, "psd_confirm.png")

NAME_IMAGE = os.path.join(PIC_DIR, "name.png")
ID_CARD_IMAGE = os.path.join(PIC_DIR, "id_card.png")

USERNAME_CHECK_IMAGE = os.path.join(PIC_DIR, "username_jianche.png")
CHUANGJIAN_IMAGE = os.path.join(PIC_DIR, "chuangjian.png")
WANCHENG_RENZHENG_IMAGE = os.path.join(PIC_DIR, "wancheng_renzheng.png")


def generate_uu_id(max_len=14):
    """
    生成 uu_id，最长 max_len 个字符
    规则：字母 + 数字（不含特殊符号）
    """
    raw = uuid.uuid4().hex  # 32 位
    return raw[:max_len]
# 新增全局账号密码与控件图片路径（请根据需要修改用户名/密码）
USERNAME = generate_uu_id(10)
PASSWORD = "a123123"

# 新增：真实姓名与身份证号（已由你提供）
NAME = "路庆峰"
ID_NUMBER = "410522197604129336"

LOCK_FILE = os.path.join(tempfile.gettempdir(), "7fgame.lock")


def is_qifan_running():
    try:
        out = subprocess.check_output("tasklist", shell=True, text=True, encoding="gbk")
        return "7fgame" in out.lower() or "起凡" in out
    except Exception:
        return False




def start_7fgame(wait: bool = False) -> subprocess.Popen:
    """
    启动 7FGame.exe 并返回 Popen 对象（如果使用 ShellExecute 提升则返回 None）。
    如果已在运行，则不重复启动。
    参数 wait=True 会在启动后阻塞直到进程结束（仅对 Popen 有效）。
    """
    lock = is_qifan_running()
    if not lock:
        print("7FGame.exe 已在运行，跳过启动。")
        sys.exit(0)

    cwd = os.path.dirname(EXE_PATH)
    try:
        # 使用 Popen 启动，设置 cwd 为 exe 所在目录
        proc = subprocess.Popen([EXE_PATH], cwd=cwd)
        #print(f"已启动 {exe_name} (pid={proc.pid})")
        # 启动后尝试等待并点击登录按钮（不阻塞进程本身）
        clicked = click_login_button()
        if clicked:
            # 等待界面稳定
            time.sleep(0.6)
            # 点击用户名输入框并输入账号
            click_and_type(USER_INPUT_IMAGE, USERNAME)
            time.sleep(0.2)
            # 点击密码输入框并输入密码（第一次）
            click_and_type(PSD_INPUT_IMAGE, PASSWORD)
            time.sleep(0.2)
            # 确认密码：点击确认密码输入框并输入密码（若无单独图片则回退到 PSD_INPUT_IMAGE）
            confirm_img = CONFIRM_PSD_IMAGE if os.path.isfile(CONFIRM_PSD_IMAGE) else PSD_INPUT_IMAGE
            if confirm_img == PSD_INPUT_IMAGE:
                print("未找到确认密码图片，使用密码输入框图片作为替代。")
            click_and_type(confirm_img, PASSWORD)
            time.sleep(0.2)
            # 点击同意（向左偏移 20 像素，按需调整）
            wait_and_click_image(TONGYI_IMAGE, offset_x=-40)
            time.sleep(0.2)
            # 点击完成
            wait_and_click_image(WANCHENG_IMAGE)

            # 等待并填写真实姓名与身份证号（如果页面出现对应输入框）
            # 先等待 name 输入框出现并输入名字
            time.sleep(0.4)
            click_and_type(NAME_IMAGE, NAME)
            time.sleep(0.2)
            # 再等待 id_card 输入框出现并输入身份证号
            click_and_type(ID_CARD_IMAGE, ID_NUMBER)
            time.sleep(0.2)
            # 点击“完成认证”按钮
            wait_and_click_image(WANCHENG_RENZHENG_IMAGE)
            time.sleep(1)

            # 滑动验证码
            print("开始处理滑动验证码...")
            hwnd = wait_for_main_window(proc.pid, timeout=5.0)
            slide_solver.solve_slider(hwnd)
            # ✅ 滑块完成后：等待用户名输入并创建
            time.sleep(0.5)
            after_slider_fill_username(USERNAME)


        if wait:
            proc.wait()
        return proc
    except OSError as e:
        # WinError 740: 需要提升（管理员权限）
        if getattr(e, "winerror", None) == 740:
            print("检测到需要提升权限，尝试以管理员身份启动...")
            # 先尝试通过 ShellExecuteEx 获取 pid
            pid = run_elevated_with_pid(EXE_PATH, cwd)
            if pid:
                print(f"已以管理员方式启动，pid={pid}。等待窗口创建...")
                hwnd = wait_for_main_window(pid, timeout=12.0)
                if hwnd:
                    print(f"找到启动窗口 hwnd={hwnd}，尝试置前并点击登录按钮...")
                    try:
                        ctypes.windll.user32.ShowWindow(hwnd, 5)
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                        time.sleep(0.12)
                    except Exception:
                        pass
                    click_login_button()
                    return None
                else:
                    print("未在超时内找到窗口，仍尝试查找登录按钮（基于屏幕截图）。")
                    click_login_button()
                    return None
            else:
                # 回退到原先的 run_elevated（无 pid）
                ok = run_elevated(EXE_PATH, cwd)
                if ok:
                    print("已使用提升权限启动程序（无法获取 pid）。")
                    click_login_button()
                    return None
                else:
                    raise RuntimeError("尝试以管理员身份启动失败。") from e
        raise

def after_slider_fill_username(username: str):
    print("等待用户名输入框出现...")

    # 1️⃣ 等待用户名检测输入框
    ok = wait_and_click_image(
        USERNAME_CHECK_IMAGE,
        timeout=15.0,
        confidence=0.8
    )
    if not ok:
        print("❌ 未检测到用户名输入框")
        return False

    time.sleep(0.15)

    user_name = generate_chinese_nickname()
    try:
        click_and_type(USERNAME_CHECK_IMAGE, user_name)
        pyautogui.keyDown('shift')
        print(f"已输入用户名：{user_name}")
        
        ok = wait_and_click_image(
            CHUANGJIAN_IMAGE,
            timeout=10.0,
            confidence=0.8
        )
        pyautogui.keyUp('shift')
    except Exception as e:
        print(f"❌ 输入用户名失败: {e}")
        return False

    print("🎉 创建流程完成")
    return True


def generate_chinese_nickname():
    """
    生成网名：
    4–5 个常见汉字 + 随机 4 位数字
    """
    # 常用、显示安全的汉字池（可自行扩展）
    chinese_chars = list(
        "风云星辰山海明月清风流光夜雨青白鹿 "
        "桃花长安浮生孤舟远行听海逐梦旅人森林"
        "小鹿星河漫游人旧梦南山晚风初雪"
    )

    # 去掉空格
    chinese_chars = [c for c in chinese_chars if c.strip()]

    name_len = random.choice([4, 5])
    name_part = ''.join(random.sample(chinese_chars, name_len))

    number_part = f"{random.randint(0, 9999):04d}"

    return name_part + number_part


def generate_uu_id(max_len=14):
    """
    生成 uu_id，最长 max_len 个字符
    规则：字母 + 数字（不含特殊符号）
    """
    raw = uuid.uuid4().hex  # 32 位
    return raw[:max_len]


def run_elevated(exe_path: str, cwd: str) -> bool:
    """
    使用 ShellExecuteW 的 'runas' 动作以提升权限启动程序（无法获得 pid）。
    返回 True 表示已成功调用。
    """
    try:
        hinst = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, None, cwd, 1)
        return int(hinst) > 32
    except Exception:
        return False

def run_elevated_with_pid(exe_path: str, cwd: str, timeout: float = 6.0):
    """
    使用 ShellExecuteEx 启动并尝试获取 hProcess -> PID，返回 pid 或 None。
    需要管理员确认弹窗；若用户拒绝或失败返回 None。
    """
    try:
        SEE_MASK_NOCLOSEPROCESS = 0x00000040
        class SHELLEXECUTEINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("fMask", ctypes.c_ulong),
                ("hwnd", ctypes.c_void_p),
                ("lpVerb", ctypes.c_wchar_p),
                ("lpFile", ctypes.c_wchar_p),
                ("lpParameters", ctypes.c_wchar_p),
                ("lpDirectory", ctypes.c_wchar_p),
                ("nShow", ctypes.c_int),
                ("hInstApp", ctypes.c_void_p),
                ("lpIDList", ctypes.c_void_p),
                ("lpClass", ctypes.c_wchar_p),
                ("hkeyClass", ctypes.c_void_p),
                ("dwHotKey", ctypes.c_ulong),
                ("hIcon", ctypes.c_void_p),
                ("hProcess", ctypes.c_void_p),
            ]
        info = SHELLEXECUTEINFO()
        info.cbSize = ctypes.sizeof(info)
        info.fMask = SEE_MASK_NOCLOSEPROCESS
        info.hwnd = None
        info.lpVerb = "runas"
        info.lpFile = exe_path
        info.lpParameters = None
        info.lpDirectory = cwd
        info.nShow = 1  # SW_SHOWNORMAL
        ok = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info))
        if not ok:
            return None
        hProcess = info.hProcess
        if not hProcess:
            return None
        GetProcessId = ctypes.windll.kernel32.GetProcessId
        pid = GetProcessId(hProcess)
        # 关闭进程句柄（不终止进程）
        try:
            ctypes.windll.kernel32.CloseHandle(hProcess)
        except Exception:
            pass
        return int(pid) if pid else Nonep
    except Exception:
        return None


def find_hwnds_for_pid(pid: int):
    """返回属于 pid 的可见窗口句柄列表（可能为空）。"""
    hwnds = []
    EnumWindows = ctypes.windll.user32.EnumWindows
    GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    GetWindowTextW = ctypes.windll.user32.GetWindowTextW

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, lParam):
        proc_id = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value == pid and IsWindowVisible(hwnd):
            # 可选：忽略无标题窗口
            buf = ctypes.create_unicode_buffer(512)
            GetWindowTextW(hwnd, buf, 512)
            if buf.value and len(buf.value.strip()) > 0:
                hwnds.append(hwnd)
        return True

    EnumWindows(_enum, 0)
    return hwnds


def wait_for_main_window(pid: int, timeout: float = 12.0, interval: float = 0.25):
    """轮询查找属于 pid 的主窗口，超时返回 None，否则返回第一个 hwnd。"""
    end = time.time() + timeout
    while time.time() < end:
        hs = find_hwnds_for_pid(pid)
        if hs:
            return hs[0]
        time.sleep(interval)
    return None


def click_login_button(image_path: str = LOGIN_IMAGE, timeout: float = 10.0, interval: float = 0.5, confidence: float = 0.8, initial_wait: float = 2.5) -> bool:
    if not os.path.isfile(image_path):
        print(f"登录图片不存在: {image_path}")
        return False

    print(f"启动后等待 {initial_wait} 秒再开始查找登录按钮...")
    time.sleep(initial_wait)

    end_time = time.time() + timeout
    print("开始查找登录按钮...")
    while time.time() < end_time:
        pos = None
        try:
            pos = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
        except Exception as e:
            print(f"使用 confidence 搜索时出错: {e}")
            try:
                pos = pyautogui.locateCenterOnScreen(image_path)
            except Exception as e2:
                print(f"不带 confidence 搜索也出错: {e2}")
                pos = None

        if pos:
            x, y = int(pos[0]), int(pos[1])
            print(f"找到登录按钮，目标位置 ({x}, {y})")

            # 尝试把位于该坐标的窗口置于前台（提高点击生效概率）
            try:
                pt = wintypes.POINT(int(x), int(y))
                hwnd = ctypes.windll.user32.WindowFromPoint(pt)
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 5)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    time.sleep(0.12)
            except Exception as e:
                print(f"尝试置前窗口时出错: {e}")

            # 仅做必要的移动并用 WinAPI 发起一次左键点击（去掉冗余可视化移动）
            try:
                ctypes.windll.user32.SetCursorPos(x, y)
                time.sleep(0.05)
                LEFTDOWN = 0x0002
                LEFTUP = 0x0004
                ctypes.windll.user32.mouse_event(LEFTDOWN, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(LEFTUP, 0, 0, 0, 0)
                print("已移动并点击目标位置。")
                return True
            except Exception as e:
                print(f"点击失败: {e}")
                return False

        time.sleep(interval)

    # 超时：保存屏幕截图以便调试
    debug_path = os.path.join(os.path.dirname(image_path), "debug_screenshot.png")
    try:
        pyautogui.screenshot(debug_path)
        print(f"超时，未找到登录按钮。已保存屏幕截图到: {debug_path}")
    except Exception as e:
        print(f"超时且保存屏幕截图失败: {e}")
    return False


def wait_and_click_image(image_path: str, timeout: float = 8.0, interval: float = 0.4, confidence: float = 0.8, offset_x: int = 0, offset_y: int = 0) -> bool:
    """等待图片出现，然后移动并用 WinAPI 点击一次。
    新增 offset_x/offset_y：在图片中心基础上偏移像素后点击（可为负数）。
    """
    if not os.path.isfile(image_path):
        print(f"缺少图片文件: {image_path}")
        return False
    end_time = time.time() + timeout
    while time.time() < end_time:
        pos = None
        try:
            pos = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
        except Exception as e:
            try:
                pos = pyautogui.locateCenterOnScreen(image_path)
            except Exception:
                pos = None
        if pos:
            x, y = int(pos[0]), int(pos[1])
            # 应用偏移并做边界保护
            x = max(0, x + int(offset_x))
            y = max(0, y + int(offset_y))
            try:
                ctypes.windll.user32.SetCursorPos(x, y)
                time.sleep(0.04)
                LEFTDOWN = 0x0002
                LEFTUP = 0x0004
                ctypes.windll.user32.mouse_event(LEFTDOWN, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(LEFTUP, 0, 0, 0, 0)
                print(f"已点击: {os.path.basename(image_path)} -> ({x},{y}) (offset_x={offset_x}, offset_y={offset_y})")
                return True
            except Exception as e:
                print(f"点击失败: {e}")
                return False
        time.sleep(interval)
    print(f"等待超时，未找到图片: {image_path}")
    return False


def click_and_type(image_path: str, text: str, timeout: float = 8.0) -> bool:
    """
    等待并点击指定图片，然后【统一通过剪贴板粘贴】输入文本，
    彻底绕过中文输入法 / IME 问题。
    """
    ok = wait_and_click_image(image_path, timeout=timeout)
    if not ok:
        return False

    time.sleep(0.12)

    # 先清空输入框（防止有残留）
    try:
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.press("backspace")
        time.sleep(0.05)
    except Exception:
        pass

    pasted = False

    # ✅ 优先：pyperclip
    try:
        import pyperclip
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        pasted = True
    except Exception:
        pasted = False

    # ✅ 兜底：tkinter 剪贴板（标准库）
    if not pasted:
        try:
            import tkinter as _tk
            r = _tk.Tk()
            r.withdraw()
            r.clipboard_clear()
            r.clipboard_append(text)
            r.update()  # 强制刷新剪贴板
            r.destroy()
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")
            pasted = True
        except Exception:
            pasted = False

    if pasted:
        print(f"✅ 已通过剪贴板粘贴文本（长度 {len(text)}）到: {os.path.basename(image_path)}")
        return True
    else:
        print("❌ 剪贴板粘贴失败")
        return False



def capture_window_by_hwnd(hwnd, save_dir=r"C:\Users\Administrator\Desktop"):
    """根据 hwnd 获取窗口矩形并截屏保存到 save_dir，返回保存路径或 None。"""
    try:
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        w, h = right - left, bottom - top
        if w <= 0 or h <= 0:
            print("窗口尺寸无效，无法截图")
            return None
        # 置前并短暂等待以确保截图内容可见
        try:
            ctypes.windll.user32.ShowWindow(hwnd, 5)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(0.12)
        except Exception:
            pass
        img = pyautogui.screenshot(region=(left, top, w, h))
        os.makedirs(save_dir, exist_ok=True)
        fname = f"window_capture_{int(time.time())}.png"
        path = os.path.join(save_dir, fname)
        img.save(path)
        print(f"已保存窗口截图: {path}")
        return path
    except Exception as e:
        print(f"窗口截图失败: {e}")
        return None


if __name__ == "__main__":
    # 命令行支持：python launch_7fgame.py [--wait]
    wait_flag = "--wait" in sys.argv
    start_7fgame(wait=wait_flag)