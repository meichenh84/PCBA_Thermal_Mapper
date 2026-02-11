#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旋轉數學工具模組 (rotation_utils.py)

用途：
    提供矩形框逆時針旋轉所需的數學工具函式，包括：
    1. 計算旋轉後的矩形四頂點座標
    2. 單點繞中心旋轉
    3. 計算旋轉矩形的 8 個錨點位置
    4. 判斷點是否在多邊形內（射線法）
    5. 建立旋轉多邊形的布林遮罩（用於溫度查詢）

在整個應用中的角色：
    - 被 editor_rect.py 呼叫，用於旋轉矩形的互動操作（錨點、縮放、點擊偵測）
    - 被 draw_rect.py 呼叫，用於計算旋轉後的頂點座標以繪製 polygon
    - 被 load_tempA.py 呼叫，用於建立旋轉多邊形遮罩進行溫度查詢

關聯檔案：
    - editor_rect.py：旋轉互動操作
    - draw_rect.py：旋轉矩形繪製
    - load_tempA.py：旋轉區域溫度查詢
"""

import math
import numpy as np


def get_rotated_corners(geo_cx, geo_cy, half_w, half_h, angle_deg):
    """計算逆時針旋轉後的 4 個頂點座標。

    以 (geo_cx, geo_cy) 為旋轉中心，將未旋轉的矩形四角
    繞中心逆時針旋轉 angle_deg 度。

    螢幕座標系 Y 軸朝下，逆時針旋轉 = 負角度旋轉矩陣。

    Args:
        geo_cx (float): 矩形幾何中心 X
        geo_cy (float): 矩形幾何中心 Y
        half_w (float): 矩形半寬 (x2-x1)/2
        half_h (float): 矩形半高 (y2-y1)/2
        angle_deg (float): 逆時針旋轉角度（度）

    Returns:
        list[tuple]: 旋轉後的 4 個頂點 [(x,y), ...] 順序為 TL, TR, BR, BL
    """
    # 螢幕座標系 Y 朝下，逆時針旋轉對應負角度
    rad = -math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    # 未旋轉的 4 個頂點相對於中心的偏移（TL, TR, BR, BL）
    offsets = [
        (-half_w, -half_h),  # TL
        ( half_w, -half_h),  # TR
        ( half_w,  half_h),  # BR
        (-half_w,  half_h),  # BL
    ]

    corners = []
    for dx, dy in offsets:
        rx = cos_a * dx - sin_a * dy + geo_cx
        ry = sin_a * dx + cos_a * dy + geo_cy
        corners.append((rx, ry))

    return corners


def rotate_point(px, py, cx, cy, angle_deg):
    """將點 (px, py) 繞 (cx, cy) 逆時針旋轉 angle_deg 度。

    Args:
        px (float): 點的 X 座標
        py (float): 點的 Y 座標
        cx (float): 旋轉中心 X
        cy (float): 旋轉中心 Y
        angle_deg (float): 逆時針旋轉角度（度）

    Returns:
        tuple: 旋轉後的座標 (rx, ry)
    """
    rad = -math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    dx = px - cx
    dy = py - cy
    rx = cos_a * dx - sin_a * dy + cx
    ry = sin_a * dx + cos_a * dy + cy
    return (rx, ry)


def get_rotated_anchor_positions(geo_cx, geo_cy, half_w, half_h, angle_deg):
    """計算旋轉矩形的 8 個錨點位置（4 角 + 4 邊中點）。

    錨點順序與 editor_rect.py create_anchors 一致：
    0=TL, 1=TR, 2=BL, 3=BR, 4=左中, 5=右中, 6=上中, 7=下中

    Args:
        geo_cx (float): 幾何中心 X
        geo_cy (float): 幾何中心 Y
        half_w (float): 半寬
        half_h (float): 半高
        angle_deg (float): 逆時針旋轉角度（度）

    Returns:
        list[tuple]: 8 個錨點座標 [(x,y), ...]
    """
    rad = -math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    def _rot(dx, dy):
        rx = cos_a * dx - sin_a * dy + geo_cx
        ry = sin_a * dx + cos_a * dy + geo_cy
        return (rx, ry)

    # 順序：TL, TR, BL, BR, L-mid, R-mid, T-mid, B-mid
    return [
        _rot(-half_w, -half_h),  # 0: TL
        _rot( half_w, -half_h),  # 1: TR
        _rot(-half_w,  half_h),  # 2: BL
        _rot( half_w,  half_h),  # 3: BR
        _rot(-half_w,  0),       # 4: L-mid
        _rot( half_w,  0),       # 5: R-mid
        _rot( 0,      -half_h),  # 6: T-mid
        _rot( 0,       half_h),  # 7: B-mid
    ]


def corners_to_flat(corners):
    """將頂點列表轉為 tkinter polygon 所需的扁平座標列表。

    Args:
        corners (list[tuple]): [(x1,y1), (x2,y2), ...]

    Returns:
        list[float]: [x1, y1, x2, y2, ...]
    """
    flat = []
    for x, y in corners:
        flat.append(x)
        flat.append(y)
    return flat


def point_in_polygon(px, py, polygon_corners):
    """判斷點 (px, py) 是否在多邊形內（射線法）。

    Args:
        px (float): 點的 X 座標
        py (float): 點的 Y 座標
        polygon_corners (list[tuple]): 多邊形頂點列表 [(x,y), ...]

    Returns:
        bool: True 表示點在多邊形內
    """
    n = len(polygon_corners)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_corners[i]
        xj, yj = polygon_corners[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def create_polygon_mask(corners, shape_hw):
    """用 cv2.fillPoly 建立旋轉多邊形的布林遮罩。

    Args:
        corners (list[tuple]): 多邊形頂點座標（在溫度矩陣座標系中）
        shape_hw (tuple): 溫度矩陣的 (height, width)

    Returns:
        numpy.ndarray: 布林遮罩，True 表示在多邊形內
    """
    import cv2
    mask = np.zeros(shape_hw, dtype=np.uint8)
    pts = np.array(corners, dtype=np.int32).reshape((-1, 1, 2))
    cv2.fillPoly(mask, [pts], 1)
    return mask.astype(bool)
