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
from logger import get_logger

log = get_logger("launch_7fgame")

# 让 pyautogui 更稳定(可按需修改)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

def get_base_dir():
    """
    获取程序运行根目录:
    - 开发环境:py 文件所在目录
    - PyInstaller 打包后:exe 解包临时目录
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 环境
        base_dir = sys._MEIPASS
        log.debug(f"运行环境: PyInstaller, BASE_DIR={base_dir}")
        return base_dir
    else:
        # 普通 python 运行
        base_dir = os.path.dirname(os.path.abspath(__file__))
        log.debug(f"运行环境: Python解释器, BASE_DIR={base_dir}")
        return base_dir

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
    生成 uu_id,最长 max_len 个字符
    规则:字母 + 数字(不含特殊符号)
    """
    raw = uuid.uuid4().hex  # 32 位
    uid = raw[:max_len]
    log.debug(f"生成 UUID: {uid}")
    return uid


# 新增全局账号密码与控件图片路径(请根据需要修改用户名/密码)
USERNAME = generate_uu_id(10)
PASSWORD = "a123123"

# 新增:真实姓名与身份证号(已由你提供)
NAME = "李文良"
ID_NUMBER = "532524196606022097"

LOCK_FILE = os.path.join(tempfile.gettempdir(), "7fgame.lock")

log.info(f"配置信息 - 用户名={USERNAME}, 姓名={NAME}, 身份证={ID_NUMBER[:6]}******")


def is_qifan_running():
    log.debug("检测起凡游戏是否正在运行")
    try:
        out = subprocess.check_output("tasklist", shell=True, text=True, encoding="gbk")
        running = "起凡" in out
        log.info(f"起凡游戏运行状态: {running}")
        return running
    except Exception as e:
        log.error("检测起凡进程失败", exc_info=True)
        return False



def start_7fgame(wait: bool = False) -> subprocess.Popen:
    """
    启动 7FGame.exe 并返回 Popen 对象(如果使用 ShellExecute 提升则返回 None)。
    如果已在运行,则不重复启动。
    参数 wait=True 会在启动后阻塞直到进程结束(仅对 Popen 有效)。
    """
    log.info("========== 开始启动起凡游戏平台 ==========")
    running  = is_qifan_running()
    if running:
        log.warning("7FGame.exe 已在运行,跳过启动")
        print("7FGame.exe 已在运行,跳过启动。")
        sys.exit(0)

    cwd = os.path.dirname(EXE_PATH)
    log.info(f"游戏路径: {EXE_PATH}")
    log.debug(f"工作目录: {cwd}")
    
    try:
        # 使用 Popen 启动,设置 cwd 为 exe 所在目录
        log.info("尝试启动游戏进程...")
        proc = subprocess.Popen([EXE_PATH], cwd=cwd)
        log.info(f"游戏进程已启动: pid={proc.pid}")
        
        log.info("等待并点击登录按钮(不阻塞进程本身)")
        clicked = click_login_button()
        
        if clicked:
            log.info("登录按钮已点击,开始自动填写流程")
            # 等待界面稳定
            time.sleep(0.6)
            
            # 点击用户名输入框并输入账号
            log.info("步骤 1: 输入用户名")
            click_and_type(USER_INPUT_IMAGE, USERNAME)
            time.sleep(0.2)
            
            # 点击密码输入框并输入密码(第一次)
            log.info("步骤 2: 输入密码")
            click_and_type(PSD_INPUT_IMAGE, PASSWORD)
            time.sleep(0.2)
            
            # 确认密码:点击确认密码输入框并输入密码(若无单独图片则回退到 PSD_INPUT_IMAGE)
            log.info("步骤 3: 确认密码")
            confirm_img = CONFIRM_PSD_IMAGE if os.path.isfile(CONFIRM_PSD_IMAGE) else PSD_INPUT_IMAGE
            if confirm_img == PSD_INPUT_IMAGE:
                log.warning("未找到确认密码图片,使用密码输入框图片作为替代")

            click_and_type(confirm_img, PASSWORD)
            time.sleep(0.2)
            
            # 点击同意(向左偏移 20 像素,按需调整)
            log.info("步骤 4: 点击同意按钮")
            wait_and_click_image(TONGYI_IMAGE, offset_x=-40)
            time.sleep(0.2)
            
            # 点击完成
            log.info("步骤 5: 点击完成按钮")
            wait_and_click_image(WANCHENG_IMAGE)

            # 等待并填写真实姓名与身份证号(如果页面出现对应输入框)
            # 先等待 name 输入框出现并输入名字
            log.info("步骤 6: 填写真实姓名")
            time.sleep(0.4)
            click_and_type(NAME_IMAGE, NAME)
            time.sleep(0.2)
            
            # 再等待 id_card 输入框出现并输入身份证号
            log.info("步骤 7: 填写身份证号")
            click_and_type(ID_CARD_IMAGE, ID_NUMBER)
            time.sleep(0.2)
            
            # 点击"完成认证"按钮
            log.info("步骤 8: 点击完成认证")
            wait_and_click_image(WANCHENG_RENZHENG_IMAGE)
            time.sleep(1)

            # 滑动验证码
            log.info("步骤 9: 处理滑动验证码")
            hwnd = wait_for_main_window(proc.pid, timeout=5.0)
            if hwnd:
                log.info(f"获取到主窗口句柄: {hwnd}")
                slide_result = slide_solver.solve_slider(hwnd)
                if slide_result:
                    log.info("✅ 滑动验证码通过")
                else:
                    log.error("❌ 滑动验证码失败")
            else:
                log.warning("未能获取主窗口句柄,跳过滑动验证")
            
            # ✅ 滑块完成后:等待用户名输入并创建
            log.info("步骤 10: 填写游戏用户名并创建")
            time.sleep(0.5)
            after_slider_fill_username(USERNAME)


        if wait:
            log.info("等待游戏进程结束...")
            proc.wait()
            log.info("游戏进程已结束")
        return proc
        
    except OSError as e:
        # WinError 740: 需要提升(管理员权限)
        if getattr(e, "winerror", None) == 740:
            log.warning("检测到需要提升权限(WinError 740),尝试以管理员身份启动...")
            print("检测到需要提升权限,尝试以管理员身份启动...")
            
            # 先尝试通过 ShellExecuteEx 获取 pid
            pid = run_elevated_with_pid(EXE_PATH, cwd)
            if pid:
                log.info(f"已以管理员方式启动,pid={pid},等待窗口创建...")
                print(f"已以管理员方式启动,pid={pid}。等待窗口创建...")
                hwnd = wait_for_main_window(pid, timeout=12.0)
                if hwnd:
                    log.info(f"找到启动窗口 hwnd={hwnd},尝试置前并点击登录按钮")
                    print(f"找到启动窗口 hwnd={hwnd},尝试置前并点击登录按钮...")
                    try:
                        ctypes.windll.user32.ShowWindow(hwnd, 5)
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                        time.sleep(0.12)
                    except Exception as ex:
                        log.warning(f"置前窗口失败: {ex}")
                    click_login_button()
                    return None
                else:
                    log.warning("未在超时内找到窗口,仍尝试查找登录按钮(基于屏幕截图)")
                    print("未在超时内找到窗口,仍尝试查找登录按钮(基于屏幕截图)。")
                    click_login_button()
                    return None
            else:
                # 回退到原先的 run_elevated(无 pid)
                log.warning("无法获取 pid,回退到原 run_elevated 方式")
                ok = run_elevated(EXE_PATH, cwd)
                if ok:
                    log.info("已使用提升权限启动程序(无法获取 pid)")
                    print("已使用提升权限启动程序(无法获取 pid)。")
                    click_login_button()
                    return None
                else:
                    log.error("尝试以管理员身份启动失败")
                    raise RuntimeError("尝试以管理员身份启动失败。") from e
        raise


def after_slider_fill_username(username: str):
    log.info("========== 滑块验证后填写用户名流程 ==========")
    print("等待用户名输入框出现...")

    # 1️⃣ 等待用户名检测输入框
    log.info("等待用户名输入框出现...")
    ok = wait_and_click_image(
        USERNAME_CHECK_IMAGE,
        timeout=15.0,
        confidence=0.8
    )
    if not ok:
        log.error("❌ 未检测到用户名输入框")
        print("❌ 未检测到用户名输入框")
        return False

    time.sleep(0.15)

    user_name = generate_chinese_nickname()
    log.info(f"生成的游戏昵称: {user_name}")
    
    try:
        click_and_type(USERNAME_CHECK_IMAGE, user_name)
        pyautogui.keyDown('shift')
        log.info(f"已输入游戏昵称: {user_name}")
        print(f"已输入用户名: {user_name}")
        
        log.info("等待创建按钮出现...")
        ok = wait_and_click_image(
            CHUANGJIAN_IMAGE,
            timeout=10.0,
            confidence=0.8
        )
        pyautogui.keyUp('shift')
        
        if ok:
            log.info("✅ 创建按钮已点击")
        else:
            log.warning("未找到创建按钮")
            
    except Exception as e:
        log.error(f"❌ 输入用户名失败: {e}", exc_info=True)
        print(f"❌ 输入用户名失败: {e}")
        return False

    log.info("🎉 创建流程完成")
    print("🎉 创建流程完成")
    return True


def generate_chinese_nickname():
    """
    生成网名:
    4—5 个常见汉字 + 随机 4 位数字
    """
    log.debug("生成中文昵称")
    # 常用、显示安全的汉字池(可自行扩展)
    chinese_chars = list(
        "风云星辰山海白武林月清风流光夜雨青白鹿 "
        "桃花长安浮生孤舟远行听海逐梦旅人森林"
        "牛马鹿星河漫游人旧梦南山晚风初雪"
    )

    # 去掉空格
    chinese_chars = [c for c in chinese_chars if c.strip()]

    name_len = random.choice([4, 5])
    name_part = ''.join(random.sample(chinese_chars, name_len))

    number_part = f"{random.randint(0, 9999):04d}"

    nickname = name_part + number_part
    log.debug(f"生成昵称: {nickname}")
    return nickname


def generate_uu_id(max_len=14):
    """
    生成 uu_id,最长 max_len 个字符
    规则:字母 + 数字(不含特殊符号)
    """
    raw = uuid.uuid4().hex  # 32 位
    return raw[:max_len]


def run_elevated(exe_path: str, cwd: str) -> bool:
    """
    使用 ShellExecuteW 的 'runas' 动作以提升权限启动程序(无法获得 pid)。
    返回 True 表示已成功调用。
    """
    log.info(f"尝试以管理员权限启动: {exe_path}")
    try:
        hinst = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, None, cwd, 1)
        success = int(hinst) > 32
        if success:
            log.info("ShellExecuteW 调用成功")
        else:
            log.warning(f"ShellExecuteW 返回值: {hinst}")
        return success
    except Exception as e:
        log.error(f"ShellExecuteW 调用失败: {e}", exc_info=True)
        return False


def run_elevated_with_pid(exe_path: str, cwd: str, timeout: float = 6.0):
    """
    使用 ShellExecuteEx 启动并尝试获取 hProcess -> PID,返回 pid 或 None。
    需要管理员确认弹窗;若用户拒绝或失败返回 None。
    """
    log.info(f"尝试使用 ShellExecuteEx 以管理员权限启动并获取 pid: {exe_path}")
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
            log.warning("ShellExecuteExW 调用失败")
            return None
            
        hProcess = info.hProcess
        if not hProcess:
            log.warning("未获取到 hProcess")
            return None
            
        GetProcessId = ctypes.windll.kernel32.GetProcessId
        pid = GetProcessId(hProcess)
        
        # 关闭进程句柄(不终止进程)
        try:
            ctypes.windll.kernel32.CloseHandle(hProcess)
        except Exception as e:
            log.warning(f"关闭进程句柄失败: {e}")
            
        if pid:
            log.info(f"成功获取进程 PID: {pid}")
        else:
            log.warning("GetProcessId 返回空值")
            
        return int(pid) if pid else None
        
    except Exception as e:
        log.error(f"ShellExecuteEx 失败: {e}", exc_info=True)
        return None


def find_hwnds_for_pid(pid: int):
    """返回属于 pid 的可见窗口句柄列表(可能为空)。"""
    log.debug(f"查找 PID {pid} 的可见窗口")
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
            # 可选:忽略无标题窗口
            buf = ctypes.create_unicode_buffer(512)
            GetWindowTextW(hwnd, buf, 512)
            if buf.value and len(buf.value.strip()) > 0:
                hwnds.append(hwnd)
                log.debug(f"找到窗口: hwnd={hwnd}, 标题={buf.value}")
        return True

    EnumWindows(_enum, 0)
    log.debug(f"找到 {len(hwnds)} 个窗口")
    return hwnds


def wait_for_main_window(pid: int, timeout: float = 12.0, interval: float = 0.25):
    """轮询查找属于 pid 的主窗口,超时返回 None,否则返回第一个 hwnd。"""
    log.info(f"等待主窗口出现: pid={pid}, timeout={timeout}s")
    end = time.time() + timeout
    attempt = 0
    while time.time() < end:
        attempt += 1
        hs = find_hwnds_for_pid(pid)
        if hs:
            log.info(f"第 {attempt} 次尝试: 找到主窗口 hwnd={hs[0]}")
            return hs[0]
        time.sleep(interval)
        if attempt % 10 == 0:
            log.debug(f"第 {attempt} 次尝试,仍未找到窗口")
    log.warning(f"超时 {timeout}s, 未找到主窗口")
    return None


def click_login_button(image_path: str = LOGIN_IMAGE, timeout: float = 10.0, interval: float = 0.5, confidence: float = 0.8, initial_wait: float = 2.5) -> bool:
    log.info(f"========== 查找并点击登录按钮 ==========")
    log.info(f"图片路径: {image_path}, 超时: {timeout}s, 置信度: {confidence}")
    
    if not os.path.isfile(image_path):
        log.error(f"登录图片不存在: {image_path}")
        print(f"登录图片不存在: {image_path}")
        return False

    log.info(f"启动后等待 {initial_wait} 秒再开始查找登录按钮...")
    print(f"启动后等待 {initial_wait} 秒再开始查找登录按钮...")
    time.sleep(initial_wait)

    end_time = time.time() + timeout
    log.info("开始查找登录按钮...")
    print("开始查找登录按钮...")
    
    attempt = 0
    while time.time() < end_time:
        attempt += 1
        pos = None
        try:
            pos = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
        except Exception as e:
            log.debug(f"第 {attempt} 次: 使用 confidence 搜索时出错: {e}")
            try:
                pos = pyautogui.locateCenterOnScreen(image_path)
            except Exception as e2:
                log.debug(f"第 {attempt} 次: 不带 confidence 搜索也出错: {e2}")
                pos = None

        if pos:
            x, y = int(pos[0]), int(pos[1])
            log.info(f"✅ 第 {attempt} 次尝试: 找到登录按钮,目标位置 ({x}, {y})")
            print(f"找到登录按钮,目标位置 ({x}, {y})")

            # 尝试把位于该坐标的窗口置于前台(提高点击生效概率)
            try:
                pt = wintypes.POINT(int(x), int(y))
                hwnd = ctypes.windll.user32.WindowFromPoint(pt)
                if hwnd:
                    log.debug(f"找到窗口句柄: {hwnd}, 尝试置前")
                    ctypes.windll.user32.ShowWindow(hwnd, 5)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    time.sleep(0.12)
            except Exception as e:
                log.warning(f"尝试置前窗口时出错: {e}")

            # 仅做必要的移动并用 WinAPI 发起一次左键点击(去掉冗余可视化移动)
            try:
                ctypes.windll.user32.SetCursorPos(x, y)
                time.sleep(0.05)
                LEFTDOWN = 0x0002
                LEFTUP = 0x0004
                ctypes.windll.user32.mouse_event(LEFTDOWN, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(LEFTUP, 0, 0, 0, 0)
                log.info("已移动并点击目标位置")
                print("已移动并点击目标位置。")
                return True
            except Exception as e:
                log.error(f"点击失败: {e}", exc_info=True)
                print(f"点击失败: {e}")
                return False

        if attempt % 5 == 0:
            log.debug(f"第 {attempt} 次尝试,未找到登录按钮")
        time.sleep(interval)

    # 超时:保存屏幕截图以便调试
    debug_path = os.path.join(os.path.dirname(image_path), "debug_screenshot.png")
    try:
        pyautogui.screenshot(debug_path)
        log.warning(f"超时,未找到登录按钮。已保存屏幕截图到: {debug_path}")
        print(f"超时,未找到登录按钮。已保存屏幕截图到: {debug_path}")
    except Exception as e:
        log.error(f"超时且保存屏幕截图失败: {e}")
        print(f"超时且保存屏幕截图失败: {e}")
    return False


def wait_and_click_image(image_path: str, timeout: float = 8.0, interval: float = 0.4, confidence: float = 0.8, offset_x: int = 0, offset_y: int = 0) -> bool:
    """等待图片出现,然后移动并用 WinAPI 点击一次。
    新增 offset_x/offset_y:在图片中心基础上偏移像素后点击(可为负数)。
    """
    log.info(f"等待并点击图片: {os.path.basename(image_path)}, offset=({offset_x}, {offset_y})")
    
    if not os.path.isfile(image_path):
        log.error(f"缺少图片文件: {image_path}")
        print(f"缺少图片文件: {image_path}")
        return False
        
    end_time = time.time() + timeout
    attempt = 0
    
    while time.time() < end_time:
        attempt += 1
        pos = None
        try:
            pos = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
        except Exception as e:
            log.debug(f"第 {attempt} 次: 使用 confidence 查找失败")
            try:
                pos = pyautogui.locateCenterOnScreen(image_path)
            except Exception:
                pos = None
                
        if pos:
            x, y = int(pos[0]), int(pos[1])
            # 应用偏移并做边界保护
            x = max(0, x + int(offset_x))
            y = max(0, y + int(offset_y))
            log.info(f"✅ 第 {attempt} 次: 找到图片,点击位置 ({x},{y})")
            
            try:
                ctypes.windll.user32.SetCursorPos(x, y)
                time.sleep(0.04)
                LEFTDOWN = 0x0002
                LEFTUP = 0x0004
                ctypes.windll.user32.mouse_event(LEFTDOWN, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(LEFTUP, 0, 0, 0, 0)
                log.info(f"已点击: {os.path.basename(image_path)} -> ({x},{y})")
                print(f"已点击: {os.path.basename(image_path)} -> ({x},{y}) (offset_x={offset_x}, offset_y={offset_y})")
                return True
            except Exception as e:
                log.error(f"点击失败: {e}", exc_info=True)
                print(f"点击失败: {e}")
                return False
                
        if attempt % 5 == 0:
            log.debug(f"第 {attempt} 次尝试,未找到图片")
        time.sleep(interval)
        
    log.warning(f"等待超时 {timeout}s, 未找到图片: {image_path}")
    print(f"等待超时,未找到图片: {image_path}")
    return False


def click_and_type(image_path: str, text: str, timeout: float = 8.0) -> bool:
    """
    等待并点击指定图片,然后【统一通过剪贴板粘贴】输入文本,
    彻底绕过中文输入法 / IME 问题。
    """
    log.info(f"点击并输入文本: 图片={os.path.basename(image_path)}, 文本长度={len(text)}")
    
    ok = wait_and_click_image(image_path, timeout=timeout)
    if not ok:
        log.error("未找到目标图片,无法输入文本")
        return False

    time.sleep(0.12)

    # 先清空输入框(防止有残留)
    try:
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.press("backspace")
        time.sleep(0.05)
        log.debug("已清空输入框")
    except Exception as e:
        log.warning(f"清空输入框失败: {e}")

    pasted = False

    # ✅ 优先: pyperclip
    try:
        import pyperclip
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        pasted = True
        log.info("✅ 已通过 pyperclip 粘贴文本")
    except Exception as e:
        log.debug(f"pyperclip 粘贴失败: {e}")
        pasted = False

    # ✅ 兜底: tkinter 剪贴板(标准库)
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
            log.info("✅ 已通过 tkinter 剪贴板粘贴文本")
        except Exception as e:
            log.error(f"tkinter 剪贴板粘贴失败: {e}", exc_info=True)
            pasted = False

    if pasted:
        log.info(f"✅ 已通过剪贴板粘贴文本(长度 {len(text)})到: {os.path.basename(image_path)}")
        print(f"✅ 已通过剪贴板粘贴文本(长度 {len(text)})到: {os.path.basename(image_path)}")
        return True
    else:
        log.error("❌ 剪贴板粘贴失败")
        print("❌ 剪贴板粘贴失败")
        return False



def capture_window_by_hwnd(hwnd, save_dir=r"C:\Users\Administrator\Desktop"):
    """根据 hwnd 获取窗口矩形并截屏保存到 save_dir,返回保存路径或 None。"""
    log.info(f"截取窗口: hwnd={hwnd}, 保存目录={save_dir}")
    try:
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        w, h = right - left, bottom - top
        
        if w <= 0 or h <= 0:
            log.warning("窗口尺寸无效,无法截图")
            print("窗口尺寸无效,无法截图")
            return None
            
        # 置前并短暂等待以确保截图内容可见
        try:
            ctypes.windll.user32.ShowWindow(hwnd, 5)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(0.12)
        except Exception as e:
            log.warning(f"置前窗口失败: {e}")
            
        img = pyautogui.screenshot(region=(left, top, w, h))
        os.makedirs(save_dir, exist_ok=True)
        fname = f"window_capture_{int(time.time())}.png"
        path = os.path.join(save_dir, fname)
        img.save(path)
        log.info(f"✅ 已保存窗口截图: {path}")
        print(f"已保存窗口截图: {path}")
        return path
    except Exception as e:
        log.error(f"窗口截图失败: {e}", exc_info=True)
        print(f"窗口截图失败: {e}")
        return None


if __name__ == "__main__":
    # 命令行支持: python launch_7fgame.py [--wait]
    wait_flag = "--wait" in sys.argv
    log.info(f"程序启动,参数: wait={wait_flag}")
    start_7fgame(wait=wait_flag)
    log.info("程序执行完毕")