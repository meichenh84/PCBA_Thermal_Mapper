# image_viewer.py

import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox
import sys

class MarginPoint:
    def __init__(self, image_path, root):
        self.root = root
        self.points = []
        self.mouse_coords = {'x': 0, 'y': 0}
        self.range = 16
        self.current_image = None  # 初始化图像引用

        # 读取和调整图像
        self.image = cv2.imread(image_path)
        self.image = cv2.resize(self.image, (1280, 960))
        self.points_path = image_path + "_points.csv"
        self.point_color = (0, 0, 255) if "B" in image_path else (0, 0, 0)

        # 创建 Tkinter 窗口
        self.root.title(image_path)

        # 创建 Canvas 用于显示图像
        self.canvas = tk.Canvas(self.root, width=1280, height=960)
        self.canvas.pack()

        # 绑定鼠标事件
        self.canvas.bind("<Button-1>", self.mouse_click)  # 左键
        self.canvas.bind("<Button-3>", self.mouse_click)  # 右键
        self.canvas.bind("<Motion>", self.mouse_move)     # 鼠标移动

        # 关闭窗口时保存数据
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def mouse_click(self, event):
        x, y = event.x, event.y
        if event.num == 1:  # 左键点击
            if len(self.points) >= 3:
                messagebox.showinfo("提示", "最多标记三个点")
                return
            self.points.append((x, y))
            # print(f"左键点击: ({x}, {y})")
        elif event.num == 3:  # 右键点击
            self.points = [(cx, cy) for cx, cy in self.points if not (x - self.range <= cx <= x + self.range and y - self.range <= cy <= y + self.range)]
            # print(f"右键点击: ({x}, {y})")
        self.update_image()

    def mouse_move(self, event):
        self.mouse_coords['x'], self.mouse_coords['y'] = event.x, event.y
        self.update_image()

    def update_image(self):
        img_copy = self.image.copy()
        
        # 绘制鼠标坐标
        cv2.putText(img_copy, f"Mouse X: {self.mouse_coords['x']}, Y: {self.mouse_coords['y']}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 绘制点
        for point in self.points:
            cv2.circle(img_copy, point, 4, self.point_color, -1)  # 绿色圆圈

        # 将 OpenCV 图像转换为 Tkinter 可显示的格式
        img_tk = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(img_copy, cv2.COLOR_BGR2RGB)))
        
        self.current_image = img_tk  # 保存图像引用
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image)

    def on_closing(self):
        if len(self.points) >= 3:
            print("self.points -> ", self.points)
            np.savetxt(self.points_path, self.points, delimiter=',', fmt='%d')
        self.root.destroy()

    def show(self):
        self.update_image()  # 初始化显示图像
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    if len(sys.argv) > 1:
        # 获取传入的参数
        imagePath = sys.argv[1]
        marginPoint = MarginPoint(imagePath, root)
        marginPoint.show()
    else:
        marginPoint = MarginPoint('imageA.jpg', root)
        marginPoint.show()
    root.mainloop()
