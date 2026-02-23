#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元器件自動識別模組 (recognize_image.py)

用途：
    提供兩種自動識別 PCB 元器件的方法：
    1. yolo_process_pcb_image()：使用 YOLOv8 深度學習模型偵測 Layout 圖上的元器件
    2. process_pcb_image()：使用傳統影像處理方法（分塊搜尋最大溫度 + 色彩遮罩邊界識別）

    兩種方法都會回傳元器件在熱力圖（imageA）和 Layout 圖（imageB）上的
    矩形框座標、中心點座標和最高溫度值。

在整個應用中的角色：
    - 核心識別引擎，被 main.py 呼叫以自動偵測元器件位置
    - 將識別結果以字典列表回傳，供 editor_rect.py 繪製標記

關聯檔案：
    - main.py：呼叫本模組的識別函式
    - recognize_component_boundary.py：被 process_pcb_image() 呼叫以識別單一元器件邊界
    - recognize_pcb_boundary.py：被 process_pcb_image() 呼叫以排除 PCB 外的區域
    - point_transformer.py：座標轉換（A 圖 ↔ B 圖）
    - color_range.py：提供色彩遮罩
    - yolo_v8.py：YOLOv8 模型實例
    - load_tempA.py：溫度資料載入器
"""

import cv2
import numpy as np
import heapq
import math
import time
from recognize_component_boundary import recognize_component_boundary
from recognize_pcb_boundary import recognize_pcb_boundary
from point_transformer import PointTransformer
from color_range import get_mask_boundary
from load_tempA import TempLoader
# from yolo_v8 import YOLOv8Instance  # YOLO 模組已停用，整個 yolo_v8.py 已註解
from PIL import Image, ImageTk


def yolo_process_pcb_image(tempA, imageA, imageB, point_transformer, min_temp, max_temp, min_width, min_height, max_ratio, auto_reduce):
    """使用 YOLOv8 模型偵測 Layout 圖上的元器件並對應到熱力圖。

    流程：
    1. 使用 YOLOv8 偵測 imageB 上的元器件邊界框
    2. 透過 point_transformer 將邊界框座標從 B 圖轉換到 A 圖
    3. 在 tempA（溫度矩陣）中取得該區域的最高溫度
    4. 過濾不符合溫度範圍的元器件

    Args:
        tempA (numpy.ndarray): 溫度矩陣（2D 陣列）
        imageA (numpy.ndarray): 熱力圖影像（BGR 格式）
        imageB (numpy.ndarray): Layout 圖影像（BGR 格式）
        point_transformer (PointTransformer): A 圖 ↔ B 圖座標轉換器
        min_temp (float): 最低溫度閾值（低於此值的元器件不標記）
        max_temp (float): 最高溫度閾值（高於此值的元器件不標記）
        min_width (int): 最小寬度閾值（未使用）
        min_height (int): 最小高度閾值（未使用）
        max_ratio (float): 最大長寬比閾值（未使用）
        auto_reduce (float): 自動縮減係數（未使用）

    Returns:
        tuple: (rectA_arr, rectB_arr)
            - rectA_arr (list[dict]): 熱力圖上的元器件矩形框列表
            - rectB_arr (list[dict]): Layout 圖上的元器件矩形框列表
            - 每個字典包含 x1, y1, x2, y2, cx, cy, max_temp, name
    """
    # 检查point_transformer是否为None
    if point_transformer is None:
        print("错误：point_transformer为None，无法进行坐标转换")
        return [], []
    
    yolo = YOLOv8Instance()
    results = yolo.process_cv_image(imageB)
    # 打印检测结果
    for bbox in results[0].boxes:
        print(f'Class-->: {int(bbox.cls[0])}, Confidence: {bbox.conf[0]}, BBox: {bbox.xyxy[0]}')
    rectA_arr = [] # 矩形 映射到 A图
    rectB_arr = [] # 矩形 映射到 B图
    # 矩形 映射到 A图；
    # tempA中检查区域内的最大值，如果最大值大于min_temp，则认为该区域温度过高，则增加标记
 
    index = 0
    for bbox in results[0].boxes:
        x1, y1, x2, y2 = map(int, bbox.xyxy[0])


        a_x1, a_y1 = point_transformer.B2A(x1, y1)
        a_x2, a_y2 = point_transformer.B2A(x2, y2)

        print("a_x1, a_y1 -->>> ", (a_x1, a_y1), (a_x2, a_y2))

        # 确保坐标是整数
        a_x1, a_y1, a_x2, a_y2 = int(a_x1), int(a_y1), int(a_x2), int(a_y2)
        # 边界检查和修正
        a_x1 = np.clip(a_x1, 0, tempA.shape[1] - 1)
        a_y1 = np.clip(a_y1, 0, tempA.shape[0] - 1)
        a_x2 = np.clip(a_x2, 0, tempA.shape[1] - 1)
        a_y2 = np.clip(a_y2, 0, tempA.shape[0] - 1)
        # 确保至少有一个像素的宽度和高度
        if a_x1 >= a_x2:
            a_x2 = min(a_x1 + 1, tempA.shape[1] - 1)
        if a_y1 >= a_y2:
            a_y2 = min(a_y1 + 1, tempA.shape[0] - 1)

        # 取区域内最大温度值、坐标
        a_matrix = tempA[a_y1:a_y2, a_x1:a_x2]
        # 最终检查矩阵是否为空
        if a_matrix.size == 0:
            print(f"警告: 空矩阵，跳过处理。边界=({a_y1}, {a_y2}, {a_x1}, {a_x2})")
            continue
        # 取区域内最大温度值、坐标
        a_matrix_max = np.max(a_matrix)
        print(f'Class: {int(bbox.cls[0])}, Confidence: {bbox.conf[0]}, BBox: {bbox.xyxy[0]}')
        print("a_matrix_max -> ", a_matrix_max, (a_y1, a_y2, a_x1, a_x2))
        if a_matrix_max < min_temp or a_matrix_max > max_temp:
            continue
        
        index += 1
        name =  "Ar" + str(index)
        a_y, a_x = a_matrix_max_pos = np.unravel_index(np.argmax(a_matrix), a_matrix.shape)
        x, y = point_transformer.A2B(a_x + a_x1, a_y + a_y1)
        rectA_arr.append({
            "x1": a_x1, 
            "y1": a_y1, 
            "x2": a_x2,  
            "y2": a_y2, 
            "cx": a_x + a_x1, 
            "cy": a_y + a_y1, 
            "max_temp": a_matrix_max, 
            "name": name,
        })
        rectB_arr.append({
            "x1": x1, 
            "y1": y1, 
            "x2": x2,  
            "y2": y2, 
            "cx": x, 
            "cy": y, 
            "max_temp": a_matrix_max, 
            "name": name,
        })

        # 调试 绘制矩形框
        # cv2.rectangle(imageA, (a_x1, a_y1), (a_x2, a_y2), (0, 0, 255), 2)
        # cv2.rectangle(imageB, (x1, y1), (x2, y2), (0, 0, 255), 2)

        # print(f'name-->: {name}, a_x: {a_x}, a_y: {a_y}, a_x1: {a_x1}, a_y1: {a_y1}, a_x2: {a_x2}, a_y2: {a_y2}')

        # tempA[a_y1:a_y2+1, a_x1:a_x2+1] = 0

    return rectA_arr, rectB_arr

def process_pcb_image(tempA, imageB, point_transformer, min_temp, max_temp, min_width, min_height, max_ratio, auto_reduce):
    """使用傳統影像處理方法識別 PCB 上的元器件。

    演算法流程：
    1. 生成 Layout 圖的色彩遮罩（green mask）
    2. 識別 PCB 邊界，將 tempA 中 PCB 外的區域歸零
    3. 將 tempA 分成小塊（60x80 像素），建立最大堆疊（max heap）
    4. 依照溫度從高到低取出每個塊，定位最高溫度點
    5. 將該點映射到 Layout 圖上，識別元器件邊界
    6. 過濾不符合條件的元器件（寬度、高度、長寬比等）
    7. 將已識別區域在 tempA 中歸零，避免重複偵測

    Args:
        tempA (numpy.ndarray): 溫度矩陣（2D 陣列，會被修改）
        imageB (numpy.ndarray): Layout 圖影像（BGR 格式）
        point_transformer (PointTransformer): A 圖 ↔ B 圖座標轉換器
        min_temp (float): 最低溫度閾值
        max_temp (float): 最高溫度閾值
        min_width (int): 元器件最小寬度（像素）
        min_height (int): 元器件最小高度（像素）
        max_ratio (float): 最大長寬比（超過則過濾）
        auto_reduce (float): 自動縮減係數（>1 時啟用外擴邊界檢查）

    Returns:
        tuple: (rectA_arr, rectB_arr)
            - rectA_arr (list[dict]): 熱力圖上的元器件矩形框列表
            - rectB_arr (list[dict]): Layout 圖上的元器件矩形框列表
    """
    # 获取掩码和点变换器
    mask_boundary = get_mask_boundary(imageB)
    # point_transformer = PointTransformer(3.2)

    # print("0 -->>> recognize_pcb_boundary ", np.max(tempA))

    # 识别PCB边界
    recognize_pcb_boundary(mask_boundary, point_transformer, tempA)

    # print("1 -->>> recognize_pcb_boundary ", np.max(tempA))

    # 分块大小
    block_height, block_width = 60, 80
    num_blocks_y = math.ceil(tempA.shape[0] / block_height)
    num_blocks_x = math.ceil(tempA.shape[1] / block_width)

    # 用于存储每个小块的最大值
    B = np.zeros((num_blocks_y, num_blocks_x))
    max_heap = []

    def update_block_max(block):
        return np.max(block)

    def update_block_value(y_min, y_max, x_min, x_max):
        nonlocal tempA
        tempA[y_min:y_max, x_min:x_max] = 0

        # 更新 B 矩阵
        for block_y in range(num_blocks_y):
            for block_x in range(num_blocks_x):
                y_start = block_y * block_height
                y_end = (block_y + 1) * block_height
                x_start = block_x * block_width
                x_end = (block_x + 1) * block_width

                if y_start < y_max and y_end > y_min and x_start < x_max and x_end > x_min:
                    block = tempA[y_start:y_end, x_start:x_end]
                    new_block_max = update_block_max(block)
                    B[block_y, block_x] = new_block_max

                    # 先检查该块是否已经在堆中
                    found = False
                    for i in range(len(max_heap)):
                        if max_heap[i] and max_heap[i][1] == block_y and max_heap[i][2] == block_x:
                            max_heap[i] = (-99, 0, 0)  # 懒删除
                            heapq.heapify(max_heap)
                            heapq.heappop(max_heap)
                            found = True
                            break
                    
                    if not found and new_block_max > min_temp and new_block_max < max_temp:
                        heapq.heappush(max_heap, (-new_block_max, block_y, block_x))

    # 初始化时计算 B 并将最大块信息存入堆
    for block_y in range(num_blocks_y):
        for block_x in range(num_blocks_x):
            y_start = block_y * block_height
            y_end = (block_y + 1) * block_height
            x_start = block_x * block_width
            x_end = (block_x + 1) * block_width

            block = tempA[y_start:y_end, x_start:x_end]
            B[block_y, block_x] = update_block_max(block)

            # print("xxx -> ", B[block_y, block_x], max_value_limit)

            if B[block_y, block_x] > min_temp and B[block_y, block_x] < max_temp:
                heapq.heappush(max_heap, (-B[block_y, block_x], block_y, block_x))

    # 开始处理最大值块
    time100 = time.time()

    __index = 0
    rectA_arr = []
    rectB_arr = []
    while len(max_heap) > 0:
        max_value, block_y, block_x = heapq.heappop(max_heap)
        max_value = -max_value  # 恢复为正值

        if max_value < min_temp and max_value < max_temp:
            break

        y_start = block_y * block_height
        y_end = (block_y + 1) * block_height
        x_start = block_x * block_width
        x_end = (block_x + 1) * block_width

        block = tempA[y_start:y_end, x_start:x_end]
        local_max_pos = np.unravel_index(np.argmax(block), block.shape)
        a_y, a_x = y_start + local_max_pos[0], x_start + local_max_pos[1]
        b_ori_x, b_ori_y = point_transformer.A_2_oriB(a_x, a_y)

        b_ori_boundary = recognize_component_boundary((b_ori_x, b_ori_y), mask_boundary)
        b_ori_left, b_ori_right, b_ori_top, b_ori_bottom, tag_component = b_ori_boundary

        # 通过B坐标系计算A坐标系的边界
        a_left, a_top = point_transformer.B2A(b_ori_left, b_ori_top)
        a_right, a_bottom = point_transformer.B2A(b_ori_right, b_ori_bottom)

        a_left, a_top, a_right, a_bottom = int(a_left), int(a_top), int(a_right), int(a_bottom)

        if a_x < a_left: a_left = a_x
        if a_x >= a_right: a_right = a_x + 1
        if a_y < a_top: a_top = a_y
        if a_y >= a_bottom: a_bottom = a_y + 1

        if a_top == a_bottom: a_bottom += 1
        if a_left == a_right: a_right += 1

        # 约束边界
        if a_top < 0: a_top = 0
        if a_left < 0: a_left = 0

        sub_matrix = tempA[a_top:a_bottom, a_left:a_right]
        __index += 1
        a_boundary_width = a_right - a_left
        a_boundary_height = a_bottom - a_top
        aspectRatio = a_boundary_width / a_boundary_height

        if tag_component == 255 or a_boundary_width < min_width or a_boundary_height < min_height or sub_matrix.size == 0 or \
            (np.sum(sub_matrix == 0) / sub_matrix.size > 0.1) or aspectRatio > max_ratio or aspectRatio < 1/max_ratio:
            update_block_value(a_top, a_bottom, a_left, a_right)
            continue

        update_block_value(a_top, a_bottom, a_left, a_right)
        name =  "Ar" + str(len(rectB_arr) + 1)

        # 绘制绿色边界框
        # cv2.rectangle(imageB, (b_ori_left, b_ori_top), (b_ori_right, b_ori_bottom), (0, 0, 255), 10)  # 红框
        # cv2.circle(imageB, (b_ori_x, b_ori_y), 1, (0, 255, 255), 20)  # 红色圆点
        # cv2.putText(imageB, f'{max_value}', (b_ori_x - 50, b_ori_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 255), 3)

        # cv2.rectangle(imageA, (a_left, a_top), (a_right, a_bottom), (188, 188, 188), 2, cv2.LINE_AA)  # 绿色框
        # # cv2.circle(imageA, (a_x, a_y), 1, (0, 255, 255), 3)  # 红色圆点
        # # 已知三角形的中心点 (x, y) 和边长
        # center = (a_x, a_y)
        # size = 6  # 三角形的边长
        # point1 = (center[0], center[1] - size // 2)
        # point2 = (center[0] - size // 2, center[1] + size // 2)
        # point3 = (center[0] + size // 2, center[1] + size // 2)
        # pts = np.array([point1, point2, point3], np.int32)
        # pts = pts.reshape((-1, 1, 2))

        # # 绘制三角形
        # cv2.fillPoly(imageA, [pts], color=(0, 0, 255))
        # cv2.putText(imageA, f'{name}', (a_left, a_top - 10 ),cv2.FONT_HERSHEY_COMPLEX, 0.6, (223, 223, 223), 1, cv2.LINE_AA)

        # cv2.putText(imageA, f'{max_value}', (a_x - 16 + 2, a_y - 10 + 2),cv2.FONT_HERSHEY_COMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
        # cv2.putText(imageA, f'{max_value}', (a_x - 16, a_y - 10), cv2.FONT_HERSHEY_COMPLEX, 0.55, (223, 223, 223), 1, cv2.LINE_AA)

        # 1.05
        flag = True
        if auto_reduce > 1:
            h, w = tempA.shape
            print("0xxx -> ", a_left, a_top, a_right, a_bottom)  
            
            out_left, out_top, out_right, out_bottom =  min(w, int(a_left * auto_reduce)), min(h, int(a_top * auto_reduce)), min(w, int(a_right * auto_reduce)), min(h, int(a_bottom * auto_reduce)),
            if out_left < out_right and out_top < out_bottom:
                print("1xxx -> ", out_left, out_top, out_right, out_bottom)
                out_matrix = tempA[out_top:out_bottom, out_left:out_right]
                out_matrix_max = np.max(out_matrix)

                inner_scale = 0.95
                if out_matrix_max > max_value:
                    rectA_arr.append({
                        "x1": a_left * inner_scale, 
                        "y1": a_top * inner_scale, 
                        "x2": a_right * inner_scale,  
                        "y2": a_bottom * inner_scale, 
                        "cx": a_x * inner_scale, 
                        "cy": a_y * inner_scale, 
                        "max_temp": max_value, 
                        "name": name,
                    })

                    rectB_arr.append({
                        "x1": b_ori_left * inner_scale, 
                        "y1": b_ori_top * inner_scale, 
                        "x2": b_ori_right * inner_scale,  
                        "y2": b_ori_bottom * inner_scale, 
                        "cx": b_ori_x * inner_scale, 
                        "cy": b_ori_y * inner_scale, 
                        "max_temp": max_value, 
                        "name": name,
                    })
                    flag = False
        if flag:
            rectA_arr.append({
                "x1": a_left, 
                "y1": a_top, 
                "x2": a_right,  
                "y2": a_bottom, 
                "cx": a_x, 
                "cy": a_y, 
                "max_temp": max_value, 
                "name": name,
            })

            rectB_arr.append({
                "x1": b_ori_left, 
                "y1": b_ori_top, 
                "x2": b_ori_right,  
                "y2": b_ori_bottom, 
                "cx": b_ori_x, 
                "cy": b_ori_y, 
                "max_temp": max_value, 
                "name": name,
            })

    time101 = time.time()
    print("Total processing time:", time101 - time100, __index)

    return rectA_arr, rectB_arr

# def to_mark_rect_B(self, itemA, imgScalePCB):
#     point_transformer = PointTransformer(imgScalePCB)
#     x1, y1 = point_transformer.A_2_oriB(itemA.get("x1"), itemA.get("y1"))
#     x2, y2 = point_transformer.A_2_oriB(itemA.get("x2"), itemA.get("y2"))
#     cx, cy = point_transformer.A_2_oriB(itemA.get("cx"), itemA.get("cy"))
#     itemA["x1"] = x1
#     itemA["y1"] = y1
#     itemA["x2"] = x2
#     itemA["y2"] = y2
#     itemA["cx"] = cx
#     itemA["cy"] = cy

# 使用示例
if __name__ == '__main__':
    temp_loader = TempLoader('user_data/A/tempA1.csv')
    tempA = temp_loader.get_tempA()
    imageA = cv2.imread('user_data/A/imageA.jpg')
    imageB = cv2.imread('user_data/A/imageB.jpg') #cv2.resize(cv2.imread('imageB.jpg'), (1280, 960))
    resized_imageA =  cv2.resize(imageA, (1280, 960)) #imageB.resize((604, 459), Image.LANCZOS)
    resized_imageB =  cv2.resize(imageB, (1280, 960)) #imageB.resize((604, 459), Image.LANCZOS)
    point_transformer = PointTransformer(1)

    print(" a ->  ", tempA.shape)

    processed_image = yolo_process_pcb_image(tempA, resized_imageA, resized_imageB, point_transformer, 50, 80, 10, 10, 1.5, 1.05)

    # 显示结果
    cv2.imshow("Processed ImageA", cv2.resize(resized_imageA, (1024, 768)))
    cv2.imshow("Processed Image", cv2.resize(resized_imageB, (1024, 768)))
    # cv2.imshow("Processed Image", resized_imageB)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
