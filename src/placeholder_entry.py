#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
帶佔位符文字的輸入框元件模組 (placeholder_entry.py)

用途：
    提供一個帶有佔位符（placeholder）功能的文字輸入框元件，
    繼承自 tk.Entry。當輸入框為空時顯示灰色的提示文字，
    使用者開始輸入時自動清除佔位符並恢復正常文字顏色。
    自動處理焦點進入/離開、滑鼠點擊、鍵盤輸入等事件。

在整個應用中的角色：
    - 在「編輯溫度」對話框的左側搜尋欄中使用，
      提供「搜尋器件名稱」的佔位符提示

關聯檔案：
    - main.py（或相關對話框模組）：在溫度編輯對話框中建立 PlaceholderEntry 實例
"""

import tkinter as tk
from tkinter import ttk

class PlaceholderEntry(tk.Entry):
    """
    帶佔位符的輸入框元件。

    繼承自 tk.Entry，在原生輸入框的基礎上增加了佔位符功能：
    - 輸入框為空時，顯示灰色的佔位符文字
    - 使用者點擊或聚焦時，自動清除佔位符
    - 使用者離開且未輸入內容時，自動恢復佔位符
    - get() 方法會自動忽略佔位符，只回傳實際輸入的內容

    屬性：
        placeholder (str): 佔位符文字內容
        placeholder_color (str): 佔位符文字顏色（預設為灰色）
        normal_color (str): 正常輸入文字顏色
        _is_placeholder (bool): 目前顯示的是否為佔位符
    """
    
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
        self.bind('<FocusIn>', self._on_focus_in)    # 輸入框獲得焦點時
        self.bind('<FocusOut>', self._on_focus_out)   # 輸入框失去焦點時
        self.bind('<Button-1>', self._on_click)       # 滑鼠左鍵點擊時
        self.bind('<Key>', self._on_key)              # 任意鍵盤按鍵時
        
    def _show_placeholder(self):
        """顯示佔位符文字。清除輸入框中的所有內容，插入佔位符並設為灰色。"""
        # 清除所有内容
        self.delete(0, tk.END)
        # 插入占位符
        self.insert(0, self.placeholder)
        self.config(fg=self.placeholder_color)
        self._is_placeholder = True
    
    def _hide_placeholder(self):
        """隱藏佔位符文字。清除佔位符並恢復正常文字顏色。"""
        if hasattr(self, '_is_placeholder') and self._is_placeholder:
            self.delete(0, tk.END)
            self.config(fg=self.normal_color)
            self._is_placeholder = False
    
    def _is_empty_or_placeholder(self):
        """檢查輸入框內容是否為空或僅包含佔位符。

        Returns:
            bool: True 表示內容為空或等於佔位符文字。
        """
        content = super().get()
        return not content or content == self.placeholder
    
    def _on_focus_in(self, event):
        """焦點進入事件處理器。當輸入框獲得焦點時，清除佔位符。"""
        if hasattr(self, '_is_placeholder') and self._is_placeholder:
            self._hide_placeholder()
    
    def _on_focus_out(self, event):
        """焦點離開事件處理器。內容為空時自動恢復佔位符。"""
        if self._is_empty_or_placeholder():
            self._show_placeholder()
    
    def _on_click(self, event):
        """滑鼠點擊事件處理器。清除佔位符並將游標移到開頭。"""
        if hasattr(self, '_is_placeholder') and self._is_placeholder:
            self._hide_placeholder()
            # 将光标移到开头
            self.icursor(0)
    
    def _on_key(self, event):
        """鍵盤按鍵事件處理器。按下任意鍵時自動清除佔位符。"""
        if hasattr(self, '_is_placeholder') and self._is_placeholder:
            self._hide_placeholder()
    
    def get(self):
        """取得輸入框中的實際內容（自動忽略佔位符）。

        Returns:
            str: 使用者實際輸入的文字。若為佔位符狀態則回傳空字串。
        """
        if hasattr(self, '_is_placeholder') and self._is_placeholder:
            return ""
        # 直接获取Entry的内容，但确保不是占位符
        content = super().get()
        if content == self.placeholder:
            return ""
        return content
    
    def set(self, value):
        """設定輸入框的內容。

        Args:
            value (str): 要設定的文字。若為空則恢復佔位符。
        """
        self.delete(0, tk.END)
        if value:
            self.insert(0, value)
            self.config(fg=self.normal_color)
            self._is_placeholder = False
        else:
            self._show_placeholder()
    
    def clear(self):
        """清除輸入框內容並恢復顯示佔位符。用於重置輸入框狀態。"""
        self.delete(0, tk.END)
        self._show_placeholder()
        self.icursor(0)  # 光标移到开头


def test_placeholder_entry():
    """佔位符輸入框的測試函式。建立測試視窗驗證佔位符行為。"""
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
