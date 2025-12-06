import os
import time
import ctypes
import pyautogui
from ctypes import wintypes
from captcha_recognizer.slider import Slider

# -----------------------------
# 可配置路径
# -----------------------------
DEBUG_DIR = r"D:\workSoftware\codeSpace\AI\python\qifanRegister\slide_debug"
SLIDER_BUTTON_IMAGE = r"D:\workSoftware\codeSpace\AI\python\qifanRegister\pic\huadong_anniu.png"
# 你提供的刷新按钮路径（注意：如果你实际文件有扩展名，请确认）
SLIDER_REFRESH_BASE = r"D:\workSoftware\codeSpace\AI\python\qifanRegister\pic\huadong_shuaxin"

os.makedirs(DEBUG_DIR, exist_ok=True)


# ----------------------------------------------------------------------
# WinAPI / 工具函数
# ----------------------------------------------------------------------
def get_window_rect(hwnd):
    """获取窗口矩形 (left, top, width, height)"""
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    l, t, r, b = rect.left, rect.top, rect.right, rect.bottom
    return l, t, r - l, b - t


def screenshot_window(hwnd):
    """对窗口截图并返回 PIL Image 与窗口左上角坐标"""
    l, t, w, h = get_window_rect(hwnd)
    img = pyautogui.screenshot(region=(l, t, w, h))
    save_path = os.path.join(DEBUG_DIR, f"window_{int(time.time())}.png")
    try:
        img.save(save_path)
    except Exception:
        pass
    return img, (l, t, w, h)


def try_locate_image_variants(base_path, confidence=0.75):
    """
    尝试使用 base_path 本身、base_path + .png、base_path + .jpg 去 locateCenterOnScreen。
    返回找到的 (x,y) 或 None。
    """
    candidates = [base_path, base_path + ".png", base_path + ".jpg"]
    for p in candidates:
        if os.path.isfile(p):
            try:
                pos = pyautogui.locateCenterOnScreen(p, confidence=confidence)
            except Exception:
                try:
                    pos = pyautogui.locateCenterOnScreen(p)
                except Exception:
                    pos = None
            if pos:
                return int(pos.x), int(pos.y), p
    return None


def get_slider_button_pos():
    """从屏幕上查找滑块按钮位置（返回屏幕坐标和实际使用的图片路径）"""
    res = try_locate_image_variants(SLIDER_BUTTON_IMAGE, confidence=0.75)
    if res is None:
        return None
    x, y, used = res
    return x, y


def find_refresh_button_pos():
    """尝试找刷新按钮（返回屏幕坐标和图片路径），基于 SLIDER_REFRESH_BASE"""
    res = try_locate_image_variants(SLIDER_REFRESH_BASE, confidence=0.75)
    if res is None:
        return None
    x, y, used = res
    return x, y, used


def click_at(x, y):
    """使用 WinAPI 在屏幕坐标点击一次"""
    try:
        ctypes.windll.user32.SetCursorPos(int(x), int(y))
        time.sleep(0.06)
        LEFTDOWN = 0x0002
        LEFTUP = 0x0004
        ctypes.windll.user32.mouse_event(LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.03)
        ctypes.windll.user32.mouse_event(LEFTUP, 0, 0, 0, 0)
        return True
    except Exception:
        return False


def drag_slider(start_pos, distance):
    """按下滑块并平滑拖动到指定水平距离（不改变 Y）"""
    x, y = start_pos
    try:
        # 移到起点
        ctypes.windll.user32.SetCursorPos(x, y)
        time.sleep(0.08)
        # 按下左键
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)

        # 拖动分步模拟 (线性分段)
        steps = 80
        for i in range(steps):
            dx = int(distance * (i + 1) / steps)
            ctypes.windll.user32.SetCursorPos(x + dx, y)
            time.sleep(0.025 + (i % 5)*0.002)  # 微微变化的延迟，让轨迹更像人操作

        # 松开
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        return True
    except Exception:
        # 尝试确保松开
        try:
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        except Exception:
            pass
        return False


# ----------------------------------------------------------------------
# 主流程：滑动验证码处理（含重试）
# ----------------------------------------------------------------------
def solve_slider(hwnd, max_retries=5):
    """
    入口：
    - 对给定 hwnd 截图
    - 用 Slider 识别缺口
    - 找到屏幕上的滑块按钮
    - 计算偏移并拖动
    - 拖动后暂停 1s，若检测到刷新按钮（huadong_shuaxin），则点击并重试
    - 最多重试 max_retries 次
    返回 True/False
    """
    attempts = 0

    while attempts < max_retries:
        attempts += 1
        print(f"[滑动尝试] 第 {attempts} 次...")

        # 1) 窗口截图
        img, (left, top, w, h) = screenshot_window(hwnd)
        import numpy as np
        img_rgb = np.array(img)

        # 2) 识别缺口
        try:
            slider = Slider()
            box, conf = slider.identify(source=img_rgb, show=False)
        except Exception as e:
            print(f"Slider 识别出错: {e}")
            box = None
            conf = 0.0

        if box is None:
            print("❌ 未识别到缺口，无法继续本次尝试。")
            # 若未识别到缺口，保存截图用于调试并直接返回 False（或进行下一次尝试）
            debug_path = os.path.join(DEBUG_DIR, f"no_gap_{int(time.time())}.png")
            try:
                img.save(debug_path)
                print(f"已保存调试截图: {debug_path}")
            except Exception:
                pass
            # 在某些情况下可以等待并重试
            time.sleep(0.5)
            # 继续下一次尝试
            continue

        gap_x = int(box[0])  # 缺口左上角 x（相对于窗口左上）
        print(f"识别到缺口 (窗口内坐标): x={gap_x}, 置信度={conf:.2f}")

        # 3) 找滑块按钮（屏幕坐标）
        slider_btn = get_slider_button_pos()
        if slider_btn is None:
            print("❌ 未在屏幕上找到滑块按钮图片（huadong_anniu）。")
            # 保存截图，重试
            time.sleep(0.5)
            continue

        slider_screen_x, slider_screen_y = slider_btn
        print(f"滑块按钮屏幕坐标: ({slider_screen_x}, {slider_screen_y})")

        # 4) 计算缺口的屏幕 x 坐标
        gap_screen_x = left + gap_x

        # 5) 计算滑动距离
        distance = gap_screen_x - slider_screen_x  + 23  # 微调补偿
        print(f"计算出的滑动距离: {distance}px")

        if distance <= 0 or distance > 250:
            print("❌ 偏移量不合法（<=0 或 >250），跳过本次尝试。")
            time.sleep(0.3)
            continue

        # 6) 执行滑动
        ok = drag_slider((slider_screen_x, slider_screen_y), distance)
        if not ok:
            print("❌ 滑动操作发生错误（drag_slider 返回 False）。准备重试。")
            time.sleep(0.4)
            continue

        # 7) 等待 2 秒，检测是否出现刷新按钮（说明失败）
        time.sleep(2.0)
        refresh = find_refresh_button_pos()
        if refresh is None:
            # 未发现刷新按钮，视为成功
            print("✅ 未检测到刷新按钮，认为滑动已成功。")
            return True

        # 如果发现刷新按钮，点击刷新并重试
        try:
            rx, ry, used_img = refresh
            print(f"检测到刷新按钮（{used_img}），说明滑动失败。准备点击刷新并重试。")
            click_at(rx, ry)
            time.sleep(0.6)  # 等待页面刷新
            continue
        except Exception as e:
            print(f"刷新按钮点击失败: {e}. 将重试整个流程。")
            time.sleep(0.6)
            continue

    # 超出重试次数仍未成功
    print(f"❌ 已达到最大重试次数 ({max_retries})，仍未成功通过滑动验证码。")
    return False
