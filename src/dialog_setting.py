#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顯示設定對話框模組 (dialog_setting.py)

用途：
    提供一個彈出式設定對話框，讓使用者調整熱力圖和 Layout 圖上
    矩形標記的顏色、字型大小等顯示設定。設定項包括：
    - 熱力圖標記：矩形框顏色、元器件名稱顏色/字型、最高溫度顏色/字型、
      選中框顏色、錨點顏色/半徑
    - Layout 圖標記：矩形框顏色、元器件名稱顏色/字型、最高溫度顏色/字型

在整個應用中的角色：
    - 當使用者點擊「設定」按鈕時彈出，修改的設定會儲存至 config.json
    - 設定立即生效，不需重啟應用

關聯檔案：
    - main.py：建立 SettingDialog 實例並傳入回呼函式
    - config.py：透過 GlobalConfig 讀取/儲存設定值
    - draw_rect.py：使用本模組儲存的顏色設定繪製標記

UI 元件對應命名：
    - dialog (tk.Toplevel): 設定對話框視窗
    - heat_frame (ttk.LabelFrame): 「熱力圖標記」設定群組框
    - layout_frame (ttk.LabelFrame): 「Layout 圖標記」設定群組框
    - color_preview (tk.Label): 顏色預覽方塊
    - rgb_entry (tk.Entry): RGB 色碼輸入框
    - color_button (tk.Button): 「選擇顏色」按鈕
    - confirm_button (tk.Button): 「確認」按鈕
    - cancel_button (tk.Button): 「取消」按鈕
"""

import tkinter as tk
from tkinter import ttk, colorchooser
from config import GlobalConfig


class SettingDialog:
    """顯示設定對話框。

    管理熱力圖和 Layout 圖的標記顏色、字型大小等設定。
    使用單例模式防止重複開啟，修改後儲存至 config.json。

    屬性：
        master (tk.Widget): 主視窗元件
        settings_button (tk.Button): 觸發本對話框的設定按鈕（用於定位）
        callback (callable): 確認後的回呼函式
        dialog (tk.Toplevel): 對話框視窗實例
        config (GlobalConfig): 全域配置管理器
        color_settings (dict): 目前的顏色與字型設定值
    """

    def __init__(self, master, settings_button, callback):
        """初始化設定對話框。

        Args:
            master (tk.Widget): 主視窗元件
            settings_button (tk.Button): 設定按鈕元件（用於計算對話框位置）
            callback (callable): 確認後的回呼函式
        """
        self.master = master
        self.settings_button = settings_button
        self.callback = callback  # 接收外部传入的回调函数
        self.dialog_result = {}
        self.config = GlobalConfig()
        self.dialog = None  # 对话框实例，用于单例模式

    def open(self):
        """開啟設定對話框。若已存在則提到前台，否則建立新對話框。"""
        if self.dialog is not None and self.dialog.winfo_exists():
            # 如果对话框已存在，将其提到前台
            self.dialog.lift()
            self.dialog.focus_force()
            return
        
        # 创建新的对话框
        self.dialog = tk.Toplevel(self.master)
        self.dialog.title("设置")
        
        # 设置对话框关闭时的回调
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_dialog_close)

        # 获取设置按钮的坐标，显示在按钮下方
        x = self.settings_button.winfo_rootx() - 7  # 按钮的 x 坐标
        y = self.settings_button.winfo_rooty() + self.settings_button.winfo_height() + 5  # 按钮下方的位置

        # 设置对话框的位置和大小
        self.dialog.geometry(f"500x660+{x}+{y}")

        # 创建主框架
        main_frame = tk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # 加载颜色配置
        self.load_color_settings()

        # 热力图标记设置
        heat_frame = ttk.LabelFrame(main_frame, text="热力图标记", padding=8)
        heat_frame.pack(fill=tk.X, padx=5, pady=5)

        # 矩形框颜色
        self.create_color_setting(heat_frame, "矩形框颜色", "heat_rect_color", "#BCBCBC", 0)
        # 元器件名称颜色
        self.create_color_setting(heat_frame, "元器件名称颜色", "heat_name_color", "#FFFFFF", 1)
        # 元器件名称字体大小
        self.create_font_setting(heat_frame, "元器件名称字体大小(px)", "heat_name_font_size", 12, 2)
        # 最高温度颜色
        self.create_color_setting(heat_frame, "最高温度颜色", "heat_temp_color", "#FF0000", 3)
        # 最高温度字体大小
        self.create_font_setting(heat_frame, "最高温度字体大小(px)", "heat_temp_font_size", 10, 4)
        # 选中矩形框颜色
        self.create_color_setting(heat_frame, "选中矩形框颜色", "heat_selected_color", "#4A90E2", 5)
        # 选中矩形框锚点颜色
        self.create_color_setting(heat_frame, "选中矩形框锚点颜色", "heat_anchor_color", "#FF0000", 6)
        # 选中矩形框锚点半径
        self.create_font_setting(heat_frame, "选中矩形框锚点半径(px)", "heat_anchor_radius", 4, 7)
        # 矩形框线粗细
        self.create_width_setting(heat_frame, "矩形框线粗细(px)", "heat_rect_width", 2, 8)

        # Layout图标记设置
        layout_frame = ttk.LabelFrame(main_frame, text="Layout图标记", padding=8)
        layout_frame.pack(fill=tk.X, padx=5, pady=5)

        # 矩形框颜色
        self.create_color_setting(layout_frame, "矩形框颜色", "layout_rect_color", "#BCBCBC", 0)
        # 元器件名称颜色
        self.create_color_setting(layout_frame, "元器件名称颜色", "layout_name_color", "#FFFFFF", 1)
        # 元器件名称字体大小
        self.create_font_setting(layout_frame, "元器件名称字体大小(px)", "layout_name_font_size", 12, 2)
        # 最高温度颜色
        self.create_color_setting(layout_frame, "最高温度颜色", "layout_temp_color", "#FF0000", 3)
        # 最高温度字体大小
        self.create_font_setting(layout_frame, "最高温度字体大小(px)", "layout_temp_font_size", 10, 4)
        # 矩形框线粗细
        self.create_width_setting(layout_frame, "矩形框线粗细(px)", "layout_rect_width", 2, 5)

        # 确认按钮
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)

        confirm_button = tk.Button(button_frame, text="确认", command=self.on_confirm, width=10)
        confirm_button.pack(side=tk.RIGHT, padx=5)

        cancel_button = tk.Button(button_frame, text="取消", command=self.on_dialog_close, width=10)
        cancel_button.pack(side=tk.RIGHT, padx=5)

        # 设置对话框为模态，但不阻塞主线程
        self.dialog.transient(self.master)
        self.dialog.grab_set()

    def load_color_settings(self):
        """從 GlobalConfig 載入所有顏色和字型設定值。"""
        # 默认颜色配置
        self.color_settings = {
            # 热力图标记
            "heat_rect_color": self.config.get("heat_rect_color", "#BCBCBC"),
            "heat_name_color": self.config.get("heat_name_color", "#FFFFFF"),
            "heat_name_font_size": self.config.get("heat_name_font_size", 12),
            "heat_temp_color": self.config.get("heat_temp_color", "#FF0000"),
            "heat_temp_font_size": self.config.get("heat_temp_font_size", 10),
            "heat_selected_color": self.config.get("heat_selected_color", "#4A90E2"),
            "heat_anchor_color": self.config.get("heat_anchor_color", "#FF0000"),
            "heat_anchor_radius": self.config.get("heat_anchor_radius", 4),
            "heat_rect_width": self.config.get("heat_rect_width", 2),

            # Layout图标记
            "layout_rect_color": self.config.get("layout_rect_color", "#BCBCBC"),
            "layout_name_color": self.config.get("layout_name_color", "#FFFFFF"),
            "layout_name_font_size": self.config.get("layout_name_font_size", 12),
            "layout_temp_color": self.config.get("layout_temp_color", "#FF0000"),
            "layout_temp_font_size": self.config.get("layout_temp_font_size", 10),
            "layout_rect_width": self.config.get("layout_rect_width", 2),
        }

    def create_color_setting(self, parent, label_text, config_key, default_color, row):
        """建立顏色設定控件（標籤 + 顏色預覽 + RGB 輸入框 + 選擇按鈕）。

        Args:
            parent (tk.Widget): 父元件
            label_text (str): 設定項目名稱
            config_key (str): 配置鍵名（如 "heat_rect_color"）
            default_color (str): 預設顏色值
            row (int): Grid 行號
        """
        frame = tk.Frame(parent)
        frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        parent.grid_columnconfigure(0, weight=1)

        # 标签
        label = tk.Label(frame, text=label_text, width=20, anchor="w")
        label.pack(side=tk.LEFT, padx=(0, 10))

        # 颜色显示框
        color_frame = tk.Frame(frame, width=30, height=25, relief="sunken", borderwidth=1)
        color_frame.pack(side=tk.LEFT, padx=(0, 5))
        color_frame.pack_propagate(False)

        # 获取当前颜色值
        current_color = self.color_settings.get(config_key, default_color)
        
        # 颜色预览
        color_preview = tk.Label(color_frame, bg=current_color, width=4, height=1)
        color_preview.pack(fill=tk.BOTH, expand=True)

        # RGB输入框
        rgb_entry = tk.Entry(frame, width=10)
        rgb_entry.insert(0, current_color)
        rgb_entry.pack(side=tk.LEFT, padx=(0, 5))

        def update_color_preview():
            color_value = rgb_entry.get()
            try:
                color_preview.config(bg=color_value)
                self.color_settings[config_key] = color_value
            except:
                pass

        # 绑定RGB输入框变化事件
        rgb_entry.bind('<KeyRelease>', lambda e: update_color_preview())

        # 颜色选择按钮
        def choose_color():
            color = colorchooser.askcolor(title=f"选择{label_text}", color=current_color)[1]
            if color:
                rgb_entry.delete(0, tk.END)
                rgb_entry.insert(0, color)
                update_color_preview()

        color_button = tk.Button(frame, text="选择颜色", command=choose_color, width=8)
        color_button.pack(side=tk.LEFT, padx=(5, 0))

    def create_font_setting(self, parent, label_text, config_key, default_value, row):
        """建立字型大小設定控件（標籤 + 數值輸入框）。

        Args:
            parent (tk.Widget): 父元件
            label_text (str): 設定項目名稱
            config_key (str): 配置鍵名（如 "heat_name_font_size"）
            default_value (int): 預設字型大小
            row (int): Grid 行號
        """
        frame = tk.Frame(parent)
        frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        parent.grid_columnconfigure(0, weight=1)

        # 标签
        label = tk.Label(frame, text=label_text, width=20, anchor="w")
        label.pack(side=tk.LEFT, padx=(0, 10))

        # 数值输入框
        value_entry = tk.Entry(frame, width=10)
        current_value = self.color_settings.get(config_key, default_value)
        value_entry.insert(0, str(current_value))
        value_entry.pack(side=tk.LEFT, padx=(0, 5))

        def update_font_value():
            try:
                value = int(value_entry.get())
                self.color_settings[config_key] = value
            except ValueError:
                pass

        # 绑定输入框变化事件
        value_entry.bind('<KeyRelease>', lambda e: update_font_value())

    def create_width_setting(self, parent, label_text, config_key, default_value, row):
        """建立框線粗細設定控件（標籤 + 下拉選單 1~5）。

        Args:
            parent (tk.Widget): 父元件
            label_text (str): 設定項目名稱
            config_key (str): 配置鍵名（如 "heat_rect_width"）
            default_value (int): 預設粗細值
            row (int): Grid 行號
        """
        frame = tk.Frame(parent)
        frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        parent.grid_columnconfigure(0, weight=1)

        # 标签
        label = tk.Label(frame, text=label_text, width=20, anchor="w")
        label.pack(side=tk.LEFT, padx=(0, 10))

        # 下拉选单
        current_value = self.color_settings.get(config_key, default_value)
        width_var = tk.StringVar(value=str(int(current_value)))
        width_combo = ttk.Combobox(frame, textvariable=width_var, values=["1", "2", "3", "4", "5"],
                                   width=7, state="readonly")
        width_combo.pack(side=tk.LEFT, padx=(0, 5))

        def on_width_change(event=None):
            try:
                value = int(width_var.get())
                self.color_settings[config_key] = value
            except ValueError:
                pass

        width_combo.bind('<<ComboboxSelected>>', on_width_change)

    def on_confirm(self):
        """確認按鈕點擊事件。儲存所有設定至 config.json 並通知主介面刷新。"""
        # 保存放大镜开关设置
        self.config.set("magnifier_switch", True)
        
        # 保存所有颜色和字体设置
        for key, value in self.color_settings.items():
            self.config.set(key, value)
        
        # 同步主窗口中的配置缓存，确保即时生效
        try:
            if hasattr(self.master, 'config') and self.master.config:
                self.master.config.set("magnifier_switch", True)
                for key, value in self.color_settings.items():
                    self.master.config.set(key, value)
        except Exception:
            pass
        
        # 保存到JSON文件
        self.config.save_to_json()
        
        # 即时生效：通知主界面刷新显示
        try:
            if hasattr(self.master, 'update_content'):
                self.master.update_content()
        except Exception:
            pass

        # 关闭对话框
        self.on_dialog_close()

    def on_dialog_close(self):
        """對話框關閉時的回呼。銷毀視窗並重設實例變數。"""
        if self.dialog is not None:
            self.dialog.destroy()
            self.dialog = None
