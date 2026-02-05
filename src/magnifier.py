import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import cv2
from circle_ring_draw import draw_points_circle_ring_text

# 放大镜
class ImageMagnifier:
    def __init__(self, canvas, original_image, points, index):
        self.canvas = canvas

        self.original_image = original_image
        self.index = index
        self.update_img(points)

        # self.tk_imageA = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)))
        # self.tk_imageB = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(imageB_np, cv2.COLOR_BGR2RGB)))
        # self.original_image = original_image

        self.original_width, self.original_height = self.original_image.size
        self.x_min = (canvas.winfo_width() - self.original_width) // 2
        self.y_min = (canvas.winfo_height() - self.original_height) // 2
        self.x_max = self.x_min + self.original_width
        self.y_max = self.y_min + self.original_height
        self.rect_width = self.original_width // 10

        # 创建放大图像区域
        self.zoomed_image = None
        self.zoomed_image_id = self.canvas.create_image(0, 0, image=self.zoomed_image)

        # 创建放大镜矩形框
        # self.magnifier_rect = self.canvas.create_rectangle(self.x_start, self.y_start, self.rect_width, self.rect_width, outline="red", width=2)

        # 默认放大镜关闭
        self.is_zoom_enabled = False

        # 绑定鼠标移动事件
        # self.canvas.bind("<Motion>", self.on_mouse_move)
        # self.canvas.bind("<Enter>", self.on_mouse_enter)
        # self.canvas.bind("<Leave>", self.on_mouse_leave)

    def toggle_magnifier(self, enable):
        """通过外部控制开关启用或禁用放大镜功能"""
        self.is_zoom_enabled = bool(enable)
        if not self.is_zoom_enabled:
            self.canvas.itemconfig(self.zoomed_image_id, image="")  # 禁用时清除放大镜
            self.canvas.unbind("<Motion>")  # 移除鼠标移动事件
            self.canvas.unbind("<Enter>")  # 移除鼠标移动事件
            self.canvas.unbind("<Leave>")  # 移除鼠标离开事件
        else:
            # 如果启用放大镜，重新绑定事件
            self.canvas.bind("<Motion>", self.on_mouse_move)
            self.canvas.bind("<Enter>", self.on_mouse_enter)
            self.canvas.bind("<Leave>", self.on_mouse_leave)

    def update_img(self, points):
        image_np = np.array(self.original_image.copy())  # 使用 .copy() 确保 image_np 是原图的副本
        # image_np = np.array(self.original_image)
        if self.index == 1:
            point_color = (0, 0, 255)
        else:
            point_color = (0, 0, 0)   
        image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        
        # 只有在有points时才绘制点标记
        if points and len(points) > 0:
            image_np = draw_points_circle_ring_text(image_np, points)
        
        self.mix_image = Image.fromarray(cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB))

    def update_points(self, points):
        self.update_img(points)

    def on_mouse_move(self, event):
        """鼠标移动时更新放大镜区域"""
        # print("on_mouse_move :", self.is_zoom_enabled)
        if not self.is_zoom_enabled:
            return  # 如果放大镜被禁用，则不做任何事情

        x, y = event.x, event.y
        if x < self.x_min or x > self.x_max or y < self.y_min or y > self.y_max:
            self.on_mouse_leave(None)
            return

        double_rect_width = self.rect_width * 2
        half_rect_width = self.rect_width // 2

        # 计算理想的裁剪区域（相对于原图的坐标）
        center_x = x - self.x_min
        center_y = y - self.y_min

        # 不再限制中心点，让放大镜始终跟随游标
        # 计算裁剪区域（可能超出图像边界）
        left = center_x - half_rect_width
        top = center_y - half_rect_width
        right = center_x + half_rect_width
        bottom = center_y + half_rect_width

        # 创建带背景色的画布，用于处理超出边界的情况
        cropped_image = Image.new('RGB', (self.rect_width, self.rect_width), (50, 50, 50))  # 深灰色背景

        # 计算实际可裁剪的区域（在图像范围内的部分）
        src_left = max(0, left)
        src_top = max(0, top)
        src_right = min(self.original_width, right)
        src_bottom = min(self.original_height, bottom)

        # 计算粘贴到目标画布的位置
        dst_left = max(0, -left)
        dst_top = max(0, -top)

        # 只有当有有效的裁剪区域时才进行裁剪和粘贴
        if src_right > src_left and src_bottom > src_top:
            # 从原图裁剪有效区域
            valid_crop = self.mix_image.crop((src_left, src_top, src_right, src_bottom))
            # 粘贴到带背景的画布上
            cropped_image.paste(valid_crop, (int(dst_left), int(dst_top)))

        # 放大图像，使用LANCZOS进行高质量缩放（等比例放大，不会扭曲）
        zoomed_image = cropped_image.resize((double_rect_width, double_rect_width), Image.Resampling.LANCZOS)


        # 创建一个和缩放后图像相同大小的白色背景
        circle_mask = Image.new('L', zoomed_image.size, 0)  # 'L' 表示灰度图，0表示透明背景
        draw = ImageDraw.Draw(circle_mask)
        draw.ellipse((0, 0, double_rect_width, double_rect_width), fill=255)  # 画一个白色圆形

        # 将圆形遮罩应用到缩放后的图像上
        result_image = Image.composite(zoomed_image, Image.new('RGBA', zoomed_image.size), circle_mask) 

        # 转换为Tkinter支持的格式
        self.zoomed_image = ImageTk.PhotoImage(result_image)

        # print("on_mouse_move222 :", self.zoomed_image, self.canvas)

        # 更新放大镜区域的图像
        self.canvas.itemconfig(self.zoomed_image_id, image=self.zoomed_image)

        # 更新放大镜位置
        self.canvas.coords(self.zoomed_image_id, x + 0, y + 0)  # 放大镜框的位置

    def on_mouse_enter(self, event):
        # print("on_mouse_enter :", self.is_zoom_enabled)
        if self.is_zoom_enabled:
            self.x_min = (self.canvas.winfo_width() - self.original_width) // 2
            self.y_min = (self.canvas.winfo_height() - self.original_height) // 2
            self.x_max = self.x_min + self.original_width
            self.y_max = self.y_min + self.original_height

    def on_mouse_leave(self, event):
        """鼠标离开时清空放大镜图像"""
        if self.is_zoom_enabled:
            self.canvas.itemconfig(self.zoomed_image_id, image="")


if __name__ == "__main__":
    # 创建主窗口（root）和 Canvas
    root = tk.Tk()

    # 加载原始图片（注意替换成你自己的图片路径）
    original_image = Image.open("imageA.jpg")
        
    # 创建 Canvas 实例
    canvas = tk.Canvas(root, width=original_image.width, height=original_image.height)
    canvas.pack()

    # 将图像显示在 Canvas 上
    image_tk = ImageTk.PhotoImage(original_image)
    canvas.create_image(0, 0, anchor="nw", image=image_tk)

    # 创建 ImageZoomApp 实例
    app = ImageMagnifier(canvas, original_image)

    # 外部控制放大镜功能
    # 例如：启用放大镜
    app.toggle_magnifier(1)

    # 运行窗口
    root.mainloop()
