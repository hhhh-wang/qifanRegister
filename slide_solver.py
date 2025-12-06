import os
import time
import random
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple, List

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None 

from PIL import Image
import pyautogui

# 调试输出目录
DEBUG_DIR = r"D:\workSoftware\codeSpace\AI\python\qifanRegister\slide_debug"
os.makedirs(DEBUG_DIR, exist_ok=True)

# 滑动按钮图片路径
SLIDER_BUTTON_IMAGE = r"D:\workSoftware\codeSpace\AI\python\qifanRegister\pic\huadong_anniu.png"


def _save_debug_img(name: str, img):
    """保存调试图片"""
    if not DEBUG_DIR:
        return
    path = os.path.join(DEBUG_DIR, name)
    try:
        if isinstance(img, np.ndarray):
            cv2.imwrite(path, img)
        else:
            img.save(path)
    except Exception:
        try:
            img.convert("RGB").save(path)
        except Exception:
            pass


def get_window_rect_from_hwnd(hwnd) -> Optional[Tuple[int, int, int, int]]:
    """根据窗口句柄获取窗口矩形"""
    try:
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return rect.left, rect.top, rect.right, rect.bottom
    except Exception:
        return None


def load_image(path: str):
    """加载图片"""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    if cv2 is not None:
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        return img
    else:
        arr = np.array(Image.open(path).convert("RGB"))
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def cv2_from_pil(pil_img: Image.Image):
    """PIL Image 转 OpenCV 格式"""
    arr = np.array(pil_img)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def find_puzzle_box_cv(img) -> Optional[Tuple[int, int, int, int]]:
    """在截图中寻找白色边框的拼图框，返回相对于 img 左上角的 bbox (x,y,w,h)"""
    if cv2 is None:
        return None
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    # 强调亮色区域（白色边框）
    _, th = cv2.threshold(blur, 200, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=2)
    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cand = None
    max_area = 0
    for c in cnts:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        # 合理尺寸过滤
        if area < 1000 or cw < 80 or ch < 80:
            continue
        # 选择在上半部分或中上位置的候选（通常拼图区靠上）
        if y > h * 0.7:
            continue
        if area > max_area:
            max_area = area
            cand = (x, y, cw, ch)
    if cand:
        # 放大一点以包含内部
        x, y, cw, ch = cand
        pad_w = int(cw * 0.06)
        pad_h = int(ch * 0.06)
        x = max(0, x - pad_w)
        y = max(0, y - pad_h)
        cw = min(w - x, cw + pad_w * 2)
        ch = min(h - y, ch + pad_h * 2)
        return x, y, cw, ch
    return None


def extract_piece_template(crop_img) -> Optional[np.ndarray]:
    """尝试在裁切的 puzzle 区中找到左侧拼图块作为模板（返回 BGR 图像）"""
    if cv2 is None:
        return None
    h, w = crop_img.shape[:2]
    
    # 保存原始裁剪图用于调试
    _save_debug_img("crop_original.png", crop_img)
    
    # 策略1: 搜索左半区域（拼图块通常在左边）
    sub = crop_img[0:int(h * 0.7), 0:int(w * 0.6)]  # 扩大搜索区域
    _save_debug_img("crop_sub.png", sub)
    
    # 尝试多种颜色范围检测拼图块
    hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
    
    # 策略1: 黄色/橙色拼图块（常见）
    lower_yellow1 = np.array([15, 50, 50])
    upper_yellow1 = np.array([35, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow1, upper_yellow1)
    
    # 策略2: 更宽的黄色范围
    lower_yellow2 = np.array([10, 30, 100])
    upper_yellow2 = np.array([40, 255, 255])
    mask_yellow2 = cv2.inRange(hsv, lower_yellow2, upper_yellow2)
    
    # 策略3: 亮色物体（高亮度）
    _, mask_bright = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    
    # 策略4: 边缘检测
    edges = cv2.Canny(gray, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    # 尝试多个掩码
    masks_to_try = [
        ("yellow1", mask_yellow),
        ("yellow2", mask_yellow2),
        ("bright", mask_bright),
        ("edges", edges_closed),
    ]
    
    # 如果颜色检测有足够像素，优先使用颜色检测
    if cv2.countNonZero(mask_yellow) > 100:
        masks_to_try = [("yellow1", mask_yellow), ("yellow2", mask_yellow2)] + masks_to_try[2:]
    elif cv2.countNonZero(mask_yellow2) > 100:
        masks_to_try = [("yellow2", mask_yellow2)] + masks_to_try[2:]
    
    # 如果颜色检测都失败，使用边缘检测
    if cv2.countNonZero(mask_yellow) < 50 and cv2.countNonZero(mask_yellow2) < 50:
        # 使用自适应阈值
        th_adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                            cv2.THRESH_BINARY_INV, 11, 2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        th_adaptive = cv2.morphologyEx(th_adaptive, cv2.MORPH_CLOSE, kernel, iterations=1)
        masks_to_try.insert(0, ("adaptive", th_adaptive))
    
    best_template = None
    best_score = 0
    
    for mask_name, mask in masks_to_try:
        _save_debug_img(f"mask_{mask_name}.png", mask)
        
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
            
        # 按面积排序，选择中等大小轮廓
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
        
        for c in cnts:
            area = cv2.contourArea(c)
            # 调整面积范围，适应不同大小的拼图块
            if area < 200 or area > 30000:
                continue
            
            x, y, cw, ch = cv2.boundingRect(c)
            # 进一步过滤形状
            if cw < 15 or ch < 15:
                continue
            
            # 计算宽高比，拼图块通常不是极端细长
            aspect_ratio = float(cw) / max(1.0, ch)
            if aspect_ratio < 0.3 or aspect_ratio > 3.0:
                continue
            
            # 扩展边界以包含完整拼图块
            pad = 6
            sx = max(0, x - pad)
            sy = max(0, y - pad)
            ex = min(sub.shape[1], x + cw + pad)
            ey = min(sub.shape[0], y + ch + pad)
            
            tpl = sub[sy:ey, sx:ex].copy()
            if tpl.size == 0:
                continue
            
            # 计算模板质量分数（面积越大、位置越靠左越好）
            score = area * (1.0 - float(x) / sub.shape[1])  # 位置权重
            
            if score > best_score:
                best_score = score
                best_template = tpl
                print(f"找到候选模板 (方法={mask_name}, 面积={area}, x={x}, y={y}, 分数={score:.1f})")
    
    if best_template is not None:
        _save_debug_img("template.png", best_template)
        print(f"成功提取模板，尺寸: {best_template.shape[1]}x{best_template.shape[0]}")
        return best_template
    
    # 如果所有方法都失败，尝试在整个左半区域寻找最突出的物体
    print("常规方法失败，尝试备用策略...")
    
    # 备用策略：使用梯度检测突出物体
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
    gradient_magnitude = np.uint8(255 * gradient_magnitude / gradient_magnitude.max())
    
    _, th_grad = cv2.threshold(gradient_magnitude, 100, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    th_grad = cv2.morphologyEx(th_grad, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    _save_debug_img("gradient_mask.png", th_grad)
    
    cnts, _ = cv2.findContours(th_grad, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 300 or area > 25000:
            continue
        x, y, cw, ch = cv2.boundingRect(c)
        if cw < 15 or ch < 15:
            continue
        # 只考虑左半部分的轮廓
        if x > sub.shape[1] * 0.5:
            continue
        
        pad = 6
        sx = max(0, x - pad)
        sy = max(0, y - pad)
        ex = min(sub.shape[1], x + cw + pad)
        ey = min(sub.shape[0], y + ch + pad)
        tpl = sub[sy:ey, sx:ex].copy()
        if tpl.size == 0:
            continue
        _save_debug_img("template.png", tpl)
        print(f"使用备用策略提取模板，尺寸: {tpl.shape[1]}x{tpl.shape[0]}")
        return tpl
    
    print("所有方法都失败，无法提取拼图块模板")
    return None


def find_piece_position(crop_img) -> Optional[Tuple[int, int, int, int]]:
    """找到拼图块的位置，返回 (x, y, w, h) 相对于 crop"""
    if cv2 is None:
        return None
    h, w = crop_img.shape[:2]
    # 搜索左半区域
    sub = crop_img[0:int(h * 0.6), 0:int(w * 0.5)]
    hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
    
    # 黄色拼图块
    lower_yellow = np.array([15, 50, 50])
    upper_yellow = np.array([35, 255, 255])
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    # 如果颜色检测失败，尝试边缘检测
    if cv2.countNonZero(mask) < 100:
        gray = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=1)
        mask = th
    
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 400 or area > 20000:
            continue
        x, y, cw, ch = cv2.boundingRect(c)
        if cw < 18 or ch < 18:
            continue
        # 返回相对于 crop 的坐标
        return x, y, cw, ch
    return None


def find_hole_x_by_template(crop_img, tpl, piece_x: Optional[int] = None) -> Optional[int]:
    """在 crop_img 中用 tpl 的边缘做匹配，返回缺口中心 x（相对于 crop 左上）
    如果提供了 piece_x，则只在 piece_x 右侧搜索缺口
    """
    if cv2 is None:
        return None
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    tpl_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
    
    # 用边缘进行匹配以减少颜色影响
    edge = cv2.Canny(gray, 50, 150)
    edge_tpl = cv2.Canny(tpl_gray, 50, 150)
    
    # 保存调试
    _save_debug_img("edge.png", edge)
    _save_debug_img("edge_tpl.png", edge_tpl)
    
    # 如果知道拼图块位置，只在右侧搜索
    if piece_x is not None:
        # 创建掩码，排除拼图块区域和左侧区域
        mask = np.ones(edge.shape, dtype=np.uint8) * 255
        # 排除左侧和拼图块区域（留一些余量）
        exclude_right = piece_x + 100  # 拼图块右侧100像素内也排除
        mask[:, :exclude_right] = 0
        edge = cv2.bitwise_and(edge, edge, mask=mask)
    
    # 若模板比目标大或小，尝试金字塔多个尺度
    best = None
    best_x = None
    for scale in np.linspace(0.7, 1.2, 10):
        try:
            tpl_rs = cv2.resize(edge_tpl, (max(3, int(edge_tpl.shape[1] * scale)),
                                           max(3, int(edge_tpl.shape[0] * scale))))
            method = cv2.TM_CCOEFF_NORMED
            res = cv2.matchTemplate(edge, tpl_rs, method)
            
            # 如果知道拼图块位置，应用掩码
            if piece_x is not None:
                mask_res = np.zeros_like(res)
                mask_res[:, piece_x + 100:] = 255
                res = cv2.bitwise_and(res, res, mask=mask_res.astype(np.uint8))
            
            _, maxv, _, maxloc = cv2.minMaxLoc(res)
            if best is None or maxv > best[0]:
                best = (maxv, maxloc, tpl_rs.shape[::-1])  # (val, (x,y), (w,h))
                best_x = maxloc[0]
        except Exception:
            continue
    
    if not best:
        return None
    val, loc, (tw, th) = best
    bx = loc[0]
    # 缺口中心 x = bx + tw/2
    gap_x = int(bx + tw / 2)
    print(f"template match confidence={val:.3f}, gap_x={gap_x}, piece_x={piece_x}")
    
    # 验证：如果知道拼图块位置，缺口应该在拼图块右侧
    if piece_x is not None:
        if gap_x <= piece_x + 50:
            print(f"警告：缺口位置 {gap_x} 在拼图块 {piece_x} 左侧或太近，可能匹配错误")
            return None
        # 计算距离，验证合理性（通常在50-400像素之间）
        distance = gap_x - piece_x
        if distance < 30 or distance > 500:
            print(f"警告：缺口与拼图块距离 {distance} 不合理，可能匹配错误")
            return None
        print(f"缺口位置验证通过：距离={distance} 像素")
    
    # 降低置信度阈值，因为边缘匹配的置信度可能较低但仍然有效
    # 如果知道拼图块位置且位置合理，可以接受更低的置信度
    min_confidence = 0.1 if piece_x is not None else 0.15
    
    if val < min_confidence:
        print(f"模板匹配置信度 {val:.3f} 低于阈值 {min_confidence:.3f}")
        # 如果位置合理，即使置信度较低也接受
        if piece_x is not None and gap_x > piece_x + 50:
            distance = gap_x - piece_x
            if 30 <= distance <= 500:
                print(f"置信度较低但位置合理，接受匹配结果")
                return gap_x
        return None
    
    return gap_x


def find_slider_center(crop_img) -> Optional[Tuple[int, int]]:
    """在 crop_img 的下半部分寻找圆形滑块按钮中心（返回相对于 crop 的坐标）"""
    if cv2 is None:
        return None
    h, w = crop_img.shape[:2]
    lower = crop_img[int(h * 0.45):int(h * 0.85), :]
    gray = cv2.cvtColor(lower, cv2.COLOR_BGR2GRAY)
    blur = cv2.medianBlur(gray, 5)
    # HoughCircles 寻找圆
    try:
        circles = cv2.HoughCircles(blur, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
                                   param1=50, param2=24, minRadius=8, maxRadius=40)
        if circles is not None:
            circles = np.uint16(np.around(circles))
            # 取第一个
            x, y, r = circles[0][0]
            # 转回 crop 坐标
            return int(x), int(y + int(h * 0.45))
    except Exception:
        pass
    # 回退方法：找最大的近圆形轮廓
    gray2 = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray2, 120, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for c in cnts:
        x, y, cw, ch = cv2.boundingRect(c)
        if y < h * 0.4:
            continue
        area = cw * ch
        if area < 200 or area > h * w * 0.1:
            continue
        ratio = float(cw) / max(1.0, ch)
        if 0.6 < ratio < 1.6:
            best = (area, x + cw // 2, y + ch // 2)
            break
    if best:
        return int(best[1]), int(best[2])
    return None


def generate_track(distance: int) -> List[int]:
    """生成模拟人类滑动的轨迹"""
    if distance <= 0:
        return []
    duration = random.uniform(0.5, 0.95)
    steps = random.randint(28, 45)
    tracks = []
    prev = 0.0
    for i in range(1, steps + 1):
        t = i / steps
        # ease out cubic
        cur = distance * (1 - (1 - t) ** 3)
        move = cur - prev
        prev = cur
        tracks.append(int(round(move)))
    # 修正误差
    diff = distance - sum(tracks)
    if diff != 0:
        tracks.append(diff)
    # 随机抖动
    tracks = [t + random.randint(-1, 1) for t in tracks if t != 0]
    return tracks


def perform_slide_screen(start_x: int, start_y: int, track: List[int]) -> bool:
    """在屏幕坐标执行滑动轨迹"""
    try:
        pyautogui.moveTo(start_x, start_y)
        time.sleep(random.uniform(0.05, 0.12))
        pyautogui.mouseDown()
        cur_x, cur_y = start_x, start_y
        for dx in track:
            cur_x += dx
            y_jitter = random.randint(-2, 2)
            dur = max(0.01, random.uniform(0.008, 0.02))
            pyautogui.moveTo(cur_x, cur_y + y_jitter, duration=dur)
            time.sleep(random.uniform(0.002, 0.01))
        # 末尾微回拉再推
        back = random.randint(-6, -2)
        pyautogui.moveRel(back, random.randint(-2, 2), duration=0.06)
        time.sleep(0.03)
        pyautogui.moveRel(-back, random.randint(-1, 1), duration=0.08)
        time.sleep(0.03)
        pyautogui.mouseUp()
        return True
    except Exception as e:
        print("perform_slide_screen error:", e)
        try:
            pyautogui.mouseUp()
        except Exception:
            pass
        return False


def find_and_click_slider_button(timeout: float = 5.0, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
    """
    查找并点击滑动按钮，返回按钮的屏幕坐标 (x, y)
    如果找不到，返回 None
    """
    if not os.path.isfile(SLIDER_BUTTON_IMAGE):
        print(f"滑动按钮图片不存在: {SLIDER_BUTTON_IMAGE}")
        return None
    
    print("正在查找滑动按钮...")
    end_time = time.time() + timeout
    while time.time() < end_time:
        pos = None
        try:
            pos = pyautogui.locateCenterOnScreen(SLIDER_BUTTON_IMAGE, confidence=confidence)
        except Exception as e:
            try:
                pos = pyautogui.locateCenterOnScreen(SLIDER_BUTTON_IMAGE)
            except Exception:
                pos = None
        
        if pos:
            x, y = int(pos[0]), int(pos[1])
            try:
                # 移动鼠标到按钮位置
                ctypes.windll.user32.SetCursorPos(x, y)
                time.sleep(0.05)
                # 点击按钮
                LEFTDOWN = 0x0002
                LEFTUP = 0x0004
                ctypes.windll.user32.mouse_event(LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.02)
                ctypes.windll.user32.mouse_event(LEFTUP, 0, 0, 0, 0)
                print(f"已点击滑动按钮，位置: ({x}, {y})")
                time.sleep(0.3)  # 等待界面响应
                return (x, y)
            except Exception as e:
                print(f"点击滑动按钮失败: {e}")
                return None
        
        time.sleep(0.2)
    
    print(f"等待超时，未找到滑动按钮: {SLIDER_BUTTON_IMAGE}")
    return None


def find_slider_button_position(timeout: float = 5.0, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
    """
    查找滑动按钮的位置，返回按钮的屏幕坐标 (x, y)
    如果找不到，返回 None（不点击，只定位）
    """
    if not os.path.isfile(SLIDER_BUTTON_IMAGE):
        print(f"滑动按钮图片不存在: {SLIDER_BUTTON_IMAGE}")
        return None
    
    print("正在查找滑动按钮...")
    end_time = time.time() + timeout
    while time.time() < end_time:
        pos = None
        try:
            pos = pyautogui.locateCenterOnScreen(SLIDER_BUTTON_IMAGE, confidence=confidence)
        except Exception as e:
            try:
                pos = pyautogui.locateCenterOnScreen(SLIDER_BUTTON_IMAGE)
            except Exception:
                pos = None
        
        if pos:
            x, y = int(pos[0]), int(pos[1])
            print(f"找到滑动按钮，位置: ({x}, {y})")
            return (x, y)
        
        time.sleep(0.2)
    
    print(f"等待超时，未找到滑动按钮: {SLIDER_BUTTON_IMAGE}")
    return None


def perform_slide_from_button(button_x: int, button_y: int, target_x: int, target_y: Optional[int] = None) -> bool:
    """
    从滑动按钮位置按住鼠标，拖动到目标位置，然后释放
    button_x, button_y: 滑动按钮的屏幕坐标
    target_x, target_y: 目标位置（缺口位置）的屏幕坐标，如果 target_y 为 None，则使用 button_y
    """
    if target_y is None:
        target_y = button_y
    
    try:
        # 计算移动距离
        distance = target_x - button_x
        if distance <= 0:
            print(f"错误：目标位置 {target_x} 在按钮位置 {button_x} 左侧")
            return False
        
        print(f"从按钮位置 ({button_x}, {button_y}) 拖动到目标位置 ({target_x}, {target_y})，距离: {distance} 像素")
        
        # 移动到按钮位置
        pyautogui.moveTo(button_x, button_y)
        time.sleep(random.uniform(0.05, 0.12))
        
        # 按下鼠标左键（不释放）
        pyautogui.mouseDown()
        time.sleep(random.uniform(0.05, 0.1))
        
        # 生成拖动轨迹
        track = generate_track(int(distance))
        if len(track) == 0:
            print(f"错误：生成的轨迹为空，距离={distance}")
            pyautogui.mouseUp()
            return False
        
        print(f"生成拖动轨迹，总步数 {len(track)}，总和={sum(track)}")
        
        # 执行拖动
        cur_x, cur_y = button_x, button_y
        for dx in track:
            cur_x += dx
            y_jitter = random.randint(-2, 2)
            dur = max(0.01, random.uniform(0.008, 0.02))
            pyautogui.moveTo(cur_x, cur_y + y_jitter, duration=dur)
            time.sleep(random.uniform(0.002, 0.01))
        
        # 确保到达目标位置（修正误差）
        final_x = button_x + sum(track)
        if abs(final_x - target_x) > 2:
            # 微调到最后位置
            adjust = target_x - final_x
            pyautogui.moveRel(adjust, random.randint(-1, 1), duration=0.05)
            time.sleep(0.02)
        
        # 末尾微回拉再推（模拟人类行为）
        back = random.randint(-6, -2)
        pyautogui.moveRel(back, random.randint(-2, 2), duration=0.06)
        time.sleep(0.03)
        pyautogui.moveRel(-back, random.randint(-1, 1), duration=0.08)
        time.sleep(0.03)
        
        # 释放鼠标左键
        pyautogui.mouseUp()
        print("拖动完成，已释放鼠标")
        return True
    except Exception as e:
        print(f"perform_slide_from_button error: {e}")
        try:
            pyautogui.mouseUp()
        except Exception:
            pass
        return False


def auto_solve_window(window_path: Optional[str] = None, hwnd: Optional[int] = None) -> bool:
    """
    自动从窗口截图或图片路径中找到拼图、定位缺口并滑动。
    若提供 hwnd，会把图片内坐标转换为屏幕坐标并直接在窗口上操作；
    若只提供 window_path，会要求你手动提供 base_left/base_top（交互）。
    """
    if window_path is None and hwnd is None:
        print("需要 window_path 或 hwnd 其中之一。")
        return False

    if cv2 is None:
        print("警告：未检测到 OpenCV，功能受限。请安装 opencv-python 提升稳定性。")
        return False

    # 如果有 hwnd，优先根据 hwnd 直接截屏并覆盖 window_path
    if hwnd is not None:
        try:
            rect = get_window_rect_from_hwnd(hwnd)
            if rect is None:
                print("无法通过 hwnd 获取窗口矩形。")
                return False
            left, top, right, bottom = rect
            w = right - left
            h = bottom - top
            img = pyautogui.screenshot(region=(left, top, w, h))
            img_cv = cv2_from_pil(img.convert("RGB"))
            _save_debug_img("window_capture.png", img_cv)
            base_left, base_top = left, top
        except Exception as e:
            print("根据 hwnd 截图失败:", e)
            return False
    else:
        img_cv = load_image(window_path)
        base_left = None
        base_top = None
        _save_debug_img("window_capture.png", img_cv)

    # 找到 puzzle 区域
    bbox = find_puzzle_box_cv(img_cv)
    if not bbox:
        print("未能自动定位拼图区域，请手动裁切 gap/full 或把窗口截图发给我以便调整算法。")
        return False
    x, y, cw, ch = bbox
    crop = img_cv[y:y + ch, x:x + cw].copy()
    _save_debug_img("puzzle_crop.png", crop)

    # 先找到拼图块的位置
    piece_pos = find_piece_position(crop)
    piece_x = None
    if piece_pos:
        px, py, pw, ph = piece_pos
        piece_x = px + pw // 2  # 拼图块中心x
        print(f"找到拼图块位置: x={px}, y={py}, w={pw}, h={ph}, center_x={piece_x}")

    # 提取模板（用于匹配缺口）
    tpl = extract_piece_template(crop)
    if tpl is None:
        print("未能提取滑块小片模板，尝试手工提供模板或手动裁切。")
        return False

    # 定位缺口 x（相对 crop 左上），传入拼图块位置以排除错误匹配
    gap_x = find_hole_x_by_template(crop, tpl, piece_x=piece_x)
    if gap_x is None:
        print("模板匹配出缺口失败，尝试增大调试阈值或手动定位。")
        return False

    # 定位滑块中心（相对 crop）- 这个可能不需要了，因为我们从按钮位置开始拖动
    slider_center = find_slider_center(crop)
    if slider_center is None:
        print("未能检测到滑块按钮中心，将使用滑动按钮位置作为起始点")
        # 如果找不到滑块中心，可以继续，因为我们会从按钮位置开始
    else:
        sx, sy = slider_center
        print(f"检测到滑块中心位置: ({sx}, {sy})")

    # 将 crop 内 x 转换为屏幕坐标
    if base_left is None:
        # 交互输入 base 左上角
        try:
            base_left = int(input("请输入 window 截图在屏幕上的 left (px)：").strip())
            base_top = int(input("请输入 window 截图在屏幕上的 top (px)：").strip())
        except Exception:
            print("输入无效，退出。")
            return False

    gap_screen_x = base_left + x + gap_x
    gap_screen_y = base_top + y + (ch // 2)  # 使用拼图区域中心作为y坐标
    
    print(f"缺口屏幕坐标: ({gap_screen_x}, {gap_screen_y})")

    # 查找滑动按钮位置
    button_pos = find_slider_button_position(timeout=5.0)
    if button_pos is None:
        print("错误：未能找到滑动按钮，无法执行滑动")
        return False
    
    button_x, button_y = button_pos
    
    # 计算从按钮到缺口的距离（用于验证）
    distance = gap_screen_x - button_x
    print(f"计算移动距离: {distance} px (gap_screen_x={gap_screen_x}, button_x={button_x})")
    
    # 验证距离合理性
    if distance <= 0:
        print(f"错误：计算出的移动距离为负数或零 ({distance})，可能是定位错误")
        return False
    
    if distance > 500:
        print(f"警告：移动距离 {distance} 过大，可能定位错误")
        return False
    
    # 从按钮位置拖动到缺口位置
    print("开始执行滑动操作...")
    ok = perform_slide_from_button(button_x, button_y, gap_screen_x, gap_screen_y)
    time.sleep(0.8)
    return ok
