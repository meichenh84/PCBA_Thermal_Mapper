import tkinter as tk

class UIStyle:
    """UI样式定义类，用于统一应用程序的视觉风格"""
    
    # 主色调 - 浅蓝色系
    PRIMARY_BLUE = "#4A90E2"      # 主蓝色
    LIGHT_BLUE = "#87CEEB"        # 浅蓝色
    DARK_BLUE = "#2E5BBA"         # 深蓝色
    VERY_LIGHT_BLUE = "#E6F3FF"   # 极浅蓝色
    
    # 辅助色
    WHITE = "#FFFFFF"
    LIGHT_GRAY = "#F5F5F5"
    GRAY = "#CCCCCC"
    DARK_GRAY = "#666666"
    BLACK = "#333333"
    
    # 功能色
    SUCCESS_GREEN = "#5CB85C"
    WARNING_ORANGE = "#F0AD4E"
    DANGER_RED = "#D9534F"
    
    # 按钮样式
    BUTTON_FONT = ("Arial", 10, "bold")
    BUTTON_RELIEF = tk.RAISED
    BUTTON_BORDER_WIDTH = 2
    
    # 文本样式
    TITLE_FONT = ("Arial", 12, "bold")
    LABEL_FONT = ("Arial", 10)
    SMALL_FONT = ("Arial", 9)
    
    # 布局样式
    PADDING_SMALL = 5
    PADDING_MEDIUM = 10
    PADDING_LARGE = 15
    
    # 边框样式
    BORDER_WIDTH = 1
    BORDER_RELIEF = tk.SUNKEN
    
    # 滚动条样式
    SCROLLBAR_WIDTH = 20
    SCROLLBAR_COLOR = "#CCCCCC"
    SCROLLBAR_TROUGH_COLOR = "#F0F0F0"
