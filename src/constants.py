# -*- coding: utf-8 -*-
"""
constants.py - 應用程式常數定義模組

用途：
    集中定義 PCBA 熱力圖溫度點位自動識別工具中使用的全域常數，
    包含預設圖片路徑與點位資料檔案路徑。

在整個應用中的角色：
    作為全域常數的唯一來源，供各模組（如主頁面 main.py、繪製模組 draw_rect.py、
    編輯器 editor_canvas.py 等）引用，確保路徑定義的一致性。

關聯檔案：
    - src/main.py：主程式啟動時讀取預設圖片路徑
    - src/draw_rect.py：繪製標記框時可能參考預設路徑
    - src/editor_canvas.py：畫布編輯器載入圖片時使用預設路徑
    - points/ 資料夾：存放各圖片對應的溫度點位 CSV 檔案

名詞說明：
    - imageA（熱力圖）：紅外線熱像儀拍攝的溫度分佈圖
    - imageB（Layout 圖 / PCB 圖）：PCB 電路板佈局圖
    - points：溫度點位資料，記錄每個標記框的座標和溫度資訊
"""


class Constants:
    """
    應用程式常數類別。

    集中管理所有預設路徑常數，包括：
    - 預設的熱力圖（imageA）檔案路徑
    - 預設的 Layout 圖（imageB）檔案路徑
    - 對應的點位資料檔案路徑（儲存在 points/ 資料夾下）

    所有屬性皆為類別層級變數或靜態方法，無需實例化即可使用。
    """

    imageA_default_path = "imageA.jpg"  # 預設熱力圖（紅外線溫度分佈圖）的檔案名稱
    imageB_default_path = "imageB.jpg"  # 預設 Layout 圖（PCB 電路板佈局圖）的檔案名稱
    
    @staticmethod
    def imageA_point_path():
        """
        取得熱力圖（imageA）對應的點位資料檔案路徑。

        點位資料為 CSV 格式，儲存在 points/ 資料夾下，
        檔名格式為「原始圖片檔名_points.csv」。
        內容包含各標記框的座標、溫度等資訊。

        回傳值：
            str: 熱力圖點位資料的相對檔案路徑，
                 例如 "points/imageA.jpg_points.csv"
        """
        return f"points/{Constants.imageA_default_path}_points.csv"
    
    @staticmethod
    def imageB_point_path():
        """
        取得 Layout 圖（imageB）對應的點位資料檔案路徑。

        點位資料為 CSV 格式，儲存在 points/ 資料夾下，
        檔名格式為「原始圖片檔名_points.csv」。
        內容包含各標記框在 Layout 圖上的對應座標和溫度資訊。

        回傳值：
            str: Layout 圖點位資料的相對檔案路徑，
                 例如 "points/imageB.jpg_points.csv"
        """
        return f"points/{Constants.imageB_default_path}_points.csv"
