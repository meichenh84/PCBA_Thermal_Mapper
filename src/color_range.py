# mask_processing.py

import numpy as np
import cv2

color_ranges = {
    "红色": ((0, 100, 100), (10, 255, 255)),  # 红色的HSV范围
    "绿色": ((40, 100, 100), (80, 255, 255)),  # 绿色的HSV范围
    "蓝色": ((100, 100, 100), (140, 255, 255)),  # 蓝色的HSV范围
    "紫色": ((140, 100, 100), (160, 255, 255)),  # 紫色的HSV范围
    "黑色": ((0, 0, 0), (180, 255, 50)),  # 黑色的HSV范围
    "白色": ((0, 0, 200), (180, 25, 255)),  # 白色的HSV范围
    "橙色": ((10, 100, 100), (25, 255, 255))  # 橙色的HSV范围
}

# 定义白色和绿色的HSV范围
lower_white = np.array([0, 0, 200])    # 白色的下界
upper_white = np.array([180, 25, 255]) # 白色的上界

lower_green = np.array([35, 100, 100]) # 绿色的下界
upper_green = np.array([85, 255, 255])  # 绿色的上界

# 浅绿色:
lower_green_1 = np.array([40, 100, 100])
upper_green_1 = np.array([80, 255, 255])

# 深绿色:
lower_green_2 = np.array([30, 50, 50])
upper_green_2 = np.array([90, 255, 255])

# 明亮的绿色:
lower_green_3 = np.array([50, 150, 150])
upper_green_3 = np.array([70, 255, 255])

def get_mask_boundary(imageB):
    """
    通过传入图像数组生成白色和绿色的掩码，返回整体掩码。
    
    参数：
    - imageB: 输入的图像数据（NumPy 数组）。
    
    返回：
    - mask_boundary: 白色和绿色区域的掩码。
    """
    if imageB is None:
        raise ValueError("输入的图像数据为空。")

    # 转换为HSV颜色空间
    hsv_image = cv2.cvtColor(imageB, cv2.COLOR_BGR2HSV)

    # 创建掩码
    mask_white = cv2.inRange(hsv_image, lower_white, upper_white)
    mask_green = cv2.inRange(hsv_image, lower_green, upper_green)
    mask_green1 = cv2.inRange(hsv_image, lower_green_1, upper_green_1)
    mask_green2 = cv2.inRange(hsv_image, lower_green_2, upper_green_2)
    mask_green3 = cv2.inRange(hsv_image, lower_green_3, upper_green_3)

    # 创建一个整体掩码，标识白色和绿色区域
    mask_boundary = mask_green | mask_green1 | mask_green2 | mask_green3
    return mask_boundary
