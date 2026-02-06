#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canvas 矩形項目資料模型 (canvas_rect_item.py)

用途：
    定義 Canvas 上矩形標記的資料結構（Data Model），
    儲存每個元器件矩形框的座標、中心點、最高溫度、名稱，
    以及在 Canvas 上的繪圖 ID。作為熱力圖與 Layout 圖上
    元器件標記的基礎資料單元。

在整個應用中的角色：
    - 被 editor_rect.py 和 editor_canvas.py 用來管理 Canvas 上的矩形標記
    - 被 main.py 用來儲存和傳遞元器件的標記資訊
    - 被 temperature_config_manager.py 用來序列化/反序列化元器件資料

關聯檔案：
    - editor_rect.py：使用 CanvasRectItem 建立和管理矩形框
    - editor_canvas.py：透過 CanvasRectItem 在 Canvas 上繪製標記
    - main.py：建立 CanvasRectItem 實例並傳遞給各模組
    - temperature_config_manager.py：透過 to_dict() 序列化資料
"""


class CanvasRectItem:
    """Canvas 矩形項目資料類別。

    儲存單一元器件在 Canvas 上的矩形框資訊，包括邊界座標、
    中心點座標、最高溫度值、元器件名稱，以及 Canvas 繪圖物件的 ID。

    屬性：
        x1 (int): 矩形框左上角 X 座標
        y1 (int): 矩形框左上角 Y 座標
        x2 (int): 矩形框右下角 X 座標
        y2 (int): 矩形框右下角 Y 座標
        cx (int): 矩形框中心點 X 座標
        cy (int): 矩形框中心點 Y 座標
        max_temp (float): 該元器件區域的最高溫度值
        name (str): 元器件名稱（如 "U1", "C3" 等）
        rectId (int): 矩形框在 Canvas 上的繪圖物件 ID
        nameId (int): 名稱標籤在 Canvas 上的繪圖物件 ID
    """

    def __init__(self, x1, y1, x2, y2, cx, cy, max_temp, name, rectId = 0, nameId = 0):
        """初始化矩形項目。

        Args:
            x1 (int): 矩形框左上角 X 座標
            y1 (int): 矩形框左上角 Y 座標
            x2 (int): 矩形框右下角 X 座標
            y2 (int): 矩形框右下角 Y 座標
            cx (int): 矩形框中心點 X 座標
            cy (int): 矩形框中心點 Y 座標
            max_temp (float): 最高溫度值
            name (str): 元器件名稱
            rectId (int): Canvas 矩形繪圖 ID（預設 0）
            nameId (int): Canvas 名稱標籤繪圖 ID（預設 0）
        """
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.cx = cx
        self.cy = cy
        self.max_temp = max_temp
        self.name = name
        self.rectId = rectId
        self.nameId = nameId

    def set_nameId(self, nameId):
        """設定名稱標籤在 Canvas 上的繪圖物件 ID。"""
        self.nameId = nameId

    def set_rectId(self, rectId):
        """設定矩形框在 Canvas 上的繪圖物件 ID。"""
        self.rectId = rectId

    def set_rect_boundary(self, x1, y1, x2, y2):
        """更新矩形框的邊界座標。用於拖曳調整矩形大小後同步資料。"""
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def __repr__(self):
        """回傳類別的字串表示，方便除錯和列印。"""
        return (f"RectItem(x1={self.x1}, y1={self.y1}, x2={self.x2}, y2={self.y2}, "
                f"cx={self.cx}, cy={self.cy}, max_temp={self.max_temp}, "
                f"name={self.name}, rectId={self.rectId}, nameId={self.nameId})")

    def to_dict(self):
        """將類別實例轉換為字典，用於 JSON 序列化儲存。"""
        return {
            "x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2,
            "cx": self.cx, "cy": self.cy, "max_temp": self.max_temp,
            "name": self.name, "rectId": self.rectId, "nameId": self.nameId
        }
    
    def get_value(self, key):
        """透過屬性名稱動態取得對應的值。

        Args:
            key (str): 屬性名稱（如 "x1", "name", "max_temp" 等）

        Returns:
            屬性值，若屬性不存在則回傳 None。
        """
        if hasattr(self, key):
            return getattr(self, key)
        else:
            return None

# 示例：创建一个 RectItem 实例
rect_item = CanvasRectItem(x1=0, y1=0, x2=10, y2=10, cx=5, cy=5, max_temp=100, name="Rect1", rectId=1, nameId=101)

# 打印 RectItem 实例
print(rect_item)

# 转换为字典
rect_dict = rect_item.to_dict()
print(rect_dict)
