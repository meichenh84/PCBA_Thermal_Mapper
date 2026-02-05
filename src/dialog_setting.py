import tkinter as tk
from tkinter import ttk, colorchooser
from config import GlobalConfig

class SettingDialog:
    def __init__(self, master, settings_button, callback):
        """
        初始化设置对话框
        :param master: 主窗口
        :param settings_button: 设置按钮
        :param callback: 外部回调函数，用于处理设置的逻辑
        """
        self.master = master
        self.settings_button = settings_button
        self.callback = callback  # 接收外部传入的回调函数
        self.dialog_result = {}
        self.config = GlobalConfig()
        self.dialog = None  # 对话框实例，用于单例模式

    def open(self):
        # 检查对话框是否已经存在且可见
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
        self.dialog.geometry(f"500x600+{x}+{y}")

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
        """加载颜色配置"""
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
            
            # Layout图标记
            "layout_rect_color": self.config.get("layout_rect_color", "#BCBCBC"),
            "layout_name_color": self.config.get("layout_name_color", "#FFFFFF"),
            "layout_name_font_size": self.config.get("layout_name_font_size", 12),
            "layout_temp_color": self.config.get("layout_temp_color", "#FF0000"),
            "layout_temp_font_size": self.config.get("layout_temp_font_size", 10),
        }

    def create_color_setting(self, parent, label_text, config_key, default_color, row):
        """创建颜色设置控件"""
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
        """创建字体设置控件"""
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

    def on_confirm(self):
        """确认按钮点击事件"""
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
        """对话框关闭时的回调"""
        if self.dialog is not None:
            self.dialog.destroy()
            self.dialog = None
