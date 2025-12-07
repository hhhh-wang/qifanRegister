import os
import time
import ctypes
import pyautogui
from ctypes import wintypes
from captcha_recognizer.slider import Slider
import random
import launch_7fgame
from logger import get_logger

log = get_logger("slide_solver")

BASE_DIR = launch_7fgame.get_base_dir()
PIC_DIR = os.path.join(BASE_DIR, "pic")
DEBUG_DIR = os.path.join(PIC_DIR, "slide_debug")

SLIDER_BUTTON_IMAGE = os.path.join(PIC_DIR, "huadong_anniu.png")
SLIDER_REFRESH_BASE = os.path.join(PIC_DIR, "huadong_shuaxin.png")


os.makedirs(DEBUG_DIR, exist_ok=True)


# ----------------------------------------------------------------------
# WinAPI / 工具函数
# ----------------------------------------------------------------------
def get_window_rect(hwnd):
    """获取窗口矩形 (left, top, width, height)"""
    log.debug(f"获取窗口矩形: hwnd={hwnd}")
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    l, t, r, b = rect.left, rect.top, rect.right, rect.bottom
    log.debug(f"窗口矩形: left={l}, top={t}, right={r}, bottom={b}")
    return l, t, r - l, b - t


def screenshot_window(hwnd):
    """对窗口截图并返回 PIL Image 与窗口左上角坐标"""
    log.info(f"开始截取窗口截图: hwnd={hwnd}")
    time.sleep(1)  # 给窗口稳定时间
    l, t, w, h = get_window_rect(hwnd)
    log.debug(f"截图区域: left={l}, top={t}, width={w}, height={h}")
    img = pyautogui.screenshot(region=(l, t, w, h))
    save_path = os.path.join(DEBUG_DIR, f"window_{int(time.time())}.png")
    try:
        img.save(save_path)
        log.debug(f"窗口截图已保存: {save_path}")
    except Exception as e:
        log.error(f"保存窗口截图失败: {e}")
    return img, (l, t, w, h)


def try_locate_image_variants(base_path, confidence=0.75):
    """
    尝试使用 base_path 本身、base_path + .png、base_path + .jpg 去 locateCenterOnScreen。
    返回找到的 (x,y) 或 None。
    """
    log.debug(f"尝试定位图片: {base_path}, confidence={confidence}")
    candidates = [base_path, base_path + ".png", base_path + ".jpg"]
    for p in candidates:
        if os.path.isfile(p):
            log.debug(f"尝试候选图片: {p}")
            try:
                pos = pyautogui.locateCenterOnScreen(p, confidence=confidence)
            except Exception as e:
                log.debug(f"带confidence定位失败: {e}")
                try:
                    pos = pyautogui.locateCenterOnScreen(p)
                except Exception as e2:
                    log.debug(f"不带confidence定位也失败: {e2}")
                    pos = None
            if pos:
                log.info(f"成功定位图片 {p}: x={int(pos.x)}, y={int(pos.y)}")
                return int(pos.x), int(pos.y), p
    log.warning(f"未能定位到图片: {base_path}")
    return None


def get_slider_button_pos():
    """从屏幕上查找滑块按钮位置(返回屏幕坐标和实际使用的图片路径)"""
    log.info("开始查找滑块按钮")
    res = try_locate_image_variants(SLIDER_BUTTON_IMAGE, confidence=0.75)
    if res is None:
        log.warning("未找到滑块按钮")
        return None
    x, y, used = res
    log.info(f"滑块按钮位置: ({x}, {y})")
    return x, y


def find_refresh_button_pos():
    """尝试找刷新按钮(返回屏幕坐标和图片路径),基于 SLIDER_REFRESH_BASE"""
    log.debug("查找刷新按钮")
    res = try_locate_image_variants(SLIDER_REFRESH_BASE, confidence=0.75)
    if res is None:
        log.debug("未找到刷新按钮")
        return None
    x, y, used = res
    log.info(f"找到刷新按钮: ({x}, {y}), 图片={used}")
    return x, y, used


def click_at(x, y):
    """使用 WinAPI 在屏幕坐标点击一次"""
    log.debug(f"点击坐标: ({x}, {y})")
    try:
        ctypes.windll.user32.SetCursorPos(int(x), int(y))
        time.sleep(0.06)
        LEFTDOWN = 0x0002
        LEFTUP = 0x0004
        ctypes.windll.user32.mouse_event(LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.03)
        ctypes.windll.user32.mouse_event(LEFTUP, 0, 0, 0, 0)
        log.debug("点击成功")
        return True
    except Exception as e:
        log.error(f"点击失败: {e}", exc_info=True)
        return False




def drag_slider(start_pos, distance):
    x, y = start_pos
    log.info(f"开始拖动滑块: 起始位置=({x}, {y}), 距离={distance}px")

    try:
        ctypes.windll.user32.SetCursorPos(x, y)
        time.sleep(0.1)

        # 左键按下
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
        log.debug("鼠标左键已按下")

        track = generate_track(distance)
        log.debug(f"生成轨迹: {len(track)} 个步骤, 总距离={sum(track)}px")

        curr_x, curr_y = x, y

        for i, dx in enumerate(track):
            dy = random.randint(-2, 2)  # 垂直抖动

            curr_x += dx
            curr_y += dy

            ctypes.windll.user32.SetCursorPos(curr_x, curr_y)

            # 速度抖动
            time.sleep(random.uniform(0.008, 0.02))
            
            if i % 10 == 0:
                log.debug(f"拖动进度: {i}/{len(track)}, 当前位置=({curr_x}, {curr_y})")

        # 松开左键
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        log.info("滑块拖动完成,已松开鼠标")
        return True

    except Exception as e:
        log.error(f"拖动滑块失败: {e}", exc_info=True)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        return False


def generate_track(distance):
    log.debug(f"生成拖动轨迹: 目标距离={distance}px")
    track = []
    current = 0
    mid = distance * 0.75
    t = 0.2
    v = 0

    while current < distance:
        if current < mid:
            a = random.uniform(1.5, 2.5)   # 加速
        else:
            a = random.uniform(-3.5, -2.0) # 减速

        v0 = v
        v = v0 + a * t
        move = v0 * t + 0.5 * a * t * t

        if move < 1:
            move = random.uniform(0.5, 1.2)

        current += move
        track.append(round(move))

    # 微调,确保精准
    offset = sum(track) - distance
    if offset != 0:
        track.append(-offset)
        log.debug(f"轨迹微调: offset={offset}")

    # 人类常见的回拉
    track.extend([-2, -1, 1])

    log.debug(f"轨迹生成完成: {len(track)} 步, 实际总距离={sum(track)}px")
    return track


# ----------------------------------------------------------------------
# 主流程:滑动验证码处理(含重试)
# ----------------------------------------------------------------------
def solve_slider(hwnd, max_retries=5):
    """
    入口:
    - 对给定 hwnd 截图
    - 用 Slider 识别缺口
    - 找到屏幕上的滑块按钮
    - 计算偏移并拖动
    - 拖动后暂停 1s,若检测到刷新按钮(huadong_shuaxin),则点击并重试
    - 最多重试 max_retries 次
    返回 True/False
    """
    log.info(f"开始解决滑动验证码: hwnd={hwnd}, 最大重试次数={max_retries}")
    try:

        attempts = 0

        while attempts < max_retries:
            attempts += 1
            log.info(f"========== 滑动尝试 第 {attempts}/{max_retries} 次 ==========")

            # 1) 窗口截图
            img, (left, top, w, h) = screenshot_window(hwnd)
            import numpy as np
            img_rgb = np.array(img)
            log.debug(f"截图尺寸: {img_rgb.shape}")

            # 2) 识别缺口
            try:
                log.info("开始识别滑块缺口")
                slider = Slider()
                box, conf = slider.identify(source=img_rgb, show=False)
                log.info(f"缺口识别完成: box={box}, confidence={conf:.3f}")
            except Exception as e:
                log.error(f"Slider 识别出错: {e}", exc_info=True)
                box = None
                conf = 0.0

            if box is None:
                log.warning("未识别到缺口,无法继续本次尝试")
                # 若未识别到缺口,保存截图用于调试并直接返回 False(或进行下一次尝试)
                debug_path = os.path.join(DEBUG_DIR, f"no_gap_{int(time.time())}.png")
                try:
                    img.save(debug_path)
                    log.info(f"已保存调试截图: {debug_path}")
                except Exception as e:
                    log.error(f"保存调试截图失败: {e}")
                # 在某些情况下可以等待并重试
                time.sleep(0.5)
                # 继续下一次尝试
                continue

            gap_x = int(box[0])  # 缺口左上角 x(相对于窗口左上)
            log.info(f"识别到缺口 (窗口内坐标): x={gap_x}, 置信度={conf:.2f}")

            # 3) 找滑块按钮(屏幕坐标)
            slider_btn = get_slider_button_pos()
            if slider_btn is None:
                log.warning("未在屏幕上找到滑块按钮图片(huadong_anniu)")
                # 保存截图,重试
                time.sleep(0.5)
                continue

            slider_screen_x, slider_screen_y = slider_btn
            log.info(f"滑块按钮屏幕坐标: ({slider_screen_x}, {slider_screen_y})")

            # 4) 计算缺口的屏幕 x 坐标
            gap_screen_x = left + gap_x
            log.debug(f"缺口屏幕 x 坐标: {gap_screen_x} (窗口left={left} + gap_x={gap_x})")

            # 5) 计算滑动距离
            distance = gap_screen_x - slider_screen_x  + 23  # 微调补偿
            log.info(f"计算出的滑动距离: {distance}px (补偿+23)")

            if distance <= 0 or distance > 250:
                log.warning(f"偏移量不合法(<=0 或 >250): {distance}px, 跳过本次尝试")
                rx, ry, used_img  = find_refresh_button_pos()
                click_at(rx, ry)
                time.sleep(0.6)  # 等待页面刷新
                continue

            # 6) 执行滑动
            ok = drag_slider((slider_screen_x, slider_screen_y), distance)
            if not ok:
                log.error("滑动操作发生错误(drag_slider 返回 False), 准备重试")
                time.sleep(0.4)
                continue

            # 7) 等待 2 秒,检测是否出现刷新按钮(说明失败)
            log.info("等待 2 秒检测验证结果...")
            time.sleep(2.0)
            refresh = find_refresh_button_pos()
            if refresh is None:
                # 未发现刷新按钮,视为成功
                log.info("✅ 未检测到刷新按钮,认为滑动已成功")
                return True

            # 如果发现刷新按钮,点击刷新并重试
            try:
                rx, ry, used_img = refresh
                log.warning(f"检测到刷新按钮({used_img}), 说明滑动失败, 准备点击刷新并重试")
                click_at(rx, ry)
                time.sleep(0.6)  # 等待页面刷新
                continue
            except Exception as e:
                log.error(f"刷新按钮点击失败: {e}, 将重试整个流程", exc_info=True)
                time.sleep(0.6)
                continue

        # 超出重试次数仍未成功
        log.error(f"❌ 已达到最大重试次数 ({max_retries}), 仍未成功通过滑动验证码")
        return False
    finally:
        #  无论成功 / 失败 / 异常,都走这里
        clear_debug_pngs()




def clear_debug_pngs():
    """删除 DEBUG_DIR 下所有 png 文件"""
    log.info("开始清理 DEBUG_DIR 下的 png 文件")
    try:
        if not os.path.isdir(DEBUG_DIR):
            log.debug(f"DEBUG_DIR 不存在: {DEBUG_DIR}")
            return

        count = 0
        for fname in os.listdir(DEBUG_DIR):
            if fname.lower().endswith(".png"):
                fpath = os.path.join(DEBUG_DIR, fname)
                try:
                    os.remove(fpath)
                    count += 1
                except Exception as e:
                    log.warning(f"删除文件失败 {fname}: {e}")
        log.info(f"🧹 DEBUG_DIR 下的 {count} 个 png 文件已清理")
    except Exception as e:
        log.error(f"清理 DEBUG_DIR 失败: {e}", exc_info=True)