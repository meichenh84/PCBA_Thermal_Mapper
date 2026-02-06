#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
對齊點標記工具（獨立視窗版）(margin_point.py)

用途：
    提供一個獨立的影像檢視視窗，讓使用者在影像上標記最多 3 個對齊點。
    左鍵點擊新增標記點，右鍵點擊移除附近的標記點。
    關閉視窗時自動將標記點座標儲存為 CSV 檔案。
    此為早期版本，功能已整合至 point_margin.py（Canvas 嵌入版）。

在整個應用中的角色：
    - 早期的獨立標記工具，用於手動標記熱力圖與 Layout 圖上的對齊點
    - 已被 point_margin.py 取代（嵌入主介面的 Canvas 中使用）

關聯檔案：
    - point_margin.py：改良版本（嵌入 Canvas 使用）
    - point_transformer.py：使用標記的對齊點計算仿射變換矩陣
"""

import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox
import sys


class MarginPoint:
    """對齊點標記工具（獨立視窗版）。

    建立一個 1280x960 的 Canvas 視窗，顯示指定影像，
    讓使用者透過滑鼠左鍵標記、右鍵移除對齊點。

    屬性：
        root (tk.Tk): 根視窗
        points (list): 已標記的點座標列表 [(x, y), ...]
        mouse_coords (dict): 目前滑鼠座標 {'x': int, 'y': int}
        range (int): 右鍵移除的搜尋範圍（像素）
        image (numpy.ndarray): 原始影像（BGR 格式）
        points_path (str): 標記點 CSV 儲存路徑
        point_color (tuple): 標記點顏色（BGR 格式）
        canvas (tk.Canvas): 顯示影像的 Canvas 元件
        current_image (ImageTk.PhotoImage): 目前顯示的影像（防止被垃圾回收）
    """

    def __init__(self, image_path, root):
        """初始化對齊點標記工具。

        Args:
            image_path (str): 影像檔案路徑
            root (tk.Tk): 根視窗
        """
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
        """滑鼠點擊事件處理器。左鍵新增標記點（最多 3 個），右鍵移除附近的點。"""
        x, y = event.x, event.y
        if event.num == 1:  # 左鍵點擊
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
        """滑鼠移動事件處理器。更新座標顯示。"""
        self.mouse_coords['x'], self.mouse_coords['y'] = event.x, event.y
        self.update_image()

    def update_image(self):
        """重新繪製影像：在影像副本上繪製滑鼠座標文字和標記點。"""
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
        """視窗關閉事件。若已標記 3 個點以上，將座標儲存為 CSV 檔案。"""
        if len(self.points) >= 3:
            print("self.points -> ", self.points)
            np.savetxt(self.points_path, self.points, delimiter=',', fmt='%d')
        self.root.destroy()

    def show(self):
        """顯示影像並啟動主事件迴圈。"""
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
