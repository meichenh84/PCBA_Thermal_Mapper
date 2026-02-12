#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
溫度數據載入器模組 (load_tempA.py)

用途：
    負責從 CSV 或 Excel 檔案中載入溫度矩陣數據 (tempA)。
    tempA 是一個二維 NumPy 陣列，每個元素代表熱力圖上對應像素位置的溫度值（攝氏度）。
    提供查詢指定矩形區域內最高溫度及其座標的功能。

在整個應用中的角色：
    - 作為溫度數據的唯一載入入口，採用單例模式確保全域只有一份溫度數據實例
    - 被 layout_temperature_query_optimized.py 呼叫，用於查詢元器件對應區域的溫度
    - 被主頁面 (main.py) 呼叫，用於初始化溫度數據及即時溫度查詢
    - 溫度檔案路徑由 temperature_config_manager.py 管理

關聯檔案：
    - temperature_config_manager.py：提供溫度檔案路徑設定
    - layout_temperature_query_optimized.py：使用本模組載入的溫度數據進行元器件溫度查詢
    - main.py：在主頁面初始化時建立 TempLoader 實例
"""

import pandas as pd
import time
import numpy as np
import os


class TempLoader:
    """
    溫度數據載入器（單例模式）。

    採用單例設計模式 (Singleton Pattern)，確保整個應用程式中只存在一個溫度數據實例。
    當檔案路徑改變時，會自動重新建立實例並載入新的溫度數據。

    類別屬性：
        _instance: 單例實例的參考
        _tempA: 儲存溫度矩陣數據的 NumPy 二維陣列（行=Y座標，列=X座標）
        _current_file_path: 目前已載入的檔案路徑，用於判斷是否需要重新載入

    使用範例：
        loader = TempLoader('path/to/tempA.csv')
        temp_matrix = loader.get_tempA()
        max_temp = loader.get_max_temp(x1, y1, x2, y2, scale=2)
    """

    _instance = None           # 單例實例，確保全域只有一個 TempLoader 物件
    _tempA = None              # 溫度矩陣數據（NumPy 二維陣列，值為攝氏溫度）
    _current_file_path = None  # 目前已載入的溫度檔案路徑

    def __new__(cls, file_path='tempA.csv'):
        """
        單例模式的建構方法。

        當尚未建立實例，或傳入的檔案路徑與目前已載入的不同時，
        會重新建立實例並載入新的溫度數據。

        Args:
            file_path (str): 溫度數據檔案路徑，支援 .csv 和 .xlsx 格式。預設為 'tempA.csv'。

        Returns:
            TempLoader: 溫度載入器的單例實例。
        """
        # 如果尚未建立實例，或檔案路徑已改變，則重新建立實例
        if cls._instance is None or cls._current_file_path != file_path:
            cls._instance = super().__new__(cls)
            cls._instance._file_path = file_path      # 記錄要載入的檔案路徑
            cls._current_file_path = file_path         # 更新類別層級的檔案路徑紀錄
            cls._instance._initialize_tempA()          # 觸發溫度數據載入
        return cls._instance

    def _initialize_tempA(self):
        """
        初始化溫度數據的載入流程。

        作為內部方法，在單例實例建立時自動呼叫，負責啟動實際的檔案讀取作業。
        """
        print("Initializing tempA...")
        self._load_tempA()

    def _detect_csv_encoding_and_sep(self):
        """
        自動偵測 CSV 檔案的編碼與分隔符號。

        偵測邏輯：
            1. 讀取檔案前 4 bytes 檢查 BOM（Byte Order Mark）
               - FF FE → UTF-16 LE
               - FE FF → UTF-16 BE
               - EF BB BF → UTF-8 with BOM
               - 其他 → 預設 UTF-8
            2. 用偵測到的編碼讀取第一行，判斷分隔符號
               - 包含 Tab (\\t) → sep='\\t'
               - 否則 → sep=','

        Returns:
            tuple: (encoding, sep) 例如 ('utf-16', '\\t') 或 ('utf-8', ',')
        """
        with open(self._file_path, 'rb') as f:
            raw = f.read(4)

        # 偵測 BOM 決定編碼
        if raw[:2] == b'\xff\xfe':
            encoding = 'utf-16'
        elif raw[:2] == b'\xfe\xff':
            encoding = 'utf-16'
        elif raw[:3] == b'\xef\xbb\xbf':
            encoding = 'utf-8-sig'
        else:
            encoding = 'utf-8'

        # 讀取第一行偵測分隔符號
        with open(self._file_path, 'r', encoding=encoding, errors='replace') as f:
            first_line = f.readline()

        sep = '\t' if '\t' in first_line else ','
        return encoding, sep

    def _load_tempA(self):
        """
        根據檔案副檔名選擇對應的方式載入溫度數據。

        支援的檔案格式：
            - .xlsx：使用 pandas.read_excel() 讀取 Excel 檔案
            - .csv：使用 pandas.read_csv() 讀取 CSV 檔案
                    自動偵測 UTF-8 / UTF-16 編碼，以及 Tab / 逗號分隔符號

        載入後的數據會轉換為 NumPy 二維陣列儲存於 self._tempA。
        陣列的 shape 為 (高度, 寬度)，對應熱力圖的像素矩陣。

        Raises:
            ValueError: 當檔案副檔名不是 .xlsx 或 .csv 時拋出。
        """
        file_extension = os.path.splitext(self._file_path)[1].lower()  # 取得檔案副檔名並轉為小寫

        if file_extension == '.xlsx':
            self._tempA = pd.read_excel(self._file_path).values  # 從 Excel 載入並轉為 NumPy 陣列
            print("-->>> tempA loaded from Excel, size:", self._tempA.shape)
        elif file_extension == '.csv':
            encoding, sep = self._detect_csv_encoding_and_sep()
            self._tempA = pd.read_csv(self._file_path, encoding=encoding, sep=sep, header=None).values
            print(f"-->>> tempA loaded from CSV (encoding={encoding}, sep={repr(sep)}), size:", self._tempA.shape)
        else:
            raise ValueError("Unsupported file type. Please use .xlsx or .csv files.")

    def get_tempA(self):
        """
        取得溫度矩陣數據。

        Returns:
            numpy.ndarray: 溫度矩陣的二維陣列，shape 為 (高度, 寬度)，
                          每個元素為該位置的攝氏溫度值。
        """
        return self._tempA
    
    def get_max_temp(self, x1, y1, x2, y2, scale = 1):
        """
        查詢指定矩形區域內的最高溫度值。

        將傳入的座標除以 scale 參數後，從溫度矩陣中擷取對應的子矩陣，
        並回傳該子矩陣中的最大值。

        Args:
            x1 (int/float): 矩形區域左邊界的 X 座標（縮放後）。
            y1 (int/float): 矩形區域上邊界的 Y 座標（縮放後）。
            x2 (int/float): 矩形區域右邊界的 X 座標（縮放後）。
            y2 (int/float): 矩形區域下邊界的 Y 座標（縮放後）。
            scale (int/float): 座標縮放比例。例如 scale=2 表示顯示圖像是原始溫度矩陣的 2 倍大小。預設為 1。

        Returns:
            float: 指定區域內的最高溫度值（攝氏度）。若區域為空或無效，則回傳 0。
        """
        maxH, maxW = self._tempA.shape  # maxH=溫度矩陣高度(列數), maxW=寬度(行數)
        # 將縮放後的座標轉換回原始溫度矩陣座標，並限制在有效範圍內
        _x1 = max(0, int(x1 / scale))              # 左邊界，不小於 0
        _y1 = max(0, int(y1 / scale))              # 上邊界，不小於 0
        _x2 = min(maxW, int(x2 / scale))           # 右邊界，不超過矩陣寬度
        _y2 = min(maxH, int(y2 / scale))           # 下邊界，不超過矩陣高度
        sub_matrix = self._tempA[_y1:_y2, _x1:_x2]  # 擷取子矩陣（NumPy 索引：[行,列] = [Y,X]）

        if sub_matrix is not None and sub_matrix.size > 0:
            return np.max(sub_matrix)  # 回傳子矩陣中的最大溫度值
        return 0
    
    def get_max_temp_coords(self, x1, y1, x2, y2, scale = 1):
        """
        查詢指定矩形區域內最高溫度點的座標。

        與 get_max_temp() 類似，但除了找出最高溫度外，還會回傳該最高溫度點
        在縮放座標系中的 (x, y) 座標位置。

        Args:
            x1 (int/float): 矩形區域左邊界的 X 座標（縮放後）。
            y1 (int/float): 矩形區域上邊界的 Y 座標（縮放後）。
            x2 (int/float): 矩形區域右邊界的 X 座標（縮放後）。
            y2 (int/float): 矩形區域下邊界的 Y 座標（縮放後）。
            scale (int/float): 座標縮放比例，預設為 1。

        Returns:
            tuple: (x, y) 最高溫度點在縮放座標系中的座標。若區域為空或無效，則回傳 (0, 0)。
        """
        maxH, maxW = self._tempA.shape  # maxH=溫度矩陣高度, maxW=寬度
        _x1 = max(0, int(x1 / scale))              # 左邊界
        _y1 = max(0, int(y1 / scale))              # 上邊界
        _x2 = min(maxW, int(x2 / scale))           # 右邊界
        _y2 = min(maxH, int(y2 / scale))           # 下邊界
        sub_matrix = self._tempA[_y1:_y2, _x1:_x2]  # 擷取子矩陣

        if sub_matrix is not None and sub_matrix.size > 0:
            max_index = np.argmax(sub_matrix)  # 取得最大值的一維索引
            max_coords = np.unravel_index(max_index, sub_matrix.shape)  # 轉為 (row, col) 即 (Y, X)
            # 將子矩陣內的相對座標轉為全域座標，並乘以 scale 還原為縮放座標系
            return (max_coords[1] + _x1)*scale, (max_coords[0] + _y1)*scale
        return 0, 0

    def get_max_temp_in_circle(self, cx, cy, radius, scale=1):
        """
        查詢指定圓形區域內的最高溫度值（僅考慮圓形內部的點）。

        Args:
            cx (float): 圓心的 X 座標（縮放後）。
            cy (float): 圓心的 Y 座標（縮放後）。
            radius (float): 圓形半徑（縮放後）。
            scale (float): 座標縮放比例，預設為 1。

        Returns:
            float: 圓形區域內的最高溫度值。若區域為空或無效，則回傳 0。
        """
        maxH, maxW = self._tempA.shape

        # 計算圓形的外接矩形範圍
        x1 = max(0, int((cx - radius) / scale))
        y1 = max(0, int((cy - radius) / scale))
        x2 = min(maxW, int((cx + radius) / scale))
        y2 = min(maxH, int((cy + radius) / scale))

        # 圓心在溫度矩陣中的座標
        center_x = cx / scale
        center_y = cy / scale
        radius_in_matrix = radius / scale

        max_temp = -float('inf')
        found = False

        # 遍歷外接矩形內的所有點
        for y in range(y1, y2):
            for x in range(x1, x2):
                # 計算點到圓心的距離
                distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                # 只考慮圓形內部的點
                if distance <= radius_in_matrix:
                    temp = self._tempA[y, x]
                    if temp > max_temp:
                        max_temp = temp
                        found = True

        return max_temp if found else 0

    def get_max_temp_coords_in_circle(self, cx, cy, radius, scale=1):
        """
        查詢指定圓形區域內最高溫度點的座標（僅考慮圓形內部的點）。

        Args:
            cx (float): 圓心的 X 座標（縮放後）。
            cy (float): 圓心的 Y 座標（縮放後）。
            radius (float): 圓形半徑（縮放後）。
            scale (float): 座標縮放比例，預設為 1。

        Returns:
            tuple: (x, y) 最高溫度點在縮放座標系中的座標。若區域為空或無效，則回傳 (0, 0)。
        """
        maxH, maxW = self._tempA.shape

        # 計算圓形的外接矩形範圍
        x1 = max(0, int((cx - radius) / scale))
        y1 = max(0, int((cy - radius) / scale))
        x2 = min(maxW, int((cx + radius) / scale))
        y2 = min(maxH, int((cy + radius) / scale))

        # 圓心在溫度矩陣中的座標
        center_x = cx / scale
        center_y = cy / scale
        radius_in_matrix = radius / scale

        max_temp = -float('inf')
        max_x, max_y = 0, 0
        found = False

        # 遍歷外接矩形內的所有點
        for y in range(y1, y2):
            for x in range(x1, x2):
                # 計算點到圓心的距離
                distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                # 只考慮圓形內部的點
                if distance <= radius_in_matrix:
                    temp = self._tempA[y, x]
                    if temp > max_temp:
                        max_temp = temp
                        max_x = x
                        max_y = y
                        found = True

        # 返回縮放座標系中的座標
        return (max_x * scale, max_y * scale) if found else (0, 0)

    def get_max_temp_in_polygon(self, corners, scale=1):
        """查詢旋轉多邊形區域內的最高溫度值。

        使用 cv2.fillPoly 建立多邊形遮罩，再以遮罩取溫度矩陣中的最大值。
        效能優於逐像素 Python 迴圈。

        Args:
            corners (list[tuple]): 多邊形頂點座標（縮放後座標系）。
                                   例如 [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]。
            scale (float): 座標縮放比例，預設為 1。

        Returns:
            float: 多邊形區域內的最高溫度值。若區域無效，則回傳 0。
        """
        from rotation_utils import create_polygon_mask

        maxH, maxW = self._tempA.shape
        # 將頂點座標轉換到溫度矩陣座標系
        matrix_corners = [(x / scale, y / scale) for x, y in corners]

        mask = create_polygon_mask(matrix_corners, (maxH, maxW))
        masked = self._tempA[mask]

        if masked.size > 0:
            return float(np.max(masked))
        return 0

    def get_max_temp_coords_in_polygon(self, corners, scale=1):
        """查詢旋轉多邊形區域內最高溫度點的座標。

        Args:
            corners (list[tuple]): 多邊形頂點座標（縮放後座標系）。
            scale (float): 座標縮放比例，預設為 1。

        Returns:
            tuple: (x, y) 最高溫度點在縮放座標系中的座標。若區域無效，則回傳 (0, 0)。
        """
        from rotation_utils import create_polygon_mask

        maxH, maxW = self._tempA.shape
        matrix_corners = [(x / scale, y / scale) for x, y in corners]

        mask = create_polygon_mask(matrix_corners, (maxH, maxW))
        masked = self._tempA[mask]

        if masked.size > 0:
            max_val = np.max(masked)
            # 找到最大值在遮罩內的位置
            # 用 np.where 同時滿足遮罩和最大值
            ys, xs = np.where(mask & (self._tempA == max_val))
            if len(ys) > 0:
                return (int(xs[0]) * scale, int(ys[0]) * scale)
        return (0, 0)


# ============================================================================
# 外部程式碼使用範例
# ============================================================================
# 在程式中其他地方使用時，不需要再次初始化，只需直接呼叫 TempLoader()
# loader = TempLoader('tempA.xlsx')

# 外部程式碼可以繼續執行其他任務，直到需要取得 tempA 時
# print("Waiting for tempA to load...")

# 取得 tempA 數據（會阻塞直到數據載入完成）
# tempA_data = loader.get_tempA()

# 數據載入完成後，外部程式碼取得數據並使用
# print("-->>> Retrieved tempA:", tempA_data)
