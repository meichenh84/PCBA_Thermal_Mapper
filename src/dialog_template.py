#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
溫度過濾與 PCB 參數設定對話框模組 (dialog_template.py)

用途：
    提供「溫度過濾」對話框，讓使用者設定元器件自動識別的參數，包括：
    - 溫度過濾範圍（最低/最高溫度閾值）
    - PCB 參數（長度、寬度、座標原點位置）
    設定完成後透過 callback 傳遞參數，並儲存至溫度配置檔。

在整個應用中的角色：
    - 當使用者點擊「溫度過濾」按鈕時彈出
    - 設定的參數被傳遞給 recognize_image.py 進行元器件識別

關聯檔案：
    - main.py：建立 TemplateDialog 實例
    - temperature_config_manager.py：儲存/讀取溫度配置參數
    - config.py：全域配置管理器
    - recognize_image.py：使用本對話框設定的參數進行識別

UI 元件對應命名：
    - dialog (tk.Toplevel): 對話框視窗
    - min_temp_entry (ttk.Entry): 最低溫度輸入框
    - max_temp_entry (ttk.Entry): 最高溫度輸入框
    - p_w_entry (ttk.Entry): PCB 長度（mm）輸入框
    - p_h_entry (ttk.Entry): PCB 寬度（mm）輸入框
    - p_origin_var (tk.StringVar): 座標原點下拉選單變數
    - confirm_button (tk.Button): 「確認」按鈕
"""

import tkinter as tk
from tkinter import ttk
from config import GlobalConfig
from temperature_config_manager import TemperatureConfigManager


class TemplateDialog:
    """溫度過濾與 PCB 參數設定對話框。

    顯示溫度過濾範圍、PCB 尺寸、座標原點等設定項，
    確認後儲存至配置檔並透過 callback 傳遞結果。

    屬性：
        master (tk.Widget): 主視窗元件
        settings_button (tk.Button): 觸發本對話框的按鈕（用於定位）
        callback (callable): 確認後的回呼函式
        config (GlobalConfig): 全域配置管理器
        temp_config (TemperatureConfigManager): 溫度配置管理器
        dialog_result (dict): 對話框結果字典
    """

    def __init__(self, master, settings_button, callback, current_folder_path=None):
        """初始化溫度過濾對話框。

        Args:
            master (tk.Widget): 主視窗元件
            settings_button (tk.Button): 觸發按鈕（用於計算對話框位置）
            callback (callable): 確認後的回呼函式，接收參數字典
            current_folder_path (str|None): 目前的資料夾路徑（用於載入配置）
        """
        self.master = master
        self.settings_button = settings_button
        self.callback = callback  # 接收外部传入的回调函数
        self.config = GlobalConfig()
        
        # 初始化温度配置管理器
        print(f"初始化温度配置管理器，文件夹路径: {current_folder_path}")
        try:
            if current_folder_path:
                self.temp_config = TemperatureConfigManager(current_folder_path)
                print("使用文件夹路径初始化配置管理器")
            else:
                # 如果没有文件夹路径，创建一个临时的配置管理器
                self.temp_config = TemperatureConfigManager()
                # 使用默认配置
                self.temp_config.config_data = self.temp_config.default_config.copy()
                print("使用默认配置初始化配置管理器")
        except Exception as e:
            print(f"初始化温度配置管理器时出错: {e}")
            # 创建一个简单的配置对象
            self.temp_config = type('TempConfig', (), {
                'get_all_parameters': lambda: {
                    "min_temp": 50.0, "max_temp": 80.0, "color": "绿色",
                    "max_ratio": 10.0, "auto_reduce": 1.0,
                    "p_w": 237.0, "p_h": 194.0, "p_origin": "左下",
                    "p_origin_offset_x": 0.0, "p_origin_offset_y": 0.0,
                    "c_padding_left": 0.0, "c_padding_top": 0.0, "c_padding_right": 0.0, "c_padding_bottom": 0.0
                },
                'get_file_info_display': lambda: "未加载文件",
                'save_parameters': lambda x: None
            })()
        
        self.dialog_result = {}

    def on_dialog_close(self):
        """對話框關閉時的回呼。收集參數並儲存。"""
        self.get_params()
        self.config.update(self.dialog_result)
        self.config.save_to_csv()
        self.dialog.destroy()

    def open(self):
        """開啟溫度過濾對話框，建立所有 UI 元件並顯示。"""
        print("開始建立溫度過濾對話框...")
        try:
            # 创建新的对话框
            dialog = tk.Toplevel(self.master)
            dialog.title("温度过滤")
            self.dialog = dialog
            print("对话框创建成功")
        except Exception as e:
            print(f"创建对话框时出错: {e}")
            import traceback
            traceback.print_exc()
            return
         # 监听窗口关闭事件
        # dialog.protocol("WM_DELETE_WINDOW", self.on_dialog_close)

        # 获取温度过滤按钮的坐标，显示在按钮下方5px（与设置弹窗一致）
        x = self.settings_button.winfo_rootx()  # 按钮的 x 坐标
        y = self.settings_button.winfo_rooty() + self.settings_button.winfo_height() + 5  # 按钮下方5px

        # 设置对话框的位置
        dialog.geometry(f"+{x}+{y}")

        # 从温度配置管理器获取参数
        print("获取温度配置参数...")
        try:
            params = self.temp_config.get_all_parameters()
            print(f"获取到参数: {params}")
        except Exception as e:
            print(f"获取参数时出错: {e}")
            # 使用默认值
            params = {
                "min_temp": 50.0,
                "max_temp": 80.0,
                "color": "绿色",
                "max_ratio": 10.0,
                "auto_reduce": 1.0,
                "p_w": 237.0,
                "p_h": 194.0,
                "p_origin": "左下",
                "p_origin_offset_x": 0.0,
                "p_origin_offset_y": 0.0,
                "c_padding_left": 0.0,
                "c_padding_top": 0.0,
                "c_padding_right": 0.0,
                "c_padding_bottom": 0.0
            }
        
        min_temp_var = params["min_temp"]
        max_temp_var = params["max_temp"]

        # PCB参数设置
        p_w_var = str(params["p_w"])
        p_h_var = str(params["p_h"])
        p_origin_var = params["p_origin"]

        # 创建主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 移除文件路径显示区域
        
        # 第一行：温度过滤参数
        temp_frame = ttk.LabelFrame(main_frame, text="温度过滤参数")
        temp_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 温度范围
        temp_range_frame = ttk.Frame(temp_frame)
        temp_range_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(temp_range_frame, text="最低温度:").pack(side=tk.LEFT, padx=5)
        self.min_temp_entry = ttk.Entry(temp_range_frame, width=10)
        self.min_temp_entry.insert(0, str(min_temp_var))
        self.min_temp_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(temp_range_frame, text="最高温度:").pack(side=tk.LEFT, padx=5)
        self.max_temp_entry = ttk.Entry(temp_range_frame, width=10)
        self.max_temp_entry.insert(0, str(max_temp_var))
        self.max_temp_entry.pack(side=tk.LEFT, padx=5)
        
        # PCB参数设置
        param_frame = ttk.LabelFrame(main_frame, text="PCB参数设置")
        param_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # PCB尺寸
        size_frame = ttk.Frame(param_frame)
        size_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(size_frame, text="PCB长度(mm):").pack(side=tk.LEFT, padx=5)
        self.p_w_entry = ttk.Entry(size_frame, width=10)
        self.p_w_entry.insert(0, str(p_w_var))
        self.p_w_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(size_frame, text="PCB宽度(mm):").pack(side=tk.LEFT, padx=5)
        self.p_h_entry = ttk.Entry(size_frame, width=10)
        self.p_h_entry.insert(0, str(p_h_var))
        self.p_h_entry.pack(side=tk.LEFT, padx=5)
        
        # 坐标原点
        origin_frame = ttk.Frame(param_frame)
        origin_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(origin_frame, text="坐标原点:").pack(side=tk.LEFT, padx=5)
        self.p_origin_var = tk.StringVar(value=p_origin_var)
        origin_combo = ttk.Combobox(origin_frame, textvariable=self.p_origin_var, 
                                   values=["左上", "右上", "右下", "左下"], 
                                   state="readonly", width=10)
        origin_combo.pack(side=tk.LEFT, padx=5)
        
        # 移除原点偏移和Padding参数，使用默认值0
        
        # 移除元器件最小尺寸設定（該參數未實際使用）

        # 隐藏检查边缘比例
        # auto_frame = ttk.Frame(main_frame)
        # auto_frame.pack(fill=tk.X, padx=5, pady=2)
        # 
        # ttk.Label(auto_frame, text="检查边缘比例:").pack(side=tk.LEFT, padx=5)
        # self.auto_reduce_entry = ttk.Entry(auto_frame, width=10)
        # self.auto_reduce_entry.insert(0, str(auto_reduce_var))
        # self.auto_reduce_entry.pack(side=tk.LEFT, padx=5)
        # ttk.Label(auto_frame, text="* 若边缘温度大于框内温度，则框自动缩放").pack(side=tk.LEFT, padx=5)



        def on_confirm():
            # 收集用户输入的参数
            self.get_params()
            
            # 保存到温度配置管理器
            self.temp_config.save_parameters(self.dialog_result)
            
            # 调用外部回调函数，并传递结果
            if self.callback:
                self.callback(self.dialog_result)

            # 关闭对话框
            dialog.destroy()

        # 确认按钮
        confirm_button = tk.Button(main_frame, text="  确认  ", command=on_confirm)
        confirm_button.pack(pady=10)

        # 设置对话框为模态，但不阻塞主线程
        dialog.transient(self.master)
        dialog.grab_set()
        
        # 不阻塞主线程，让对话框异步运行
        # dialog.wait_window(dialog)  # 移除这行，避免阻塞
        
        print("温度过滤对话框创建完成，应该已经显示")

    def get_params(self):
        """從所有輸入框收集參數值並存入 dialog_result 字典。"""
        self.dialog_result = {
            "min_temp": float(self.min_temp_entry.get()),
            "max_temp": float(self.max_temp_entry.get()),
            "color": "绿色",  # 默认值
            # min_width 和 min_height 已移除（未實際使用）
            "max_ratio": 10.0,  # 默认值
            "auto_reduce": 1.0,  # 默认值
            # PCB参数
            "p_w": float(self.p_w_entry.get()),
            "p_h": float(self.p_h_entry.get()),
            "p_origin": self.p_origin_var.get(),
            # 使用默认值0，不再显示输入框
            "p_origin_offset_x": 0.0,
            "p_origin_offset_y": 0.0,
            "c_padding_left": 0.0,
            "c_padding_top": 0.0,
            "c_padding_right": 0.0,
            "c_padding_bottom": 0.0
        }
