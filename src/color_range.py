#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
色彩範圍與遮罩處理模組 (color_range.py)

用途：
    定義各種顏色在 HSV 色彩空間中的數值範圍，並提供
    根據顏色範圍生成二值化遮罩（mask）的功能。
    主要用於在 Layout 圖（imageB）中識別綠色 PCB 基板區域，
    透過 HSV 色彩空間的閾值分割來區分元器件與基板。

在整個應用中的角色：
    - 提供 get_mask_boundary() 函式，被元器件邊界識別模組呼叫
    - 生成的遮罩用於判斷 Layout 圖上哪些區域是 PCB 基板（綠色）

關聯檔案：
    - recognize_component_boundary.py：使用 mask_boundary 判斷元器件邊界
    - recognize_pcb_boundary.py：使用 mask_boundary 判斷 PCB 邊界
    - main.py：透過上述模組間接使用本模組
"""

import numpy as np
import cv2

# ===== 各顏色在 HSV 色彩空間中的範圍定義 =====
# 格式：(H_min, S_min, V_min), (H_max, S_max, V_max)
# H: 色相 (0-180), S: 飽和度 (0-255), V: 明度 (0-255)
color_ranges = {
    "红色": ((0, 100, 100), (10, 255, 255)),      # 紅色的 HSV 範圍
    "绿色": ((40, 100, 100), (80, 255, 255)),      # 綠色的 HSV 範圍
    "蓝色": ((100, 100, 100), (140, 255, 255)),    # 藍色的 HSV 範圍
    "紫色": ((140, 100, 100), (160, 255, 255)),    # 紫色的 HSV 範圍
    "黑色": ((0, 0, 0), (180, 255, 50)),           # 黑色的 HSV 範圍
    "白色": ((0, 0, 200), (180, 25, 255)),         # 白色的 HSV 範圍
    "橙色": ((10, 100, 100), (25, 255, 255))       # 橙色的 HSV 範圍
}

# ===== 白色 HSV 範圍（用於 PCB 上白色絲印層識別） =====
lower_white = np.array([0, 0, 200])        # 白色下界
upper_white = np.array([180, 25, 255])     # 白色上界

# ===== 綠色 HSV 範圍（用於 PCB 綠色基板識別） =====
# 基本綠色範圍
lower_green = np.array([35, 100, 100])     # 綠色下界
upper_green = np.array([85, 255, 255])     # 綠色上界

# 淺綠色範圍（覆蓋較亮的 PCB 基板）
lower_green_1 = np.array([40, 100, 100])
upper_green_1 = np.array([80, 255, 255])

# 深綠色範圍（覆蓋較暗的 PCB 基板）
lower_green_2 = np.array([30, 50, 50])
upper_green_2 = np.array([90, 255, 255])

# 明亮綠色範圍（覆蓋高飽和度的 PCB 基板）
lower_green_3 = np.array([50, 150, 150])
upper_green_3 = np.array([70, 255, 255])


def get_mask_boundary(imageB):
    """根據 HSV 色彩範圍生成 PCB 基板區域的二值化遮罩。

    將輸入的 Layout 圖（imageB）轉換為 HSV 色彩空間，
    分別建立多個綠色範圍的遮罩，最後合併為一個整體遮罩。
    遮罩中像素值為 255 表示該位置為綠色基板區域，0 表示非基板區域。

    Args:
        imageB (numpy.ndarray): 輸入的 Layout 圖影像（BGR 格式的 NumPy 陣列）

    Returns:
        numpy.ndarray: 二值化遮罩影像，255=綠色基板區域，0=非基板區域

    Raises:
        ValueError: 當輸入影像為 None 時拋出
    """
    if imageB is None:
        raise ValueError("輸入的影像資料為空。")

    # 將 BGR 影像轉換為 HSV 色彩空間
    hsv_image = cv2.cvtColor(imageB, cv2.COLOR_BGR2HSV)

    # 分別建立各顏色範圍的遮罩
    mask_white = cv2.inRange(hsv_image, lower_white, upper_white)      # 白色遮罩（目前未使用）
    mask_green = cv2.inRange(hsv_image, lower_green, upper_green)      # 基本綠色遮罩
    mask_green1 = cv2.inRange(hsv_image, lower_green_1, upper_green_1) # 淺綠色遮罩
    mask_green2 = cv2.inRange(hsv_image, lower_green_2, upper_green_2) # 深綠色遮罩
    mask_green3 = cv2.inRange(hsv_image, lower_green_3, upper_green_3) # 明亮綠色遮罩

    # 將所有綠色遮罩做 OR 運算合併，形成完整的基板區域遮罩
    mask_boundary = mask_green | mask_green1 | mask_green2 | mask_green3
    return mask_boundary
