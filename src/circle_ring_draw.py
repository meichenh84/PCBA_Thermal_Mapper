import cv2
import numpy as np

def draw_circle_ring_text(imageA_np, point, index = "", radius_red = 8, ring_width = 2, scale_factor=8):
    """
    在给定图像上绘制内外圆圈，并返回经过处理后的图像。
    
    参数:
    - imageA_np: 输入图像（numpy 数组）。
    - point: 圆心位置 (x, y)。
    - radius_red: 内圆半径。
    - ring_width: 外圆宽度。
    - scale_factor: 缩放系数，默认为 8，用于提高绘制精度。
    
    返回:
    - 处理后的图像（numpy 数组）。
    """
    # 获取原图的尺寸
    original_height, original_width = imageA_np.shape[:2]

    # 增加图像分辨率（用于提高圆的精度）
    imageA_np_resized = cv2.resize(imageA_np, (original_width * scale_factor, original_height * scale_factor))

    # 重新定义半径和圆心位置，适应放大的图像尺寸
    point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    # 绘制外圆（白色圆环）
    cv2.circle(imageA_np_resized, point_resized, radius_red_resized + ring_width_resized, (255, 255, 255), thickness=-1)

    # 绘制内圆（红色圆）
    cv2.circle(imageA_np_resized, point_resized, radius_red_resized, (0, 0, 255), thickness=-1)

    if index:
        # cv2.putText(imageA_np_resized, "2", (point_resized[0] - scale_factor * 4 + 2, point_resized[1] + scale_factor * 3 + 2),cv2.FONT_HERSHEY_COMPLEX, 4, (255, 255, 255), 8, cv2.LINE_AA)
        cv2.putText(imageA_np_resized, str(index), (point_resized[0] - scale_factor * 4, point_resized[1] + scale_factor * 4), cv2.FONT_HERSHEY_COMPLEX, 3.5, (255, 255, 255), 10, cv2.LINE_AA)

    # 将图像缩小回原始尺寸
    imageA_np_resized = cv2.resize(imageA_np_resized, (original_width, original_height))

    # 使用高斯模糊处理图像，减少锯齿
    # imageA_np_resized = cv2.GaussianBlur(imageA_np_resized, (5, 5), 0)

    return imageA_np_resized

def draw_circle_ring(imageA_np, point, radius_red = 8, ring_width = 2, scale_factor=8):
    """
    在给定图像上绘制内外圆圈，并返回经过处理后的图像。
    
    参数:
    - imageA_np: 输入图像（numpy 数组）。
    - point: 圆心位置 (x, y)。
    - radius_red: 内圆半径。
    - ring_width: 外圆宽度。
    - scale_factor: 缩放系数，默认为 8，用于提高绘制精度。
    
    返回:
    - 处理后的图像（numpy 数组）。
    """
    # 获取原图的尺寸
    original_height, original_width = imageA_np.shape[:2]

    # 增加图像分辨率（用于提高圆的精度）
    imageA_np_resized = cv2.resize(imageA_np, (original_width * scale_factor, original_height * scale_factor))

    # 重新定义半径和圆心位置，适应放大的图像尺寸
    point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    # 绘制外圆（白色圆环）
    cv2.circle(imageA_np_resized, point_resized, radius_red_resized + ring_width_resized, (255, 255, 255), thickness=-1)

    # 绘制内圆（红色圆）
    cv2.circle(imageA_np_resized, point_resized, radius_red_resized, (0, 255, 0), thickness=-1)

    # 将图像缩小回原始尺寸
    imageA_np_resized = cv2.resize(imageA_np_resized, (original_width, original_height))

    # 使用高斯模糊处理图像，减少锯齿
    # imageA_np_resized = cv2.GaussianBlur(imageA_np_resized, (5, 5), 0)

    return imageA_np_resized


def draw_points_circle_ring_text(imageA_np, points, radius_red = 8, ring_width = 2, scale_factor=8):
    """
    在给定图像上绘制内外圆圈，并返回经过处理后的图像。
    
    参数:
    - imageA_np: 输入图像（numpy 数组）。
    - point: 圆心位置 (x, y)。
    - radius_red: 内圆半径。
    - ring_width: 外圆宽度。
    - scale_factor: 缩放系数，默认为 8，用于提高绘制精度。
    
    返回:
    - 处理后的图像（numpy 数组）。
    """
    # 获取原图的尺寸
    original_height, original_width = imageA_np.shape[:2]

    # 增加图像分辨率（用于提高圆的精度）
    imageA_np_resized = cv2.resize(imageA_np, (original_width * scale_factor, original_height * scale_factor))

    # 重新定义半径和圆心位置，适应放大的图像尺寸
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    index = 0
    for point in points:
        index += 1
        point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))

        # 绘制外圆（白色圆环）
        cv2.circle(imageA_np_resized, point_resized, radius_red_resized + ring_width_resized, (255, 255, 255), thickness=-1)

        # 绘制内圆（红色圆）
        cv2.circle(imageA_np_resized, point_resized, radius_red_resized, (0, 0, 255), thickness=-1)

        if index:
            # cv2.putText(imageA_np_resized, "2", (point_resized[0] - scale_factor * 4 + 2, point_resized[1] + scale_factor * 3 + 2),cv2.FONT_HERSHEY_COMPLEX, 4, (255, 255, 255), 8, cv2.LINE_AA)
            cv2.putText(imageA_np_resized, str(index), (point_resized[0] - scale_factor * 4, point_resized[1] + scale_factor * 4), cv2.FONT_HERSHEY_COMPLEX, 3.5, (255, 255, 255), 10, cv2.LINE_AA)

    # 将图像缩小回原始尺寸
    imageA_np_resized = cv2.resize(imageA_np_resized, (original_width, original_height))

    # 使用高斯模糊处理图像，减少锯齿
    # imageA_np_resized = cv2.GaussianBlur(imageA_np_resized, (5, 5), 0)

    return imageA_np_resized

def draw_points_circle_ring(image_np, points, radius_red = 8, ring_width = 2, scale_factor=8):
    """
    在给定图像上绘制内外圆圈，并返回经过处理后的图像。
    
    参数:
    - image_np: 输入图像（numpy 数组）。
    - point: 圆心位置 (x, y)。
    - radius_red: 内圆半径。
    - ring_width: 外圆宽度。
    - scale_factor: 缩放系数，默认为 8，用于提高绘制精度。
    
    返回:
    - 处理后的图像（numpy 数组）。
    """

    # 获取原图的尺寸
    original_height, original_width = image_np.shape[:2]

    # 增加图像分辨率（用于提高圆的精度）
    image_np_resized = cv2.resize(image_np, (original_width * scale_factor, original_height * scale_factor))
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    index = 0
    for point in points:
        index += 1

        # 重新定义半径和圆心位置，适应放大的图像尺寸
        point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))

        # 绘制外圆（白色圆环）
        cv2.circle(image_np_resized, point_resized, radius_red_resized + ring_width_resized, (255, 255, 255), thickness=-1)

        # 绘制内圆（红色圆）
        cv2.circle(image_np_resized, point_resized, radius_red_resized, (0, 255, 0), thickness=-1)

    # 将图像缩小回原始尺寸
    image_np_resized = cv2.resize(image_np_resized, (original_width, original_height))

    # 使用高斯模糊处理图像，减少锯齿
    # imageA_np_resized = cv2.GaussianBlur(image_np_resized, (5, 5), 0)
    return image_np_resized



def draw_points(imageA_np, points, radius_red = 8, ring_width = 2, scale_factor=8):
    """
    在给定图像上绘制内外圆圈，并返回经过处理后的图像。
    
    参数:
    - imageA_np: 输入图像（numpy 数组）。
    - point: 圆心位置 (x, y)。
    - radius_red: 内圆半径。
    - ring_width: 外圆宽度。
    - scale_factor: 缩放系数，默认为 8，用于提高绘制精度。
    
    返回:
    - 处理后的图像（numpy 数组）。
    """
    # 获取原图的尺寸
    original_height, original_width = imageA_np.shape[:2]

    # 增加图像分辨率（用于提高圆的精度）
    imageA_np_resized = cv2.resize(imageA_np, (original_width * scale_factor, original_height * scale_factor))

    # 重新定义半径和圆心位置，适应放大的图像尺寸
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    index = 0
    for point in points:
        index += 1
        point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))

        # 绘制外圆（白色圆环）
        cv2.circle(imageA_np_resized, point_resized, radius_red_resized + ring_width_resized, (255, 255, 255), thickness=-1)

        # 绘制内圆（红色圆）
        cv2.circle(imageA_np_resized, point_resized, radius_red_resized, (0, 0, 255), thickness=-1)

        if index:
            # cv2.putText(imageA_np_resized, "2", (point_resized[0] - scale_factor * 4 + 2, point_resized[1] + scale_factor * 3 + 2),cv2.FONT_HERSHEY_COMPLEX, 4, (255, 255, 255), 8, cv2.LINE_AA)
            cv2.putText(imageA_np_resized, str(index), (point_resized[0] - scale_factor * 4, point_resized[1] + scale_factor * 4), cv2.FONT_HERSHEY_COMPLEX, 3.5, (255, 255, 255), 10, cv2.LINE_AA)

    # 将图像缩小回原始尺寸
    imageA_np_resized = cv2.resize(imageA_np_resized, (original_width, original_height))

    # 使用高斯模糊处理图像，减少锯齿
    # imageA_np_resized = cv2.GaussianBlur(imageA_np_resized, (5, 5), 0)

    return imageA_np_resized

# 使用示例
if __name__ == "__main__":
    # 创建一个空白图像
    height, width = 500, 500
    imageA_np = np.zeros((height, width, 3), dtype=np.uint8)

    # 圆心位置和半径
    point = (250, 250)  # 圆心坐标
    radius_red = 50  # 内圆半径
    ring_width = 10  # 外圆宽度

    # 调用函数
    result_image = draw_circle_ring(imageA_np, point, radius_red, ring_width, scale_factor=2)

    # 显示图像
    cv2.imshow("Smooth Circle", result_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
