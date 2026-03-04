#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元器件編輯對話框模組 (dialog_component_setting.py)

用途：
    提供一個彈出式對話框，讓使用者編輯單一元器件的屬性，
    目前允許修改的欄位為「器件名稱」和「最高溫度」（唯讀）。
    其他座標欄位（x1, y1, x2, y2, cx, cy）保留不變。

在整個應用中的角色：
    - 當使用者在主介面雙擊某個矩形標記時，彈出此對話框
    - 編輯完成後透過 callback 回傳修改結果給主程式

關聯檔案：
    - main.py：在雙擊矩形框時建立本對話框
    - editor_rect.py：管理矩形標記，可能觸發本對話框
    - bean/canvas_rect_item.py：提供 oldRect 資料來源

UI 元件對應命名：
    - fields (list): 輸入欄位列表，每項包含 (key, label, Entry 元件)
    - confirm_button (tk.Button): 「確認」按鈕
    - frame (tk.Frame): 主要內容框架（含 20px 內邊距）
"""

import tkinter as tk
from tkinter import messagebox


class ComponentSettingDialog(tk.Toplevel):
    """元器件屬性編輯對話框。

    繼承自 tk.Toplevel，建立一個獨立的彈出視窗。
    顯示元器件的名稱和最高溫度供編輯，確認後透過 callback 回傳結果。

    屬性：
        oldRect (dict): 原始的矩形框資料字典
        callback (callable): 確認後的回呼函式，接收修改後的資料字典
        fields (list): 輸入欄位列表 [(key, label, Entry), ...]
    """

    def __init__(self, parent, oldRect, callback):
        """初始化元器件編輯對話框。

        Args:
            parent (tk.Widget): 父視窗元件
            oldRect (dict): 原始矩形框資料（包含 name, max_temp, x1, y1 等）
            callback (callable): 確認後的回呼函式
        """
        super().__init__(parent)
        self.title("Edit Area")
        # self.window_width = 350
        # self.window_height = 320
        
        # 设置窗口大小并使其居中
        # self.geometry("300x400")
        # self.center_window()
        # 创建根窗口
        # root = tk.Tk()
        # 设置窗口的外边距
        frame = tk.Frame(self, padx=20, pady=20)  # 通过 Frame 设置内边距
        frame.pack(fill=tk.BOTH, expand=True)

        # 创建字段标签和输入框（只显示器件名称和最高温度）
        self.fields = [
            ("name", "器件名称: ", tk.Entry(frame)),
            ("max_temp", "最高温度: ", tk.Entry(frame)),
            ("_orient", "Orient.: ", tk.Entry(frame)),
            # 其他字段暂时注释掉
            # ("cx", "最高温度 x坐标: ", tk.Entry(frame)),
            # ("cy", "最高温度 y坐标: ", tk.Entry(frame)),
            # ("x1", "左上角 x坐标: ", tk.Entry(frame)),
            # ("y1", "左上角 y坐标: ", tk.Entry(frame)),
            # ("x2", "右下角 x坐标: ", tk.Entry(frame)),
            # ("y2", "右下角 y坐标: ", tk.Entry(frame))
        ]
        # print("xxx ", oldRect, callback)
        self.oldRect  = oldRect
        self.callback = callback

        # 创建输入字段布局
        for idx, (key, label, entry) in enumerate(self.fields):
            tk.Label(frame, text=label).grid(row=idx, column=0, padx=10, pady=5, sticky="e")
            if oldRect:
                if key == "_orient":
                    # Orient. 顯示原始值，從 angle 欄位讀取
                    raw_orient = oldRect.get("angle", None)
                    import math
                    if raw_orient is None or (isinstance(raw_orient, float) and math.isnan(raw_orient)):
                        entry.insert(0, "空值")
                    else:
                        entry.insert(0, raw_orient)
                    entry.config(state='readonly')
                else:
                    entry.insert(0, oldRect[key])  # 将 oldRect[key] 的值插入到 entry 中
                    if key == "max_temp":  # 最高温度字段设为只读
                        entry.config(state='readonly')
            entry.grid(row=idx, column=1, padx=10, pady=5)

        # 创建确认按钮
        self.confirm_button = tk.Button(frame, text="   确认   ", command=self.on_confirm)
        self.confirm_button.grid(row=len(self.fields), column=0, columnspan=2, pady=(20, 0))

    def center_window(self):
        """將對話框置中於螢幕。"""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width - self.window_width) // 2
        y = (screen_height - self.window_height) // 2

        # 设置窗口位置
        self.geometry(f'{self.window_width}x{self.window_height}+{x}+{y}')

    def on_confirm(self):
        """確認按鈕點擊事件處理器。驗證輸入值、保留原始座標資料，並透過 callback 回傳結果。"""
        values = {}
        for key, label, entry in self.fields:
            if key == "_orient":  # Orient. 為唯讀顯示欄位，不回傳
                continue
            value = entry.get()
            if key == "name":  # 对"器件名称"字段不做类型转换，保留字符串
                values[key] = value
            else:
                try:
                    # 尝试转换为float，如果失败，则提示错误
                    values[key] = float(value)
                except ValueError:
                    messagebox.showerror("输入错误", f"'{label}' 必须是数字类型！")
                    return
        
        # 🔥 重要：保留原始矩形框的所有坐标数据
        # 对话框只允许修改name和max_temp，其他字段保持不变
        if self.oldRect:
            # 保留oldRect中所有未在对话框中显示的字段
            for key, value in self.oldRect.items():
                if key not in values:
                    values[key] = value
        
        # 由于只显示器件名称和最高温度，不需要坐标验证
        # 注释掉坐标验证逻辑
        # if values["x1"] >= values["x2"]:
        #     messagebox.showerror("输入错误", "左上角x坐标必须小于右下角x坐标")
        #     return
        # 
        # if values["y1"] >= values["y2"]:
        #     messagebox.showerror("输入错误", "左上角y坐标必须小于右下角y坐标")
        #     return

        # 输出所有输入的数据
        print("输入的数据：")
        for key, value in values.items():
            print(f"{key}: {value}")
        # 调用外部回调函数，并传递结果

        if self.callback:
            self.callback(values)

        # 关闭对话框
        self.destroy()


if __name__ == "__main__":
    dialog = ComponentSettingDialog()
    dialog.grab_set()  # 禁用主窗口，确保只能与对话框交互
    dialog.mainloop()
