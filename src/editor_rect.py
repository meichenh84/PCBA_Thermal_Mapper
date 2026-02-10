#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
矩形框編輯器模組 (editor_rect.py)

用途：
    提供 Canvas 上矩形標記框的完整編輯功能，包括：
    1. 矩形框的建立、拖曳移動、調整大小和刪除
    2. 錨點（anchor）顯示和拖曳調整尺寸
    3. 溫度資料的查詢和顯示
    4. 智慧文字定位（避免重疊）
    5. 雙擊矩形框彈出編輯對話框（單例模式）
    6. 座標轉換和縮放處理
    7. 多選框選功能

在整個應用中的角色：
    - 被 editor_canvas.py 建立，作為「編輯溫度」對話框中的核心編輯引擎
    - 管理所有矩形標記框的互動操作

關聯檔案：
    - editor_canvas.py：建立 RectEditor 實例並提供 Canvas
    - dialog_component_setting.py：雙擊矩形框時彈出的編輯對話框
    - draw_rect.py：呼叫 draw_canvas_item() 繪製矩形標記
    - load_tempA.py：載入溫度資料進行查詢
    - bean/canvas_rect_item.py：矩形標記的資料模型

UI 元件對應命名：
    - canvas (tk.Canvas): 繪圖用的 Canvas 元件
    - rectangles (list): 所有矩形框的 CanvasRectItem 列表
    - anchors (list): 目前選中矩形框的 8 個錨點 ID 列表
    - drag_data (dict): 拖曳操作的狀態資訊
    - multi_select_rect (int): 多選框的 Canvas 物件 ID
    - selected_rect_ids (set): 目前選中的矩形框 ID 集合
"""

import tkinter as tk
import numpy as np

from dialog_component_setting import ComponentSettingDialog
from load_tempA import TempLoader
from draw_rect import draw_canvas_item, calc_temp_text_offset, OUTLINE_OFFSETS


class RectEditor:
    """矩形框編輯器。

    管理 Canvas 上所有矩形標記框的建立、選取、拖曳、調整大小和刪除。
    支援單選拖曳、多選框選、雙擊編輯等互動操作。

    屬性：
        canvas (tk.Canvas): 繫結的 Canvas 元件
        parent (tk.Widget): 父元件
        mark_rect (list): 元器件標記資料列表
        temp_file_path (str): 溫度資料檔案路徑
        on_rect_change_callback (callable): 矩形框變更時的回呼函式
        display_scale (float): 目前顯示的縮放比例
        drag_threshold (int): 拖曳閾值（小於此值不觸發拖曳）
        rectangles (list): 所有矩形框的 CanvasRectItem 列表
        anchors (list): 目前選中矩形框的錨點 ID 列表
        multi_select_enabled (bool): 多選功能是否啟用
        selected_rect_ids (set): 選中的矩形框 ID 集合
    """

    def __init__(self, parent, canvas, mark_rect = None, temp_file_path = None, on_rect_change_callback=None):
        """初始化矩形框編輯器。

        Args:
            parent (tk.Widget): 父元件
            canvas (tk.Canvas): 繪圖用的 Canvas 元件
            mark_rect (list|None): 初始的元器件標記資料列表
            temp_file_path (str|None): 溫度資料檔案路徑
            on_rect_change_callback (callable|None): 矩形框變更時的回呼函式
        """
        super().__init__()

        self.canvas = canvas
        self.parent = parent
        self.temp_file_path = temp_file_path
        self.on_rect_change_callback = on_rect_change_callback  # 矩形框变化回调
        self.display_scale = 1.0  # 当前显示缩放比例
        self.drag_threshold = 3  # 拖拽阈值，小于此值不触发拖拽
        # Create canvas if not passed as argument
        # if canvas:
        #     self.canvas = canvas
        # else:
        #     self.canvas = tk.Canvas(self, bg="white", width=800, height=600)
        #     self.canvas.pack(fill=tk.BOTH, expand=True)
        self.mark_rect = mark_rect
        # Store rectangle state information
        self.drag_data = {"rectId": None, "nameId": None, "x": 0, "y": 0, "resize": False, "anchor": None, "triangleId": 0, "tempTextId": 0}
        # rectItem = {"x1": 0,  "y1": 0, "x2": 10, "y2": 10, "cx": 5, "cy": 5, "max_temp": 73.2, "name": "A","rectId": 0,"nameId": 0, "rectId": 0}

        self.rectangles = []  # To store multiple rectangles
        self.anchors = []     # To store anchors for active rectangle

        # 多选相关状态
        self.multi_select_enabled = False  # 多选功能启用标志（由EditorCanvas控制）
        self.multi_select_mode = False  # 是否处于多选模式（正在框选中）
        self.multi_select_rect = None  # 多选框的canvas ID
        self.multi_select_start = None  # 多选框起点 (x, y)
        self.selected_rect_ids = set()  # 当前选中的矩形框ID集合

        # Initialize rectangle creation parameters
        self.conner_width = 3  # Anchor size
        self.min_width = 10    # Minimum size for resizing
        
        # 使用传递的温度文件路径创建TempLoader
        if self.temp_file_path:
            self.tempALoader = TempLoader(self.temp_file_path)
        else:
            # 如果没有传递文件路径，尝试使用默认文件名
            self.tempALoader = TempLoader('tempA1.csv')

        self.add_new_count = 0
        self.delete_origin_count = 0
        self.modify_origin_set = set()
        
        # 弹窗管理
        self.current_dialog = None  # 当前显示的弹窗

        # 縮放和拖動相關屬性
        self.magnifier_mode_enabled = False  # 放大模式是否啟用（由 EditorCanvas 控制）
        self.zoom_scale = 1.0                # 當前縮放比例
        self.min_zoom = 1.0                  # 最小縮放比例（fit to window）
        self.max_zoom = 5.0                  # 最大縮放比例
        self.canvas_offset_x = 0             # Canvas 圖像偏移 X
        self.canvas_offset_y = 0             # Canvas 圖像偏移 Y
        self.is_panning = False              # 是否正在拖動視圖
        self.pan_start_x = 0                 # 拖動起始點 X
        self.pan_start_y = 0                 # 拖動起始點 Y
        self.original_bg_image = None        # 原始背景圖像
        self.scaled_bg_image = None          # 縮放後的背景圖像
        self.bg_image_id = None              # 背景圖像的 Canvas ID

        # Bind events for canvas
        self.canvas.bind("<ButtonPress-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        # 移除右键删除功能，改用Delete键和删除按钮
        self.canvas.bind("<Double-Button-1>", self.on_double_click) # 绑定双击事件

        # 綁定滾輪縮放事件
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows/macOS
        self.canvas.bind("<Button-4>", lambda e: self.on_mouse_wheel_linux(e, 1))  # Linux 向上
        self.canvas.bind("<Button-5>", lambda e: self.on_mouse_wheel_linux(e, -1))  # Linux 向下

        # 綁定右鍵拖動事件
        self.canvas.bind("<Button-3>", self.on_right_click_start)
        self.canvas.bind("<B3-Motion>", self.on_right_click_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_right_click_end)

        self.canvas.after(100, self.init_marks)

    # 不再需要缩放坐标，直接使用原图像坐标

    def init_marks(self):
        if len(self.mark_rect) > 0:
            for item in self.mark_rect:
                # 確保舊資料相容性：沒有 shape 欄位的預設為矩形
                if "shape" not in item:
                    item["shape"] = "rectangle"
                self.create_rectangle(item)

    def update_display_scale(self, display_scale):
        """更新显示缩放比例，用于正确绘制矩形框"""
        self.display_scale = display_scale
        # 重新绘制所有矩形框
        self.redraw_all_rectangles()
    
    def _position_temp_text(self, rect, display_cx, display_cy, tempTextId, display_scale):
        """根據 rect 的 temp_text_dir 定位溫度文字。

        Args:
            rect (dict): 元器件資料字典（含 temp_text_dir 欄位）
            display_cx (float): 三角形中心 X 的顯示座標
            display_cy (float): 三角形中心 Y 的顯示座標
            tempTextId (int): Canvas 溫度文字物件 ID
            display_scale (float): 目前的顯示縮放比例
        """
        temp_bbox = self.canvas.bbox(tempTextId)
        if not temp_bbox:
            self.canvas.coords(tempTextId, display_cx, display_cy - 16 * display_scale)
            self._move_outline(rect.get("tempOutlineIds"), display_cx, display_cy - 16 * display_scale)
            return
        temp_w = temp_bbox[2] - temp_bbox[0]
        temp_h = temp_bbox[3] - temp_bbox[1]
        direction = rect.get("temp_text_dir", "T")
        tri_half = max(7, int(8 * display_scale)) / 2
        dx, dy = calc_temp_text_offset(direction, tri_half, temp_w, temp_h)
        self.canvas.coords(tempTextId, display_cx + dx, display_cy + dy)
        self._move_outline(rect.get("tempOutlineIds"), display_cx + dx, display_cy + dy)

    def _move_outline(self, outline_ids, x, y):
        """移動描邊文字到指定中心位置。"""
        if not outline_ids:
            return
        for oid, (odx, ody) in zip(outline_ids, OUTLINE_OFFSETS):
            try:
                self.canvas.coords(oid, x + odx, y + ody)
            except:
                pass

    def _delete_outline(self, outline_ids):
        """刪除描邊文字。"""
        if not outline_ids:
            return
        for oid in outline_ids:
            try:
                self.canvas.delete(oid)
            except:
                pass

    def set_temp_text_dir(self, rect_ids, direction):
        """設定指定元器件的溫度文字方向，並立即更新 Canvas 顯示。

        Args:
            rect_ids (list): 要設定的矩形框 rectId 列表
            direction (str): 方向代碼 ("TL", "T", "TR", "L", "R", "BL", "B", "BR")
        """
        rect_id_set = set(rect_ids)
        for rect in self.rectangles:
            if rect.get("rectId") in rect_id_set:
                rect["temp_text_dir"] = direction
                tempTextId = rect.get("tempTextId")
                if not tempTextId:
                    continue

                # 計算顯示座標
                cx = rect.get("cx", 0)
                cy = rect.get("cy", 0)
                if self.magnifier_mode_enabled and abs(self.zoom_scale - 1.0) > 0.001:
                    display_cx = cx * self.zoom_scale + self.canvas_offset_x
                    display_cy = cy * self.zoom_scale + self.canvas_offset_y
                    # 🔥 使用 font_scale=1.0，與三角形和文字的實際大小一致
                    # 不可使用 zoom_scale，否則 tri_half 會隨放大倍率變大導致文字離三角形太遠
                    display_scale = 1.0
                else:
                    display_scale = self.display_scale if self.display_scale > 0 else 1.0
                    display_cx = cx * display_scale
                    display_cy = cy * display_scale

                self._position_temp_text(rect, display_cx, display_cy, tempTextId, display_scale)

    def redraw_all_rectangles(self):
        """重新绘制所有矩形框 - 直接缩放现有矩形，不删除重建"""
        from config import GlobalConfig
        config = GlobalConfig()
        name_font_size = config.get("heat_name_font_size", 12)
        temp_font_size = config.get("heat_temp_font_size", 10)
        name_font_size_scaled = max(1, int(name_font_size * self.display_scale))
        temp_font_size_scaled = max(1, int(temp_font_size * self.display_scale))

        for rect in self.rectangles:
            rectId = rect.get('rectId')
            nameId = rect.get('nameId')
            triangleId = rect.get('triangleId')
            tempTextId = rect.get('tempTextId')

            if rectId:
                # 计算缩放后的坐标（保持精度）
                left = rect.get("x1", 0) * self.display_scale
                top = rect.get("y1", 0) * self.display_scale
                right = rect.get("x2", 0) * self.display_scale
                bottom = rect.get("y2", 0) * self.display_scale
                cx = rect.get("cx", 0) * self.display_scale
                cy = rect.get("cy", 0) * self.display_scale

                # 直接更新现有矩形的坐标
                self.canvas.coords(rectId, left, top, right, bottom)

                # 更新名称标签位置和字體大小
                if nameId:
                    name_center_x = (left + right) / 2
                    name_y = top - 3 * self.display_scale
                    self.canvas.coords(nameId, name_center_x, name_y)
                    self.canvas.itemconfig(nameId, font=("Arial", name_font_size_scaled, "bold"))
                    # 同步描邊
                    self._move_outline(rect.get("nameOutlineIds"), name_center_x, name_y)
                    for oid in (rect.get("nameOutlineIds") or []):
                        try:
                            self.canvas.itemconfig(oid, font=("Arial", name_font_size_scaled, "bold"))
                        except:
                            pass

                # 更新温度文本位置和字體大小
                if tempTextId:
                    self.canvas.itemconfig(tempTextId, font=("Arial", temp_font_size_scaled))
                    for oid in (rect.get("tempOutlineIds") or []):
                        try:
                            self.canvas.itemconfig(oid, font=("Arial", temp_font_size_scaled))
                        except:
                            pass
                    self._position_temp_text(rect, cx, cy, tempTextId, self.display_scale)

                # 更新三角形位置
                if triangleId:
                    size = max(7, int(8 * self.display_scale))
                    point1 = (cx, cy - size // 2)
                    point2 = (cx - size // 2, cy + size // 2)
                    point3 = (cx + size // 2, cy + size // 2)
                    self.canvas.coords(triangleId, point1[0], point1[1], point2[0], point2[1], point3[0], point3[1])

            # 更新保存的字體縮放比例
            rect["_font_scale"] = self.display_scale

        print(f"✓ 已缩放所有矩形框，显示比例: {self.display_scale:.3f}")

    # 画三角形
    def draw_triangle(self, a_x, a_y):
        size = 6
        # 计算三角形的三个顶点
        point1 = (a_x, a_y - size // 2)  # 尖角
        point2 = (a_x - size // 2, a_y + size // 2)  # 左下角
        point3 = (a_x + size // 2, a_y + size // 2)  # 右下角
        # 绘制三角形
        # 从配置中读取温度颜色
        from config import GlobalConfig
        config = GlobalConfig()
        temp_color = config.get("heat_temp_color", "#FF0000")
        return self.canvas.create_polygon(point1, point2, point3, fill=temp_color, outline=temp_color)
    
    def update_rect(self, newRect, oldRect = None):
        # if oldRect["name"] == newRect["name"]:
        #     return
        if oldRect:
            oldRect.update(newRect)
        # todo 更新UI
        rectId, nameId, triangleId, tempTextId = self.drag_data.get("rectId"), self.drag_data.get("nameId"), self.drag_data.get("triangleId"), self.drag_data.get("tempTextId"),
        x1, y1, x2, y2, cx, cy, max_temp, name = newRect.get("x1"), newRect.get("y1"), newRect.get("x2"), newRect.get("y2"), newRect.get("cx"), newRect.get("cy"), newRect.get("max_temp"), newRect.get("name")

        # print("update_rect ------>>>> ", x1, y1, x2, y2, cx, cy, max_temp, name, nameId, triangleId, tempTextId, rectId)
        # 更新canvas显示 - 需要将原图像坐标转换为显示坐标
        # 放大模式下使用 zoom_scale + offset，否則使用 display_scale
        if self.magnifier_mode_enabled and abs(self.zoom_scale - 1.0) > 0.001:
            scale = self.zoom_scale
            offset_x = self.canvas_offset_x
            offset_y = self.canvas_offset_y
            display_x1 = x1 * scale + offset_x
            display_y1 = y1 * scale + offset_y
            display_x2 = x2 * scale + offset_x
            display_y2 = y2 * scale + offset_y
            display_cx = cx * scale + offset_x
            display_cy = cy * scale + offset_y
            display_scale = scale
        else:
            display_x1 = x1 * self.display_scale
            display_y1 = y1 * self.display_scale
            display_x2 = x2 * self.display_scale
            display_y2 = y2 * self.display_scale
            display_cx = cx * self.display_scale
            display_cy = cy * self.display_scale
            display_scale = self.display_scale
        
        # 找到對應 rect，用於讀取描邊 ID
        target_rect = None
        for r in self.rectangles:
            if r.get("rectId") == rectId:
                target_rect = r
                break

        if nameId:
            self.canvas.itemconfig(nameId, text=name)
            name_center_x = (display_x1 + display_x2) / 2
            name_y = display_y1 - 3 * display_scale
            self.canvas.coords(nameId, name_center_x, name_y)
            # 同步描邊
            if target_rect:
                for oid in (target_rect.get("nameOutlineIds") or []):
                    try:
                        self.canvas.itemconfig(oid, text=name)
                    except:
                        pass
                self._move_outline(target_rect.get("nameOutlineIds"), name_center_x, name_y)
        if tempTextId:
            self.canvas.itemconfig(tempTextId, text=max_temp)
            # 同步描邊文字內容
            if target_rect:
                for oid in (target_rect.get("tempOutlineIds") or []):
                    try:
                        self.canvas.itemconfig(oid, text=max_temp)
                    except:
                        pass
            if target_rect:
                self._position_temp_text(target_rect, display_cx, display_cy, tempTextId, display_scale)
            else:
                self.canvas.coords(tempTextId, display_cx, display_cy - 16 * display_scale)
        if triangleId:
            size = max(7, int(8 * display_scale))
            self.canvas.coords(triangleId, display_cx, display_cy - size // 2,
                             display_cx - size // 2, display_cy + size // 2,
                             display_cx + size // 2, display_cy + size // 2)
        if rectId:
            self.canvas.coords(rectId, display_x1, display_y1, display_x2, display_y2)
        self.update_anchors()
        
        # 通知EditorCanvas更新列表显示
        if self.on_rect_change_callback:
            self.on_rect_change_callback(rectId, "dialog_update")

    def add_rect(self, newRect):
        self.add_new_count += 1
        newRect["isNew"] = True  #标记是手动新增的
        # print("-------->>> add newRect ", newRect)
        rect = self.create_rectangle(newRect)
        
        # 先通知列表更新（添加新项）
        if self.on_rect_change_callback:
            self.on_rect_change_callback()
        
        # 延迟选中新创建的矩形框，确保列表更新完成
        def select_new_rect():
            rect_id = rect.get("rectId")
            if rect_id:
                # 直接设置选中状态，不使用fake_event
                self.drag_data["rectId"] = rect_id
                self.drag_data["nameId"] = rect.get("nameId")
                self.drag_data["triangleId"] = rect.get("triangleId")
                self.drag_data["tempTextId"] = rect.get("tempTextId")
                self.drag_data["isNew"] = rect.get("isNew")
                self.drag_data["resize"] = False
                self.drag_data["anchor"] = None
                self.drag_data["has_moved"] = False  # 初始化移动标记
                
                # 创建锚点
                self.create_anchors(rect_id)
                
                # 通知外部选中变化
                if self.on_rect_change_callback:
                    print(f"✓ 直接选中新矩形框 {rect_id}")
                    self.on_rect_change_callback(rect_id, "select")
            else:
                print(f"✗ 新矩形框没有有效的rectId")
        
        # 使用after延迟50ms执行选中操作
        self.canvas.after(50, select_new_rect)

    def query_component_name_by_coordinate(self, cx, cy):
        """
        根据点击坐标查询对应的元器件名称和边界信息
        
        Args:
            cx, cy: 热力图坐标
            
        Returns:
            tuple: (元器件名称, 热力图坐标边界字典) 或 (None, None)
                  边界字典包含: {'x1': left, 'y1': top, 'x2': right, 'y2': bottom, 'cx': center_x, 'cy': center_y}
        """
        try:
            # 检查是否有必要的映射数据
            if not hasattr(self.parent, 'layout_query') or self.parent.layout_query is None:
                print("警告：没有Layout查询器，无法查询元器件名称")
                return None, None
            
            # 使用Layout查询器进行坐标映射查询
            # 这里需要实现一个反向查询方法：从热力图坐标查询元器件
            result = self.parent.layout_query.query_component_by_thermal_coord(cx, cy)
            
            if result and isinstance(result, dict):
                component_name = result.get('refdes')
                thermal_bounds = result.get('thermal_bounds')
                
                print(f"✓ 查询到元器件: {component_name}")
                print(f"  热力图边界: {thermal_bounds}")
                return component_name, thermal_bounds
            else:
                print("未找到对应的元器件")
                return None, None
                
        except Exception as e:
            print(f"查询元器件名称时出错: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def generate_next_ar_name(self):
        """
        生成下一个AR名称：查询列表中所有ARXXX格式的名称，找出XXX最大的数，然后加1
        
        Returns:
            str: 新的AR名称，格式为 "AR{最大编号+1}"
        """
        import re
        max_number = 0
        
        # 遍历所有矩形框的名称
        for rect in self.rectangles:
            name = rect.get('name', '')
            # 匹配 AR 开头后跟数字的模式（不区分大小写）
            match = re.match(r'^AR(\d+)$', name, re.IGNORECASE)
            if match:
                number = int(match.group(1))
                max_number = max(max_number, number)
        
        # 返回最大编号+1的新名称
        next_number = max_number + 1
        return f"AR{next_number}"

    def on_double_click(self, event):
        # modify info
        rectId = self.drag_data["rectId"]
        # print("-------->>> on_double_click bb ", rectId, event)
        if rectId:
            for oldRect in self.rectangles:
                if oldRect["rectId"] == rectId:
                    # 关闭当前弹窗（如果存在）
                    self.close_current_dialog()
                    
                    # 创建新弹窗
                    dialog = ComponentSettingDialog(self.parent.dialog, oldRect, lambda newRect: self.update_rect(newRect, oldRect))
                    dialog.grab_set()  # 禁用主窗口，确保只能与对话框交互
                    
                    # 设置弹窗关闭回调
                    dialog.protocol("WM_DELETE_WINDOW", lambda: self.on_dialog_close(dialog))
                    
                    # 保存当前弹窗引用
                    self.current_dialog = dialog
                    break
        else:
            # 双击创建新矩形框
            rectWidth = 20
            display_cx, display_cy = event.x, event.y
            
            # 转换显示坐标到原图像坐标
            if self.display_scale > 0:
                cx = display_cx / self.display_scale
                cy = display_cy / self.display_scale
                orig_rectWidth = rectWidth / self.display_scale
            else:
                cx, cy = display_cx, display_cy
                orig_rectWidth = rectWidth
            
            # 计算原图像坐标系下的矩形框
            x1 = max(0, cx - orig_rectWidth)
            y1 = max(0, cy - orig_rectWidth)
            x2 = cx + orig_rectWidth
            y2 = cy + orig_rectWidth
            
            # 🔥 新增：根据点击坐标查询元器件名称和边界
            component_name, thermal_bounds = self.query_component_name_by_coordinate(cx, cy)
            
            if component_name and thermal_bounds:
                # 如果能查询到元器件名称，使用layout_data中的边界创建矩形框
                name = component_name
                print(f"✓ 自动识别元器件: {name}，使用元器件边界创建矩形框")
                
                # 使用返回的热力图坐标边界
                x1 = thermal_bounds['x1']
                y1 = thermal_bounds['y1']
                x2 = thermal_bounds['x2']
                y2 = thermal_bounds['y2']
                
                print(f"  使用元器件边界: ({x1:.2f}, {y1:.2f}) - ({x2:.2f}, {y2:.2f})")
                
                # 查询这个区域的最高温度和最高温度点坐标
                max_temp = self.tempALoader.get_max_temp(int(x1), int(y1), int(x2), int(y2), 1.0)
                temp_cx, temp_cy = self.tempALoader.get_max_temp_coords(int(x1), int(y1), int(x2), int(y2), 1.0)
                
                # 确保所有坐标值都不是None
                if temp_cx is None or temp_cy is None:
                    print(f"警告：温度坐标查询失败，使用区域中心点坐标")
                    temp_cx = (x1 + x2) / 2
                    temp_cy = (y1 + y2) / 2
                
                if max_temp is None:
                    print(f"警告：温度查询失败，使用默认值0")
                    max_temp = 0
                
                rectItem = {
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2, 
                    "cx": temp_cx, "cy": temp_cy, 
                    "max_temp": max_temp, 
                    "name": name, 
                    "rectId": 0, "nameId": 0, "triangleId": 0, "tempTextId": 0
                }
                
                print(f"创建矩形框参数: x1={x1:.2f}, y1={y1:.2f}, x2={x2:.2f}, y2={y2:.2f}, cx={temp_cx:.2f}, cy={temp_cy:.2f}, temp={max_temp:.2f}°C, name={name}")
                
                # 直接创建矩形框
                self.add_rect(rectItem)
                
            else:
                # 如果无法查询到元器件名称，保持原有逻辑，显示弹窗
                # 查询列表中所有 ARXXX 格式的名称，找出 XXX 最大的数字
                name = self.generate_next_ar_name()
                print(f"未识别到元器件，使用默认名称: {name}")
                
                # 查询温度数据，包括最高温度值和最高温度点坐标
                max_temp = self.tempALoader.get_max_temp(int(x1), int(y1), int(x2), int(y2), 1.0)
                temp_cx, temp_cy = self.tempALoader.get_max_temp_coords(int(x1), int(y1), int(x2), int(y2), 1.0)
                rectItem = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "cx": temp_cx, "cy": temp_cy, "max_temp": max_temp, "name": name, "rectId": 0, "nameId": 0, "triangleId": 0, "tempTextId": 0}
              
                # 关闭当前弹窗（如果存在）
                self.close_current_dialog()
                
                dialog = ComponentSettingDialog(self.parent.dialog, rectItem, lambda newRect: self.add_rect(newRect)) 
                dialog.grab_set()  # 禁用主窗口，确保只能与对话框交互
                
                # 设置弹窗关闭回调
                dialog.protocol("WM_DELETE_WINDOW", lambda: self.on_dialog_close(dialog))
                
                # 保存当前弹窗引用
                self.current_dialog = dialog

    def create_rectangle(self, newRect):
        # 🔥 根據當前模式選擇正確的縮放比例和偏移量
        if self.magnifier_mode_enabled and abs(self.zoom_scale - 1.0) > 0.001:
            # 縮放模式：使用 zoom_scale 和 offset
            scale = self.zoom_scale
            offset = (self.canvas_offset_x, self.canvas_offset_y)
            # 🔥 放大模式下，字體大小保持不變（不隨著縮放而放大）
            font_scale_override = 1.0
        else:
            # 非縮放模式：使用 display_scale
            scale = self.display_scale
            offset = (0, 0)
            # 非放大模式，字體正常縮放
            font_scale_override = None

        rectId, triangleId, tempTextId, nameId = draw_canvas_item(
            self.canvas, newRect, scale, offset, 0, font_scale=font_scale_override
        )
        newRect["rectId"] = rectId
        newRect["triangleId"] = triangleId
        newRect["tempTextId"] = tempTextId
        newRect["nameId"] = nameId

        # 🔥 保存創建時的字體縮放比例，用於後續重繪時保持一致
        if font_scale_override is not None:
            newRect["_font_scale"] = font_scale_override
        else:
            newRect["_font_scale"] = scale

        self.rectangles.append(newRect)
        return newRect

    def convert_to_circle(self, rect):
        """將矩形轉換為圓形

        Args:
            rect (dict): 矩形資料字典
        """
        # 記住轉換前的矩形邊界，以便轉回矩形時恢復
        rect["_rect_bounds"] = (rect["x1"], rect["y1"], rect["x2"], rect["y2"])

        # 計算矩形的幾何中心（邊界框中心）
        geometric_cx = (rect["x1"] + rect["x2"]) / 2
        geometric_cy = (rect["y1"] + rect["y2"]) / 2

        # 計算外接圓半徑（使用矩形的較長邊）
        width = rect["x2"] - rect["x1"]
        height = rect["y2"] - rect["y1"]
        radius = max(width, height) / 2

        # 更新邊界（圓形用正方形邊界框，以幾何中心為圓心）
        rect["x1"] = geometric_cx - radius
        rect["y1"] = geometric_cy - radius
        rect["x2"] = geometric_cx + radius
        rect["y2"] = geometric_cy + radius

        # 設定形狀類型
        rect["shape"] = "circle"

        # 重新計算圓形範圍內的最高溫度點位置（僅考慮圓形內部的點）
        cx, cy = self.tempALoader.get_max_temp_coords_in_circle(
            geometric_cx, geometric_cy, radius, 1.0)
        max_temp = self.tempALoader.get_max_temp_in_circle(
            geometric_cx, geometric_cy, radius, 1.0)

        rect["cx"] = cx
        rect["cy"] = cy
        rect["max_temp"] = max_temp

        # 刪除舊的 Canvas 物件，重新繪製
        self._redraw_single_rect(rect)

    def convert_to_rectangle(self, rect):
        """將圓形轉換為矩形（恢復轉換前的矩形邊界）

        Args:
            rect (dict): 矩形資料字典
        """
        rect["shape"] = "rectangle"

        # 恢復轉換前保存的矩形邊界（若有的話）
        saved = rect.pop("_rect_bounds", None)
        if saved:
            rect["x1"], rect["y1"], rect["x2"], rect["y2"] = saved

        # 重新計算範圍內的最高溫度點位置
        cx, cy = self.tempALoader.get_max_temp_coords(
            int(rect["x1"]), int(rect["y1"]),
            int(rect["x2"]), int(rect["y2"]), 1.0)
        max_temp = self.tempALoader.get_max_temp(
            int(rect["x1"]), int(rect["y1"]),
            int(rect["x2"]), int(rect["y2"]), 1.0)

        rect["cx"] = cx
        rect["cy"] = cy
        rect["max_temp"] = max_temp

        # 刪除舊的 Canvas 物件，重新繪製
        self._redraw_single_rect(rect)

    def _redraw_single_rect(self, rect):
        """重繪單個矩形/圓形

        Args:
            rect (dict): 矩形資料字典
        """
        # 刪除舊的 Canvas 物件（含描邊）
        self._delete_outline(rect.get("tempOutlineIds"))
        self._delete_outline(rect.get("nameOutlineIds"))
        old_ids = [
            rect.get("rectId"),
            rect.get("nameId"),
            rect.get("triangleId"),
            rect.get("tempTextId")
        ]
        for canvas_id in old_ids:
            if canvas_id:
                try:
                    self.canvas.delete(canvas_id)
                except:
                    pass

        # 🔥 根據當前模式選擇正確的縮放比例和偏移量
        if self.magnifier_mode_enabled and abs(self.zoom_scale - 1.0) > 0.001:
            # 縮放模式：使用 zoom_scale 和 offset
            scale = self.zoom_scale
            offset = (self.canvas_offset_x, self.canvas_offset_y)
            # 🔥 放大模式下，字體大小保持不變（不隨著縮放而放大）
            font_scale_override = 1.0
        else:
            # 非縮放模式：使用 display_scale
            scale = self.display_scale
            offset = (0, 0)
            # 🔥 重繪時使用保存的原始字體縮放比例，確保轉換前後字體大小一致
            # 如果沒有保存的 _font_scale，則使用當前的 display_scale
            font_scale_override = rect.get("_font_scale", None)

        # 呼叫 draw_canvas_item 重新繪製
        rectId, triangleId, tempTextId, nameId = draw_canvas_item(
            self.canvas, rect, scale, offset, 0, font_scale=font_scale_override
        )

        # 更新 ID
        rect["rectId"] = rectId
        rect["triangleId"] = triangleId
        rect["tempTextId"] = tempTextId
        rect["nameId"] = nameId

    def convert_shapes_batch(self, rect_ids, target_shape):
        """批次轉換形狀

        Args:
            rect_ids (list): 要轉換的矩形 ID 列表
            target_shape (str): "rectangle" 或 "circle"

        Returns:
            int: 成功轉換的數量
        """
        converted_count = 0

        for rect_id in rect_ids:
            # 找到對應的矩形資料
            rect = None
            for r in self.rectangles:
                if r.get("rectId") == rect_id:
                    rect = r
                    break

            if not rect:
                continue

            current_shape = rect.get("shape", "rectangle")

            # 跳過已經是目標形狀的
            if current_shape == target_shape:
                continue

            # 執行轉換
            if target_shape == "circle":
                self.convert_to_circle(rect)
            else:
                self.convert_to_rectangle(rect)

            converted_count += 1

        return converted_count

    def close_current_dialog(self):
        """关闭当前显示的弹窗"""
        if self.current_dialog is not None:
            try:
                if self.current_dialog.winfo_exists():
                    self.current_dialog.destroy()
                    print("✓ 已关闭当前弹窗")
            except tk.TclError:
                # 弹窗已经被销毁
                pass
            finally:
                self.current_dialog = None

    def on_dialog_close(self, dialog):
        """弹窗关闭时的回调"""
        if dialog == self.current_dialog:
            self.current_dialog = None
        try:
            dialog.destroy()
        except tk.TclError:
            # 弹窗已经被销毁
            pass

    def update_rectangle_coordinate(self, rectId):
        if self.canvas.coords(rectId):
            # 获取canvas显示坐标（螢幕座標）
            screen_x1, screen_y1, screen_x2, screen_y2 = self.canvas.coords(rectId)

            # 檢查是否啟用了縮放模式
            if self.magnifier_mode_enabled and abs(self.zoom_scale - 1.0) > 0.001:
                # 縮放模式：使用 zoom_scale 和 offset 轉換回圖像座標
                x1 = (screen_x1 - self.canvas_offset_x) / self.zoom_scale
                y1 = (screen_y1 - self.canvas_offset_y) / self.zoom_scale
                x2 = (screen_x2 - self.canvas_offset_x) / self.zoom_scale
                y2 = (screen_y2 - self.canvas_offset_y) / self.zoom_scale
            else:
                # 非縮放模式：使用 display_scale 轉換
                if self.display_scale > 0:
                    x1 = screen_x1 / self.display_scale
                    y1 = screen_y1 / self.display_scale
                    x2 = screen_x2 / self.display_scale
                    y2 = screen_y2 / self.display_scale
                else:
                    x1, y1, x2, y2 = screen_x1, screen_y1, screen_x2, screen_y2
            
            for rect in self.rectangles:
                if rect["rectId"] == rectId:
                    old_temp = rect.get("max_temp", 0)
                    rect["x1"] = x1
                    rect["y1"] = y1
                    rect["x2"] = x2
                    rect["y2"] = y2

                    # 根據形狀類型查詢溫度數據
                    shape = rect.get("shape", "rectangle")
                    if shape == "circle":
                        # 圓形：只考慮圓形內部的點
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        radius = (x2 - x1) / 2
                        cx, cy = self.tempALoader.get_max_temp_coords_in_circle(center_x, center_y, radius, 1.0)
                        max_temp = self.tempALoader.get_max_temp_in_circle(center_x, center_y, radius, 1.0)
                    else:
                        # 矩形：使用矩形區域查詢
                        cx, cy = self.tempALoader.get_max_temp_coords(int(x1), int(y1), int(x2), int(y2), 1.0)
                        max_temp = self.tempALoader.get_max_temp(int(x1), int(y1), int(x2), int(y2), 1.0)

                    # 更新数据
                    rect["cx"] = cx
                    rect["cy"] = cy
                    rect["max_temp"] = max_temp
                    
                    # 🔥 关键修复：同时更新canvas显示
                    nameId = rect.get("nameId")
                    tempTextId = rect.get("tempTextId")
                    triangleId = rect.get("triangleId")

                    if nameId and tempTextId and triangleId:
                        # 檢查是否啟用了縮放模式，選擇正確的座標轉換方式
                        if self.magnifier_mode_enabled and abs(self.zoom_scale - 1.0) > 0.001:
                            # 縮放模式：使用 zoom_scale 和 offset
                            display_cx = cx * self.zoom_scale + self.canvas_offset_x
                            display_cy = cy * self.zoom_scale + self.canvas_offset_y
                            display_x1 = x1 * self.zoom_scale + self.canvas_offset_x
                            display_y1 = y1 * self.zoom_scale + self.canvas_offset_y
                            display_x2 = x2 * self.zoom_scale + self.canvas_offset_x
                            display_scale = self.zoom_scale
                            # 🔥 放大模式下，三角形和文字大小保持不變
                            font_scale = 1.0
                        else:
                            # 非縮放模式：使用 display_scale
                            display_cx = cx * self.display_scale if self.display_scale > 0 else cx
                            display_cy = cy * self.display_scale if self.display_scale > 0 else cy
                            display_x1 = x1 * self.display_scale if self.display_scale > 0 else x1
                            display_y1 = y1 * self.display_scale if self.display_scale > 0 else y1
                            display_x2 = x2 * self.display_scale if self.display_scale > 0 else x2
                            display_scale = self.display_scale if self.display_scale > 0 else 1.0
                            font_scale = display_scale

                        # 更新名称标签位置（置中于矩形框上方）
                        name_center_x = (display_x1 + display_x2) / 2
                        name_y = display_y1 - 3 * font_scale
                        self.canvas.coords(nameId, name_center_x, name_y)
                        self._move_outline(rect.get("nameOutlineIds"), name_center_x, name_y)

                        # 更新温度文本位置（根據方向定位）
                        self.canvas.itemconfig(tempTextId, text=max_temp)
                        for oid in (rect.get("tempOutlineIds") or []):
                            try:
                                self.canvas.itemconfig(oid, text=max_temp)
                            except:
                                pass
                        self._position_temp_text(rect, display_cx, display_cy, tempTextId, font_scale)

                        # 更新三角形
                        size = max(7, int(8 * font_scale))
                        point1 = (display_cx, display_cy - size // 2)
                        point2 = (display_cx - size // 2, display_cy + size // 2)
                        point3 = (display_cx + size // 2, display_cy + size // 2)
                        self.canvas.coords(triangleId, point1[0], point1[1], point2[0], point2[1], point3[0], point3[1])

                    # 如果温度发生变化，通知列表更新
                    if abs(max_temp - old_temp) > 0.1:  # 温度变化超过0.1度
                        if self.on_rect_change_callback:
                            self.on_rect_change_callback(rectId, "temp_update")
                    break  # 第一个匹配的对象后退出循环
    def delete_rectangle(self):
        rectId = self.drag_data["rectId"]
        nameId = self.drag_data["nameId"]
        triangleId = self.drag_data["triangleId"]
        tempTextId = self.drag_data["tempTextId"]
        isNew = self.drag_data.get("isNew")

        # print("--------->>> find_item_isNew_by_rectId ", isNew, self.drag_data)

        if isNew:
            self.add_new_count -= 1
        else:
            self.delete_origin_count += 1

        # 刪除描邊文字
        for rect in self.rectangles:
            if rect.get("rectId") == rectId:
                self._delete_outline(rect.get("tempOutlineIds"))
                self._delete_outline(rect.get("nameOutlineIds"))
                break
        # rectId = self.drag_data["rectId"]
        self.canvas.delete(rectId)
        self.canvas.delete(nameId)
        self.canvas.delete(triangleId)
        self.canvas.delete(tempTextId)
        self.rectangles = [rect for rect in self.rectangles if rect["rectId"] != rectId]
        self.reset_drag_data()
        self.delete_anchors()
        
        # 通知列表更新
        if self.on_rect_change_callback:
            self.on_rect_change_callback()
    def reset_drag_data(self):
        self.drag_data = {"rectId": None, "nameId": None, "triangleId": None, "tempTextId": None, "x": 0, "y": 0, "resize": False, "anchor": None, "has_moved": False}
        # 通知清空选中
        if self.on_rect_change_callback:
            self.on_rect_change_callback(None, "clear_select")
    def create_anchors(self, rect):
        """Create anchors for the given rectangle."""
        # Create anchors for the given rectangle
        self.delete_anchors()
        
        try:
            coords = self.canvas.coords(rect)
            if not coords or len(coords) < 4:
                print(f"× create_anchors 失败: 无法获取矩形 {rect} 的坐标，coords={coords}")
                return
                
            x1, y1, x2, y2 = coords
            print(f"✓ create_anchors: 矩形 {rect} 坐标=({x1}, {y1}, {x2}, {y2}), conner_width={self.conner_width}")
            
            # 从配置中读取锚点颜色
            from config import GlobalConfig
            config = GlobalConfig()
            anchor_fill_color = config.get("heat_anchor_color", "#FF0000")
            anchor_outline_color = "#000000"  # 锚点边框保持黑色
            
            self.anchors = [
                self.canvas.create_oval(x1 - self.conner_width, y1 - self.conner_width, x1 + self.conner_width, y1 + self.conner_width, fill=anchor_fill_color, outline=anchor_outline_color, tags="anchor"),
                self.canvas.create_oval(x2 - self.conner_width, y1 - self.conner_width, x2 + self.conner_width, y1 + self.conner_width, fill=anchor_fill_color, outline=anchor_outline_color, tags="anchor"),
                self.canvas.create_oval(x1 - self.conner_width, y2 - self.conner_width, x1 + self.conner_width, y2 + self.conner_width, fill=anchor_fill_color, outline=anchor_outline_color, tags="anchor"),
                self.canvas.create_oval(x2 - self.conner_width, y2 - self.conner_width, x2 + self.conner_width, y2 + self.conner_width, fill=anchor_fill_color, outline=anchor_outline_color, tags="anchor"),
                self.canvas.create_oval(x1 - self.conner_width, (y1 + y2) // 2 - self.conner_width, x1 + self.conner_width, (y1 + y2) // 2 + self.conner_width, fill=anchor_fill_color, outline=anchor_outline_color, tags="anchor"),
                self.canvas.create_oval(x2 - self.conner_width, (y1 + y2) // 2 - self.conner_width, x2 + self.conner_width, (y1 + y2) // 2 + self.conner_width, fill=anchor_fill_color, outline=anchor_outline_color, tags="anchor"),
                self.canvas.create_oval((x1 + x2) // 2 - self.conner_width, y1 - self.conner_width, (x1 + x2) // 2 + self.conner_width, y1 + self.conner_width, fill=anchor_fill_color, outline=anchor_outline_color, tags="anchor"),
                self.canvas.create_oval((x1 + x2) // 2 - self.conner_width, y2 - self.conner_width, (x1 + x2) // 2 + self.conner_width, y2 + self.conner_width, fill=anchor_fill_color, outline=anchor_outline_color, tags="anchor"),
            ]
            print(f"✓ 已创建 {len(self.anchors)} 个锚点: {self.anchors}")
            
        except Exception as e:
            print(f"× create_anchors 错误: {e}")
            self.anchors = []
    def delete_anchors(self):
        """Delete anchors for the given rectangle."""
        if self.anchors:
            print(f"✓ delete_anchors: 删除 {len(self.anchors)} 个锚点: {self.anchors}")
            for anchor in self.anchors:
                self.canvas.delete(anchor)
        else:
            print("✓ delete_anchors: 没有锚点需要删除")
        self.anchors = []
    def on_click(self, event):
        """Handle click event to determine drag or resize action."""
        # Find the clicked rectangle
        clicked_rect = None
        clicked_name = None
        clicked_isNew = False
        anchorIndex = -1
        rectId = self.drag_data["rectId"]

        if rectId and self.canvas.coords(rectId):
            x1, y1, x2, y2 = self.canvas.coords(rectId)
            # 是否是锚点
            for i, anchor in enumerate(self.anchors):
                coords = _x1, _y1, _x2, _y2 = self.canvas.coords(anchor)
                if (_x1 <= event.x <= _x2) and (_y1 <= event.y <= _y2): #  and (x1 <= ((_x1 + _x2) // 2) <= x2) and (y1 <= ((_y1 + _y2) // 2) <= y2)
                    clicked_isNew = self.find_item_isNew_by_rectId(rectId)
                    anchorIndex = i
                    break

        # 非锚点
        if anchorIndex == -1:
            for rect in self.rectangles:
                rectId = rect.get("rectId")
                if rectId and self.canvas.coords(rectId):
                    # 使用canvas实际坐标进行判断，而不是原图像坐标
                    x1, y1, x2, y2 = self.canvas.coords(rectId)
                    nameId, triangleId, tempTextId, isNew = rect.get("nameId"), rect.get("triangleId"), rect.get("tempTextId"), rect.get("isNew")
                    # 是否是矩形范围内 
                    if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                        clicked_rect = rectId 
                        clicked_name = nameId
                        clicked_triangleId = triangleId
                        clicked_tempTextId = tempTextId
                        clicked_isNew = isNew
                        break

        if anchorIndex > -1:
            self.drag_data["anchor"] = anchorIndex
            self.drag_data["resize"] = True
            self.drag_data["isNew"] = clicked_isNew
        elif clicked_rect:
            self.drag_data["rectId"] = clicked_rect
            self.drag_data["nameId"] = clicked_name
            self.drag_data["triangleId"] = clicked_triangleId
            self.drag_data["tempTextId"] = clicked_tempTextId
            self.drag_data["isNew"] = clicked_isNew
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            self.drag_data["resize"] = False
            self.drag_data["anchor"] = None
            self.drag_data["has_moved"] = False  # 初始化移动标记
            self.canvas.tag_raise(clicked_rect)
            print(f"✓ on_click: 点击了矩形 {clicked_rect}，准备创建锚点")
            self.create_anchors(clicked_rect)  # Show anchors for the selected rectangle
            # 通知外部选中变化
            if self.on_rect_change_callback:
                print(f"✓ on_click: 通知外部选中变化，rect_id={clicked_rect}")
                self.on_rect_change_callback(clicked_rect, "select")
            else:
                print(f"⚠️ on_click: on_rect_change_callback为None，无法通知外部选中变化")
            
            # 确保焦点回到对话框，以便接收Delete键事件
            if hasattr(self.parent, 'dialog'):
                print(f"🔍🔍🔍 Canvas点击后设置焦点到对话框")
                self.parent.dialog.focus_set()
                print(f"🔍🔍🔍 焦点设置完成，当前焦点: {self.parent.dialog.focus_get()}")
            else:
                print(f"⚠️ Canvas点击后无法找到parent.dialog")
        else:
            # 点击空白区域：根据多选功能是否启用，决定是启动框选还是清除选择
            if self.multi_select_enabled:
                # 多选功能启用：启动多选框选模式
                self.multi_select_mode = True
                self.multi_select_start = (event.x, event.y)
                self.selected_rect_ids.clear()  # 清空之前的多选
                print(f"✓ 启动多选框选模式，起点: ({event.x}, {event.y})")
            else:
                # 多选功能关闭：保持原有的清除选择行为
                print(f"✓ 多选功能未启用，清除选择")
            
            self.drag_data["rectId"] = None
            self.drag_data["nameId"] = None
            self.drag_data["triangleId"] = None
            self.drag_data["tempTextId"] = None
            self.drag_data["resize"] = False
            self.drag_data["anchor"] = None
            self.delete_anchors()
            # 通知清空选中
            if self.on_rect_change_callback:
                self.on_rect_change_callback(None, "clear_select")

    def on_mouse_move(self, event):
        # print("on_mouse_move event", event, self.anchors, self.canvas.winfo_width(), self.canvas.winfo_height())
        anchorIndex = -1
        if len(self.anchors) > 0:
            for i, anchor in enumerate(self.anchors):
                coords = self.canvas.coords(anchor)
                if len(coords) > 3 and (coords[0] <= event.x <= coords[2]) and (coords[1] <= event.y <= coords[3]):
                    anchorIndex = i
                    break        
        # 判断鼠标是否在矩形内
        if anchorIndex > -1:
            # 鼠标在矩形内，改变鼠标样式为双箭头（fleur）
            self.canvas.config(cursor="fleur")
        else:
            # 鼠标不在矩形内，恢复默认鼠标样式
            self.canvas.config(cursor="")

    def on_drag(self, event):
        """Handle drag event to move or resize the selected rectangle."""
        # 多选框选模式
        if self.multi_select_mode and self.multi_select_start:
            # 删除旧的多选框
            if self.multi_select_rect:
                self.canvas.delete(self.multi_select_rect)
            
            # 绘制新的虚线多选框
            x1, y1 = self.multi_select_start
            x2, y2 = event.x, event.y
            
            # 从配置中读取多选框颜色
            from config import GlobalConfig
            config = GlobalConfig()
            multi_select_color = config.get("heat_selected_color", "#4A90E2")
            
            self.multi_select_rect = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline=multi_select_color,
                dash=(5, 5),  # 虚线样式
                width=2,
                tags="multi_select"
            )
            return
        
        if self.drag_data["resize"]:
            self.resize_rectangle(event)
        elif self.drag_data["rectId"]:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            
            # 只有移动距离超过阈值才触发拖拽
            if abs(dx) > self.drag_threshold or abs(dy) > self.drag_threshold:
                # print("-------->>> ", dx, dy, self.drag_data["x"], self.drag_data["y"], event.x, event.y)
                self.canvas.move(self.drag_data["rectId"], dx, dy)
                self.drag_data["x"] = event.x
                self.drag_data["y"] = event.y
                self.drag_data["has_moved"] = True  # 标记实际发生了移动
                self.update_anchors()

    def resize_rectangle(self, event):
        """Resize the selected rectangle based on the anchor point."""
        rectId = self.drag_data["rectId"]
        x1, y1, x2, y2 = self.canvas.coords(rectId)
        anchor = self.drag_data["anchor"]

        # 檢查是否為圓形
        rect_data = None
        for r in self.rectangles:
            if r.get("rectId") == rectId:
                rect_data = r
                break

        is_circle = rect_data and rect_data.get("shape") == "circle"

        if is_circle:
            # 圓形調整：保持正方形邊界，維持圓形
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            # 根據錨點計算新半徑
            if anchor in [0, 1, 2, 3]:  # 角落錨點
                # 使用滑鼠到中心的距離作為新半徑
                new_radius = max(abs(event.x - cx), abs(event.y - cy))
            elif anchor in [4, 5]:  # 左右邊錨點
                new_radius = abs(event.x - cx)
            elif anchor in [6, 7]:  # 上下邊錨點
                new_radius = abs(event.y - cy)
            else:
                new_radius = (x2 - x1) / 2

            # 確保最小尺寸
            new_radius = max(new_radius, self.min_width / 2)

            # 更新為正方形邊界
            self.canvas.coords(rectId,
                cx - new_radius, cy - new_radius,
                cx + new_radius, cy + new_radius)
        else:
            # 矩形調整：原有邏輯
            if anchor == 0:  # top-left corner
                self.canvas.coords(rectId, min(event.x, x2 - self.min_width), min(event.y, y2 - self.min_width), x2, y2)
            elif anchor == 1:  # top-right corner
                self.canvas.coords(rectId, x1, min(event.y, y2 - self.min_width), max(event.x, x1 + self.min_width), y2)
            elif anchor == 2:  # bottom-left corner
                self.canvas.coords(rectId, min(event.x, x2 - self.min_width), y1, x2, max(event.y, y1 + self.min_width))
            elif anchor == 3:  # bottom-right corner
                self.canvas.coords(rectId, x1, y1,  max(event.x, x1 + self.min_width),  max(event.y, y1 + self.min_width))
            elif anchor == 6:  # top-center edge (vertical stretch)
                self.canvas.coords(rectId, x1, min(event.y, y2 - self.min_width), x2, y2)
            elif anchor == 5:  # right-center edge (horizontal stretch)
                self.canvas.coords(rectId, x1, y1, max(event.x, x1 + self.min_width), y2)
            elif anchor == 7:  # bottom-center edge (vertical stretch)
                self.canvas.coords(rectId, x1, y1, x2, max(event.y, y1 + self.min_width))
            elif anchor == 4:  # left-center edge (horizontal stretch)
                self.canvas.coords(rectId, min(event.x, x2 - self.min_width), y1, x2, y2)

        # Update the anchors after resize
        self.update_anchors()

    def on_release(self, event):
        """End drag or resize when mouse is released."""
        print("on_release ->>> ")
        
        # 处理多选框选模式
        if self.multi_select_mode and self.multi_select_start:
            # 计算多选框的范围
            x1, y1 = self.multi_select_start
            x2, y2 = event.x, event.y
            
            # 确保 x1 < x2, y1 < y2
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y1, y2), max(y1, y2)
            
            # 查找被包含在多选框内的矩形框
            self.selected_rect_ids.clear()
            for rect in self.rectangles:
                rectId = rect.get("rectId")
                if rectId and self.canvas.coords(rectId):
                    rx1, ry1, rx2, ry2 = self.canvas.coords(rectId)
                    # 判断矩形框是否完全包含在多选框内
                    if (min_x <= rx1 and rx2 <= max_x and 
                        min_y <= ry1 and ry2 <= max_y):
                        self.selected_rect_ids.add(rectId)
            
            # 删除多选框
            if self.multi_select_rect:
                self.canvas.delete(self.multi_select_rect)
                self.multi_select_rect = None
            
            # 重置多选模式
            self.multi_select_mode = False
            self.multi_select_start = None
            
            # 通知外部多选变化
            if len(self.selected_rect_ids) > 0:
                print(f"✓ 多选了 {len(self.selected_rect_ids)} 个矩形框: {self.selected_rect_ids}")
                if self.on_rect_change_callback:
                    self.on_rect_change_callback(list(self.selected_rect_ids), "multi_select")
            else:
                print("✓ 多选框内没有矩形框")
            
            return
        
        # 只有在实际移动或调整大小时才更新坐标
        rectId = self.drag_data["rectId"]
        if rectId and (self.drag_data.get("has_moved", False) or self.drag_data.get("resize", False)):
            print(f"✓ 矩形框 {rectId} 发生了移动或调整，更新坐标和温度数据")
            self.update_rectangle_coordinate(rectId)
        else:
            print(f"✓ 矩形框 {rectId} 仅被点击选中，不更新温度数据")

        # self.drag_data = {"rectId": None, "x": 0, "y": 0, "resize": False, "anchor": None}
    # 移除右键删除方法，改用Delete键和删除按钮

    def update_anchors(self):
        rectId = self.drag_data["rectId"]
        if rectId and len(self.anchors) > 0:
            #"""更新锚点位置"""
            # 获取矩形的坐标
            x1, y1, x2, y2 = self.canvas.coords(rectId)
            
            # 更新锚点的位置
            self.canvas.coords(self.anchors[0], x1 - self.conner_width, y1 - self.conner_width, x1 + self.conner_width, y1 + self.conner_width)  # top-left
            self.canvas.coords(self.anchors[1], x2 - self.conner_width, y1 - self.conner_width, x2 + self.conner_width, y1 + self.conner_width)  # top-right
            self.canvas.coords(self.anchors[2], x1 - self.conner_width, y2 - self.conner_width, x1 + self.conner_width, y2 + self.conner_width)  # bottom-left
            self.canvas.coords(self.anchors[3], x2 - self.conner_width, y2 - self.conner_width, x2 + self.conner_width, y2 + self.conner_width)  # bottom-right
            self.canvas.coords(self.anchors[4], x1 - self.conner_width, (y1 + y2) // 2 - self.conner_width, x1 + self.conner_width, (y1 + y2) // 2 + self.conner_width)  # top-center
            self.canvas.coords(self.anchors[5], x2 - self.conner_width, (y1 + y2) // 2 - self.conner_width, x2 + self.conner_width, (y1 + y2) // 2 + self.conner_width)  # right-center
            self.canvas.coords(self.anchors[6], (x1 + x2) // 2 - self.conner_width, y1 - self.conner_width, (x1 + x2) // 2 + self.conner_width, y1 + self.conner_width)  # left-center
            self.canvas.coords(self.anchors[7], (x1 + x2) // 2 - self.conner_width, y2 - self.conner_width, (x1 + x2) // 2 + self.conner_width, y2 + self.conner_width)  # bottom-center


            nameId, tempTextId, triangleId, isNew = self.drag_data["nameId"], self.drag_data["tempTextId"], self.drag_data["triangleId"], self.drag_data["isNew"],
            self.update_temp_rect(x1, y1, x2, y2, nameId, tempTextId, triangleId)

            if isNew is None:
                self.modify_origin_set.add(rectId)

    def update_temp_rect(self, x1, y1, x2, y2, nameId, tempTextId, triangleId):
        # x1, y1, x2, y2 是canvas显示坐标（螢幕座標），需要转换为原图像坐标来查询温度

        # 檢查是否啟用了縮放模式
        if self.magnifier_mode_enabled and abs(self.zoom_scale - 1.0) > 0.001:
            # 縮放模式：使用 zoom_scale 和 offset 轉換
            orig_x1 = (x1 - self.canvas_offset_x) / self.zoom_scale
            orig_y1 = (y1 - self.canvas_offset_y) / self.zoom_scale
            orig_x2 = (x2 - self.canvas_offset_x) / self.zoom_scale
            orig_y2 = (y2 - self.canvas_offset_y) / self.zoom_scale

            display_scale = self.zoom_scale
            # 🔥 放大模式下，三角形和文字大小保持不變
            font_scale = 1.0
        else:
            # 非縮放模式：使用 display_scale 轉換
            if self.display_scale > 0:
                orig_x1 = x1 / self.display_scale
                orig_y1 = y1 / self.display_scale
                orig_x2 = x2 / self.display_scale
                orig_y2 = y2 / self.display_scale
            else:
                orig_x1, orig_y1, orig_x2, orig_y2 = x1, y1, x2, y2

            display_scale = self.display_scale if self.display_scale > 0 else 1.0
            font_scale = display_scale

        # 從 nameId 反查對應的 rect（用於描邊同步）
        target_rect = None
        for r in self.rectangles:
            if r.get("nameId") == nameId:
                target_rect = r
                break

        # 更新名称标签位置（置中于矩形框上方）
        name_center_x = (x1 + x2) / 2
        name_y = y1 - 3 * font_scale
        self.canvas.coords(nameId, name_center_x, name_y)
        if target_rect:
            self._move_outline(target_rect.get("nameOutlineIds"), name_center_x, name_y)

        # 使用原图像坐标查询温度和最高温度位置
        max_temp = self.tempALoader.get_max_temp(int(orig_x1), int(orig_y1), int(orig_x2), int(orig_y2), 1.0)
        orig_cx, orig_cy = self.tempALoader.get_max_temp_coords(int(orig_x1), int(orig_y1), int(orig_x2), int(orig_y2), 1.0)

        # 将原图像坐标转换为显示坐标来显示温度文本和三角形
        if self.magnifier_mode_enabled and abs(self.zoom_scale - 1.0) > 0.001:
            # 縮放模式：使用 zoom_scale 和 offset 轉換
            display_cx = orig_cx * self.zoom_scale + self.canvas_offset_x
            display_cy = orig_cy * self.zoom_scale + self.canvas_offset_y
        else:
            # 非縮放模式
            display_cx = orig_cx * display_scale
            display_cy = orig_cy * display_scale

        # 更新温度文本位置（根據方向定位）
        self.canvas.itemconfig(tempTextId, text=max_temp)
        # 同步描邊文字內容
        if target_rect:
            for oid in (target_rect.get("tempOutlineIds") or []):
                try:
                    self.canvas.itemconfig(oid, text=max_temp)
                except:
                    pass
        if target_rect:
            self._position_temp_text(target_rect, display_cx, display_cy, tempTextId, font_scale)
        else:
            self.canvas.coords(tempTextId, display_cx, display_cy - 16 * font_scale)

        # 计算新的三角形三个顶点（使用显示坐标）
        size = max(7, int(8 * font_scale))
        point1 = (display_cx, display_cy - size // 2)  # 顶点1 (尖角)
        point2 = (display_cx - size // 2, display_cy + size // 2)  # 顶点2 (左下角)
        point3 = (display_cx + size // 2, display_cy + size // 2)  # 顶点3 (右下角)
        self.canvas.coords(triangleId, point1[0], point1[1], point2[0], point2[1], point3[0], point3[1])

        # 注意：不在这里更新rect数据，避免与update_rectangle_coordinate重复更新
        # 数据更新统一在update_rectangle_coordinate中处理
        # print("update_temp_rect -> ", orig_cx, orig_cy, max_temp)

    # 外部选择某个矩形：显示锚点但不改变颜色
    def select_rect_by_id(self, rect_id: int):
        for rect in self.rectangles:
            if rect.get("rectId") == rect_id:
                self.drag_data["rectId"] = rect.get("rectId")
                self.drag_data["nameId"] = rect.get("nameId")
                self.drag_data["triangleId"] = rect.get("triangleId")
                self.drag_data["tempTextId"] = rect.get("tempTextId")
                self.drag_data["resize"] = False
                self.drag_data["anchor"] = None
                self.create_anchors(rect_id)
                return True
        return False

    # 外部清空选中
    def clear_selection(self):
        self.delete_anchors()
        self.reset_drag_data()

    # 还原成1280x960的坐标 
    def get_mark_rect(self):
         # 直接返回rectangles，不需要缩放转换
         return self.rectangles.copy()
    
    def find_item_isNew_by_rectId(self, rectId):
        # 使用列表推导式找到具有指定 rectId 的项
        result = [item for item in self.rectangles if item['rectId'] == rectId]

        # print("find_item_isNew_by_rectId -> ", len(result), "isNew" in result[0] , result[0]["isNew"])
        
        # 如果找到结果，返回第一个匹配的项；否则返回 None
        if len(result) > 0 and "isNew" in result[0] and result[0]["isNew"] is not None:
            return result[0]["isNew"]
        else:
            return None
        
    def get_modify_log_count(self):
        return self.add_new_count, self.delete_origin_count, self.modify_origin_set
    
    def delete_rectangle_by_id(self, rect_id):
        """根据ID删除矩形"""
        for rect in self.rectangles:
            if rect.get("rectId") == rect_id:
                # 刪除描邊文字
                self._delete_outline(rect.get("tempOutlineIds"))
                self._delete_outline(rect.get("nameOutlineIds"))
                # 删除canvas元素
                if rect.get("rectId"):
                    self.canvas.delete(rect["rectId"])
                if rect.get("nameId"):
                    self.canvas.delete(rect["nameId"])
                if rect.get("triangleId"):
                    self.canvas.delete(rect["triangleId"])
                if rect.get("tempTextId"):
                    self.canvas.delete(rect["tempTextId"])

                # 从列表中移除
                self.rectangles.remove(rect)
                
                # 更新计数
                if rect.get("isNew"):
                    self.add_new_count -= 1
                else:
                    self.delete_origin_count += 1
                
                break
        
        # 清空锚点
        self.delete_anchors()
        # 重置拖拽数据
        self.reset_drag_data()
        
        # 通知EditorCanvas更新列表显示
        if self.on_rect_change_callback:
            self.on_rect_change_callback(rect_id, "delete")
    
    def delete_rectangles_by_ids(self, rect_ids):
        """批量删除多个矩形框"""
        if not rect_ids:
            return
        
        deleted_count = 0
        for rect_id in rect_ids:
            for rect in self.rectangles[:]:  # 使用切片创建副本以避免迭代时修改列表
                if rect.get("rectId") == rect_id:
                    # 刪除描邊文字
                    self._delete_outline(rect.get("tempOutlineIds"))
                    self._delete_outline(rect.get("nameOutlineIds"))
                    # 删除canvas元素
                    if rect.get("rectId"):
                        self.canvas.delete(rect["rectId"])
                    if rect.get("nameId"):
                        self.canvas.delete(rect["nameId"])
                    if rect.get("triangleId"):
                        self.canvas.delete(rect["triangleId"])
                    if rect.get("tempTextId"):
                        self.canvas.delete(rect["tempTextId"])

                    # 从列表中移除
                    self.rectangles.remove(rect)

                    # 更新计数
                    if rect.get("isNew"):
                        self.add_new_count -= 1
                    else:
                        self.delete_origin_count += 1

                    deleted_count += 1
                    break

        # 清空锚点
        self.delete_anchors()
        # 重置拖拽数据
        self.reset_drag_data()
        # 清空多选状态
        self.selected_rect_ids.clear()
        
        print(f"✓ 批量删除了 {deleted_count} 个矩形框")
        
        # 通知EditorCanvas更新列表显示
        if self.on_rect_change_callback:
            self.on_rect_change_callback(list(rect_ids), "multi_delete")
    
    def merge_rectangles_by_ids(self, rect_ids):
        """
        合并多个矩形框
        
        Args:
            rect_ids: 要合并的矩形框ID列表
            
        Returns:
            合并后的新矩形框ID，失败返回None
        """
        if not rect_ids or len(rect_ids) <= 1:
            print("⚠️ 需要至少2个矩形框才能合并")
            return None
        
        # 收集要合并的矩形框
        rects_to_merge = []
        for rect in self.rectangles:
            if rect.get("rectId") in rect_ids:
                rects_to_merge.append(rect)
        
        if len(rects_to_merge) != len(rect_ids):
            print(f"⚠️ 部分矩形框未找到: 需要{len(rect_ids)}个，找到{len(rects_to_merge)}个")
            return None
        
        print(f"🔗 开始合并 {len(rects_to_merge)} 个矩形框")
        
        # 1. 计算外接矩形
        min_x1 = min(rect.get("x1", float('inf')) for rect in rects_to_merge)
        min_y1 = min(rect.get("y1", float('inf')) for rect in rects_to_merge)
        max_x2 = max(rect.get("x2", float('-inf')) for rect in rects_to_merge)
        max_y2 = max(rect.get("y2", float('-inf')) for rect in rects_to_merge)
        
        print(f"  外接矩形: ({min_x1:.2f}, {min_y1:.2f}) - ({max_x2:.2f}, {max_y2:.2f})")
        
        # 2. 找到最左上角的矩形框（y坐标最小，如果y相同则x最小）
        top_left_rect = min(rects_to_merge, key=lambda r: (r.get("y1", 0), r.get("x1", 0)))
        merged_name = top_left_rect.get("name", "合并区域")
        
        print(f"  使用名称: {merged_name}")
        
        # 3. 重新计算该矩形框下的最高温度和最高温度点
        max_temp = self.tempALoader.get_max_temp(
            int(min_x1), int(min_y1), int(max_x2), int(max_y2), 1.0
        )
        temp_cx, temp_cy = self.tempALoader.get_max_temp_coords(
            int(min_x1), int(min_y1), int(max_x2), int(max_y2), 1.0
        )
        
        # 确保温度坐标不为None
        if temp_cx is None or temp_cy is None:
            print(f"⚠️ 温度坐标查询失败，使用区域中心点")
            temp_cx = (min_x1 + max_x2) / 2
            temp_cy = (min_y1 + max_y2) / 2
        
        if max_temp is None:
            print(f"⚠️ 温度查询失败，使用默认值0")
            max_temp = 0
        
        print(f"  最高温度: {max_temp:.2f}°C，位置: ({temp_cx:.2f}, {temp_cy:.2f})")
        
        # 4. 创建新的矩形框数据
        merged_rect_item = {
            "x1": min_x1,
            "y1": min_y1,
            "x2": max_x2,
            "y2": max_y2,
            "cx": temp_cx,
            "cy": temp_cy,
            "max_temp": max_temp,
            "name": merged_name,
            "rectId": 0,
            "nameId": 0,
            "triangleId": 0,
            "tempTextId": 0
        }
        
        # 5. 删除原有的N个矩形框
        for rect_id in rect_ids:
            for rect in self.rectangles[:]:
                if rect.get("rectId") == rect_id:
                    # 刪除描邊文字
                    self._delete_outline(rect.get("tempOutlineIds"))
                    self._delete_outline(rect.get("nameOutlineIds"))
                    # 删除canvas元素
                    if rect.get("rectId"):
                        self.canvas.delete(rect["rectId"])
                    if rect.get("nameId"):
                        self.canvas.delete(rect["nameId"])
                    if rect.get("triangleId"):
                        self.canvas.delete(rect["triangleId"])
                    if rect.get("tempTextId"):
                        self.canvas.delete(rect["tempTextId"])
                    
                    # 从列表中移除
                    self.rectangles.remove(rect)
                    
                    # 更新计数
                    if rect.get("isNew"):
                        self.add_new_count -= 1
                    else:
                        self.delete_origin_count += 1
                    
                    break
        
        # 6. 创建新的合并矩形框
        new_rect = self.create_rectangle(merged_rect_item)
        new_rect["isNew"] = True  # 标记为新增
        self.add_new_count += 1
        
        merged_rect_id = new_rect.get("rectId")
        
        print(f"✓ 合并完成，新矩形框ID: {merged_rect_id}")
        
        # 清空多选状态
        self.selected_rect_ids.clear()
        
        return merged_rect_id

    # ========== 縮放和拖動功能 ==========

    def set_magnifier_mode(self, enabled):
        """設定放大模式是否啟用"""
        was_enabled = self.magnifier_mode_enabled
        self.magnifier_mode_enabled = enabled

        if not enabled and was_enabled:
            # 關閉放大模式時，重置縮放參數但不觸發重新繪製
            self.zoom_scale = self.min_zoom
            self.canvas_offset_x = 0
            self.canvas_offset_y = 0
            # 不調用 on_zoom_change_callback，讓 EditorCanvas 處理模式切換

    def set_background_image(self, pil_image):
        """設定背景圖像（用於縮放）"""
        self.original_bg_image = pil_image
        # 計算 fit 比例
        self.calculate_fit_scale()

    def calculate_fit_scale(self, canvas_w=None, canvas_h=None):
        """計算能完整顯示圖像的最小縮放比例

        Args:
            canvas_w: Canvas 寬度（可選，預設用 winfo_width）
            canvas_h: Canvas 高度（可選，預設用 winfo_height）
        """
        if not self.original_bg_image:
            return

        if canvas_w is None:
            canvas_w = self.canvas.winfo_width()
        if canvas_h is None:
            canvas_h = self.canvas.winfo_height()
        img_w = self.original_bg_image.width
        img_h = self.original_bg_image.height

        if canvas_w > 0 and canvas_h > 0:
            fit_scale = min(canvas_w / img_w, canvas_h / img_h)
            self.min_zoom = fit_scale
            # 確保初始縮放不小於 min_zoom
            if self.zoom_scale < self.min_zoom:
                self.zoom_scale = self.min_zoom

    def reset_zoom(self):
        """重置縮放到 fit 顯示"""
        self.zoom_scale = self.min_zoom
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        # 通知重新繪製
        if hasattr(self, 'on_zoom_change_callback') and self.on_zoom_change_callback:
            self.on_zoom_change_callback()

    def on_mouse_wheel(self, event):
        """處理滾輪縮放（Windows/macOS）"""
        if not self.magnifier_mode_enabled:
            return

        # 計算縮放增量
        delta = event.delta / 120  # Windows 標準增量
        zoom_factor = 1.1 ** delta  # 每次 10% 變化

        self._apply_zoom(event.x, event.y, zoom_factor)

        # 阻止事件傳播，避免影響其他邏輯
        return "break"

    def on_mouse_wheel_linux(self, event, direction):
        """處理滾輪縮放（Linux）"""
        if not self.magnifier_mode_enabled:
            return

        zoom_factor = 1.1 if direction > 0 else 1.0 / 1.1
        self._apply_zoom(event.x, event.y, zoom_factor)

        # 阻止事件傳播，避免影響其他邏輯
        return "break"

    def _apply_zoom(self, mouse_x, mouse_y, zoom_factor):
        """應用縮放變換"""
        # 計算新縮放比例，限制在 min_zoom 和 max_zoom 之間
        new_zoom = self.zoom_scale * zoom_factor
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))

        if abs(new_zoom - self.zoom_scale) < 0.001:
            return  # 縮放比例沒有變化

        # 更新縮放比例
        old_zoom = self.zoom_scale
        self.zoom_scale = new_zoom

        # 🎯 如果縮放到最小（min_zoom），重置位置為 default
        if abs(self.zoom_scale - self.min_zoom) < 0.001:
            self.canvas_offset_x = 0
            self.canvas_offset_y = 0
        else:
            # 否則以游標位置為中心縮放
            # 計算游標下的圖像座標（縮放前）
            img_x = (mouse_x - self.canvas_offset_x) / old_zoom
            img_y = (mouse_y - self.canvas_offset_y) / old_zoom

            # 調整偏移量，保持游標下的圖像點不動
            self.canvas_offset_x = mouse_x - img_x * self.zoom_scale
            self.canvas_offset_y = mouse_y - img_y * self.zoom_scale

        # 通知重新繪製
        if hasattr(self, 'on_zoom_change_callback') and self.on_zoom_change_callback:
            self.on_zoom_change_callback()

    def on_right_click_start(self, event):
        """開始右鍵拖動"""
        # 只在放大模式且已放大（超過 min_zoom）時允許拖動
        if not self.magnifier_mode_enabled or abs(self.zoom_scale - self.min_zoom) < 0.01:
            return

        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas.config(cursor="fleur")  # 改變游標樣式為移動

    def on_right_click_drag(self, event):
        """處理右鍵拖動"""
        if not self.is_panning:
            return

        # 計算位移
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y

        # 更新偏移
        self.canvas_offset_x += dx
        self.canvas_offset_y += dy

        # 限制拖動範圍（可選）
        self.constrain_pan_boundaries()

        # 更新起始點
        self.pan_start_x = event.x
        self.pan_start_y = event.y

        # 通知重新繪製
        if hasattr(self, 'on_zoom_change_callback') and self.on_zoom_change_callback:
            self.on_zoom_change_callback()

    def on_right_click_end(self, event):
        """結束右鍵拖動"""
        if self.is_panning:
            self.is_panning = False
            self.canvas.config(cursor="")  # 恢復游標

    def constrain_pan_boundaries(self):
        """限制拖動範圍，避免圖像完全拖出視野"""
        if not self.original_bg_image:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        img_w = self.original_bg_image.width * self.zoom_scale
        img_h = self.original_bg_image.height * self.zoom_scale

        # 至少保留 100px 可見區域
        margin = 100

        max_offset_x = canvas_w - margin
        min_offset_x = -img_w + margin

        max_offset_y = canvas_h - margin
        min_offset_y = -img_h + margin

        self.canvas_offset_x = max(min_offset_x, min(max_offset_x, self.canvas_offset_x))
        self.canvas_offset_y = max(min_offset_y, min(max_offset_y, self.canvas_offset_y))

    def get_zoom_transform(self):
        """獲取當前縮放變換參數（供外部繪製使用）"""
        return {
            'zoom_scale': self.zoom_scale,
            'offset_x': self.canvas_offset_x,
            'offset_y': self.canvas_offset_y
        }

    def screen_to_image_coords(self, screen_x, screen_y):
        """將螢幕座標轉換為圖像座標"""
        img_x = (screen_x - self.canvas_offset_x) / self.zoom_scale
        img_y = (screen_y - self.canvas_offset_y) / self.zoom_scale
        return img_x, img_y

    def image_to_screen_coords(self, img_x, img_y):
        """將圖像座標轉換為螢幕座標"""
        screen_x = img_x * self.zoom_scale + self.canvas_offset_x
        screen_y = img_y * self.zoom_scale + self.canvas_offset_y
        return screen_x, screen_y


# 自定义事件类
class CustomEvent:
    def __init__(self, x, y, custom_data):
        self.x = x
        self.y = y
        self.custom_data = custom_data

# 创建并运行应用
if __name__ == "__main__":
    root = tk.Tk()
    canvas = tk.Canvas(root, bg="white", width=800, height=600)
    canvas.pack(fill=tk.BOTH, expand=True)
    mark_rect = []
    rectItem1 = {"x1": 0,  "y1": 0, "x2": 100, "y2": 100, "cx": 50, "cy": 50, "max_temp": 73.2, "name": "A","rectId": 0,"nameId": 0, "triangleId": 0, "tempTextId": 0}
    rectItem2 = {"x1": 200,  "y1": 200, "x2": 300, "y2": 350, "cx": 220, "cy": 290, "max_temp": 50.3, "name": "A1","rectId": 0,"nameId": 0, "triangleId": 0, "tempTextId": 0}
    rectItem3 = {"x1": 400,  "y1": 400, "x2": 500, "y2": 550, "cx": 433, "cy": 499, "max_temp": 23.2, "name": "A2","rectId": 0,"nameId": 0, "triangleId": 0, "tempTextId": 0}
    mark_rect.append(rectItem1)
    mark_rect.append(rectItem2)
    mark_rect.append(rectItem3)
    app = RectEditor(canvas, mark_rect)
    root.mainloop()