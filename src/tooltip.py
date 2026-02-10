#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tooltip 提示框模組 (tooltip.py)

用途：
    提供滑鼠懸停提示框功能，當使用者將滑鼠移到元件上時，
    在游標附近顯示提示訊息。支援多行文字和自定義樣式。

在整個應用中的角色：
    - 通用 UI 組件，可在任何需要提示訊息的地方使用
    - 提供統一的提示框外觀和行為

關聯檔案：
    - editor_canvas.py：使用 Tooltip 顯示多選操作說明
    - 其他需要提示訊息的 UI 模組

使用範例：
    from tooltip import Tooltip

    # 為按鈕添加提示
    button = tk.Button(root, text="按鈕")
    Tooltip(button, "這是一個按鈕")

    # 自定義樣式
    Tooltip(label, "提示訊息", bg_color="#FFFFE0", delay=500)
"""

import tkinter as tk


class Tooltip:
    """
    Tooltip 提示框類。

    當滑鼠移到元件上時，在游標附近顯示提示訊息。
    支援多行文字、自定義背景色、延遲顯示等功能。

    屬性：
        widget (tk.Widget): 要添加提示的元件
        text (str): 提示訊息文字（支援多行，使用 \\n 分隔）
        bg_color (str): 提示框背景顏色
        fg_color (str): 提示框文字顏色
        delay (int): 延遲顯示時間（毫秒），0 表示立即顯示
        tooltip_window (tk.Toplevel|None): 提示框視窗
    """

    def __init__(self, widget, text, bg_color="#FFFFCC", fg_color="#000000", delay=0):
        """
        初始化 Tooltip。

        Args:
            widget (tk.Widget): 要添加提示的元件
            text (str): 提示訊息文字（支援多行，使用 \\n 分隔）
            bg_color (str): 提示框背景顏色，預設為淺黃色 #FFFFCC
            fg_color (str): 提示框文字顏色，預設為黑色 #000000
            delay (int): 延遲顯示時間（毫秒），預設為 0（立即顯示）
        """
        self.widget = widget
        self.text = text
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.delay = delay
        self.tooltip_window = None
        self._after_id = None  # 延遲顯示的計時器 ID

        # 綁定滑鼠事件
        self.widget.bind("<Enter>", self._on_enter)
        self.widget.bind("<Leave>", self._on_leave)
        self.widget.bind("<Motion>", self._on_motion)

    def _on_enter(self, event):
        """滑鼠進入元件時觸發"""
        if self.delay > 0:
            # 延遲顯示
            self._after_id = self.widget.after(self.delay, lambda: self._show_tooltip(event))
        else:
            # 立即顯示
            self._show_tooltip(event)

    def _on_leave(self, event):
        """滑鼠離開元件時觸發"""
        # 取消延遲顯示計時器
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        # 隱藏提示框
        self._hide_tooltip()

    def _on_motion(self, event):
        """滑鼠移動時更新提示框位置"""
        if self.tooltip_window:
            x, y = self._calc_position(event.x_root, event.y_root)
            self.tooltip_window.wm_geometry(f"+{x}+{y}")

    def _calc_position(self, cursor_x, cursor_y):
        """計算提示框位置，避免超出螢幕邊界。

        優先顯示在游標右下方；若超出螢幕右邊界則改為左側，
        若超出螢幕下邊界則改為上方。

        Args:
            cursor_x (int): 游標螢幕 X 座標
            cursor_y (int): 游標螢幕 Y 座標

        Returns:
            tuple: (x, y) 提示框左上角螢幕座標
        """
        offset = 15
        screen_w = self.widget.winfo_screenwidth()
        screen_h = self.widget.winfo_screenheight()

        # 取得提示框尺寸（需要先 update 才能拿到正確值）
        if self.tooltip_window:
            self.tooltip_window.update_idletasks()
            tip_w = self.tooltip_window.winfo_reqwidth()
            tip_h = self.tooltip_window.winfo_reqheight()
        else:
            tip_w = 0
            tip_h = 0

        # 水平方向：預設右側，超出則改左側
        x = cursor_x + offset
        if x + tip_w > screen_w:
            x = cursor_x - offset - tip_w

        # 垂直方向：預設下方，超出則改上方
        y = cursor_y + 10
        if y + tip_h > screen_h:
            y = cursor_y - 10 - tip_h

        return x, y

    def _show_tooltip(self, event):
        """顯示提示框"""
        if self.tooltip_window:
            return  # 已經顯示，不重複創建

        # 創建提示框視窗
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)  # 移除視窗邊框和標題列

        # 創建提示訊息標籤
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify=tk.LEFT,
            background=self.bg_color,
            foreground=self.fg_color,
            relief=tk.SOLID,
            borderwidth=1,
            font=("Arial", 9),
            padx=8,
            pady=6
        )
        label.pack()

        # 計算位置（需在 label.pack() 後才能取得正確尺寸）
        x, y = self._calc_position(event.x_root, event.y_root)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # 確保提示框在最上層
        self.tooltip_window.lift()

    def _hide_tooltip(self):
        """隱藏提示框"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def update_text(self, new_text):
        """
        更新提示訊息文字。

        Args:
            new_text (str): 新的提示訊息文字
        """
        self.text = new_text
        # 如果提示框正在顯示，重新創建以更新內容
        if self.tooltip_window:
            self._hide_tooltip()
