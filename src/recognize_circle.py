#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
圓形標記偵測模組 (recognize_circle.py)

用途：
    使用 OpenCV 的霍夫圓變換（Hough Circle Transform）偵測影像中的圓形標記。
    提供兩組偵測函式：detect_A_circles() 用於熱力圖（imageA），
    detect_B_circles() 用於 Layout 圖（imageB），兩者的參數略有不同
    （半徑範圍不同）。另外提供 find_circle_containing_point() 判斷
    某個點是否落在某個偵測到的圓內。

在整個應用中的角色：
    - 用於偵測使用者手動標記的圓形對齊點
    - 偵測結果用於 point_transformer.py 計算仿射變換矩陣

關聯檔案：
    - main.py：呼叫本模組偵測圓形標記
    - point_transformer.py：使用偵測到的圓心座標計算仿射變換
"""

import cv2
import numpy as np
import math


def detect_A_circles(image):
    """偵測熱力圖（imageA）中的圓形標記。

    使用霍夫圓變換偵測圓形，適用於熱力圖的參數設定
    （最小半徑 4px，最大半徑 30px）。

    Args:
        image (numpy.ndarray): 輸入的熱力圖影像（BGR 格式）

    Returns:
        numpy.ndarray | list: 偵測到的圓形參數陣列 [[x, y, r], ...]，
                              若無偵測到則回傳空列表
    """
    # 将图像转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 使用高斯模糊减少噪声
    gray_blurred = cv2.GaussianBlur(gray, (15, 15), 0)

    # 使用 HoughCircles 检测圆形
    circles = cv2.HoughCircles(
        gray_blurred,              # 输入图像
        cv2.HOUGH_GRADIENT,        # 使用霍夫梯度方法
        dp=1,                      # 累加器分辨率与图像分辨率的反比（1表示与输入图像大小相同）
        minDist=10,                # 圆心之间的最小距离
        param1=50,                 # 边缘检测的高阈值（传递给 Canny 边缘检测）
        param2=30,                 # 在累加器中检测到圆形的阈值，越低可以检测到更多的圆
        minRadius=4,               # 圆的最小半径
        maxRadius=30               # 圆的最大半径
    )

    # 检查是否检测到圆形
    if circles is not None:
        # 将圆心和半径转换为整数
        circles = np.round(circles[0, :]).astype("int")
        return circles  # 返回圆心 (x, y) 和半径 r 数组
    else:
        return []  # 如果没有检测到圆形，返回 None
    

def detect_B_circles(image):
    """偵測 Layout 圖（imageB）中的圓形標記。

    使用霍夫圓變換偵測圓形，適用於 Layout 圖的參數設定
    （最小半徑 13px，最大半徑 30px，較大的最小半徑避免誤偵測小型通孔）。

    Args:
        image (numpy.ndarray): 輸入的 Layout 圖影像（BGR 格式）

    Returns:
        numpy.ndarray | list: 偵測到的圓形參數陣列 [[x, y, r], ...]，
                              若無偵測到則回傳空列表
    """
    # 将图像转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 使用高斯模糊减少噪声
    gray_blurred = cv2.GaussianBlur(gray, (11, 11), 0)

    # 使用 HoughCircles 检测圆形
    circles = cv2.HoughCircles(
        gray_blurred,              # 输入图像
        cv2.HOUGH_GRADIENT,        # 使用霍夫梯度方法
        dp=1,                      # 累加器分辨率与图像分辨率的反比（1表示与输入图像大小相同）
        minDist=10,                # 圆心之间的最小距离
        param1=50,                 # 边缘检测的高阈值（传递给 Canny 边缘检测）
        param2=30,                 # 在累加器中检测到圆形的阈值，越低可以检测到更多的圆
        minRadius=13,              # 圆的最小半径
        maxRadius=30               # 圆的最大半径
    )
    # 检查是否检测到圆形
    if circles is not None:
        # 将圆心和半径转换为整数
        circles = np.round(circles[0, :]).astype("int")
        return circles  # 返回圆心 (x, y) 和半径 r 数组
    else:
        return []  # 如果没有检测到圆形，返回 None
    
def find_circle_containing_point(circles, px, py):
    """判斷指定的點 (px, py) 是否落在某個偵測到的圓內。

    遍歷所有偵測到的圓，計算點到各圓心的歐幾里得距離，
    若距離小於等於圓的半徑，則表示點在該圓內。

    Args:
        circles (list): 圓形參數列表 [[x_center, y_center, radius], ...]
        px (int): 指定點的 X 座標
        py (int): 指定點的 Y 座標

    Returns:
        tuple | None: 包含該點的圓的參數 (cx, cy, r)，若找不到則回傳 None
    """

    if len(circles) == 0:
        return None

    for index, (cx, cy, r) in enumerate(circles):
        # 计算点 (px, py) 到圆心 (cx, cy) 的欧几里得距离
        distance = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
        
        # 如果距离小于或等于圆的半径，则说明点在圆内
        if distance <= r:
            return cx, cy, r
    
    return None  # 如果没有找到包含该点的圆

# # 示例：使用该函数进行圆形检测
# image = cv2.imread('imageA.jpg')  # 外部传入图像
# detected_circles = detect_circles(image)

# if detected_circles is not None:
#     for (x, y, r) in detected_circles:
#         print(f"圆心: ({x}, {y}), 半径: {r}")
#         # 绘制圆形轮廓
#         cv2.circle(image, (x, y), r, (0, 0, 0), 2)  # 绿色圆环
#         # 绘制圆心
#         cv2.circle(image, (x, y), 2, (0, 0, 0), 2)  # 红色圆心

#     # 显示检测到圆形后的图像
#     cv2.imshow("Detected Circles", cv2.resize(image, (1280, 960)))
#     cv2.waitKey(0)
#     cv2.destroyAllWindows()
# else:
#     print("没有检测到圆形")


# # 读取图像
# image = cv2.imread('imageB1.jpg')

# # 将图像转换为灰度图
# gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# # 使用高斯模糊减少噪声
# gray_blurred = cv2.GaussianBlur(gray, (15, 15), 0)

# # 使用 HoughCircles 检测圆形
# circles = cv2.HoughCircles(
#     gray_blurred,              # 输入图像
#     cv2.HOUGH_GRADIENT,        # 使用霍夫梯度方法
#     dp=1,                      # 累加器分辨率与图像分辨率的反比（1表示与输入图像大小相同）
#     minDist=10,                # 圆心之间的最小距离
#     param1=50,                 # 边缘检测的高阈值（传递给 Canny 边缘检测）
#     param2=30,                 # 在累加器中检测到圆形的阈值，越低可以检测到更多的圆
#     minRadius=13,              # 圆的最小半径
#     maxRadius=30               # 圆的最大半径
# )

# # 检查是否检测到圆形
# if circles is not None:
#     # 将圆心和半径转换为整数
#     circles = np.round(circles[0, :]).astype("int")

#     # 遍历检测到的圆形
#     for (x, y, r) in circles:
#         # 在原图上绘制圆形轮廓
#         cv2.circle(image, (x, y), r, (0, 255, 0), 4)  # 绿色圆环
#         # 绘制圆心
#         cv2.circle(image, (x, y), 2, (0, 0, 255), 3)  # 红色圆心

# # 显示结果图像
# cv2.imshow("Detected Circles",  cv2.resize(image, (1280, 960)))

# # 等待用户按键并关闭窗口
# cv2.waitKey(0)
# cv2.destroyAllWindows()
