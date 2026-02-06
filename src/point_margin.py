#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
對齊點標記工具（Canvas 嵌入版）(point_margin.py)

用途：
    提供嵌入到主介面 Canvas 中的對齊點標記功能。
    讓使用者在熱力圖或 Layout 圖上標記最多 3 個對齊點。
    左鍵點擊新增標記點，右鍵點擊移除附近的標記點。
    相比 margin_point.py（獨立視窗版），本版本直接嵌入主介面使用。

在整個應用中的角色：
    - 被 main.py 用於在兩張圖片上分別標記對齊點
    - 標記的 3 個對齊點用於計算仿射變換矩陣（point_transformer.py）

關聯檔案：
    - main.py：建立 MarginPoint 實例並管理標記流程
    - point_transformer.py：使用標記的對齊點計算仿射變換
    - constants.py：引用常數定義
    - margin_point.py：早期獨立視窗版本
"""

import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox
import sys
from constants import Constants


class MarginPoint:
    """對齊點標記工具（Canvas 嵌入版）。

    直接嵌入到主介面的 Canvas 中，提供左鍵標記、右鍵移除的交互功能。
    支援在 NumPy 陣列格式的影像上進行標記。

    屬性：
        root (tk.Widget): 根視窗或父元件
        canvas (tk.Canvas): 繫結的 Canvas 元件
        points (list): 已標記的點座標列表 [(x, y), ...]
        mouse_coords (dict): 目前滑鼠座標
        range (int): 右鍵移除的搜尋範圍（像素）
        image (numpy.ndarray): 原始影像（BGR 格式）
        point_color (tuple): 標記點顏色（index=0 紅色，index=1 黑色）
        current_image (ImageTk.PhotoImage): 目前顯示的影像
    """

    def __init__(self, root, canvas, imageNumpy, index = 0):
        """初始化對齊點標記工具。

        Args:
            root (tk.Widget): 根視窗或父元件
            canvas (tk.Canvas): 要繫結的 Canvas 元件
            imageNumpy (numpy.ndarray): 影像資料（BGR 格式）
            index (int): 影像索引（0=使用紅色標記，1=使用黑色標記）
        """
        self.root = root
        self.points = []
        self.mouse_coords = {'x': 0, 'y': 0}
        self.range = 16
        self.current_image = None  # 初始化图像引用

        # 读取和调整图像
        self.image = imageNumpy
        self.point_color = (0, 0, 255) if index == 0 else (0, 0, 0)


        # 创建 Canvas 用于显示图像
        # self.canvas = tk.Canvas(self.root, width=1280, height=960)
        # self.canvas.pack()

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

        # 繪製滑鼠座標文字
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
