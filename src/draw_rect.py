#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
熱力圖標記繪製模組 (draw_rect.py)

用途：
    在熱力圖（imageA）和 Layout 圖（imageB）上繪製元器件的溫度標記，
    包括矩形邊框、元器件名稱文字、最高溫度三角形標記和溫度數值文字。
    實作智慧文字定位演算法，自動避免文字與文字之間的重疊。
    支援從 GlobalConfig 讀取自訂的顏色和字型大小設定。

在整個應用中的角色：
    - 被 editor_rect.py 呼叫，在 Canvas 畫面上繪製元器件標記
    - 被 main.py 呼叫，在匯出影像時繪製標記

關聯檔案：
    - editor_rect.py：呼叫 draw_canvas_item() 繪製標記
    - main.py：匯出影像時呼叫繪製函式
    - config.py：讀取顏色和字型設定
    - bean/canvas_rect_item.py：提供元器件資料

主要函式：
    - draw_triangle_and_text()：在影像上繪製三角形標記和溫度文字
    - draw_canvas_item()：在 tkinter Canvas 上繪製矩形框和名稱標籤
"""

import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont
import traceback
from config import GlobalConfig


OUTLINE_OFFSETS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

def _create_outline_texts(canvas, x, y, text, font, anchor="center", color="#000000"):
    """建立 4 個偏移黑色文字，形成描邊效果。回傳 outline_ids 列表。"""
    ids = []
    for dx, dy in OUTLINE_OFFSETS:
        oid = canvas.create_text(x + dx, y + dy, text=text, font=font, fill=color, anchor=anchor)
        ids.append(oid)
    return ids

def calc_temp_text_offset(direction, tri_half, temp_w, temp_h, gap=0):
    """根據方向計算溫度文字中心相對於三角形中心的偏移量 (dx, dy)。

    Args:
        direction (str): 方向代碼，可選 "TL", "T", "TR", "L", "R", "BL", "B", "BR"
        tri_half (float): 三角形半徑（從中心到邊緣的距離）
        temp_w (float): 溫度文字寬度
        temp_h (float): 溫度文字高度
        gap (int): 三角形與文字之間的間距（預設 1px）

    Returns:
        tuple: (dx, dy) 偏移量
    """
    x_off = tri_half + gap + temp_w / 2
    y_off = tri_half + gap + temp_h / 2
    offsets = {
        "TL": (-x_off, -y_off), "T": (0, -y_off), "TR": (x_off, -y_off),
        "L":  (-x_off, 0),                         "R":  (x_off, 0),
        "BL": (-x_off, y_off),  "B": (0, y_off),   "BR": (x_off, y_off),
    }
    return offsets.get(direction, (0, -y_off))  # 預設正上方

def draw_triangle_and_text(imageA, item, imageScale = 1, imageIndex = 0, size=8):
    """在影像上繪製三角形溫度標記和文字。

    在元器件最高溫度點的位置繪製一個倒三角形標記，
    並在三角形上方顯示溫度數值文字，在矩形框左上方顯示元器件名稱。
    顏色和字型大小從 GlobalConfig 中讀取。

    Args:
        imageA (numpy.ndarray): 輸入的影像（BGR 格式）
        item (dict): 元器件資料字典（含 x1, y1, x2, y2, cx, cy, max_temp, name）
        imageScale (float): 影像縮放比例（預設 1）
        imageIndex (int): 影像索引（0=熱力圖，1=Layout 圖）
        size (int): 三角形的邊長（預設 8）
    """

    imgWidth = imageA.shape[1]
    textScale = imgWidth / 1024
    size = size * textScale

    # 从配置中读取颜色
    config = GlobalConfig()
    if imageIndex == 0:
        # 热力图标记
        rect_color_hex = config.get("heat_rect_color", "#BCBCBC")
        name_color_hex = config.get("heat_name_color", "#FFFFFF")
        temp_color_hex = config.get("heat_temp_color", "#FF0000")
    else:
        # Layout图标记
        rect_color_hex = config.get("layout_rect_color", "#BCBCBC")
        name_color_hex = config.get("layout_name_color", "#FFFFFF")
        temp_color_hex = config.get("layout_temp_color", "#FF0000")

    # 两个canvas统一使用热力图的字体大小配置，确保文字大小完全一致
    name_font_size = config.get("heat_name_font_size", 12)
    temp_font_size = config.get("heat_temp_font_size", 10)

    # 转换十六进制颜色为RGB元组
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    rectColor = hex_to_rgb(rect_color_hex)
    textColor = hex_to_rgb(name_color_hex)
    tempColor = hex_to_rgb(temp_color_hex)
    shadowColor = (0, 0, 0)

    left, top, right, bottom, cx, cy, max_temp, name = item.get("x1"), item.get("y1"), item.get("x2"), item.get("y2"), item.get("cx"), item.get("cy"), item.get("max_temp"), item.get("name")
    left = int(left * imageScale)
    top = int(top * imageScale)
    right = int(right * imageScale)
    bottom = int(bottom * imageScale)
    cx = int(cx * imageScale)
    cy = int(cy * imageScale)

    cv2.rectangle(imageA, (left, top), (right, bottom), rectColor, 1, cv2.LINE_AA)  # 绿色框
    # 计算三角形的三个顶点
    center = (cx, cy)
    # 顶点1 (尖角)
    point1 = (center[0], center[1] - size // 2)
    # 顶点2 (左下角)
    point2 = (center[0] - size // 2, center[1] + size // 2)
    # 顶点3 (右下角)
    point3 = (center[0] + size // 2, center[1] + size // 2)
    
    # 将顶点连接成一个三角形
    pts = np.array([point1, point2, point3], np.int32)
    pts = pts.reshape((-1, 1, 2))

    # 绘制三角形
    cv2.fillPoly(imageA, [pts], color=tempColor)

        
    # 使用配置的字体大小
    name_font_scale = (name_font_size / 12.0) * 0.55 * textScale
    temp_font_scale = (temp_font_size / 10.0) * 0.55 * textScale
    
    # 名稱文字 4 方向描邊
    name_pos = (left, top - int(4*textScale))
    for odx, ody in OUTLINE_OFFSETS:
        cv2.putText(imageA, f'{name}', (name_pos[0] + odx, name_pos[1] + ody), cv2.FONT_HERSHEY_COMPLEX, name_font_scale, shadowColor, 1, cv2.LINE_AA)
    cv2.putText(imageA, f'{name}', name_pos, cv2.FONT_HERSHEY_COMPLEX, name_font_scale, textColor, 1, cv2.LINE_AA)

    # 根據方向計算溫度文字偏移
    direction = item.get("temp_text_dir", "T")
    temp_text = f'{max_temp}'
    (tw, th), _ = cv2.getTextSize(temp_text, cv2.FONT_HERSHEY_COMPLEX, temp_font_scale, 1)
    tri_half = size / 2
    dx, dy = calc_temp_text_offset(direction, tri_half, tw, th)
    # cv2 putText 使用左下角錨點，需從中心偏移轉換
    temp_x = int(cx + dx - tw / 2)
    temp_y = int(cy + dy + th / 2)

    # 溫度文字 4 方向描邊
    for odx, ody in OUTLINE_OFFSETS:
        cv2.putText(imageA, temp_text, (temp_x + odx, temp_y + ody), cv2.FONT_HERSHEY_COMPLEX, temp_font_scale, shadowColor, 1, cv2.LINE_AA)
    cv2.putText(imageA, temp_text, (temp_x, temp_y), cv2.FONT_HERSHEY_COMPLEX, temp_font_scale, tempColor, 1, cv2.LINE_AA)

    print("draw_triangle_and_text------->>> ", point1, point2, point3, cx, cy)


def draw_canvas_item(canvas, item, imageScale=1, offset=(0, 0), imageIndex=0, size=8, font_scale=None):
    """在 tkinter Canvas 上繪製元器件的矩形框、名稱標籤、三角形標記和溫度文字。

    Args:
        canvas (tk.Canvas): Tkinter Canvas 元件
        item (dict): 元器件資料字典（含 x1, y1, x2, y2, cx, cy, max_temp, name）
        imageScale (float): 縮放比例（預設 1）
        offset (tuple): 偏移量 (offset_x, offset_y)（預設 (0, 0)）
        imageIndex (int): 影像索引（0=熱力圖，1=Layout 圖）
        size (int): 三角形標記邊長（預設 8）
        font_scale (float): 字體縮放比例（預設 None，則自動從 imageScale 計算）

    Returns:
        tuple: (rectId, nameId, tempTextId, triangleId) Canvas 繪圖物件 ID
    """

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    # 提取 item 中的值并应用缩放
    left, top, right, bottom, cx, cy, max_temp, name = (
        item.get("x1"), item.get("y1"), item.get("x2"), item.get("y2"), 
        item.get("cx"), item.get("cy"), item.get("max_temp"), item.get("name")
    )

    # 验证所有坐标值都不是None
    if None in (left, top, right, bottom, cx, cy):
        print(f"错误：矩形框坐标包含None值: left={left}, top={top}, right={right}, bottom={bottom}, cx={cx}, cy={cy}")
        print(f"完整的item数据: {item}")
        raise ValueError(f"矩形框坐标不能为None")
    
    if imageScale is None:
        print(f"错误：imageScale为None")
        raise ValueError(f"imageScale不能为None")

    off_x, off_y = offset
    left = int(left * imageScale) + off_x
    top = int(top * imageScale) + off_y
    right = int(right * imageScale) + off_x
    bottom = int(bottom * imageScale) + off_y
    cx = int(cx * imageScale) + off_x
    cy = int(cy * imageScale) + off_y

    # 🔥 移除邊界檢查，允許矩形超出可視範圍
    # Canvas 會自動裁剪超出範圍的繪製，不需要手動修改座標
    # 這在縮放模式下特別重要，因為矩形可能部分超出可視範圍
    #
    # 註：之前的邊界檢查會導致在縮放模式下，當矩形部分超出邊界時
    # 座標被錯誤地裁剪，造成框線範圍變動的問題

    # 🔥 字體縮放：如果有傳入 font_scale 則使用，否則從 imageScale 計算
    # 在放大模式下，會傳入 font_scale=1.0 保持字體大小不變
    # 在正常模式下（font_scale=None），固定使用 imageScale 但確保一致性
    if font_scale is None:
        # 🔥 修正：在正常縮放模式下（imageScale < 1.0），固定使用 imageScale
        # 避免使用 max(0.7, imageScale) 導致不一致
        font_scale = imageScale

    # 🔥 三角形大小：與字體一樣，使用 font_scale 控制
    size = max(7, int(size * font_scale))

    # 从配置中读取颜色
    config = GlobalConfig()
    if imageIndex == 0:
        # 热力图标记
        rectColor = config.get("heat_rect_color", "#BCBCBC")
        textColor = config.get("heat_name_color", "#FFFFFF")
        tempColor = config.get("heat_temp_color", "#FF0000")
    else:
        # Layout图标记
        rectColor = config.get("layout_rect_color", "#BCBCBC")
        textColor = config.get("layout_name_color", "#FFFFFF")
        tempColor = config.get("layout_temp_color", "#FF0000")

    # 两个canvas统一使用热力图的字体大小配置，确保文字大小完全一致
    name_font_size = config.get("heat_name_font_size", 12)
    temp_font_size = config.get("heat_temp_font_size", 10)
    
    shadowColor = "#000000"  # 黑色

    # 绘制形状（矩形或圆形）
    shape = item.get("shape", "rectangle")  # 預設為矩形
    if shape == "circle":
        rectId = canvas.create_oval(left, top, right, bottom, outline=rectColor, width=2)
    else:
        rectId = canvas.create_rectangle(left, top, right, bottom, outline=rectColor, width=2)

    # 计算三角形的三个顶点
    point1 = (cx, cy - size // 2)  # 顶点1 (尖角)
    point2 = (cx - size // 2, cy + size // 2)  # 顶点2 (左下角)
    point3 = (cx + size // 2, cy + size // 2)  # 顶点3 (右下角)

    # 绘制三角形
    triangleId = canvas.create_polygon([point1, point2, point3], fill=tempColor, outline=tempColor, width=1)

    # 使用配置的字体大小
    name_font_size_scaled = int(name_font_size * font_scale)
    temp_font_size_scaled = int(temp_font_size * font_scale)
    print(f"draw_canvas_item: name_font={name_font_size}*{font_scale:.2f}={name_font_size_scaled}, temp_font={temp_font_size}*{font_scale:.2f}={temp_font_size_scaled}")

    # 先建立溫度描邊文字（在主文字下方），再建立主文字
    temp_font_tuple = ("Arial", temp_font_size_scaled)
    tempOutlineIds = _create_outline_texts(canvas, cx, cy, f'{max_temp}', temp_font_tuple)
    tempTextId = canvas.create_text(cx, cy, text=f'{max_temp}',
                       font=temp_font_tuple, fill=tempColor, anchor="center")

    # 根據方向計算溫度文字偏移
    direction = item.get("temp_text_dir", "T")
    temp_bbox = canvas.bbox(tempTextId)
    if temp_bbox:
        temp_w = temp_bbox[2] - temp_bbox[0]
        temp_h = temp_bbox[3] - temp_bbox[1]
        tri_half = size / 2
        dx, dy = calc_temp_text_offset(direction, tri_half, temp_w, temp_h)
        canvas.coords(tempTextId, cx + dx, cy + dy)
        # 同步移動描邊文字
        for oid, (odx, ody) in zip(tempOutlineIds, OUTLINE_OFFSETS):
            canvas.coords(oid, cx + dx + odx, cy + dy + ody)
    else:
        # fallback: 預設正上方
        canvas.coords(tempTextId, cx, cy - 16 * imageScale)
        for oid, (odx, ody) in zip(tempOutlineIds, OUTLINE_OFFSETS):
            canvas.coords(oid, cx + odx, cy - 16 * imageScale + ody)

    # 名称文字置中于矩形框上方外侧（anchor="s" 使文字底部對齊指定 Y 座標）
    name_center_x = (left + right) / 2  # 矩形框水平中心
    name_y = top - 3 * imageScale
    name_font_tuple = ("Arial", name_font_size_scaled, "bold")
    nameOutlineIds = _create_outline_texts(canvas, name_center_x, name_y, f'{name}', name_font_tuple, anchor="s")
    nameId = canvas.create_text(name_center_x, name_y, text=f'{name}',
                       font=name_font_tuple, fill=textColor, anchor="s")

    # 將描邊 ID 存入 item
    item["tempOutlineIds"] = tempOutlineIds
    item["nameOutlineIds"] = nameOutlineIds

    return rectId, triangleId, tempTextId, nameId


def update_canvas_item(canvas, item, imageScale=1):
    """更新 Canvas 上已存在的矩形標記位置和大小（用於縮放或拖曳後重繪）。

    Args:
        canvas (tk.Canvas): Tkinter Canvas 元件
        item (dict): 元器件資料字典（需含 rectId, nameId 等 Canvas 物件 ID）
        imageScale (float): 縮放比例
    """

    x1, y1, x2, y2, cx, cy, rectId, nameId, tempTextId, triangleId = (
        item.get("x1"), item.get("y1"), item.get("x2"), item.get("y2"), item.get("cx"), item.get("cy"), 
        item.get("rectId"), item.get("nameId"), item.get("tempTextId"), item.get("triangleId")
    )

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    x1 = int(x1 * imageScale)
    y1 = int(y1 * imageScale)
    x2 = min(canvas_width, int(x2 * imageScale))
    y2 = min(canvas_height, int(y2 * imageScale)) 
    cx = int(cx * imageScale)
    cy = int(cy * imageScale)
    size = 8  # 假设三角形大小为 100
    font_scale = max(0.7, imageScale)
    size = max(7, int(size * imageScale))

    # if(canvas_width < x2):
    # print("uuuuu -> ", x2, y2, imageScale)

    canvas.coords(rectId, x1, y1, x2, y2)

    # 名称文字置中于矩形框上方外侧
    name_center_x = (x1 + x2) / 2
    canvas.coords(nameId, name_center_x, y1 - 3 * imageScale)
    canvas.itemconfig(nameId, font=("Arial", int(28 * font_scale), "bold"))

    # 根據方向計算溫度文字偏移
    canvas.itemconfig(tempTextId, font=("Arial", int(14 * font_scale)))
    direction = item.get("temp_text_dir", "T")
    temp_bbox = canvas.bbox(tempTextId)
    if temp_bbox:
        temp_w = temp_bbox[2] - temp_bbox[0]
        temp_h = temp_bbox[3] - temp_bbox[1]
        tri_half = size / 2
        dx, dy = calc_temp_text_offset(direction, tri_half, temp_w, temp_h)
        canvas.coords(tempTextId, cx + dx, cy + dy)
    else:
        canvas.coords(tempTextId, cx, cy - 16 * imageScale)

    # 计算新的三角形三个顶点
    point1 = (cx, cy - size // 2)  # 顶点1 (尖角)
    point2 = (cx - size // 2, cy + size // 2)  # 顶点2 (左下角)
    point3 = (cx + size // 2, cy + size // 2)  # 顶点3 (右下角)
    canvas.coords(triangleId, point1, point2, point3)


def draw_points_on_canvas(canvas, points, radius_red=8, ring_width=2, scale_factor=1):
    """在 Canvas 上繪製對齊點的內外圓圈標記（白色外環 + 紅色內圓 + 編號文字）。

    参数:
    - canvas: Tkinter Canvas 对象。
    - points: 一组点，每个点为 (x, y) 坐标。
    - radius_red: 内圆半径。
    - ring_width: 外圆宽度。
    - scale_factor: 缩放系数，默认为 8，用于提高绘制精度。
    """
    # 获取 Canvas 的宽高
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    # 增加绘制精度（类似于原始图像的缩放）
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    index = 0
    for point in points:
        index += 1
        # 计算缩放后的点位置
        point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))

        # 绘制外圆（白色圆环）
        canvas.create_oval(
            point_resized[0] - radius_red_resized - ring_width_resized,  # 左上角 x 坐标
            point_resized[1] - radius_red_resized - ring_width_resized,  # 左上角 y 坐标
            point_resized[0] + radius_red_resized + ring_width_resized,  # 右下角 x 坐标
            point_resized[1] + radius_red_resized + ring_width_resized,  # 右下角 y 坐标
            fill="white",  # 填充白色
            outline="white"  # 边框颜色为白色
        )

        # 绘制内圆（红色圆）
        canvas.create_oval(
            point_resized[0] - radius_red_resized,  # 左上角 x 坐标
            point_resized[1] - radius_red_resized,  # 左上角 y 坐标
            point_resized[0] + radius_red_resized,  # 右下角 x 坐标
            point_resized[1] + radius_red_resized,  # 右下角 y 坐标
            fill="red",  # 填充红色
            outline="red"  # 边框颜色为红色
        )

        # 绘制文本
        if index:
            canvas.create_text(
                point_resized[0],  # x 坐标偏移
                point_resized[1],  # y 坐标偏移
                text=str(index),  # 显示的文本为点的索引
                font=("Arial", 12),  # 设置字体和大小
                fill="white"  # 文本颜色为白色
            )


def draw_numpy_image_item(imageA, mark_rect_A, imageScale=1, imageIndex=0, size=8):
    """在 NumPy 影像上繪製所有元器件標記（用於匯出影像）。

    遍歷 mark_rect_A 列表，為每個元器件繪製矩形框、名稱文字、
    三角形標記和溫度文字。使用智慧文字定位避免重疊。

    Args:
        imageA (numpy.ndarray): 輸入影像（BGR 格式，會被就地修改）
        mark_rect_A (list[dict]): 元器件標記資料列表
        imageScale (float): 縮放比例
        imageIndex (int): 影像索引（0=熱力圖，1=Layout 圖）
        size (int): 三角形標記邊長
    """
    imgWidth = imageA.shape[1]
    textScale = imgWidth / 1024
    size = size * textScale

    # 从配置中读取颜色
    config = GlobalConfig()
    if imageIndex == 0:
        # 热力图标记
        rect_color_hex = config.get("heat_rect_color", "#BCBCBC")
        name_color_hex = config.get("heat_name_color", "#FFFFFF")
        temp_color_hex = config.get("heat_temp_color", "#FF0000")
    else:
        # Layout图标记
        rect_color_hex = config.get("layout_rect_color", "#BCBCBC")
        name_color_hex = config.get("layout_name_color", "#FFFFFF")
        temp_color_hex = config.get("layout_temp_color", "#FF0000")

    # 两个canvas统一使用热力图的字体大小配置，确保文字大小完全一致
    name_font_size = config.get("heat_name_font_size", 12)
    temp_font_size = config.get("heat_temp_font_size", 10)

    # 转换十六进制颜色为RGB元组
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    rectColor = hex_to_rgb(rect_color_hex)
    textColor = hex_to_rgb(name_color_hex)
    tempColor = hex_to_rgb(temp_color_hex)
    shadowColor = (0, 0, 0)

    try:
        font = ImageFont.truetype("font/msyh.ttc", int(20 * textScale))
        print("Font loaded successfully.")
    except IOError as e:
        font = ImageFont.load_default()

    # 获取图像尺寸
    img_height, img_width = imageA.shape[:2]
    
    for item in mark_rect_A:
        # 获取 item 中的坐标和文本信息
        left, top, right, bottom, cx, cy, max_temp, name = item.get("x1"), item.get("y1"), item.get("x2"), item.get("y2"), item.get("cx"), item.get("cy"), item.get("max_temp"), item.get("name")
        left = int(left * imageScale)
        top = int(top * imageScale)
        right = int(right * imageScale)
        bottom = int(bottom * imageScale)
        cx = int(cx * imageScale)
        cy = int(cy * imageScale)

        # 对于Layout图，使用图像实际尺寸进行边界检查
        if imageIndex != 0:
            # 使用图像实际尺寸进行边界检查
            left = max(0, left)
            top = max(0, top)
            right = min(right, img_width)
            bottom = min(bottom, img_height)
            cx = max(0, min(cx, img_width - 1))
            cy = max(0, min(cy, img_height - 1))

        # 绘制矩形框
        cv2.rectangle(imageA, (left, top), (right, bottom), rectColor, 1, cv2.LINE_AA)

        # 计算三角形的三个顶点
        center = (cx, cy)
        point1 = (center[0], center[1] - size // 2)
        point2 = (center[0] - size // 2, center[1] + size // 2)
        point3 = (center[0] + size // 2, center[1] + size // 2)

        # 对于Layout图，检查三角形是否在边界内
        if imageIndex != 0:
            # 检查三角形顶点是否在边界内
            triangle_in_bounds = (
                0 <= point1[0] < img_width and 0 <= point1[1] < img_height and
                0 <= point2[0] < img_width and 0 <= point2[1] < img_height and
                0 <= point3[0] < img_width and 0 <= point3[1] < img_height
            )
            
            if not triangle_in_bounds:
                print(f"警告：三角形 {name} 超出Layout图边界，跳过绘制")
                # 跳过三角形绘制，但继续绘制文本
            else:
                # 将顶点连接成一个三角形
                pts = np.array([point1, point2, point3], np.int32)
                pts = pts.reshape((-1, 1, 2))
                # 绘制三角形
                cv2.fillPoly(imageA, [pts], color=tempColor)
        else:
            # 热力图直接绘制三角形
            pts = np.array([point1, point2, point3], np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.fillPoly(imageA, [pts], color=tempColor)

        # 使用 Pillow 绘制文本
        pil_image = Image.fromarray(cv2.cvtColor(imageA, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        # 使用配置的字体大小
        name_font_scale = (name_font_size / 12.0) * 20 * textScale
        temp_font_scale = (temp_font_size / 10.0) * 20 * textScale
        
        # 创建字体对象
        try:
            name_font = ImageFont.truetype("font/msyh.ttc", int(name_font_scale))
            temp_font = ImageFont.truetype("font/msyh.ttc", int(temp_font_scale))
        except IOError:
            name_font = ImageFont.load_default()
            temp_font = ImageFont.load_default()

        # 根據方向計算溫度文字偏移（PIL 使用左上角錨點）
        direction = item.get("temp_text_dir", "T")
        temp_text_str = str(max_temp)
        temp_bbox = draw.textbbox((0, 0), temp_text_str, font=temp_font)
        tw = temp_bbox[2] - temp_bbox[0]
        th = temp_bbox[3] - temp_bbox[1]
        tri_half = size / 2
        dx, dy = calc_temp_text_offset(direction, tri_half, tw, th)
        # 從中心偏移轉換為 PIL 左上角座標
        temp_text_x = int(cx + dx - tw / 2)
        temp_text_y = int(cy + dy - th / 2)

        # 对于Layout图，检查文本位置是否在边界内
        if imageIndex != 0:
            name_text_x = left
            name_text_y = top - int(name_font_scale) - int(4 * textScale)

            # 检查温度文本是否在边界内
            if 0 <= temp_text_x < img_width and 0 <= temp_text_y < img_height:
                # 溫度文字 4 方向描邊
                for odx, ody in OUTLINE_OFFSETS:
                    draw.text((temp_text_x + odx, temp_text_y + ody), temp_text_str, font=temp_font, fill=shadowColor)
                draw.text((temp_text_x, temp_text_y), temp_text_str, font=temp_font, fill=tempColor)
            else:
                print(f"警告：温度文本 {name} 超出Layout图边界，跳过绘制")

            # 检查名称文本是否在边界内
            if 0 <= name_text_x < img_width and 0 <= name_text_y < img_height:
                # 名稱文字 4 方向描邊
                for odx, ody in OUTLINE_OFFSETS:
                    draw.text((name_text_x + odx, name_text_y + ody), name, font=name_font, fill=shadowColor)
                draw.text((name_text_x, name_text_y), name, font=name_font, fill=textColor)
            else:
                print(f"警告：名称文本 {name} 超出Layout图边界，跳过绘制")
        else:
            # 热力图直接绘制文本 — 溫度文字 4 方向描邊
            for odx, ody in OUTLINE_OFFSETS:
                draw.text((temp_text_x + odx, temp_text_y + ody), temp_text_str, font=temp_font, fill=shadowColor)
            draw.text((temp_text_x, temp_text_y), temp_text_str, font=temp_font, fill=tempColor)
            # 名稱文字 4 方向描邊
            name_pos_x = left
            name_pos_y = top - int(name_font_scale) - int(4 * textScale)
            for odx, ody in OUTLINE_OFFSETS:
                draw.text((name_pos_x + odx, name_pos_y + ody), name, font=name_font, fill=shadowColor)
            draw.text((name_pos_x, name_pos_y), name, font=name_font, fill=textColor)

        # pil_image.show()  # 直接显示 PIL 图像

        # 将 PIL 图像转换回 OpenCV 图像
        imageA = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # print(f"Text position: ({cx - int(16 * textScale)}, {cy - int(10 * textScale)})")
    return imageA

# 调用示例：
# 假设你有一个图像 `imageA` 和一个 `max_value`，你可以像这样调用该函数：
# draw_triangle_and_text(imageA, a_x=100, a_y=100, max_value=50)
