#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Toast 通知元件模組 (toast.py)

用途：
    提供非侵入式的浮動通知功能（Toast Notification），
    在螢幕右上角彈出短暫的訊息提示，不會打斷使用者的操作流程。
    支持 info/success/warning/error 四種通知類型，
    每種類型以不同的標題顏色區分，背景統一使用淺藍色主題。
    帶有淡入淡出動畫效果。

在整個應用中的角色：
    - 作為全域通知系統，供各模組呼叫 show_toast() 顯示操作結果回饋
    - 替代傳統的 messagebox 彈窗，避免打斷使用者的工作流程

關聯檔案：
    - main.py：主頁面中匯入 show_toast() 用於顯示各種操作結果通知
"""

import tkinter as tk
from tkinter import ttk
import threading
import time

# 匯入應用的 UI 樣式常數
try:
    from main import UIStyle
except ImportError:
    # 如果无法导入，定义备用样式
    class UIStyle:
        PRIMARY_BLUE = "#4A90E2"
        LIGHT_BLUE = "#87CEEB"
        DARK_BLUE = "#2E5BBA"
        VERY_LIGHT_BLUE = "#E6F3FF"
        WHITE = "#FFFFFF"
        SUCCESS_GREEN = "#5CB85C"
        WARNING_ORANGE = "#F0AD4E"
        DANGER_RED = "#D9534F"
        BLACK = "#333333"
        DARK_GRAY = "#666666"
        BUTTON_FONT = ("Arial", 10, "bold")
        LABEL_FONT = ("Arial", 10)
        SMALL_FONT = ("Arial", 9)

class Toast:
    """獨立的 Toast 通知元件，不依賴系統通知功能。

    在螢幕右上角顯示一個無邊框的浮動視窗，包含標題和訊息內容，
    經過指定時間後自動消失。

    屬性：
        parent (tk.Widget): 父視窗元件
        toast_window (tk.Toplevel): Toast 的浮動視窗實例
        toast_thread (threading.Thread): 控制顯示和計時的背景執行緒
        is_showing (bool): Toast 是否正在顯示中"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.toast_window = None
        self.toast_thread = None
        self.is_showing = False
        
    def show(self, title="通知", message="", duration=3000, toast_type="info"):
        """
        显示Toast通知
        
        Args:
            title: 通知标题
            message: 通知内容
            duration: 显示时长（毫秒）
            toast_type: 通知类型 ("info", "success", "warning", "error")
        """
        if self.is_showing:
            self.hide()
            
        self.is_showing = True
        
        # 在新线程中显示toast，避免阻塞主线程
        self.toast_thread = threading.Thread(
            target=self._show_toast, 
            args=(title, message, duration, toast_type),
            daemon=True
        )
        self.toast_thread.start()
    
    def _show_toast(self, title, message, duration, toast_type):
        """在独立线程中显示toast"""
        try:
            # 创建toast窗口
            self.toast_window = tk.Toplevel()
            self.toast_window.withdraw()  # 先隐藏
            
            # 设置窗口属性
            self.toast_window.overrideredirect(True)  # 无边框
            self.toast_window.attributes('-topmost', True)  # 置顶
            self.toast_window.attributes('-alpha', 0.95)  # 半透明
            
            # 根据类型设置颜色
            colors = self._get_colors(toast_type)
            
            # 创建主框架
            main_frame = tk.Frame(
                self.toast_window,
                bg=colors['bg'],
                relief=tk.FLAT,
                bd=0
            )
            main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            
            # 创建内容框架
            content_frame = tk.Frame(main_frame, bg=colors['bg'])
            content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
            
            # 标题
            if title:
                title_label = tk.Label(
                    content_frame,
                    text=title,
                    font=UIStyle.BUTTON_FONT,
                    fg=colors['title_fg'],
                    bg=colors['bg'],
                    anchor=tk.W
                )
                title_label.pack(fill=tk.X, pady=(0, 3))
            
            # 消息内容
            if message:
                message_label = tk.Label(
                    content_frame,
                    text=message,
                    font=UIStyle.SMALL_FONT,
                    fg=colors['message_fg'],
                    bg=colors['bg'],
                    anchor=tk.W,
                    wraplength=320,
                    justify=tk.LEFT
                )
                message_label.pack(fill=tk.X)
            
            # 计算窗口大小和位置
            self.toast_window.update_idletasks()
            width = self.toast_window.winfo_reqwidth()
            height = self.toast_window.winfo_reqheight()
            
            # 获取屏幕尺寸
            screen_width = self.toast_window.winfo_screenwidth()
            screen_height = self.toast_window.winfo_screenheight()
            
            # 计算位置（右上角）
            x = screen_width - width - 20
            y = 20
            
            # 设置窗口位置和大小
            self.toast_window.geometry(f"{width}x{height}+{x}+{y}")
            
            # 显示窗口
            self.toast_window.deiconify()
            
            # 添加淡入动画效果
            self._fade_in()
            
            # 等待指定时间
            time.sleep(duration / 1000.0)
            
            # 添加淡出动画效果
            self._fade_out()
            
        except Exception as e:
            print(f"Toast显示错误: {e}")
        finally:
            self._cleanup()
    
    def _get_colors(self, toast_type):
        """根据类型获取颜色配置，使用应用的统一浅蓝色主题"""
        color_schemes = {
            "info": {
                "bg": UIStyle.VERY_LIGHT_BLUE,  # 极浅蓝色背景
                "title_fg": UIStyle.DARK_BLUE,  # 深蓝色标题
                "message_fg": UIStyle.BLACK     # 黑色消息
            },
            "success": {
                "bg": UIStyle.VERY_LIGHT_BLUE,  # 极浅蓝色背景
                "title_fg": UIStyle.SUCCESS_GREEN, # 成功绿色标题
                "message_fg": UIStyle.BLACK     # 黑色消息
            },
            "warning": {
                "bg": UIStyle.VERY_LIGHT_BLUE,  # 极浅蓝色背景
                "title_fg": UIStyle.WARNING_ORANGE, # 警告橙色标题
                "message_fg": UIStyle.BLACK     # 黑色消息
            },
            "error": {
                "bg": UIStyle.VERY_LIGHT_BLUE,  # 极浅蓝色背景
                "title_fg": UIStyle.DANGER_RED, # 错误红色标题
                "message_fg": UIStyle.BLACK     # 黑色消息
            }
        }
        return color_schemes.get(toast_type, color_schemes["info"])
    
    def _fade_in(self):
        """淡入动画"""
        if not self.toast_window:
            return
            
        try:
            for alpha in [0.4, 0.6, 0.8, 0.95]:
                self.toast_window.attributes('-alpha', alpha)
                self.toast_window.update()
                time.sleep(0.03)
        except:
            pass
    
    def _fade_out(self):
        """淡出动画"""
        if not self.toast_window:
            return
            
        try:
            for alpha in [0.8, 0.6, 0.4, 0.1]:
                self.toast_window.attributes('-alpha', alpha)
                self.toast_window.update()
                time.sleep(0.03)
        except:
            pass
    
    def _cleanup(self):
        """清理资源"""
        try:
            if self.toast_window:
                self.toast_window.destroy()
                self.toast_window = None
        except:
            pass
        finally:
            self.is_showing = False
    
    def hide(self):
        """立即隐藏toast"""
        if self.is_showing and self.toast_window:
            try:
                self.toast_window.destroy()
            except:
                pass
            finally:
                self._cleanup()

# 全局toast实例
_global_toast = None

def show_toast(title="通知", message="", duration=3000, toast_type="info", parent=None):
    """
    显示Toast通知的全局函数
    
    Args:
        title: 通知标题
        message: 通知内容
        duration: 显示时长（毫秒）
        toast_type: 通知类型 ("info", "success", "warning", "error")
        parent: 父窗口
    """
    global _global_toast
    
    if _global_toast is None:
        _global_toast = Toast(parent)
    
    _global_toast.show(title, message, duration, toast_type)

def hide_toast():
    """隐藏当前显示的toast"""
    global _global_toast
    
    if _global_toast:
        _global_toast.hide()
