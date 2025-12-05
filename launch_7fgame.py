import os
import subprocess
import sys
import ctypes
import time
import pyautogui
import ctypes
from ctypes import wintypes

# 让 pyautogui 更稳定（可按需修改）
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

EXE_PATH  = r"D:\Game\7fgame\7FGame.exe"
LOGIN_IMAGE = r"D:\workSoftware\codeSpace\AI\python\qifanRegister\pic\login.png"

# 新增全局账号密码与控件图片路径（请根据需要修改用户名/密码）
USERNAME = "your_username"
PASSWORD = "your_password"

USER_INPUT_IMAGE = r"D:\workSoftware\codeSpace\AI\python\qifanRegister\pic\user_input.png"
PSD_INPUT_IMAGE = r"D:\workSoftware\codeSpace\AI\python\qifanRegister\pic\psd_input.png"
CONFIRM_PSD_IMAGE = r"D:\workSoftware\codeSpace\AI\python\qifanRegister\pic\psd_confirm.png"

TONGYI_IMAGE    = r"D:\workSoftware\codeSpace\AI\python\qifanRegister\pic\tongyi.png"
WANCHENG_IMAGE  = r"D:\workSoftware\codeSpace\AI\python\qifanRegister\pic\wancheng.png"


def is_process_running(exe_name: str) -> bool:
    """通过 tasklist 检查是否已运行（Windows）。"""
    try:
        output = subprocess.check_output(["tasklist"], encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return exe_name.lower() in output.lower()


def run_elevated(exe_path: str, cwd: str) -> bool:
    """
    使用 ShellExecuteW 的 'runas' 动作以提升权限启动程序。
    返回 True 表示已成功调用（注意无法获得 Popen 对象）。
    """
    try:
        # SW_SHOWNORMAL = 1
        hinst = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, None, cwd, 1)
        return int(hinst) > 32
    except Exception:
        return False


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
    """等待并点击指定图片，然后输入文本（使用 pyautogui.write）。"""
    ok = wait_and_click_image(image_path, timeout=timeout)
    if not ok:
        return False
    time.sleep(0.12)
    try:
        pyautogui.write(text, interval=0.04)
        print(f"已输入文本（长度 {len(text)}）到: {os.path.basename(image_path)}")
        return True
    except Exception as e:
        print(f"输入文本失败: {e}")
        return False


def start_7fgame(wait: bool = False) -> subprocess.Popen:
    """
    启动 7FGame.exe 并返回 Popen 对象（如果使用 ShellExecute 提升则返回 None）。
    如果已在运行，则不重复启动。
    参数 wait=True 会在启动后阻塞直到进程结束（仅对 Popen 有效）。
    """
    if not os.path.isfile(EXE_PATH):
        raise FileNotFoundError(f"找不到可执行文件: {EXE_PATH}")

    exe_name = os.path.basename(EXE_PATH)
    if is_process_running(exe_name):
        print(f"{exe_name} 已在运行，跳过启动。")
        return None

    cwd = os.path.dirname(EXE_PATH)
    try:
        # 使用 Popen 启动，设置 cwd 为 exe 所在目录
        proc = subprocess.Popen([EXE_PATH], cwd=cwd)
        print(f"已启动 {exe_name} (pid={proc.pid})")
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
        if wait:
            proc.wait()
        return proc
    except OSError as e:
        # WinError 740: 需要提升（管理员权限）
        if getattr(e, "winerror", None) == 740:
            print("检测到需要提升权限，尝试以管理员身份启动...")
            ok = run_elevated(EXE_PATH, cwd)
            if ok:
                print("已使用提升权限启动程序（无法获取 pid）。")
                # 即使提升启动无法获取 pid，仍尝试等待并点击登录按钮
                click_login_button()
                return None
            else:
                raise RuntimeError("尝试以管理员身份启动失败。") from e
        raise


if __name__ == "__main__":
    # 命令行支持：python launch_7fgame.py [--wait]
    wait_flag = "--wait" in sys.argv
    start_7fgame(wait=wait_flag)