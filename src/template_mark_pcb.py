#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCB 元器件標記獨立腳本（早期版本）(template_mark_pcb.py)

用途：
    此為早期的獨立測試腳本，用於驗證 PCB 元器件自動識別演算法。
    直接讀取熱力圖、Layout 圖和溫度矩陣，執行元器件邊界偵測，
    並在影像上繪製標記結果。功能已整合至 recognize_image.py。

    注意：此檔案為獨立執行的腳本（非模組），包含頂層執行程式碼。
    主要保留作為演算法原型參考。

在整個應用中的角色：
    - 早期原型腳本，目前不被其他模組引用
    - 可獨立執行用於測試和驗證演算法

關聯檔案：
    - recognize_image.py：整合後的正式版本
    - recognize_component_boundary.py：元器件邊界識別（重構後的版本）
"""

import cv2
import numpy as np
import random
import pandas as pd
import time


# 读取PCB图像
image_file = 'imageA.jpg'  # 请替换为你的PCB图像文件名
imageA = cv2.imread(image_file)

# 读取温度矩阵（.xlsx格式）
tempA = pd.read_excel('tempA.xlsx').values  # 确保你安装了openpyxl库  todo 这里是耗时操作，需要处理

# 读取PCB图像
image_file_b = 'imageB.jpg'  # 请替换为你的PCB图像文件名
imageB = cv2.imread(image_file_b)
imageB_1280 = cv2.resize(imageB, (1280, 960))

points_imageA = np.array([[588, 135], [220, 387], [1175, 782]], dtype='float32')
points_imageB = np.array([[563, 160], [234, 396],[1105, 735]], dtype='float32')
B2A_matrix = cv2.getAffineTransform(points_imageB, points_imageA) #3x2矩阵

# 从 A 变换到 B
def A2B(x, y):
    point_A = np.array([x, y], dtype='float32')
    point_A_homogeneous = np.array([point_A[0], point_A[1], 1])
    # 将 B2A_matrix 转换为 3x3 矩阵
    B2A_matrix_full = np.vstack([B2A_matrix, [0, 0, 1]])
    # 计算 B2A_matrix
    A2B_matrix = np.linalg.inv(B2A_matrix_full)
    point_B_homogeneous = A2B_matrix @ point_A_homogeneous
    x, y, other = A2B_matrix @ point_A_homogeneous
    print("point_A_homogeneous", point_B_homogeneous)
    return (x, y)

# 从 B 变换到 A
def B2A(x, y):
    point_B = np.array([x, y], dtype='float32')
    point_B_homogeneous = np.array([point_B[0], point_B[1], 1])
    return B2A_matrix @ point_B_homogeneous

# 扩展函数，将矩阵 R1 变换为 R2
def B2A_m(boundary):
    top, bottom, left, right = boundary
    # 生成矩阵 R1
    R1 = np.array([[left, top],
                   [right, top],
                   [left, bottom],
                   [right, bottom]])
    
    R2 = np.zeros_like(R1, dtype='float32')
    for i in range(R1.shape[0]):
        a_x, a_y = B2A(R1[i, 0], R1[i, 1])
        R2[i] = [a_x, a_y]
        
    return R2

def A2B_m(boundary):
    top, bottom, left, right = boundary
    # 生成矩阵 R1
    R1 = np.array([[left, top],
                   [right, top],
                   [left, bottom],
                   [right, bottom]])
    
    R2 = np.zeros_like(R1, dtype='float32')
    for i in range(R1.shape[0]):
        b_x, b_y = A2B(R1[i, 0], R1[i, 1])
        R2[i] = [b_x, b_y]
    return R2
   

# 对图像PCB进行变换 
aligned_imageB_1280 = cv2.warpAffine(imageB_1280, B2A_matrix, (1280, 960))

# 叠加图片
# blended = cv2.addWeighted(aligned_imageB_1280, 0.33, imageA, 0.66, 0)
# cv2.imshow('blended', blended)

# blended2 = cv2.addWeighted(imageB_1280, 0.33, imageA, 0.66, 0)
# cv2.imshow('blended2', blended2)

# 确保图像成功加载
if imageA is None:
    print("无法加载图像")
    exit()

imgScale = 1
imgScalePCB = 3.2
color_ranges = {
    "红色": ((0, 100, 100), (10, 255, 255)),  # 红色的HSV范围
    "绿色": ((40, 100, 100), (80, 255, 255)),  # 绿色的HSV范围
    "蓝色": ((100, 100, 100), (140, 255, 255)),  # 蓝色的HSV范围
    "紫色": ((140, 100, 100), (160, 255, 255)),  # 紫色的HSV范围
    "黑色": ((0, 0, 0), (180, 255, 50)),  # 黑色的HSV范围
    "白色": ((0, 0, 200), (180, 25, 255)),  # 白色的HSV范围
    "橙色": ((10, 100, 100), (25, 255, 255))  # 橙色的HSV范围
}

# 定义多个中心点（这里示例为10个点）
centers = [
    ((int)(946 * imgScale), (int)(673 * imgScale)),
    ((int)(509 * imgScale), (int)(344 * imgScale)),
     ((int)(1081 * imgScale), (int)(436 * imgScale)),
      ((int)(383 * imgScale), (int)(561 * imgScale)),
      ((int)(963 * imgScale), (int)(240 * imgScale)),
    # (int(563 * imgScale), int(160 * imgScale)),
    # (int(234 * imgScale), int(396 * imgScale)),
    # (int(1105 * imgScale), int(735 * imgScale)),
    # (int(1010 * imgScale), int(409 * imgScale)),
    # (int(336 * imgScale), int(433 * imgScale)),
    # (int(496 * imgScale), int(350 * imgScale)),
    # (int(1220 * imgScale), int(733 * imgScale)),
    # (int(1236 * imgScale), int(436 * imgScale)),
    # (int(1090 * imgScale), int(150 * imgScale)),
    # (int(790 * imgScale), int(365 * imgScale)),
    # (int(673 * imgScale), int(400 * imgScale)),
    # (int(720 * imgScale), int(465 * imgScale)),
    # (int(373 * imgScale), int(600 * imgScale)),
]

# 定义白色和绿色的HSV范围
lower_white = np.array([0, 0, 200])    # 白色的下界
upper_white = np.array([180, 25, 255]) # 白色的上界

lower_green = np.array([35, 100, 100]) # 绿色的下界
upper_green = np.array([85, 255, 255])  # 绿色的上界

#浅绿色:
lower_green_1 = np.array([40, 100, 100])
upper_green_1 = np.array([80, 255, 255])
#深绿色:
lower_green_2 = np.array([30, 50, 50])
upper_green_2 = np.array([90, 255, 255])
#明亮的绿色:
lower_green_3 = np.array([50, 150, 150])
upper_green_3 = np.array([70, 255, 255])

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

def divide_into_parts(A, parts):
    # 计算每一部分的间隔
    interval = A / parts
    # 生成包含 5 个部分的列表
    result = [int((i + 1) * interval) for i in range(parts)]
    return result

# 从中心点向四个方向扩展以查找边界
def find_boundaries(center, mask_boundary):
    x, y = center
    left, right, top, bottom = x, x, y, y
    multiple = 1.05
    multiple2 = 2
    default_point_count = 5
    default_point_enable_probability = 0.75
    point_count = 1
    point_enable = 2

    # 向上扩展
    while top > 0 and mask_boundary[top, x] == 0:
        top -= 1
    top += 1  # 调整边界为最后一个有效像素的下一个位置

    # 向下扩展
    while bottom < mask_boundary.shape[0] - 1 and mask_boundary[bottom, x] == 0:
        bottom += 1
    bottom -= 1  # 调整边界为最后一个有效像素的上一个位置

    print("1 -> ", top, bottom)

    #    # 向左扩展
    # while left > 0 and mask_boundary[y, left] == 0 :
    #     left -= 1
    # left += 1  # 调整边界为最后一个有效像素的下一个位置

    # # 向右扩展``````````````
    # while right < mask_boundary.shape[1] - 1 and mask_boundary[y, right] == 0 :
    #     right += 1
    # right -= 1  # 调整边界为最后一个有效像素的上一个位置

    # 从 100 到 200 之间随机选择 10 个唯一数

    # 假设 mask_boundary 是一个 2D NumPy 数组
    # mask_boundary_ = np.array([
    #     [10, 1, 2],
    #     [20, 4, 5],
    #     [30, 7, 8],
    #     [40, 10, 11],
    #     [50, 13, 14],
    #     [60, 16, 17],
    #     [70, 19, 20],
    #     [80, 22, 23],
    #     [90, 25, 26],
    #     [100, 28, 29],
    #     [110, 31, 32]
    # ])

    # # 随机选择的 10 个行索引
    # random_numbers = [0, 2, 4, 6, 8, 1, 3, 5, 7, 9]  # 这些是示例索引

    # # 提取 random_numbers 指定行的第 0 列的值
    # selected_values = mask_boundary_[random_numbers, 0]
    if y <= top :
        y = top + 1

    # point_count = min(default_point_count, int(y - top))
    # point_enable = point_count * default_point_enable_probability
    left_w_random_numbers = [y - a for a in divide_into_parts(int((y - top) * 0.99), point_count)] #y - divide_into_parts(int((y - top) * 0.95), point_count) #random.sample(range(top, y + 1), point_count)
    # w_random_numbers.append(int(y + (y - top)/multiple), left)
    # w_random_numbers.append(int(y + (bottom - y) / multiple), left)


    # # 输出结果
    # print(top, bottom, bottom - top, w_random_numbers)
   
      # 向左扩展
    while left > 0 and [ 
        mask_boundary[y, left], 
        mask_boundary[int(y + (y - top)/multiple), left], 
        mask_boundary[int(y + (bottom - y) / multiple), left],
        mask_boundary[int(y + (y - top)/multiple2), left], 
        mask_boundary[int(y + (bottom - y) / multiple2), left]].count(0) > point_enable :
        #and (mask_boundary[left_w_random_numbers, left] == 0).sum() > point_enable:
        left -= 1
    left += 1  # 调整边界为最后一个有效像素的下一个位置


    # 向右扩展``````````````
    if bottom <= y :
        bottom = y + 1
    # point_count = min(default_point_count, int(bottom - y))
    # point_enable = point_count * default_point_enable_probability
    right_w_random_numbers = [y + a for a in divide_into_parts(int((bottom - y) * 0.99), point_count)] # y + divide_into_parts(int((bottom - y) * 0.95), point_count) # random.sample(range(top, y + 1), point_count)
    while right < mask_boundary.shape[1] - 1 and [
            mask_boundary[y, right],
            mask_boundary[int(y + (y - top)/multiple), right],
            mask_boundary[int(y + (bottom - y)/multiple), right],
            mask_boundary[int(y + (y - top)/multiple2), right],
            mask_boundary[int(y + (bottom - y)/multiple2), right] ].count(0) > point_enable :
        #(mask_boundary[right_w_random_numbers, right] == 0).sum() > point_enable:
        right += 1
    right -= 1  # 调整边界为最后一个有效像素的上一个位置

    top = y
    bottom = y

    if x <= left :
        x = left + 1

    # point_count = min(default_point_count, int(x - left))
    # point_enable = point_count * default_point_enable_probability
    top_h_random_numbers = [x - a for a in  divide_into_parts(int((x - left) * 0.99), point_count)] #x - divide_into_parts(int((x - left) * 0.95), point_count) #random.sample(range(left, x + 1), point_count)
    # top_h_random_numbers.append(top, int(x - (x - left)/multiple))
    # top_h_random_numbers.append(top, int(x + (right - x)/multiple))
    
    # 向上扩展
    while top > 0 and [ 
        mask_boundary[top, x],
        mask_boundary[top, int(x - (x - left)/multiple)],
        mask_boundary[top, int(x + (right - x)/multiple)],
        mask_boundary[top, int(x - (x - left)/multiple2)],
        mask_boundary[top, int(x + (right - x)/multiple2)] ].count(0) > 2 :
    # (mask_boundary[top, top_h_random_numbers] == 0).sum() > point_enable:
        top -= 1
    top += 1  # 调整边界为最后一个有效像素的下一个位置

    # 向下扩展
    if right <= x :
        right = x + 1
    # point_count = min(default_point_count, int(right - x))
    # point_enable = point_count * default_point_enable_probability
    bottom_h_random_numbers = [x + a for a in divide_into_parts(int((right - x) * 0.99), point_count)] #x + divide_into_parts(int((right - x) * 0.95), point_count) #random.sample(range(x, right + 1), point_count)
    while bottom < mask_boundary.shape[0] - 1 and [ 
        mask_boundary[bottom, x],
        mask_boundary[bottom, int(x - (x - left)/multiple)],
        mask_boundary[bottom, int(x + (right - x)/multiple)],
        mask_boundary[bottom, int(x - (x - left)/multiple2)],
        mask_boundary[bottom, int(x + (right - x)/multiple2)] ].count(0) > 2 :
    #  and (mask_boundary[bottom, bottom_h_random_numbers] == 0).sum() > point_enable:
        bottom += 1
    bottom -= 1  # 调整边界为最后一个有效像素的上一个位置

    #没有找到元器件 继续扩大范围 -> 暂不考虑
    # if right - left < 20 and bottom - top < 20:
    #     max_step = 20

    #     top_step = 0
    #      # 向上扩展
    #     # print("top", mask_boundary[top, x], mask_boundary[top - 1, x], mask_boundary[top + 1, x], top_step, top)
    #     top = top - 1
    #     while top > 0 and mask_boundary[top, x] != 0 and top_step < max_step:
    #         print("top step", mask_boundary[top, x], mask_boundary[top-1, x], top_step, top)
    #         top -= 1
    #         top_step += 1
    #     #top += 1  # 调整边界为最后一个有效像素的下一个位置

    #     # 向下扩展
    #     max_step = 20
    #     bottom_step = 0
    #     while bottom < mask_boundary.shape[0] - 1 and mask_boundary[bottom, x] != 0 and bottom_step < max_step:
    #         bottom += 1
    #         bottom_step += 1
    #     bottom -= 1  # 调整边界为最后一个有效像素的上一个位置

    #     # 向左扩展
    #     max_step = 20
    #     left_step = 0
    #     while left > 0 and mask_boundary[y, left] != 0 and left_step < max_step:
    #         left -= 1
    #         left_step += 1
    #     left += 1  # 调整边界为最后一个有效像素的下一个位置

    #     # 向右扩展
    #     max_step = 20
    #     right_step = 0
    #     while right < mask_boundary.shape[1] - 1 and mask_boundary[y, right] != 0 and right_step < max_step:
    #         right += 1
    #         right_step += 1
    #     right -= 1  # 调整边界为最后一个有效像素的上一个位置

    #     print("xx2", left, right, top, bottom)
    #     print("xx3", left_step, right_step, top_step, bottom_step)

    return left, right, top, bottom

# 遍历每个中心点，找到并绘制边界框和标记点
# for i, center in enumerate(centers):
# 找到tempA中最大值及其坐标 1280x960
__index = 0
time100 = time.time()
while True:
    time1 = time.time()
    # max_val = np.max(tempA)
    max_index = np.argmax(tempA)
    time10 = time.time()
    a_y, a_x = np.unravel_index(max_index, tempA.shape)
    time11 = time.time()
    max_value = tempA[a_y, a_x]
    # 检查最大值是否小于 40
    if max_value < 70:
        break
    b_x, b_y = A2B(a_x, a_y)
    b_ori_x, b_ori_y = int(b_x*imgScalePCB), int(b_y*imgScalePCB)  # 转换为整数坐标

    b_ori_boundary = b_ori_left, b_ori_right, b_ori_top, b_ori_bottom = find_boundaries((b_ori_x, b_ori_y), mask_boundary)
    time2 = time.time()
 
    b_boundary = b_top, b_bottom, b_left, b_right = ((b_ori_top / imgScalePCB), (b_ori_bottom / imgScalePCB), (b_ori_left / imgScalePCB), (b_ori_right / imgScalePCB))
    #清空tempA中已经处理的值
    # b_ori_boundary = np.zeros(tempA.shape, dtype=int) # 创建一个掩码以标记边界区域
    # b_ori_boundary[int(top / imgScalePCB):int(bottom / imgScalePCB), int(left / imgScalePCB): int(right / imgScalePCB)] = True  # 假设边界为矩形区域
    # print("最大值:", max_value, (a_x, a_y), (b_x, b_y), (b_ori_x, b_ori_y), (left, right, b_ori_left, bottom), (a_top, a_bottom, a_left, a_right))
    # if(a_top == a_bottom):
    #     a_bottom += 1
    # if(a_left == a_right):
    #     a_right += 1

    a_left, a_top = B2A(b_left, b_top)
    a_right, a_bottom = B2A(b_right, b_bottom)
    a_top, a_bottom, a_left, a_right = int(a_top), int(a_bottom), int(a_left), int(a_right)

    # 算法计算出来的区域不够精确，需要重新约束该点所在的范围
    if(a_x < a_left): a_left = a_x
    if(a_x >= a_right): a_right = a_x + 1
    if(a_y < a_top): a_top = a_y
    if(a_y >= a_bottom): a_bottom = a_y + 1
    if(a_top == a_bottom): a_bottom += 1
    if(a_left == a_right): a_right += 1
    time21 = time.time()
 
    a_boundary = (a_top, a_bottom, a_left, a_right)
    print("最大值2:", max_value, (a_x, a_y), (b_x, b_y), b_ori_boundary, b_boundary, a_boundary, (time11 - time10), (time10 - time1))
    sub_matrix = tempA[a_top:a_bottom, a_left:a_right]
    __index += 1
    # index = 0
    #没有找到元器件 -> 暂不考虑
    #若范围内，大部分被置0，说明数据已经被处理过；无需再次处理了
    if a_right - a_left < 8 or a_bottom - a_top < 8 or (np.sum(sub_matrix == 0) / sub_matrix.size > 0.8):  
        time3 = time.time()
        print("find_boundaries2 use time continue", (time3 - time1), __index)
        print("continue ", max_value)
        tempA[a_boundary[0]:a_boundary[1], a_boundary[2]: a_boundary[3]] = 0   
        continue

    print("hhhhh",__index)
    # probability = np.sum(sub_matrix == 0) / sub_matrix.size
    # print("probability real -- --->>>  ", max_value, probability, sub_matrix.size, np.sum(sub_matrix == 0))
    tempA[a_boundary[0]:a_boundary[1], a_boundary[2]: a_boundary[3]] = 0   
    # 绘制绿色边界框
    cv2.rectangle(imageB, (b_ori_left, b_ori_top), (b_ori_right, b_ori_bottom), (0, 0, 255), 3)  # 绿色框

    # if(index == 1):
    #     break;

    # 标记中心点

    cv2.circle(imageB, (b_ori_x, b_ori_y), 1, (0, 255, 255), -1)  # 红色圆点
    # cv2.circle(imageA, (a_x, a_y), 5, (0, 0, 255), -1)  # 红色圆点
    time4 = time.time()
    print("find_boundaries use time", (time2 - time1), (time4 - time1), __index)

# 在点附近添加文本标签
# cv2.putText(image, f'Point {i+1}', (cx + 10, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
time101 = time.time()
print("while use time", (time101 - time100), __index)
    
# 显示结果
# cv2.imshow("带框和标记的热力图", imageA)
cv2.imshow("带框和标记的元器件", cv2.resize(imageB, (1280, 960)))
cv2.imwrite("out_imgB.jpg", imageB)
cv2.waitKey(0)
cv2.destroyAllWindows()