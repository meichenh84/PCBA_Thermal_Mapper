import cv2
import numpy as np

def recognize_pcb_boundary(mask_boundary, point_transformer, tempA):
    """
    处理绿色区域轮廓，生成边界掩码并应用到tempA。

    参数:
        mask_boundary (ndarray): 二值化的掩码图像，其中绿色区域为1，背景为0。
        point_transformer (object): 包含 B2A 方法的对象，用于坐标变换。
        tempA (ndarray): 要处理的图像，将根据边界掩码进行更新。

    返回:
        tempA (ndarray): 更新后的图像。
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
