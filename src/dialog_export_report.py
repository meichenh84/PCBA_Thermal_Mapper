#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
測試報告 Sheet 名稱選擇對話框模組 (dialog_export_report.py)
=============================================================================
用途：
    提供「寫入測試報告」功能的 Sheet 名稱選擇對話框，讓使用者選擇或自訂
    要寫入的 Sheet 名稱。預設選項包括 High_Vac_Data 和 Low_Vac_Data，
    也可自行輸入名稱。

在整個應用中的角色：
    - 當使用者點擊「寫入測試報告」按鈕時彈出
    - 選擇的 Sheet 名稱會傳遞給 main.py 中的寫入邏輯

關聯檔案：
    - main.py：建立 ExportReportDialog 實例，接收 callback 結果
    - ui_style.py：引用統一 UI 樣式常數
=============================================================================
"""

import tkinter as tk
from tkinter import ttk

try:
    from .ui_style import UIStyle
except ImportError:
    from ui_style import UIStyle


class ExportReportDialog:
    """測試報告 Sheet 名稱選擇對話框。

    提供三種選項：High_Vac_Data / Low_Vac_Data / 自訂名稱，
    確認後透過 callback 傳遞選擇的 Sheet 名稱。

    屬性：
        master (tk.Widget): 主視窗元件
        button (tk.Button): 觸發本對話框的按鈕（用於定位）
        callback (callable): 確認後的回呼函式，接收 sheet_name 字串
    """

    def __init__(self, master, button, callback):
        """初始化 Sheet 名稱選擇對話框。

        Args:
            master (tk.Widget): 主視窗元件
            button (tk.Button): 觸發按鈕（用於計算對話框位置）
            callback (callable): 確認後的回呼函式，接收 sheet_name 字串
        """
        self.master = master
        self.button = button
        self.callback = callback

    def open(self):
        """開啟 Sheet 名稱選擇對話框，建立所有 UI 元件並顯示。"""
        dialog = tk.Toplevel(self.master)
        dialog.title("選擇 Sheet 名稱")
        self.dialog = dialog

        # 定位在按鈕下方
        x = self.button.winfo_rootx()
        y = self.button.winfo_rooty() + self.button.winfo_height() + 5
        dialog.geometry(f"+{x}+{y}")

        # 主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # 標題
        ttk.Label(main_frame, text="請選擇要寫入的 Sheet 名稱：",
                  font=UIStyle.LABEL_FONT).pack(anchor=tk.W, pady=(0, 10))

        # Radio 選項
        self.sheet_var = tk.StringVar(value="High_Vac_Data")

        options = [
            ("High_Vac_Data", "High_Vac_Data"),
            ("Low_Vac_Data", "Low_Vac_Data"),
            ("custom", "自訂"),
        ]

        for value, text in options:
            rb = ttk.Radiobutton(main_frame, text=text, variable=self.sheet_var,
                                 value=value, command=self._on_radio_change)
            rb.pack(anchor=tk.W, pady=2)

        # 自訂 Entry
        self.custom_entry = ttk.Entry(main_frame, width=30, state=tk.DISABLED)
        self.custom_entry.pack(anchor=tk.W, padx=(20, 0), pady=(2, 10))

        # 按鈕列
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        confirm_btn = tk.Button(btn_frame, text="  確認  ", command=self._on_confirm,
                                bg=UIStyle.PRIMARY_BLUE, fg=UIStyle.WHITE,
                                font=UIStyle.BUTTON_FONT)
        confirm_btn.pack(side=tk.LEFT, padx=(0, 10))

        cancel_btn = tk.Button(btn_frame, text="  取消  ", command=dialog.destroy,
                               bg=UIStyle.GRAY, fg=UIStyle.WHITE,
                               font=UIStyle.BUTTON_FONT)
        cancel_btn.pack(side=tk.LEFT)

        # 模態
        dialog.transient(self.master)
        dialog.grab_set()

    def _on_radio_change(self):
        """當 Radio 選項變更時，切換自訂 Entry 的啟用狀態。"""
        if self.sheet_var.get() == "custom":
            self.custom_entry.config(state=tk.NORMAL)
            self.custom_entry.focus_set()
        else:
            self.custom_entry.config(state=tk.DISABLED)

    def _on_confirm(self):
        """確認按鈕回呼：取得 sheet 名稱並透過 callback 傳回。"""
        selected = self.sheet_var.get()
        if selected == "custom":
            sheet_name = self.custom_entry.get().strip()
            if not sheet_name:
                return  # 空白不處理
        else:
            sheet_name = selected

        self.dialog.destroy()
        if self.callback:
            self.callback(sheet_name)
