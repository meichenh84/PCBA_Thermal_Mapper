#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI 統一樣式定義模組 (ui_style.py)

用途：
    集中定義整個應用程式的 UI 視覺樣式常數，包含色彩主題、字型大小、
    間距、邊框等。所有模組統一引用此處的常數，確保全域視覺風格一致。

在整個應用中的角色：
    - 作為全域樣式常數庫，被所有需要 UI 元素的模組引用
    - 統一管理色彩主題（淺藍色系）、字型、按鈕樣式等
    - 修改此檔案即可全域變更應用程式的視覺風格

關聯檔案：
    - main.py：主介面引用 UIStyle 的顏色和字型常數
    - toast.py：Toast 通知元件引用色彩常數
    - dialog_setting.py：設定對話框引用樣式常數
    - editor_canvas.py：畫布編輯器引用樣式常數
"""

import tkinter as tk


class UIStyle:
    """UI 統一樣式定義類別，集中管理應用程式的視覺風格常數。

    所有顏色使用十六進制色碼格式（#RRGGBB），
    字型使用 (字型名稱, 大小, 樣式) 的元組格式。

    類別屬性分類：
        - 主色調：淺藍色系（PRIMARY_BLUE / LIGHT_BLUE / DARK_BLUE / VERY_LIGHT_BLUE）
        - 輔助色：白/灰/黑系列
        - 功能色：成功綠 / 警告橙 / 危險紅
        - 按鈕樣式：字型、邊框、寬度
        - 文字樣式：標題 / 標籤 / 小字型
        - 佈局樣式：內距大小
        - 邊框樣式：寬度、樣式
        - 捲軸樣式：寬度、顏色
    """

    # ===== 主色調 - 淺藍色系 =====
    PRIMARY_BLUE = "#4A90E2"      # 主藍色（按鈕、選中狀態）
    LIGHT_BLUE = "#87CEEB"        # 淺藍色（懸停效果）
    DARK_BLUE = "#2E5BBA"         # 深藍色（標題、強調文字）
    VERY_LIGHT_BLUE = "#E6F3FF"   # 極淺藍色（背景、Toast 底色）

    # ===== 輔助色 =====
    WHITE = "#FFFFFF"             # 白色
    LIGHT_GRAY = "#F5F5F5"        # 淺灰色（次要背景）
    GRAY = "#CCCCCC"              # 灰色（邊框、分隔線）
    DARK_GRAY = "#666666"         # 深灰色（次要文字）
    BLACK = "#333333"             # 黑色（主要文字）

    # ===== 功能色 =====
    SUCCESS_GREEN = "#5CB85C"     # 成功綠色（成功通知標題）
    WARNING_ORANGE = "#F0AD4E"    # 警告橙色（警告通知標題）
    DANGER_RED = "#D9534F"        # 危險紅色（錯誤通知標題）

    # ===== 按鈕樣式 =====
    BUTTON_FONT = ("Arial", 10, "bold")   # 按鈕字型（Arial 10pt 粗體）
    BUTTON_RELIEF = tk.RAISED             # 按鈕邊框樣式（凸起）
    BUTTON_BORDER_WIDTH = 2               # 按鈕邊框寬度

    # ===== 文字樣式 =====
    TITLE_FONT = ("Arial", 12, "bold")    # 標題字型（Arial 12pt 粗體）
    LABEL_FONT = ("Arial", 10)            # 標籤字型（Arial 10pt）
    SMALL_FONT = ("Arial", 9)             # 小字型（Arial 9pt，用於 Toast 訊息等）

    # ===== 佈局樣式 =====
    PADDING_SMALL = 5                     # 小間距（5px）
    PADDING_MEDIUM = 10                   # 中間距（10px）
    PADDING_LARGE = 15                    # 大間距（15px）

    # ===== 邊框樣式 =====
    BORDER_WIDTH = 1                      # 邊框寬度
    BORDER_RELIEF = tk.SUNKEN             # 邊框樣式（凹陷）

    # ===== 捲軸樣式 =====
    SCROLLBAR_WIDTH = 20                  # 捲軸寬度
    SCROLLBAR_COLOR = "#CCCCCC"           # 捲軸顏色
    SCROLLBAR_TROUGH_COLOR = "#F0F0F0"    # 捲軸滑槽顏色
