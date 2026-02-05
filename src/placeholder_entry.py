#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
占位符输入框控件
提供成熟的占位符功能，自动处理焦点、点击、输入等事件
"""

import tkinter as tk
from tkinter import ttk

class PlaceholderEntry(tk.Entry):
    """带占位符的输入框控件"""
    
    def __init__(self, parent, placeholder="", placeholder_color="gray", **kwargs):
        """
        初始化占位符输入框
        
        Args:
            parent: 父控件
            placeholder: 占位符文本
            placeholder_color: 占位符颜色
            **kwargs: 其他Entry参数
        """
        # 保存占位符信息
        self.placeholder = placeholder
        self.placeholder_color = placeholder_color
        self.normal_color = kwargs.get('fg', 'black')
        
        # 创建Entry
        super().__init__(parent, **kwargs)
        
        # 设置初始状态
        self._show_placeholder()
        
        # 绑定事件
        self.bind('<FocusIn>', self._on_focus_in)
        self.bind('<FocusOut>', self._on_focus_out)
        self.bind('<Button-1>', self._on_click)
        self.bind('<Key>', self._on_key)
        
    def _show_placeholder(self):
        """显示占位符"""
        # 清除所有内容
        self.delete(0, tk.END)
        # 插入占位符
        self.insert(0, self.placeholder)
        self.config(fg=self.placeholder_color)
        self._is_placeholder = True
    
    def _hide_placeholder(self):
        """隐藏占位符"""
        if hasattr(self, '_is_placeholder') and self._is_placeholder:
            self.delete(0, tk.END)
            self.config(fg=self.normal_color)
            self._is_placeholder = False
    
    def _is_empty_or_placeholder(self):
        """检查内容是否为空或只有占位符"""
        content = super().get()
        return not content or content == self.placeholder
    
    def _on_focus_in(self, event):
        """焦点进入事件"""
        if hasattr(self, '_is_placeholder') and self._is_placeholder:
            self._hide_placeholder()
    
    def _on_focus_out(self, event):
        """焦点离开事件"""
        if self._is_empty_or_placeholder():
            self._show_placeholder()
    
    def _on_click(self, event):
        """点击事件"""
        if hasattr(self, '_is_placeholder') and self._is_placeholder:
            self._hide_placeholder()
            # 将光标移到开头
            self.icursor(0)
    
    def _on_key(self, event):
        """按键事件"""
        if hasattr(self, '_is_placeholder') and self._is_placeholder:
            self._hide_placeholder()
    
    def get(self):
        """获取输入内容（忽略占位符）"""
        if hasattr(self, '_is_placeholder') and self._is_placeholder:
            return ""
        # 直接获取Entry的内容，但确保不是占位符
        content = super().get()
        if content == self.placeholder:
            return ""
        return content
    
    def set(self, value):
        """设置输入内容"""
        self.delete(0, tk.END)
        if value:
            self.insert(0, value)
            self.config(fg=self.normal_color)
            self._is_placeholder = False
        else:
            self._show_placeholder()
    
    def clear(self):
        """清除内容并显示占位符"""
        self.delete(0, tk.END)
        self._show_placeholder()
        self.icursor(0)  # 光标移到开头


def test_placeholder_entry():
    """测试占位符输入框"""
    root = tk.Tk()
    root.title("占位符输入框测试")
    root.geometry("400x200")
    
    # 创建占位符输入框
    entry = PlaceholderEntry(
        root, 
        placeholder="搜索器件名称",
        placeholder_color="gray",
        font=("Arial", 10),
        width=30
    )
    entry.pack(pady=20)
    
    # 清除按钮
    def clear_entry():
        entry.clear()
        print("清除输入框")
    
    clear_btn = tk.Button(root, text="清除", command=clear_entry)
    clear_btn.pack(pady=10)
    
    # 获取内容按钮
    def get_content():
        content = entry.get()
        print(f"输入内容: '{content}'")
    
    get_btn = tk.Button(root, text="获取内容", command=get_content)
    get_btn.pack(pady=5)
    
    root.mainloop()


if __name__ == "__main__":
    test_placeholder_entry()
