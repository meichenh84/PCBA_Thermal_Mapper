"""
热力图绘制模块

主要功能：
1. 在热力图上绘制温度标记（三角形和文字）
2. 智能文字定位算法，避免文字重叠
3. 温度数据的可视化显示
4. 支持多种绘制模式和样式
"""

import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont
import traceback
from config import GlobalConfig

def draw_triangle_and_text(imageA, item, imageScale = 1, imageIndex = 0, size=8):
    """
    在图像上绘制一个三角形并添加文本。

    参数：
    imageA (numpy.ndarray): 输入的图像。
    a_x (int): 三角形的中心点的 x 坐标。
    a_y (int): 三角形的中心点的 y 坐标。
    max_value (str): 要显示在图像上的文本值。
    size (int): 三角形的边长（默认 6）。
    """

    imgWidth = imageA.shape[1]
    textScale = imgWidth / 1024
    size = size * textScale
    
    # 从配置中读取颜色
    config = GlobalConfig()
    if imageIndex == 0:
        # 热力图标记
        rect_color_hex = config.get("heat_rect_color", "#BCBCBC")
        name_color_hex = config.get("heat_name_color", "#FFFFFF")
        temp_color_hex = config.get("heat_temp_color", "#FF0000")
        name_font_size = config.get("heat_name_font_size", 12)
        temp_font_size = config.get("heat_temp_font_size", 10)
    else:
        # Layout图标记
        rect_color_hex = config.get("layout_rect_color", "#BCBCBC")
        name_color_hex = config.get("layout_name_color", "#FFFFFF")
        temp_color_hex = config.get("layout_temp_color", "#FF0000")
        name_font_size = config.get("layout_name_font_size", 12)
        temp_font_size = config.get("layout_temp_font_size", 10)
    
    # 转换十六进制颜色为RGB元组
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    rectColor = hex_to_rgb(rect_color_hex)
    textColor = hex_to_rgb(name_color_hex)
    tempColor = hex_to_rgb(temp_color_hex)
    shadowColor = (0, 0, 0)

    left, top, right, bottom, cx, cy, max_temp, name = item.get("x1"), item.get("y1"), item.get("x2"), item.get("y2"), item.get("cx"), item.get("cy"), item.get("max_temp"), item.get("name")
    left = int(left * imageScale)
    top = int(top * imageScale)
    right = int(right * imageScale)
    bottom = int(bottom * imageScale)
    cx = int(cx * imageScale)
    cy = int(cy * imageScale)

    cv2.rectangle(imageA, (left, top), (right, bottom), rectColor, 1, cv2.LINE_AA)  # 绿色框
    # 计算三角形的三个顶点
    center = (cx, cy)
    # 顶点1 (尖角)
    point1 = (center[0], center[1] - size // 2)
    # 顶点2 (左下角)
    point2 = (center[0] - size // 2, center[1] + size // 2)
    # 顶点3 (右下角)
    point3 = (center[0] + size // 2, center[1] + size // 2)
    
    # 将顶点连接成一个三角形
    pts = np.array([point1, point2, point3], np.int32)
    pts = pts.reshape((-1, 1, 2))

    # 绘制三角形
    cv2.fillPoly(imageA, [pts], color=tempColor)

        
    # 使用配置的字体大小
    name_font_scale = (name_font_size / 12.0) * 0.55 * textScale
    temp_font_scale = (temp_font_size / 10.0) * 0.55 * textScale
    
    cv2.putText(imageA, f'{name}', (left - int(10*textScale), cy - int(40*textScale)), cv2.FONT_HERSHEY_COMPLEX, name_font_scale, textColor, 1, cv2.LINE_AA)

    # 在三角形的中心点附近绘制文本（阴影效果）
    cv2.putText(imageA, f'{max_temp}', (cx - int(16*textScale) + int(2*textScale), cy - int(10*textScale) + int(2*textScale)), cv2.FONT_HERSHEY_COMPLEX, temp_font_scale, shadowColor, 1, cv2.LINE_AA)
    cv2.putText(imageA, f'{max_temp}', (cx - int(16*textScale), cy - int(10*textScale)), cv2.FONT_HERSHEY_COMPLEX, temp_font_scale, tempColor, 1, cv2.LINE_AA)

    print("draw_triangle_and_text------->>> ", point1, point2, point3, cx, cy)


def draw_canvas_item(canvas, item, imageScale=1, offset=(0, 0), imageIndex=0, size=8):
    """
    在Canvas上绘制一个三角形并添加文本。

    参数：
    canvas (tk.Canvas): Tkinter的Canvas控件。
    item (dict): 包含绘制信息的字典。
    imageScale (float): 缩放因子，默认为1。
    imageIndex (int): 图像索引，决定颜色。
    size (int): 三角形的边长，默认为8。
    """

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    # 提取 item 中的值并应用缩放
    left, top, right, bottom, cx, cy, max_temp, name = (
        item.get("x1"), item.get("y1"), item.get("x2"), item.get("y2"), 
        item.get("cx"), item.get("cy"), item.get("max_temp"), item.get("name")
    )

    # 验证所有坐标值都不是None
    if None in (left, top, right, bottom, cx, cy):
        print(f"错误：矩形框坐标包含None值: left={left}, top={top}, right={right}, bottom={bottom}, cx={cx}, cy={cy}")
        print(f"完整的item数据: {item}")
        raise ValueError(f"矩形框坐标不能为None")
    
    if imageScale is None:
        print(f"错误：imageScale为None")
        raise ValueError(f"imageScale不能为None")

    off_x, off_y = offset
    left = int(left * imageScale) + off_x
    top = int(top * imageScale) + off_y
    right = int(right * imageScale) + off_x
    bottom = int(bottom * imageScale) + off_y
    cx = int(cx * imageScale) + off_x
    cy = int(cy * imageScale) + off_y
    
    # 对于Layout图，使用实际图像区域进行边界检查
    if imageIndex != 0:
        # 计算实际图像显示区域
        # 图像在Canvas中是居中显示的，所以需要计算实际的图像边界
        image_width = canvas_width - 2 * off_x  # 实际图像宽度
        image_height = canvas_height - 2 * off_y  # 实际图像高度
        
        # 使用实际图像区域进行边界检查
        left = max(off_x, left)
        top = max(off_y, top)
        right = min(right, off_x + image_width)
        bottom = min(bottom, off_y + image_height)
        cx = max(off_x, min(cx, off_x + image_width - 1))
        cy = max(off_y, min(cy, off_y + image_height - 1))
    else:
        # 热力图使用原有的边界检查
        right = min(right, canvas_width)
        bottom = min(bottom, canvas_height)
    font_scale = max(0.7, imageScale)
    size = max(7, int(size * imageScale))

    # 从配置中读取颜色
    config = GlobalConfig()
    if imageIndex == 0:
        # 热力图标记
        rectColor = config.get("heat_rect_color", "#BCBCBC")
        textColor = config.get("heat_name_color", "#FFFFFF")
        tempColor = config.get("heat_temp_color", "#FF0000")
        name_font_size = config.get("heat_name_font_size", 12)
        temp_font_size = config.get("heat_temp_font_size", 10)
    else:
        # Layout图标记
        rectColor = config.get("layout_rect_color", "#BCBCBC")
        textColor = config.get("layout_name_color", "#FFFFFF")
        tempColor = config.get("layout_temp_color", "#FF0000")
        name_font_size = config.get("layout_name_font_size", 12)
        temp_font_size = config.get("layout_temp_font_size", 10)
    
    shadowColor = "#000000"  # 黑色

    # 绘制矩形框
    rectId = canvas.create_rectangle(left, top, right, bottom, outline=rectColor, width=2)

    # 计算三角形的三个顶点
    point1 = (cx, cy - size // 2)  # 顶点1 (尖角)
    point2 = (cx - size // 2, cy + size // 2)  # 顶点2 (左下角)
    point3 = (cx + size // 2, cy + size // 2)  # 顶点3 (右下角)

    # 绘制三角形
    triangleId = canvas.create_polygon([point1, point2, point3], fill=tempColor, outline=tempColor, width=1)

    # 绘制文本（带阴影效果）
    shadow_offset = 2  # 阴影偏移量

    # 使用配置的字体大小
    name_font_size_scaled = int(name_font_size * font_scale)
    temp_font_size_scaled = int(temp_font_size * font_scale)
    print(f"draw_canvas_item: name_font={name_font_size}*{font_scale:.2f}={name_font_size_scaled}, temp_font={temp_font_size}*{font_scale:.2f}={temp_font_size_scaled}")

    # 绘制实际文本
    # 温度文字置中于矩形框内
    tempTextId = canvas.create_text(cx, cy - 16 * imageScale, text=f'{max_temp}',
                       font=("Arial", temp_font_size_scaled), fill=tempColor, anchor="center")

    # 名称文字置中于矩形框上方外侧
    name_center_x = (left + right) / 2  # 矩形框水平中心
    nameId = canvas.create_text(name_center_x, top - 15 * imageScale, text=f'{name}',
                       font=("Arial", name_font_size_scaled, "bold"), fill=textColor, anchor="center")
    
    return rectId, triangleId, tempTextId, nameId


def update_canvas_item(canvas, item, imageScale=1, ):

    x1, y1, x2, y2, cx, cy, rectId, nameId, tempTextId, triangleId = (
        item.get("x1"), item.get("y1"), item.get("x2"), item.get("y2"), item.get("cx"), item.get("cy"), 
        item.get("rectId"), item.get("nameId"), item.get("tempTextId"), item.get("triangleId")
    )

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    x1 = int(x1 * imageScale)
    y1 = int(y1 * imageScale)
    x2 = min(canvas_width, int(x2 * imageScale))
    y2 = min(canvas_height, int(y2 * imageScale)) 
    cx = int(cx * imageScale)
    cy = int(cy * imageScale)
    size = 8  # 假设三角形大小为 100
    font_scale = max(0.7, imageScale)
    size = max(7, int(size * imageScale))

    # if(canvas_width < x2):
    # print("uuuuu -> ", x2, y2, imageScale)

    canvas.coords(rectId, x1, y1, x2, y2)

    # 名称文字置中于矩形框上方外侧
    name_center_x = (x1 + x2) / 2
    canvas.coords(nameId, name_center_x, y1 - 15 * imageScale)
    canvas.itemconfig(nameId, font=("Arial", int(28 * font_scale), "bold"))

    # 温度文字置中于矩形框内
    canvas.coords(tempTextId, cx, cy - 16 * imageScale)
    canvas.itemconfig(tempTextId, font=("Arial", int(14 * font_scale)))

    # 计算新的三角形三个顶点
    point1 = (cx, cy - size // 2)  # 顶点1 (尖角)
    point2 = (cx - size // 2, cy + size // 2)  # 顶点2 (左下角)
    point3 = (cx + size // 2, cy + size // 2)  # 顶点3 (右下角)
    canvas.coords(triangleId, point1, point2, point3)


def draw_points_on_canvas(canvas, points, radius_red=8, ring_width=2, scale_factor=1):
    """
    在给定的 Tkinter Canvas 上绘制内外圆圈，并返回处理后的图像。
    
    参数:
    - canvas: Tkinter Canvas 对象。
    - points: 一组点，每个点为 (x, y) 坐标。
    - radius_red: 内圆半径。
    - ring_width: 外圆宽度。
    - scale_factor: 缩放系数，默认为 8，用于提高绘制精度。
    """
    # 获取 Canvas 的宽高
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    # 增加绘制精度（类似于原始图像的缩放）
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    index = 0
    for point in points:
        index += 1
        # 计算缩放后的点位置
        point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))

        # 绘制外圆（白色圆环）
        canvas.create_oval(
            point_resized[0] - radius_red_resized - ring_width_resized,  # 左上角 x 坐标
            point_resized[1] - radius_red_resized - ring_width_resized,  # 左上角 y 坐标
            point_resized[0] + radius_red_resized + ring_width_resized,  # 右下角 x 坐标
            point_resized[1] + radius_red_resized + ring_width_resized,  # 右下角 y 坐标
            fill="white",  # 填充白色
            outline="white"  # 边框颜色为白色
        )

        # 绘制内圆（红色圆）
        canvas.create_oval(
            point_resized[0] - radius_red_resized,  # 左上角 x 坐标
            point_resized[1] - radius_red_resized,  # 左上角 y 坐标
            point_resized[0] + radius_red_resized,  # 右下角 x 坐标
            point_resized[1] + radius_red_resized,  # 右下角 y 坐标
            fill="red",  # 填充红色
            outline="red"  # 边框颜色为红色
        )

        # 绘制文本
        if index:
            canvas.create_text(
                point_resized[0],  # x 坐标偏移
                point_resized[1],  # y 坐标偏移
                text=str(index),  # 显示的文本为点的索引
                font=("Arial", 12),  # 设置字体和大小
                fill="white"  # 文本颜色为白色
            )


def draw_numpy_image_item(imageA, mark_rect_A, imageScale=1, imageIndex=0, size=8):
    imgWidth = imageA.shape[1]
    textScale = imgWidth / 1024
    size = size * textScale

    # 从配置中读取颜色
    config = GlobalConfig()
    if imageIndex == 0:
        # 热力图标记
        rect_color_hex = config.get("heat_rect_color", "#BCBCBC")
        name_color_hex = config.get("heat_name_color", "#FFFFFF")
        temp_color_hex = config.get("heat_temp_color", "#FF0000")
        name_font_size = config.get("heat_name_font_size", 12)
        temp_font_size = config.get("heat_temp_font_size", 10)
    else:
        # Layout图标记
        rect_color_hex = config.get("layout_rect_color", "#BCBCBC")
        name_color_hex = config.get("layout_name_color", "#FFFFFF")
        temp_color_hex = config.get("layout_temp_color", "#FF0000")
        name_font_size = config.get("layout_name_font_size", 12)
        temp_font_size = config.get("layout_temp_font_size", 10)
    
    # 转换十六进制颜色为RGB元组
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    rectColor = hex_to_rgb(rect_color_hex)
    textColor = hex_to_rgb(name_color_hex)
    tempColor = hex_to_rgb(temp_color_hex)
    shadowColor = (0, 0, 0)

    try:
        font = ImageFont.truetype("font/msyh.ttc", int(20 * textScale))
        print("Font loaded successfully.")
    except IOError as e:
        font = ImageFont.load_default()

    # 获取图像尺寸
    img_height, img_width = imageA.shape[:2]
    
    for item in mark_rect_A:
        # 获取 item 中的坐标和文本信息
        left, top, right, bottom, cx, cy, max_temp, name = item.get("x1"), item.get("y1"), item.get("x2"), item.get("y2"), item.get("cx"), item.get("cy"), item.get("max_temp"), item.get("name")
        left = int(left * imageScale)
        top = int(top * imageScale)
        right = int(right * imageScale)
        bottom = int(bottom * imageScale)
        cx = int(cx * imageScale)
        cy = int(cy * imageScale)

        # 对于Layout图，使用图像实际尺寸进行边界检查
        if imageIndex != 0:
            # 使用图像实际尺寸进行边界检查
            left = max(0, left)
            top = max(0, top)
            right = min(right, img_width)
            bottom = min(bottom, img_height)
            cx = max(0, min(cx, img_width - 1))
            cy = max(0, min(cy, img_height - 1))

        # 绘制矩形框
        cv2.rectangle(imageA, (left, top), (right, bottom), rectColor, 1, cv2.LINE_AA)

        # 计算三角形的三个顶点
        center = (cx, cy)
        point1 = (center[0], center[1] - size // 2)
        point2 = (center[0] - size // 2, center[1] + size // 2)
        point3 = (center[0] + size // 2, center[1] + size // 2)

        # 对于Layout图，检查三角形是否在边界内
        if imageIndex != 0:
            # 检查三角形顶点是否在边界内
            triangle_in_bounds = (
                0 <= point1[0] < img_width and 0 <= point1[1] < img_height and
                0 <= point2[0] < img_width and 0 <= point2[1] < img_height and
                0 <= point3[0] < img_width and 0 <= point3[1] < img_height
            )
            
            if not triangle_in_bounds:
                print(f"警告：三角形 {name} 超出Layout图边界，跳过绘制")
                # 跳过三角形绘制，但继续绘制文本
            else:
                # 将顶点连接成一个三角形
                pts = np.array([point1, point2, point3], np.int32)
                pts = pts.reshape((-1, 1, 2))
                # 绘制三角形
                cv2.fillPoly(imageA, [pts], color=tempColor)
        else:
            # 热力图直接绘制三角形
            pts = np.array([point1, point2, point3], np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.fillPoly(imageA, [pts], color=tempColor)

        # 使用 Pillow 绘制文本
        pil_image = Image.fromarray(cv2.cvtColor(imageA, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        # 使用配置的字体大小
        name_font_scale = (name_font_size / 12.0) * 20 * textScale
        temp_font_scale = (temp_font_size / 10.0) * 20 * textScale
        
        # 创建字体对象
        try:
            name_font = ImageFont.truetype("font/msyh.ttc", int(name_font_scale))
            temp_font = ImageFont.truetype("font/msyh.ttc", int(temp_font_scale))
        except IOError:
            name_font = ImageFont.load_default()
            temp_font = ImageFont.load_default()

        # 对于Layout图，检查文本位置是否在边界内
        if imageIndex != 0:
            # 计算文本位置
            temp_text_x = cx - int(16 * textScale)
            temp_text_y = cy - int(10 * textScale)
            name_text_x = left - int(10 * textScale)
            name_text_y = cy - int(40 * textScale)
            
            # 检查温度文本是否在边界内
            if 0 <= temp_text_x < img_width and 0 <= temp_text_y < img_height:
                # 绘制温度文本
                draw.text((temp_text_x, temp_text_y), str(max_temp), font=temp_font, fill=shadowColor)
                draw.text((temp_text_x, temp_text_y), str(max_temp), font=temp_font, fill=tempColor)
            else:
                print(f"警告：温度文本 {name} 超出Layout图边界，跳过绘制")
            
            # 检查名称文本是否在边界内
            if 0 <= name_text_x < img_width and 0 <= name_text_y < img_height:
                # 绘制名称文本
                draw.text((name_text_x, name_text_y), name, font=name_font, fill=textColor)
            else:
                print(f"警告：名称文本 {name} 超出Layout图边界，跳过绘制")
        else:
            # 热力图直接绘制文本
            draw.text((cx - int(16 * textScale), cy - int(10 * textScale)), str(max_temp), font=temp_font, fill=shadowColor)
            draw.text((cx - int(16 * textScale), cy - int(10 * textScale)), str(max_temp), font=temp_font, fill=tempColor)
            draw.text((left - int(10 * textScale), cy - int(40 * textScale)), name, font=name_font, fill=textColor)

        # pil_image.show()  # 直接显示 PIL 图像

        # 将 PIL 图像转换回 OpenCV 图像
        imageA = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # print(f"Text position: ({cx - int(16 * textScale)}, {cy - int(10 * textScale)})")
    return imageA

# 调用示例：
# 假设你有一个图像 `imageA` 和一个 `max_value`，你可以像这样调用该函数：
# draw_triangle_and_text(imageA, a_x=100, a_y=100, max_value=50)
