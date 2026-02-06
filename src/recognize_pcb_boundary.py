#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCB 邊界識別模組 (recognize_pcb_boundary.py)

用途：
    從 Layout 圖的色彩遮罩中找出 PCB 板的外輪廓邊界，
    並將邊界座標轉換到熱力圖座標系，然後將 tempA（溫度矩陣）
    中 PCB 邊界以外的區域歸零。這是元器件識別前的預處理步驟，
    確保只在 PCB 板範圍內搜尋元器件。

在整個應用中的角色：
    - 被 recognize_image.py 的 process_pcb_image() 呼叫
    - 在元器件自動識別前排除 PCB 板外的雜訊區域

關聯檔案：
    - recognize_image.py：呼叫本函式進行 PCB 邊界識別
    - color_range.py：提供 mask_boundary 色彩遮罩
    - point_transformer.py：B 圖座標轉換為 A 圖座標
"""

import cv2
import numpy as np


def recognize_pcb_boundary(mask_boundary, point_transformer, tempA):
    """識別 PCB 板的外輪廓邊界，並將 tempA 中 PCB 外的區域歸零。

    流程：
    1. 使用 OpenCV findContours 找出遮罩中的所有輪廓
    2. 取面積最大的輪廓作為 PCB 板邊界
    3. 取得外接矩形座標，透過 point_transformer 轉換到 A 圖座標系
    4. 建立邊界遮罩，將 tempA 中邊界外的像素值歸零

    Args:
        mask_boundary (numpy.ndarray): 二值化遮罩影像（255=PCB 基板區域）
        point_transformer (PointTransformer): B 圖 → A 圖座標轉換器
        tempA (numpy.ndarray): 溫度矩陣（2D 陣列，會被就地修改）

    Returns:
        numpy.ndarray: 更新後的溫度矩陣 tempA
    """
    
    # 5. 找到绿色区域的轮廓
    contours, _ = cv2.findContours(mask_boundary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 6. 找到最大的轮廓
    if contours:
        # 按轮廓面积从大到小排序，取最大轮廓
        largest_contour = max(contours, key=cv2.contourArea)

        print("recognize_pcb_boundary largest_contour -> ", largest_contour)
        
        # 获取最大的轮廓的外接矩形
        x1, y1, w, h = cv2.boundingRect(largest_contour)
        x2, y2 = x1 + w, y1 + h

        print("A recognize_pcb_boundary -> ", (x1, y1), (x2, y2))
        
        # 使用 point_transformer 将 B 坐标转换为 A 坐标
        a_boundry_x1, a_boundry_y1 = point_transformer.B2A(x1, y1)
        a_boundry_x2, a_boundry_y2 = point_transformer.B2A(x2, y2)

        print("B recognize_pcb_boundary -> ", (a_boundry_x1, a_boundry_y1), (a_boundry_x2, a_boundry_y2))
        
        # 进行坐标范围的限制，确保坐标在图像范围内
        a_boundry_x1 = np.clip(a_boundry_x1, 0, 1280 - 1)
        a_boundry_y1 = np.clip(a_boundry_y1, 0, 960 - 1)
        a_boundry_x2 = np.clip(a_boundry_x2, 0, 1280 - 1)
        a_boundry_y2 = np.clip(a_boundry_y2, 0, 960 - 1)

        print("C recognize_pcb_boundary -> ", (a_boundry_x1, a_boundry_y1), (a_boundry_x2, a_boundry_y2))

        # 1. 生成掩码：在矩形范围内为 True，外部为 False
        a_boundry_mask = np.zeros_like(tempA, dtype=bool)
        a_boundry_mask[a_boundry_y1:a_boundry_y2+1, a_boundry_x1:a_boundry_x2+1] = True

        # 2. 使用掩码，将 tempA 中不在矩形范围内的部分置为 0
        tempA[~a_boundry_mask] = 0
    
    return tempA
