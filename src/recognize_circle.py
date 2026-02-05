import cv2
import numpy as np
import math

def detect_A_circles(image):
    """
    检测图像中的圆形，并返回圆心坐标 (x, y) 和半径 r 的数组。

    参数：
        image (ndarray): 输入的图像（BGR 格式）。

    返回：
        circles (ndarray): 检测到的圆形参数数组，包含圆心 (x, y) 和半径 r。
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
    """
    检测图像中的圆形，并返回圆心坐标 (x, y) 和半径 r 的数组。

    参数：
        image (ndarray): 输入的图像（BGR 格式）。

    返回：
        circles (ndarray): 检测到的圆形参数数组，包含圆心 (x, y) 和半径 r。
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
    """
    判断传入点 (px, py) 是否落在圆内，并返回包含该点的圆的 index 和 圆的参数 (x, y, r)。

    参数：
        circles (list): 包含圆的参数 [x_center, y_center, radius] 的列表。
        px (int): 传入点的 x 坐标。
        py (int): 传入点的 y 坐标。

    返回：
        tuple: 包含圆的 index 和 圆的 (x, y, r) 参数。如果没有找到符合条件的圆，返回 None。
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
