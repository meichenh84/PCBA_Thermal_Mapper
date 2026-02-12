#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
溫度配置管理器模組 (temperature_config_manager.py)

用途：
    管理每個資料夾（專案）的溫度相關配置，包括：
    - 溫度過濾參數（最低/最高溫度閾值、最小寬高）
    - PCB 板尺寸（寬度 p_w、高度 p_h，單位 mm）
    - PCB 座標原點設定（左下/左上/右上/右下）及原點偏移量
    - Layout 圖的 padding 參數（上下左右邊距）
    - 各類檔案路徑（熱力圖、PCB 圖、溫度數據、Layout 圖、Layout 數據）
    所有配置會持久化儲存到資料夾下的 config/temperature_config.json。

在整個應用中的角色：
    - 作為全域配置中心，統一管理溫度查詢所需的所有參數
    - 在使用者切換資料夾時自動載入/建立對應的配置檔
    - 配置變更後自動儲存，確保下次開啟時恢復設定

關聯檔案：
    - main.py：主頁面建立並持有 TemperatureConfigManager 實例，讀取/寫入配置
    - layout_temperature_query_optimized.py：從配置管理器取得 PCB 尺寸、原點、padding 等參數
    - load_tempA.py：溫度檔案路徑由配置管理器提供
"""

import json
import os
import threading
from pathlib import Path


class TemperatureConfigManager:
    """
    溫度配置管理器。

    負責管理單一資料夾（專案）的所有溫度相關配置參數，
    並以 JSON 格式持久化到磁碟。每個資料夾有獨立的配置檔，
    切換資料夾時會自動載入對應配置。

    屬性：
        folder_path (str): 目前管理的資料夾路徑
        config_data (dict): 當前的配置數據字典
        current_files (dict): 目前已載入的各類檔案路徑資訊
        default_config (dict): 預設配置值，當配置檔不存在時使用
    """

    def __init__(self, folder_path=None):
        """
        初始化溫度配置管理器。

        Args:
            folder_path (str, optional): 資料夾路徑。若提供，會自動載入該資料夾的配置；
                                         若為 None，則使用預設配置。
        """
        print(f"初始化温度配置管理器，文件夹路径: {folder_path}")
        self.folder_path = folder_path    # 目前管理的資料夾路徑
        self.config_data = {}             # 配置數據字典，儲存所有參數的鍵值對
        self.current_files = {}           # 目前已載入的各類檔案路徑
        
        # 預設配置 - 定義所有可配置參數的預設值
        self.default_config = {
            # === 溫度過濾參數 ===
            "min_temp": 50.0,             # 最低溫度閾值（攝氏度），低於此溫度的元器件不顯示
            "max_temp": 80.0,             # 最高溫度閾值（攝氏度），高於此溫度的元器件不顯示
            # min_width 和 min_height 已移除（未實際使用）
            # === PCB 板實體尺寸（單位：mm） ===
            "p_w": 237.0,                 # PCB 板寬度（毫米）
            "p_h": 194.0,                 # PCB 板高度（毫米）
            # === PCB 座標原點設定 ===
            "p_origin": "左下",            # PCB 座標系原點位置
            "p_origin_offset_x": 0.0,     # PCB 原點在 X 方向的偏移量（像素）
            "p_origin_offset_y": 0.0,     # PCB 原點在 Y 方向的偏移量（像素）
            # === Layout 圖 padding 參數（單位：像素） ===
            "c_padding_left": 0.0,        # Layout 圖左側邊距
            "c_padding_top": 0.0,         # Layout 圖上方邊距
            "c_padding_right": 0.0,       # Layout 圖右側邊距
            "c_padding_bottom": 0.0,      # Layout 圖下方邊距
            # === 檔案路徑配置 ===
            "current_heat_file": None,         # 目前選擇的熱力圖檔案路徑
            "current_pcb_file": None,          # 目前選擇的 PCB 圖檔案路徑
            "current_temp_file": None,         # 目前選擇的溫度數據檔案路徑（tempA）
            "current_layout_file": None,       # 目前選擇的 Layout 圖檔案路徑
            "current_layout_data_file": None,  # (已棄用) 舊的 Layout 數據檔案路徑
            "current_layout_xy_file": None,    # 目前選擇的元器件座標檔案路徑（RefDes, Orient., X, Y）
            "current_layout_lwt_file": None    # 目前選擇的元器件尺寸檔案路徑（RefDes, L, W, T）
        }
        
        if folder_path:
            self.set_folder_path(folder_path)  # 若有提供路徑，立即載入配置
        else:
            # 如果沒有提供資料夾路徑，使用預設配置
            self.config_data = self.default_config.copy()
            print("使用默认配置初始化配置管理器")
    
    def set_folder_path(self, folder_path):
        """
        設定資料夾路徑並載入對應的配置。

        會在資料夾下建立 config/ 子目錄（若不存在），
        然後載入或建立 temperature_config.json 配置檔。

        Args:
            folder_path (str): 目標資料夾的絕對路徑。
        """
        print(f"TemperatureConfigManager: 开始设置文件夹路径 {folder_path}")
        try:
            self.folder_path = folder_path
            print(f"set_folder_path: 开始处理文件夹路径 {folder_path}")
            
            # 建立配置目錄（若不存在）
            config_dir = os.path.join(folder_path, "config")  # 配置檔存放目錄
            print(f"set_folder_path: 配置目录 {config_dir}")

            if not os.path.exists(config_dir):
                print(f"set_folder_path: 检查配置目录是否存在")
                os.makedirs(config_dir, exist_ok=True)  # 遞迴建立目錄
                print(f"创建配置目录: {config_dir}")
            
            # 載入配置
            print(f"set_folder_path: 开始加载配置")
            self.load_config()
            print(f"set_folder_path: 配置加载完成")
            
            print(f"TemperatureConfigManager: 文件夹路径设置完成")
        except Exception as e:
            print(f"设置文件夹路径时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def load_config(self):
        """
        從磁碟載入配置檔。

        讀取 {folder_path}/config/temperature_config.json，
        若檔案不存在則使用預設配置並儲存一份新的配置檔。
        若載入過程中發生錯誤，則回退為預設配置。
        """
        try:
            if not self.folder_path:
                print("没有文件夹路径，使用默认配置")
                self.config_data = self.default_config.copy()
                return
            
            config_file = os.path.join(self.folder_path, "config", "temperature_config.json")  # 配置檔完整路徑
            print(f"load_config: 开始加载配置文件 {config_file}")
            
            if os.path.exists(config_file):
                print(f"load_config: 配置文件存在，开始读取")
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)  # 從 JSON 反序列化為字典
                print(f"加载温度过滤配置: {config_file}")
            else:
                print(f"配置文件不存在，使用默认配置")
                self.config_data = self.default_config.copy()
                self.save_config()  # 建立新的配置檔
            
            print(f"load_config: 配置加载完成")
        except Exception as e:
            print(f"加载配置时出错: {e}")
            import traceback
            traceback.print_exc()
            self.config_data = self.default_config.copy()  # 錯誤時回退為預設配置
    
    def save_config(self):
        """
        將目前的配置數據儲存到磁碟。

        序列化 self.config_data 為 JSON 格式，寫入配置檔。
        使用 UTF-8 編碼且保留非 ASCII 字元（如中文）。
        """
        try:
            if not self.folder_path:
                print("没有文件夹路径，无法保存配置")
                return
            
            config_file = os.path.join(self.folder_path, "config", "temperature_config.json")
            print(f"保存温度过滤配置: {config_file}")
            
            # 確保配置目錄存在
            config_dir = os.path.dirname(config_file)
            os.makedirs(config_dir, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)  # 格式化輸出
            
            print(f"配置保存成功")
        except Exception as e:
            print(f"保存配置时出错: {e}")
            import traceback
            traceback.print_exc()

    def get(self, key, default=None):
        """
        取得單一配置值。

        Args:
            key (str): 配置鍵名（如 "min_temp"、"p_w" 等）。
            default: 當鍵不存在時回傳的預設值。

        Returns:
            配置值，型別視具體參數而定（float、str 或 None）。
        """
        return self.config_data.get(key, default)
    
    def set(self, key, value):
        """
        設定單一配置值（僅在記憶體中，不會自動儲存到磁碟）。

        Args:
            key (str): 配置鍵名。
            value: 要設定的值。
        """
        self.config_data[key] = value
    
    def get_current_files(self):
        """
        取得目前已載入的檔案資訊。

        Returns:
            dict: 目前檔案資訊的副本，避免外部直接修改內部狀態。
        """
        return self.current_files.copy()
    
    def set_current_files(self, files):
        """
        設定目前已載入的檔案資訊。

        Args:
            files (dict): 檔案資訊字典，鍵為檔案類型名稱，值為檔案路徑。
        """
        self.current_files = files.copy()
    
    def get_relative_path(self, file_path):
        """
        將絕對路徑轉換為相對於資料夾的相對路徑，用於介面上顯示較短的路徑文字。

        Args:
            file_path (str): 檔案的絕對路徑。

        Returns:
            str: 相對路徑字串；若轉換失敗則回傳原始路徑。
        """
        if not file_path or not self.folder_path:
            return file_path
        
        try:
            return os.path.relpath(file_path, self.folder_path)
        except:
            return file_path
    
    def get_file_info_display(self):
        """
        取得檔案資訊的顯示文字，用於 UI 介面呈現。

        將所有已載入的檔案以「類型: 相對路徑」格式組合成多行文字。

        Returns:
            str: 格式化的檔案資訊文字。若無檔案則回傳「未加載文件」。
        """
        try:
            if not self.current_files:
                return "未加载文件"
            
            info_lines = []
            for file_type, file_path in self.current_files.items():
                if file_path:
                    relative_path = self.get_relative_path(file_path)
                    info_lines.append(f"{file_type}: {relative_path}")
                else:
                    info_lines.append(f"{file_type}: 未选择")
            
            return "\n".join(info_lines)
        except Exception as e:
            print(f"get_file_info_display: 获取文件信息时出错: {e}")
            return "未加载文件"
    
    def get_all_parameters(self):
        """
        取得所有配置參數。

        Returns:
            dict: 所有配置參數的副本。
        """
        return self.config_data.copy()
    
    def save_parameters(self, params):
        """
        批次更新並儲存配置參數。

        Args:
            params (dict): 要更新的參數鍵值對。
        """
        try:
            print(f"保存参数: {params}")
            self.config_data.update(params)  # 合併新參數到配置中
            self.save_config()               # 持久化到磁碟
            print(f"参数保存成功")
        except Exception as e:
            print(f"保存参数时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def update(self, **kwargs):
        """
        使用關鍵字參數更新配置並自動儲存。

        Args:
            **kwargs: 要更新的配置鍵值對。
        """
        self.config_data.update(kwargs)
        self.save_config()
    
    def set_file_path(self, file_type, file_path):
        """
        設定指定類型的檔案路徑並儲存配置。

        Args:
            file_type (str): 檔案類型鍵名，必須是以下之一：
                "current_heat_file", "current_pcb_file", "current_temp_file",
                "current_layout_file", "current_layout_xy_file", "current_layout_lwt_file",
                "current_layout_xy_file", "current_layout_lwt_file"
            file_path (str): 檔案的絕對路徑。
        """
        if file_type in ["current_heat_file", "current_pcb_file", "current_temp_file", "current_layout_file", "current_layout_data_file", "current_layout_xy_file", "current_layout_lwt_file"]:
            self.config_data[file_type] = file_path
            self.save_config()
            print(f"设置文件路径: {file_type} = {file_path}")
        else:
            print(f"不支持的文件类型: {file_type}")
    
    def get_file_path(self, file_type):
        """
        取得指定類型的檔案路徑。

        Args:
            file_type (str): 檔案類型鍵名。

        Returns:
            str 或 None: 檔案路徑，若未設定則為 None。
        """
        return self.config_data.get(file_type, None)
    
    def get_all_file_paths(self):
        """
        取得所有檔案路徑的字典。

        Returns:
            dict: 包含所有五種檔案類型及其路徑的字典。
        """
        return {
            "current_heat_file": self.config_data.get("current_heat_file"),       # 熱力圖路徑
            "current_pcb_file": self.config_data.get("current_pcb_file"),         # PCB 圖路徑
            "current_temp_file": self.config_data.get("current_temp_file"),       # 溫度數據路徑
            "current_layout_file": self.config_data.get("current_layout_file"),   # Layout 圖路徑
            "current_layout_data_file": self.config_data.get("current_layout_data_file"),  # (已棄用)
            "current_layout_xy_file": self.config_data.get("current_layout_xy_file"),    # 元器件座標路徑
            "current_layout_lwt_file": self.config_data.get("current_layout_lwt_file")   # 元器件尺寸路徑
        }
    
    def clear_file_paths(self):
        """
        清空所有檔案路徑配置並儲存。用於重置檔案選擇狀態。
        """
        for file_type in ["current_heat_file", "current_pcb_file", "current_temp_file", "current_layout_file", "current_layout_data_file", "current_layout_xy_file", "current_layout_lwt_file"]:
            self.config_data[file_type] = None
        self.save_config()
        print("已清空所有文件路径")
