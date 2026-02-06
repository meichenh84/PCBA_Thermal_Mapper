#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全域配置管理模組 (config.py)

用途：
    提供應用程式的全域配置管理功能，使用單例模式（Singleton Pattern）
    確保整個應用只有一個配置實例。配置資料以字典形式存放在記憶體中，
    並可序列化為 JSON 檔案持久儲存至 config/config.json。
    管理的設定項包括：放大鏡開關、圓形標記開關、上次開啟資料夾路徑、
    熱力圖與 Layout 圖的矩形框顏色/字型大小等。

在整個應用中的角色：
    - 被所有需要讀取或寫入設定的模組透過 GlobalConfig() 取得同一實例
    - 作為設定對話框（dialog_setting.py）與主介面（main.py）之間的橋樑

關聯檔案：
    - main.py：讀取放大鏡開關、顏色設定等配置
    - dialog_setting.py：寫入使用者在設定對話框中修改的配置
    - temperature_config_manager.py：可能讀取相關配置
"""

import json
import os


class GlobalConfig:
    """全域配置管理器（單例模式）。

    使用 __new__ 實現單例模式，確保整個應用程式只會建立一個實例。
    配置資料儲存在 self._config 字典中，支援讀取/寫入/刪除/清空操作，
    以及 JSON 檔案的序列化與反序列化。

    屬性：
        _instance (GlobalConfig): 單例實例（類別變數）
        _config (dict): 配置資料字典
        _initialized (bool): 是否已初始化完成的旗標
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """實現單例模式，確保只建立一個實例。"""
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
        return cls._instance

    def __init__(self):
        """初始化配置管理器。首次建立時從 JSON 檔案載入配置。"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            if not os.path.exists("config"):
                os.makedirs("config")
            self.load_from_json()
            # self._config = {
            #     "debug": True,
            #     "log_level": "INFO",
            #     "theme": "light",
            #     "max_connections": 10,
            #     "magnifier_switch": False,
            #     "circle_switch": False,
            # }

    def set(self, key, value):
        """設定配置項目。

        Args:
            key (str): 配置鍵名
            value: 配置值（任意可序列化的型別）
        """
        self._config[key] = value

    def get(self, key, default=None):
        """取得配置項目的值。

        Args:
            key (str): 配置鍵名
            default: 預設值，當鍵不存在時回傳

        Returns:
            配置值，若鍵不存在則回傳 default。
        """
        return self._config.get(key, default)

    def remove(self, key):
        """移除指定的配置項目。"""
        if key in self._config:
            del self._config[key]

    def clear(self):
        """清空所有配置項目。"""
        self._config.clear()

    def save_to_json(self, filename='config/config.json'):
        """將配置字典序列化並儲存為 JSON 檔案。"""
        # 確保配置目錄存在
        config_dir = os.path.dirname(filename)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        with open(filename, mode='w', encoding='utf-8') as file:
            json.dump(self._config, file, ensure_ascii=False, indent=2)

    def load_from_json(self, file_path='config/config.json'):
        """從 JSON 檔案載入配置資料至 self._config。

        Args:
            file_path (str): JSON 配置檔案路徑（預設為 config/config.json）
        """
        if os.path.exists(file_path):
            try:
                with open(file_path, mode='r', encoding='utf-8') as file:
                    self._config = json.load(file)
                print(f"Load config from: {file_path}")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Load config failed: {e}, using default config")
                self._config = self._get_default_config()
        else:
            print(f"Config file not found: {file_path}, using default config")
            self._config = self._get_default_config()
    
    def _get_default_config(self):
        """取得預設配置字典。當 JSON 檔案不存在或解析失敗時使用。

        Returns:
            dict: 包含所有預設配置項目的字典
        """
        return {
            "magnifier_switch": True,               # 放大鏡開關（預設開啟）
            "circle_switch": False,                  # 圓形對齊點標記開關（預設關閉）
            "last_folder_path": None,                # 上次開啟的資料夾路徑

            # ===== 熱力圖標記的顏色與字型設定 =====
            "heat_rect_color": "#BCBCBC",           # 熱力圖 - 矩形框顏色
            "heat_name_color": "#FFFFFF",           # 熱力圖 - 元器件名稱顏色
            "heat_name_font_size": 28,              # 熱力圖 - 元器件名稱字型大小
            "heat_temp_color": "#FF0000",           # 熱力圖 - 最高溫度顏色
            "heat_temp_font_size": 14,              # 熱力圖 - 最高溫度字型大小
            "heat_selected_color": "#4A90E2",       # 熱力圖 - 選中矩形框顏色
            "heat_anchor_color": "#FF0000",         # 熱力圖 - 選中矩形框錨點顏色
            "heat_anchor_radius": 4,                # 熱力圖 - 選中矩形框錨點半徑

            # ===== Layout 圖標記的顏色與字型設定 =====
            "layout_rect_color": "#BCBCBC",         # Layout 圖 - 矩形框顏色
            "layout_name_color": "#FFFFFF",         # Layout 圖 - 元器件名稱顏色
            "layout_name_font_size": 28,            # Layout 圖 - 元器件名稱字型大小
            "layout_temp_color": "#FF0000",         # Layout 圖 - 最高溫度顏色
            "layout_temp_font_size": 14,            # Layout 圖 - 最高溫度字型大小
        }

    def update(self, newObj):
        """批次更新配置。將 newObj 字典的內容合併覆蓋至目前配置。

        Args:
            newObj (dict): 要合併的配置字典
        """
        self._config.update(newObj)
       


# 使用示例
# config = GlobalConfig()
# config.set("app_name", "MyApp")

# print(config.get("app_name"))  # 输出: MyApp
# print(config.get("log_level"))  # 输出: INFO
