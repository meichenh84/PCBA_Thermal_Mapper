"""
矩形编辑器模块

主要功能：
1. 矩形框的创建、编辑和删除
2. 温度数据的查询和显示
3. 智能文字定位
4. 弹窗管理（单例模式）
5. 坐标转换和缩放处理
"""

import tkinter as tk
import numpy as np 

from dialog_component_setting import ComponentSettingDialog
from load_tempA import TempLoader
from draw_rect import draw_canvas_item

class RectEditor:
    def __init__(self, parent, canvas, mark_rect = None, temp_file_path = None, on_rect_change_callback=None):
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

        # Bind events for canvas
        self.canvas.bind("<ButtonPress-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        # 移除右键删除功能，改用Delete键和删除按钮
        self.canvas.bind("<Double-Button-1>", self.on_double_click) # 绑定双击事件
        self.canvas.after(100, self.init_marks)

    # 不再需要缩放坐标，直接使用原图像坐标

    def init_marks(self):
        if len(self.mark_rect) > 0:
            for item in self.mark_rect:
                self.create_rectangle(item)

    def update_display_scale(self, display_scale):
        """更新显示缩放比例，用于正确绘制矩形框"""
        self.display_scale = display_scale
        # 重新绘制所有矩形框
        self.redraw_all_rectangles()
    
    def redraw_all_rectangles(self):
        """重新绘制所有矩形框 - 直接缩放现有矩形，不删除重建"""
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
                
                # 更新名称标签位置
                if nameId:
                    self.canvas.coords(nameId, left + 10, top - 10)
                
                # 更新温度文本位置
                if tempTextId:
                    self.canvas.coords(tempTextId, cx, cy - 16)
                
                # 更新三角形位置
                if triangleId:
                    size = max(7, int(8 * self.display_scale))
                    point1 = (cx, cy - size // 2)
                    point2 = (cx - size // 2, cy + size // 2)
                    point3 = (cx + size // 2, cy + size // 2)
                    self.canvas.coords(triangleId, point1[0], point1[1], point2[0], point2[1], point3[0], point3[1])
        
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
        display_x1 = x1 * self.display_scale
        display_y1 = y1 * self.display_scale
        display_x2 = x2 * self.display_scale
        display_y2 = y2 * self.display_scale
        display_cx = cx * self.display_scale
        display_cy = cy * self.display_scale
        
        if nameId:
            self.canvas.itemconfig(nameId, text=name)
            self.canvas.coords(nameId, display_x1 + 10, display_y1 - 10)
        if tempTextId:
            self.canvas.itemconfig(tempTextId, text=max_temp)
            self.canvas.coords(tempTextId, display_cx, display_cy - 16)
        if triangleId:
            size = max(7, int(8 * self.display_scale))
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
        rectId, triangleId, tempTextId, nameId = draw_canvas_item(
            self.canvas, newRect, self.display_scale, (0, 0), 0
        )
        newRect["rectId"] = rectId
        newRect["triangleId"] = triangleId
        newRect["tempTextId"] = tempTextId
        newRect["nameId"] = nameId
        self.rectangles.append(newRect)
        return newRect

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
            # 获取canvas显示坐标
            display_x1, display_y1, display_x2, display_y2 = self.canvas.coords(rectId)
            
            # 转换回原图像坐标（与update_temp_rect保持一致）
            if self.display_scale > 0:
                x1 = display_x1 / self.display_scale
                y1 = display_y1 / self.display_scale
                x2 = display_x2 / self.display_scale
                y2 = display_y2 / self.display_scale
            else:
                x1, y1, x2, y2 = display_x1, display_y1, display_x2, display_y2
            
            for rect in self.rectangles:
                if rect["rectId"] == rectId:
                    old_temp = rect.get("max_temp", 0)
                    rect["x1"] = x1
                    rect["y1"] = y1
                    rect["x2"] = x2
                    rect["y2"] = y2
                    # 查询温度数据
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
                        # 将原图像坐标转换为显示坐标
                        display_cx = cx * self.display_scale if self.display_scale > 0 else cx
                        display_cy = cy * self.display_scale if self.display_scale > 0 else cy
                        
                        # 更新canvas显示
                        self.canvas.coords(tempTextId, display_cx, display_cy - 16)
                        self.canvas.itemconfig(tempTextId, text=max_temp)
                        
                        # 更新三角形
                        size = max(7, int(8 * self.display_scale)) if self.display_scale > 0 else 8
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
        # x1, y1, x2, y2 是canvas显示坐标，需要转换为原图像坐标来查询温度
        if self.display_scale > 0:
            orig_x1 = x1 / self.display_scale
            orig_y1 = y1 / self.display_scale
            orig_x2 = x2 / self.display_scale
            orig_y2 = y2 / self.display_scale
        else:
            orig_x1, orig_y1, orig_x2, orig_y2 = x1, y1, x2, y2
        
        # 更新名称标签位置（使用显示坐标）
        self.canvas.coords(nameId, x1 + 10, y1 - 10)

        # 使用原图像坐标查询温度和最高温度位置
        max_temp = self.tempALoader.get_max_temp(int(orig_x1), int(orig_y1), int(orig_x2), int(orig_y2), 1.0)
        orig_cx, orig_cy = self.tempALoader.get_max_temp_coords(int(orig_x1), int(orig_y1), int(orig_x2), int(orig_y2), 1.0)
        
        # 将原图像坐标转换为显示坐标来显示温度文本和三角形
        display_cx = orig_cx * self.display_scale
        display_cy = orig_cy * self.display_scale
        
        self.canvas.coords(tempTextId, display_cx, display_cy - 16)
        self.canvas.itemconfig(tempTextId, text=max_temp)

        # 计算新的三角形三个顶点（使用显示坐标）
        size = max(7, int(8 * self.display_scale))
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