#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
溫度編輯畫布對話框模組 (editor_canvas.py)

用途：
    提供「編輯溫度」的獨立彈出視窗，包含一個背景影像的 Canvas
    和左側的元器件列表。使用者可以在 Canvas 上建立、編輯、刪除
    矩形標記框，並在左側列表中查看和搜尋所有元器件。
    支援視窗縮放時自動調整影像和矩形框的顯示比例。

在整個應用中的角色：
    - 被 main.py 的「編輯溫度」按鈕觸發，開啟獨立編輯視窗
    - 內部建立 RectEditor 實例處理矩形框的互動操作

關聯檔案：
    - main.py：建立 EditorCanvas 實例
    - editor_rect.py：提供矩形框編輯功能
    - ui_style.py：統一的 UI 樣式常數
    - draw_rect.py：矩形框繪製功能

UI 元件對應命名：
    - dialog (tk.Toplevel): 編輯對話框視窗
    - canvas (tk.Canvas): 繪圖用的 Canvas 元件
    - left_panel (tk.Frame): 左側面板（含搜尋和列表）
    - search_entry (PlaceholderEntry): 搜尋輸入框
    - list_frame (tk.Frame): 元器件列表容器
    - list_canvas (tk.Canvas): 列表滾動區域的 Canvas
    - scrollbar (tk.Scrollbar): 列表的垂直捲軸
    - multi_select_checkbox (tk.Checkbutton): 多選開關勾選框
    - delete_selected_btn (tk.Button): 刪除選中項目按鈕
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageGrab
from placeholder_entry import PlaceholderEntry

# 匯入 UIStyle 以保持樣式統一
try:
    from .ui_style import UIStyle
except ImportError:
    from ui_style import UIStyle

try:
    from .editor_rect import RectEditor
except ImportError:
    from editor_rect import RectEditor

try:
    from .tooltip import Tooltip
except ImportError:
    from tooltip import Tooltip


class EditorCanvas:
    """溫度編輯畫布對話框。

    建立一個獨立的 Toplevel 視窗，包含背景影像的 Canvas、
    左側元器件列表和搜尋功能。內部使用 RectEditor 處理
    矩形框的互動操作。

    屬性：
        parent (tk.Widget): 父元件
        mark_rect (list): 元器件標記資料列表（深拷貝）
        temp_file_path (str): 溫度資料檔案路徑
        on_close_callback (callable): 視窗關閉時的回呼函式
        bg_image (PIL.Image): 背景影像
        dialog (tk.Toplevel): 對話框視窗
        canvas (tk.Canvas): 繪圖 Canvas
        rect_editor (RectEditor): 矩形框編輯器實例
        display_scale (float): 目前的顯示縮放比例
    """

    def __init__(self, parent, image, mark_rect, on_close_callback=None, temp_file_path=None, origin_mark_rect=None):
        """初始化溫度編輯畫布對話框。

        Args:
            parent (tk.Widget): 父元件
            image (PIL.Image): 背景影像
            mark_rect (list): 元器件標記資料列表
            on_close_callback (callable|None): 視窗關閉時的回呼函式
            temp_file_path (str|None): 溫度資料檔案路徑
            origin_mark_rect (list|None): 原始辨識結果（用於跨 session 回到起點）
        """
        super().__init__()

        self.on_close_callback = on_close_callback
        self.parent = parent
        # 使用深拷贝避免修改主页面的原始数据
        import copy
        self.mark_rect = copy.deepcopy(mark_rect)
        self.origin_mark_rect = copy.deepcopy(origin_mark_rect) if origin_mark_rect is not None else None
        self.temp_file_path = temp_file_path
        self.last_window_width = 0
          # 控制更新的频率
        self.resize_after = None

        # 加载背景图片（使用 Pillow）
        self.bg_image = image #Image.open(image_path)  # 通过参数传入图片路径
        self.tk_bg_image = None  # 保持对图像的引用
        self.bg_image_id = None
        # 获取原始图像的宽高
        self.original_width, self.original_height = self.bg_image.size

        # 创建新的对话框
        # 如果parent是ResizableImagesApp实例，使用其root窗口作为父窗口
        if hasattr(self.parent, 'root'):
            parent_window = self.parent.root
        else:
            parent_window = self.parent
            
        dialog = tk.Toplevel(parent_window)
        dialog.title("Edit Temperature")
        dialog.state('zoomed')  # 直接以全螢幕方式開啟
        dialog.bind("<Configure>", self.on_resize)
        dialog.protocol("WM_DELETE_WINDOW", self.on_window_close)

        # 初始化列表相关变量
        self.rect_list_items = []  # 存储列表项
        self.selected_rect_id = None  # 当前选中的矩形ID
        self.selected_rect_ids = set()  # 多选模式下选中的矩形ID集合
        self.multi_select_enabled = True  # 多选模式启用标志（默認開啟）
        self.last_selected_index = None  # 記錄最後一次選中的項目索引（用於 Shift + 點擊範圍選擇）

        # 功能開關變量
        self.realtime_temp_enabled = True  # 溫度座標顯示模式（默認開啟）
        self.magnifier_enabled = True  # 放大模式（默認開啟）
        self.temp_label_id = None  # 溫度座標標籤ID

        # 排序相关变量
        self.sort_mode = "name_asc"  # 排序模式: "name_asc"=名称升序(默认), "temp_desc"=温度降序, "desc_asc"=描述升序

        # 篩選相關變量
        self.all_rectangles = []  # 保存所有矩形框（未經篩選）
        self.filtered_rectangles = []  # 保存篩選後的矩形框

        # 欄位寬度配置（統一管理，修改此處即可同步更新所有相關欄位）
        self.COLUMN_WIDTH_NAME = 3   # 點位名稱欄位寬度
        self.COLUMN_WIDTH_DESC = 28   # 描述欄位寬度
        self.COLUMN_WIDTH_TEMP = 3    # 溫度欄位寬度

        # Treeview 儲存格 tooltip 相關變量
        self._cell_tooltip = None      # tooltip Toplevel 視窗
        self._cell_tooltip_key = None  # 目前 tooltip 對應的 (item, column) 鍵

        # 先设置dialog属性
        self.dialog = dialog

        # 创建主框架
        main_frame = tk.Frame(dialog)
        main_frame.grid(row=0, column=0, sticky="nsew")

        # 配置dialog的grid属性
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_columnconfigure(0, weight=1)

        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # 使用 PanedWindow 讓左側面板可拖曳調整寬度
        self.paned = tk.PanedWindow(main_frame, orient=tk.HORIZONTAL, sashwidth=5, sashrelief=tk.RAISED, bg=UIStyle.VERY_LIGHT_BLUE)
        self.paned.grid(row=0, column=0, sticky="nsew")

        # 创建左侧列表面板（加到 PanedWindow）
        self.create_rect_list_panel(self.paned)

        # 创建右侧容器（canvas + toolbar）
        right_container = tk.Frame(self.paned)
        right_container.grid_rowconfigure(0, weight=1)
        right_container.grid_columnconfigure(0, weight=1)
        right_container.grid_columnconfigure(1, weight=0)
        self.paned.add(right_container, stretch="always")

        # 创建中间canvas区域，使用grid布局
        canvas_frame = tk.Frame(right_container, bg='white')  # 白色背景
        canvas_frame.grid(row=0, column=0, sticky="nsew")

        # 配置canvas_frame的grid属性，确保Canvas居中
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        # 创建 Canvas，使用grid布局实现真正的居中
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        # 使用grid布局让Canvas在框架中居中
        self.canvas.grid(row=0, column=0, sticky="")

        # 绑定框架大小变化事件，调用update_bg_image进行缩放
        canvas_frame.bind('<Configure>', lambda e: self.update_bg_image() if hasattr(self, 'canvas') and self.canvas is not None else None)

        # 延迟执行一次调整，确保框架已初始化
        self.dialog.after(200, self.update_bg_image)

        # 创建右侧操作条
        self.create_vertical_toolbar(right_container)
        
        # 绑定键盘 Delete / BackSpace 键到对话框和 Canvas
        # 注意：on_delete_rect 內部會檢查事件來源，忽略來自 Entry/Text 的事件
        self.dialog.bind('<Delete>', self.on_delete_rect)
        self.dialog.bind('<KeyPress-Delete>', self.on_delete_rect)
        self.dialog.bind('<Key-Delete>', self.on_delete_rect)
        self.dialog.bind('<KP_Delete>', self.on_delete_rect)
        self.dialog.bind('<BackSpace>', self.on_delete_rect)
        self.dialog.bind('<KeyPress-BackSpace>', self.on_delete_rect)
        self.canvas.bind('<Delete>', self.on_delete_rect)
        self.canvas.bind('<KeyPress-Delete>', self.on_delete_rect)
        self.canvas.bind('<Key-Delete>', self.on_delete_rect)
        self.canvas.bind('<KP_Delete>', self.on_delete_rect)
        self.canvas.bind('<BackSpace>', self.on_delete_rect)
        self.canvas.bind('<KeyPress-BackSpace>', self.on_delete_rect)

        # 綁定 Ctrl+Z 快捷鍵到回到上一步（排除文字輸入框）
        def _on_ctrl_z(event):
            if hasattr(event, 'widget') and isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text)):
                return
            self.on_undo()
        self.dialog.bind('<Control-z>', _on_ctrl_z)
        self.canvas.bind('<Control-z>', _on_ctrl_z)
        
        # 确保对话框可以接收键盘事件
        self.dialog.focus_set()
        
        # 绑定窗口关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_window_close)

        # 绑定右键选单事件
        self.canvas.bind("<Button-3>", self.show_context_menu)

        # mark_rect = []
        # rectItem1 = {"x1": 0,  "y1": 0, "x2": 100, "y2": 100, "cx": 50, "cy": 50, "max_temp": 73.2, "name": "A","rectId": 0,"nameId": 0, "triangleId": 0, "tempTextId": 0}
        # rectItem2 = {"x1": 200,  "y1": 200, "x2": 300, "y2": 350, "cx": 220, "cy": 290, "max_temp": 50.3, "name": "A1","rectId": 0,"nameId": 0, "triangleId": 0, "tempTextId": 0}
        # rectItem3 = {"x1": 400,  "y1": 400, "x2": 500, "y2": 550, "cx": 433, "cy": 499, "max_temp": 23.2, "name": "A2","rectId": 0,"nameId": 0, "triangleId": 0, "tempTextId": 0}
        # mark_rect.append(rectItem1)
        # mark_rect.append(rectItem2)
        # mark_rect.append(rectItem3)
        
        # 绑定全局滚轮事件作为备选
        if hasattr(self, '_bind_to_dialog_later') and self._bind_to_dialog_later:
            self.dialog.bind_all("<MouseWheel>", self._on_mousewheel_global)
            print("已绑定全局滚轮事件")
        
        # 然后创建editor_rect，传递温度文件路径和回调函数
        # 传递self而不是self.parent，这样editor_rect可以访问到dialog
        self.editor_rect = RectEditor(self, self.canvas, self.mark_rect, self.temp_file_path, self.on_rect_change)

        # 設置縮放功能的背景圖像和回調
        self.editor_rect.set_background_image(self.bg_image)
        self.editor_rect.on_zoom_change_callback = self.on_zoom_change

        # 重新綁定右鍵與滾輪事件：攔截篩選條件生效時的操作
        self.canvas.bind("<Button-3>", self._on_right_click_with_filter_check)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel_with_filter_check)

        # 快照系統（復原功能）
        self._initial_snapshot = None  # 初始快照（回到起點用）
        self._undo_stack = []          # 歷史堆疊（最多 3 筆，回到上一步用）

        # 初始化Layout查询器（用于智能识别元器件名称）
        self.layout_query = None
        self.initialize_layout_query()

        # 延迟设置显示缩放比例和更新列表，确保canvas完全初始化
        self.dialog.after(100, self.delayed_initialization)

    def delayed_initialization(self):
        """延迟初始化，确保canvas尺寸正确"""
        # 放大模式預設開啟時，先同步 editor_rect（必須在 update_bg_image 之前）
        if self.magnifier_enabled and hasattr(self, 'editor_rect') and self.editor_rect:
            self.editor_rect.set_magnifier_mode(True)
            # 重置 zoom_scale 為 0，讓 calculate_fit_scale 能正確設為 min_zoom（fit 顯示）
            # 否則預設 zoom_scale=1.0 大於 min_zoom，不會被更新，導致圖片以原始尺寸繪製
            self.editor_rect.zoom_scale = 0
            self.editor_rect.canvas_offset_x = 0
            self.editor_rect.canvas_offset_y = 0
        # 先建立所有標記（必須在 update_bg_image 之前，讓 on_zoom_change 能正確重繪）
        if hasattr(self, 'editor_rect') and self.editor_rect:
            self.editor_rect.init_marks()
        # 強制 update_bg_image 執行（避免 <Configure> 事件已設定 last_window_width 導致跳過）
        self.last_window_width = -1
        # 更新背景圖像並設定正確的縮放比例
        # 放大模式：update_bg_image → calculate_fit_scale → on_zoom_change（重繪所有標記）
        # 非放大模式：update_bg_image → update_editor_display_scale → redraw_all_rectangles
        self.update_bg_image()
        # 同步多选模式状态到 editor_rect
        if hasattr(self, 'editor_rect') and self.editor_rect:
            self.editor_rect.multi_select_enabled = self.multi_select_enabled
        # 溫度座標預設開啟時，綁定滑鼠移動事件
        if self.realtime_temp_enabled and hasattr(self, 'dialog') and self.dialog:
            self.dialog.bind('<Motion>', self.on_canvas_motion_show_temp, add='+')
        # 應用預設排序（點位名稱 A~Z）
        self.apply_sort()
        # 最后更新列表（apply_sort 內部已經調用了 update_rect_list，這裡可以移除）
        # self.update_rect_list()

        # 計算排除元器件列表（未通過溫度篩選的元器件）
        self._compute_excluded_components()

        # 儲存初始快照（所有矩形繪製完成後）
        self._initial_snapshot = self._create_snapshot()

        # 建立原始辨識快照（用於跨 session 回到起點）
        if self.origin_mark_rect is not None:
            import copy
            self._origin_snapshot = {
                "rectangles": copy.deepcopy(self.origin_mark_rect),
                "add_new_count": 0,
                "delete_origin_count": 0,
                "modify_origin_set": set(),
            }
        else:
            self._origin_snapshot = None
        self._update_reset_button_state()

    def _compute_excluded_components(self):
        """計算目前不在左側列表中的元器件，預先轉換為熱力圖像素座標與 Layout 圖中心座標"""
        self.excluded_components = []
        if not self.layout_query or not hasattr(self.parent, 'layout_data') or not self.parent.layout_data:
            return

        # 目前左側列表中的元器件名稱（以 editor_rect.rectangles 為準）
        included_names = set()
        if hasattr(self, 'editor_rect') and self.editor_rect:
            included_names = {r.get('name', '') for r in self.editor_rect.rectangles}
        else:
            included_names = {r.get('name', '') for r in self.mark_rect}

        for comp in self.parent.layout_data:
            refdes = comp['RefDes']
            if refdes in included_names:
                continue

            # PCB座標 → Layout圖座標 → 熱力圖座標
            cr1 = self.layout_query.convert_pcb_to_layout(comp['left'], comp['top'], comp['right'], comp['bottom'])
            if cr1 is None:
                continue
            ar1 = self.layout_query.convert_layout_to_thermal(*cr1)
            if ar1 is None:
                continue

            ar1_left, ar1_top, ar1_right, ar1_bottom = [int(v) for v in ar1]
            self.excluded_components.append({
                'RefDes': refdes,
                'X': comp.get('X', 0), 'Y': comp.get('Y', 0),
                'L': comp.get('L', 0), 'W': comp.get('W', 0), 'T': comp.get('T', 0),
                'Orient.': comp.get('Orient.', 0),
                'Description': comp.get('Description', ''),
                'ar1_left': ar1_left, 'ar1_top': ar1_top,
                'ar1_right': ar1_right, 'ar1_bottom': ar1_bottom,
            })

        print(f"可加回元器件數量: {len(self.excluded_components)}")

    def create_rect_list_panel(self, parent):
        """创建左侧矩形框列表面板"""
        # 创建左侧面板框架
        left_panel = tk.Frame(parent, width=340, bg=UIStyle.VERY_LIGHT_BLUE)
        self.paned.add(left_panel, minsize=200, width=340, stretch="never")
        self.left_panel = left_panel
        # 限制左側面板最大寬度：不超過視窗寬度的 1/3
        def _enforce_max_width(event=None):
            try:
                max_width = self.dialog.winfo_width() // 3
                sash_pos = self.paned.sash_coord(0)[0]
                if sash_pos > max_width:
                    self.paned.sash_place(0, max_width, 0)
            except (tk.TclError, IndexError):
                pass
        left_panel.bind('<Configure>', _enforce_max_width)
        
        # 配置左侧面板的grid属性
        left_panel.grid_rowconfigure(0, weight=0)  # 标题行，固定高度
        # left_panel.grid_rowconfigure(1, weight=0)  # 搜索框行（已註解）
        left_panel.grid_rowconfigure(2, weight=0)  # 篩選條件行，固定高度
        left_panel.grid_rowconfigure(3, weight=1)  # Treeview表格區域，自適應高度
        left_panel.grid_columnconfigure(0, weight=1)  # 单列，占满宽度

        # 标题行
        title_row = tk.Frame(left_panel, bg=UIStyle.VERY_LIGHT_BLUE)
        title_row.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # 标题（动态显示数量）
        self.title_label = tk.Label(title_row, text="元器件列表(0)", font=UIStyle.TITLE_FONT, bg=UIStyle.VERY_LIGHT_BLUE, fg=UIStyle.BLACK)
        self.title_label.pack(side="left")

        # 提示圖示（驚嘆號）
        help_icon = tk.Label(
            title_row,
            text="ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        help_icon.pack(side="left", padx=(5, 0))

        # 為提示圖示添加 tooltip
        Tooltip(
            help_icon,
            "多選操作說明：\n"
            "• 單擊：選擇單一項目\n"
            "• Shift + 點擊：列表選擇連續範圍\n"
            "• Ctrl + 點擊：列表跳選個別項目"
        )

        # [已註解] 搜索輸入框功能（已由篩選保留系統取代）
        # search_frame = tk.Frame(left_panel, bg=UIStyle.VERY_LIGHT_BLUE)
        # search_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        # search_frame.grid_columnconfigure(1, weight=1)
        # search_label = tk.Label(search_frame, text="🔍", font=("Arial", 12), bg=UIStyle.VERY_LIGHT_BLUE, fg=UIStyle.PRIMARY_BLUE)
        # search_label.grid(row=0, column=0, sticky="w", padx=(0, 3))
        # self.search_entry = PlaceholderEntry(
        #     search_frame,
        #     placeholder="搜索器件名称",
        #     placeholder_color="gray",
        #     font=UIStyle.SMALL_FONT
        # )
        # self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 3))
        # clear_button = tk.Button(
        #     search_frame,
        #     text="✕",
        #     font=("Arial", 10, "bold"),
        #     width=3,
        #     height=1,
        #     bg=UIStyle.VERY_LIGHT_BLUE,
        #     fg=UIStyle.PRIMARY_BLUE,
        #     relief='flat',
        #     bd=0,
        #     command=self.clear_search
        # )
        # clear_button.grid(row=0, column=2, sticky="e")
        # self.search_entry.bind('<KeyRelease>', self.on_search_changed)

        # 篩選條件輸入框框架（在表頭上方）
        filter_frame = tk.Frame(left_panel, bg=UIStyle.VERY_LIGHT_BLUE)
        filter_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))

        # 統一的篩選輸入框寬度（縮減為原本的一半）
        FILTER_INPUT_WIDTH = 17

        # === 第一列：篩選保留標籤 + 點位名稱篩選輸入框 + ⓘ ===
        # "篩選保留" 標籤
        filter_label = tk.Label(
            filter_frame,
            text="篩選保留",
            font=("Arial", 10),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.DARK_GRAY
        )
        filter_label.grid(row=0, column=0, sticky="w", padx=(5, 5), pady=3)

        # 點位名稱篩選輸入框（與篩選保留同一列）
        self.filter_name_entry = PlaceholderEntry(
            filter_frame,
            placeholder='點位名稱：輸入 C,HS',
            placeholder_color="gray",
            font=("Arial", 9),
            width=FILTER_INPUT_WIDTH,
            bg=UIStyle.WHITE,
            relief="solid",
            bd=1
        )
        self.filter_name_entry.grid(row=0, column=1, sticky="w", padx=(0, 2), pady=3)
        self.filter_name_entry.bind('<KeyRelease>', self.on_filter_changed)

        # 點位名稱篩選資訊圖示（帶 tooltip）
        name_info_label = tk.Label(
            filter_frame,
            text="ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        name_info_label.grid(row=0, column=2, sticky="w", padx=(0, 5), pady=3)
        Tooltip(name_info_label,
                "名稱篩選說明：\n"
                "• 單一值：輸入 C 篩選包含 C 的項目\n"
                "• 多值（OR）：輸入 \"C\",\"HS\" 篩選包含 C 或 HS 的項目\n"
                "• 格式支援：\"C\",\"HA\" 或 C,HS")

        # === 第二列：刪除其他按鈕 + ⓘ（篩選保留正下方） ===
        delete_others_sub_frame = tk.Frame(filter_frame, bg=UIStyle.VERY_LIGHT_BLUE)
        delete_others_sub_frame.grid(row=1, column=0, sticky="w", padx=(5, 5), pady=(0, 3))

        self.delete_others_btn = tk.Button(
            delete_others_sub_frame,
            text="\u26A0 刪除其他",
            font=("Arial", 8),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.BLACK,
            relief="raised",
            bd=1,
            padx=4,
            pady=0,
            command=self.on_delete_others,
            state='disabled'
        )
        self.delete_others_btn.pack(side='left')

        # 刪除其他說明圖示
        delete_others_info_label = tk.Label(
            delete_others_sub_frame,
            text="ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        delete_others_info_label.pack(side='left', padx=(4, 0))
        Tooltip(
            delete_others_info_label,
            "刪除其他說明：\n"
            "• 先用篩選條件篩選出要保留的元器件\n"
            "• 點擊按鈕後，不符合篩選條件的項目將被刪除\n"
            "• 可透過「回到上一步」復原，或用「加回元器件」找回\n"
            "• 也可透過「回到起點」恢復為最初辨識結果"
        )

        # === 第三列：描述篩選輸入框 + ⓘ ===
        # 描述篩選輸入框
        self.filter_desc_entry = PlaceholderEntry(
            filter_frame,
            placeholder='描述：輸入 EC,CAP',
            placeholder_color="gray",
            font=("Arial", 9),
            width=FILTER_INPUT_WIDTH,
            bg=UIStyle.WHITE,
            relief="solid",
            bd=1
        )
        self.filter_desc_entry.grid(row=1, column=1, sticky="w", padx=(0, 2), pady=3)
        self.filter_desc_entry.bind('<KeyRelease>', self.on_filter_changed)

        # 描述篩選資訊圖示（帶 tooltip）
        desc_info_label = tk.Label(
            filter_frame,
            text="ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        desc_info_label.grid(row=1, column=2, sticky="w", padx=(0, 5), pady=3)
        Tooltip(desc_info_label,
                "描述篩選說明：\n"
                "• 單一值：輸入 EC 篩選包含 EC 的項目\n"
                "• 多值（OR）：輸入 \"EC\",\"CAP\" 篩選包含 EC 或 CAP 的項目\n"
                "• 格式支援：\"EC\",\"CAP\" 或 EC,CAP")

        # === 第三列：溫度篩選輸入框 + 驚嘆號 ===
        # 溫度篩選輸入框
        self.filter_temp_entry = PlaceholderEntry(
            filter_frame,
            placeholder='溫度：輸入 >60, <75, =60',
            placeholder_color="gray",
            font=("Arial", 9),
            width=FILTER_INPUT_WIDTH,
            bg=UIStyle.WHITE,
            relief="solid",
            bd=1
        )
        self.filter_temp_entry.grid(row=2, column=1, sticky="w", padx=(0, 2), pady=3)
        self.filter_temp_entry.bind('<KeyRelease>', self.on_filter_changed)

        # 溫度篩選資訊圖示（帶 tooltip）
        temp_info_label = tk.Label(
            filter_frame,
            text="ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        temp_info_label.grid(row=2, column=2, sticky="w", padx=(0, 5), pady=3)
        Tooltip(temp_info_label,
                "溫度篩選說明：\n"
                "• >60   : 大於 60°C\n"
                "• <75   : 小於 75°C\n"
                "• >=60.5: 大於等於 60.5°C\n"
                "• <=70  : 小於等於 70°C\n"
                "• =60   : 等於 60°C")

        # 创建 Treeview 表格框架
        tree_frame = tk.Frame(left_panel, bg=UIStyle.VERY_LIGHT_BLUE)
        tree_frame.grid(row=3, column=0, sticky="nsew")

        # 創建 Treeview（表格）
        self.tree = ttk.Treeview(
            tree_frame,
            columns=('name', 'desc', 'temp'),
            show='tree headings',  # 顯示表頭
            selectmode='extended'  # 支持多選
        )

        # 配置欄位：名稱與溫度固定不縮小，描述欄位自動填滿可縮小
        self.tree.column('#0', width=0, stretch=tk.NO)  # 隱藏第一欄（tree column）
        self.tree.column('name', width=70, minwidth=70, anchor='w', stretch=tk.NO)  # 點位名稱欄位（固定寬度）
        self.tree.column('desc', width=180, minwidth=40, anchor='w', stretch=tk.YES)  # 描述欄位（可縮小，自動填滿）
        self.tree.column('temp', width=60, minwidth=60, anchor='center', stretch=tk.NO)  # 溫度欄位（固定寬度）

        # 配置表頭
        self.tree.heading('name', text='點位名稱 ▼', command=self.toggle_sort_by_name)
        self.tree.heading('desc', text='描述', command=self.toggle_sort_by_desc)
        self.tree.heading('temp', text='溫度', command=self.toggle_sort_by_temp)

        # 創建垂直滾動條
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 佈局
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # 配置 grid 權重
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(1, weight=0)

        # 綁定點擊事件
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Button-1>', self.on_tree_click)

        # 綁定儲存格 hover tooltip 事件
        self.tree.bind('<Motion>', self._on_tree_cell_motion)
        self.tree.bind('<Leave>', self._on_tree_cell_leave)

        # 移除名称推荐下拉框

        # 初始化列表（應用預設排序：點位名稱 A~Z）
        # 注意：update_rect_list() 會自動調用 update_sort_indicators()
        self.update_rect_list()

    def _on_tree_cell_motion(self, event):
        """Treeview 儲存格 hover tooltip：偵測游標所在的 row+column 並顯示完整文字"""
        try:
            item = self.tree.identify_row(event.y)
            col = self.tree.identify_column(event.x)
            if not item or not col:
                self._hide_cell_tooltip()
                return

            key = (item, col)
            if key == self._cell_tooltip_key:
                # 同一儲存格，只更新位置
                if self._cell_tooltip:
                    x = event.x_root + 15
                    y = event.y_root + 10
                    self._cell_tooltip.wm_geometry(f"+{x}+{y}")
                return

            # 取得儲存格文字
            col_index = int(col.replace('#', '')) - 1
            columns = ('name', 'desc', 'temp')
            if col_index < 0 or col_index >= len(columns):
                self._hide_cell_tooltip()
                return
            values = self.tree.item(item, 'values')
            if not values or col_index >= len(values):
                self._hide_cell_tooltip()
                return
            text = str(values[col_index])
            if not text:
                self._hide_cell_tooltip()
                return

            # 建立新的 tooltip
            self._hide_cell_tooltip()
            self._cell_tooltip_key = key
            tw = tk.Toplevel(self.tree)
            tw.wm_overrideredirect(True)
            label = tk.Label(
                tw, text=text, justify=tk.LEFT,
                background="#FFFFCC", foreground="#000000",
                relief=tk.SOLID, borderwidth=1,
                font=("Arial", 9), padx=8, pady=6
            )
            label.pack()
            x = event.x_root + 15
            y = event.y_root + 10
            tw.wm_geometry(f"+{x}+{y}")
            tw.lift()
            self._cell_tooltip = tw
        except (tk.TclError, Exception):
            pass

    def _on_tree_cell_leave(self, event):
        """離開 Treeview 時隱藏儲存格 tooltip"""
        self._hide_cell_tooltip()

    def _hide_cell_tooltip(self):
        """銷毀儲存格 tooltip"""
        if self._cell_tooltip:
            try:
                self._cell_tooltip.destroy()
            except (tk.TclError, Exception):
                pass
            self._cell_tooltip = None
        self._cell_tooltip_key = None

    def _on_mousewheel(self, event):
        """统一的滚轮事件处理 - 直接控制列表滚动"""
        try:
            # 判断事件类型并计算滚动方向
            if hasattr(event, 'delta') and event.delta != 0:
                # Windows系统：event.delta为正数表示向上滚动，负数表示向下滚动
                delta = -1 * (event.delta / 120)  # 标准化滚动量
            elif hasattr(event, 'num'):
                # Linux系统：Button-4为向上，Button-5为向下
                if event.num == 4:
                    delta = -1  # 向上滚动
                elif event.num == 5:
                    delta = 1   # 向下滚动
                else:
                    return
            else:
                return
            
            # 直接滚动列表，使用较大的步长确保明显效果
            scroll_amount = int(delta * 3)  # 每次滚动3个单位
            
            # 确保list_canvas存在且可滚动
            if hasattr(self, 'list_canvas') and self.list_canvas:
                # 获取当前滚动区域
                scrollregion = self.list_canvas.cget("scrollregion")
                if scrollregion and scrollregion != "0 0 0 0":
                    self.list_canvas.yview_scroll(scroll_amount, "units")
                    # print(f"✓ 滚轮滚动成功: delta={delta}, 滚动量={scroll_amount}")
                else:
                    print("× 滚动区域未设置或为空")
            else:
                print("× list_canvas不存在")
            
        except Exception as e:
            print(f"滚轮滚动错误: {e}")
    
    def _on_mousewheel_global(self, event):
        """全局滚轮事件处理 - 检查鼠标位置后处理"""
        try:
            # 检查鼠标是否在列表区域
            if hasattr(self, '_scroll_widgets'):
                mouse_x = event.x_root
                mouse_y = event.y_root
                
                for widget in self._scroll_widgets:
                    try:
                        x1 = widget.winfo_rootx()
                        y1 = widget.winfo_rooty()
                        x2 = x1 + widget.winfo_width()
                        y2 = y1 + widget.winfo_height()
                        
                        if x1 <= mouse_x <= x2 and y1 <= mouse_y <= y2:
                            # print(f"全局滚轮事件 - 鼠标在列表区域内")
                            self._on_mousewheel(event)
                            return
                    except:
                        continue
                        
        except Exception as e:
            print(f"全局滚轮处理错误: {e}")

    def on_canvas_click(self, event):
        """处理Canvas点击事件，点击空白区域时清除选择"""
        # 检查是否点击在列表项上
        clicked_widget = self.list_canvas.find_closest(event.x, event.y)
        if not clicked_widget:
            # 点击在空白区域，清除所有选择
            self.clear_all_selections()
            self.selected_rect_id = None
            # 更新删除按钮状态
            self.update_delete_button_state()

    def update_rect_list(self):
        """更新矩形框列表（使用 Treeview）"""
        # 清除現有項目
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 檢查是否有篩選條件
        has_filter = False
        if hasattr(self, 'filter_name_entry') and hasattr(self, 'filter_desc_entry') and hasattr(self, 'filter_temp_entry'):
            name_filter = self.filter_name_entry.get().strip()
            desc_filter = self.filter_desc_entry.get().strip()
            temp_filter = self.filter_temp_entry.get().strip()
            has_filter = bool(name_filter or desc_filter or temp_filter)

        # 獲取要顯示的矩形框列表
        rectangles = []
        if has_filter and hasattr(self, 'filtered_rectangles') and self.filtered_rectangles is not None:
            # 如果有篩選條件，使用篩選後的列表
            rectangles = self.filtered_rectangles
        elif hasattr(self, 'editor_rect') and self.editor_rect:
            # 否則使用完整列表
            rectangles = self.editor_rect.rectangles
        elif hasattr(self, 'mark_rect') and self.mark_rect:
            # 如果editor_rect还没有初始化，使用mark_rect数据
            rectangles = self.mark_rect

        # 添加項目到 Treeview
        for i, rect in enumerate(rectangles):
            rect_name = rect.get('name', f'AR{i+1}')
            description = rect.get('description', '')
            max_temp = rect.get('max_temp', 0)
            temp_text = f"{max_temp:.1f}°C"

            # 🔥 使用原始列表中的索引作為 iid，確保在篩選模式下索引仍然正確
            # 需要找到這個 rect 在完整列表中的實際索引
            original_index = i  # 預設使用當前索引
            if has_filter and hasattr(self, 'editor_rect') and self.editor_rect:
                # 在篩選模式下，找到此 rect 在完整列表中的索引
                for idx, full_rect in enumerate(self.editor_rect.rectangles):
                    if full_rect is rect:  # 使用物件相同性檢查
                        original_index = idx
                        break

            # 插入項目，使用原始列表索引作為 iid
            self.tree.insert('', 'end', iid=str(original_index),
                           values=(rect_name, description, temp_text),
                           tags=(str(original_index),))

        # 確保所有矩形都是灰色邊框（未選中狀態）
        if hasattr(self, 'set_all_rects_unselected'):
            self.set_all_rects_unselected()

        # 更新標題數量
        try:
            self.title_label.config(text=f"元器件列表({len(rectangles)})")
        except Exception:
            pass

        # 更新排序指示符號
        self.update_sort_indicators()

        # 根據篩選結果更新 Canvas 上的顯示
        self.update_canvas_visibility()

    def on_tree_select(self, event):
        """Treeview 選擇事件處理"""
        selection = self.tree.selection()
        if not selection:
            return

        # 🔥 獲取選中的項目ID（現在是列表索引）
        selected_indices = [int(iid) for iid in selection]

        # 🔥 將列表索引轉換為 Canvas rectId
        selected_rect_ids = []
        if hasattr(self, 'editor_rect') and self.editor_rect:
            for index in selected_indices:
                if 0 <= index < len(self.editor_rect.rectangles):
                    rect = self.editor_rect.rectangles[index]
                    rect_id = rect.get('rectId')
                    if rect_id:
                        selected_rect_ids.append(rect_id)

        # 更新選中狀態
        self.selected_rect_ids = set(selected_rect_ids)

        if len(selected_rect_ids) == 1:
            # 單選
            self.selected_rect_id = selected_rect_ids[0]
            self.highlight_rect_in_canvas(self.selected_rect_id)
        elif len(selected_rect_ids) > 1:
            # 多選
            self.selected_rect_id = None
            self.highlight_multiple_rects_in_canvas(selected_rect_ids)
            # 使用 Ctrl/Shift 選取多個時，自動勾選多選模式
            if hasattr(self, 'multi_select_var') and not self.multi_select_var.get():
                self.multi_select_var.set(True)
                self.toggle_multi_select_mode()

        # 更新按鈕狀態
        if hasattr(self, 'update_delete_button_state'):
            self.update_delete_button_state()
        # 更新旋轉控制狀態
        self._update_rotation_state_for_selection()

    def on_tree_click(self, event):
        """Treeview 點擊事件處理（支持 Ctrl/Shift 鍵）"""
        # 這個方法可以用來處理特殊的點擊行為
        # Treeview 原生支持 Ctrl+點擊（跳選）和 Shift+點擊（範圍選擇）
        pass

    def update_canvas_visibility(self):
        """根據篩選結果更新 Canvas 上的顯示"""
        if not hasattr(self, 'canvas') or not self.canvas:
            return

        # 檢查是否有篩選條件
        has_filter = False
        if hasattr(self, 'filter_name_entry') and hasattr(self, 'filter_desc_entry') and hasattr(self, 'filter_temp_entry'):
            name_filter = self.filter_name_entry.get().strip()
            desc_filter = self.filter_desc_entry.get().strip()
            temp_filter = self.filter_temp_entry.get().strip()
            has_filter = bool(name_filter or desc_filter or temp_filter)

        # 獲取所有矩形框
        all_rects = []
        if hasattr(self, 'editor_rect') and self.editor_rect:
            all_rects = self.editor_rect.rectangles
        elif hasattr(self, 'mark_rect') and self.mark_rect:
            all_rects = self.mark_rect

        if not all_rects:
            return

        # 如果沒有篩選條件，顯示所有項目
        if not has_filter:
            for rect in all_rects:
                rect_id = rect.get('rectId')
                name_id = rect.get('nameId')
                temp_text_id = rect.get('tempTextId')
                triangle_id = rect.get('triangleId')

                if rect_id:
                    try:
                        self.canvas.itemconfig(rect_id, state='normal')
                    except tk.TclError:
                        # Canvas item 已失效，重新繪製整個元器件
                        if hasattr(self, 'editor_rect') and self.editor_rect:
                            self.editor_rect._redraw_single_rect(rect)
                        continue  # 重繪後所有子項目都是新的，跳過後續設定
                if name_id:
                    try:
                        self.canvas.itemconfig(name_id, state='normal')
                    except:
                        pass
                if temp_text_id:
                    try:
                        self.canvas.itemconfig(temp_text_id, state='normal')
                    except:
                        pass
                if triangle_id:
                    try:
                        self.canvas.itemconfig(triangle_id, state='normal')
                    except:
                        pass
                # 同步顯示描邊（黑色輪廓）
                for oid in (rect.get('tempOutlineIds') or []):
                    try:
                        self.canvas.itemconfig(oid, state='normal')
                    except:
                        pass
                for oid in (rect.get('nameOutlineIds') or []):
                    try:
                        self.canvas.itemconfig(oid, state='normal')
                    except:
                        pass
                for oid in (rect.get('triangleOutlineIds') or []):
                    try:
                        self.canvas.itemconfig(oid, state='normal')
                    except:
                        pass
            return

        # 獲取符合篩選條件的矩形框 ID 集合
        filtered_rect_ids = set()
        if hasattr(self, 'filtered_rectangles') and self.filtered_rectangles:
            for rect in self.filtered_rectangles:
                rect_id = rect.get('rectId')
                if rect_id:
                    filtered_rect_ids.add(rect_id)

        # 遍歷所有矩形框，根據是否在篩選結果中決定顯示或隱藏
        for rect in all_rects:
            rect_id = rect.get('rectId')
            name_id = rect.get('nameId')
            temp_text_id = rect.get('tempTextId')
            triangle_id = rect.get('triangleId')

            # 決定是顯示還是隱藏
            if rect_id in filtered_rect_ids:
                # 顯示符合條件的項目
                state = 'normal'
            else:
                # 隱藏不符合條件的項目
                state = 'hidden'

            # 更新 Canvas 上的顯示狀態
            if rect_id:
                try:
                    self.canvas.itemconfig(rect_id, state=state)
                except tk.TclError:
                    if state == 'normal' and hasattr(self, 'editor_rect') and self.editor_rect:
                        # Canvas item 已失效，重新繪製整個元器件
                        self.editor_rect._redraw_single_rect(rect)
                    continue  # 重繪後所有子項目都是新的，或是要隱藏的失效項目直接跳過
            if name_id:
                try:
                    self.canvas.itemconfig(name_id, state=state)
                except:
                    pass
            if temp_text_id:
                try:
                    self.canvas.itemconfig(temp_text_id, state=state)
                except:
                    pass
            if triangle_id:
                try:
                    self.canvas.itemconfig(triangle_id, state=state)
                except:
                    pass
            # 同步顯示/隱藏描邊（黑色輪廓）
            for oid in (rect.get('tempOutlineIds') or []):
                try:
                    self.canvas.itemconfig(oid, state=state)
                except:
                    pass
            for oid in (rect.get('nameOutlineIds') or []):
                try:
                    self.canvas.itemconfig(oid, state=state)
                except:
                    pass
            for oid in (rect.get('triangleOutlineIds') or []):
                try:
                    self.canvas.itemconfig(oid, state=state)
                except:
                    pass

    # 🗑️ 已廢棄：此方法使用舊的 rect_list_items API 和自定義 Frame/Label，已被 Treeview 版本取代
    # 新版本直接在 update_rect_list() 中使用 tree.insert() 創建項目
    # def create_list_item(self, rect, index):
    #     """创建单个列表项（已廢棄）"""
    #     # 创建列表项框架
    #     item_frame = tk.Frame(self.scrollable_frame, bg=UIStyle.WHITE, relief=tk.SOLID, bd=1)
    #     item_frame.pack(fill=tk.X, padx=2, pady=1)
    #
    #     # 获取矩形框数据
    #     rect_name = rect.get('name', f'AR{index+1}')
    #     max_temp = rect.get('max_temp', 0)
    #     rect_id = rect.get('rectId', index)
    #     description = rect.get('description', '')  # 獲取描述資訊
    #
    #     # 名称标签（帶框線，使用統一的欄位寬度）
    #     name_label = tk.Label(
    #         item_frame,
    #         text=rect_name,
    #         width=self.COLUMN_WIDTH_NAME,
    #         font=UIStyle.SMALL_FONT,
    #         bg=UIStyle.WHITE,
    #         anchor='w',
    #         relief=tk.SOLID,
    #         bd=1
    #     )
    #     name_label.pack(side=tk.LEFT, padx=0, pady=0)
    #
    #     # 描述标签（帶框線，使用統一的欄位寬度）
    #     desc_label = tk.Label(
    #         item_frame,
    #         text=description,
    #         width=self.COLUMN_WIDTH_DESC,
    #         font=UIStyle.SMALL_FONT,
    #         bg=UIStyle.WHITE,
    #         anchor='w',
    #         relief=tk.SOLID,
    #         bd=1
    #     )
    #     desc_label.pack(side=tk.LEFT, padx=0, pady=0)
    #
    #     # 温度标签（帶框線，使用統一的欄位寬度）
    #     temp_text = f"{max_temp:.1f}°C"
    #     temp_label = tk.Label(
    #         item_frame,
    #         text=temp_text,
    #         width=self.COLUMN_WIDTH_TEMP,
    #         font=UIStyle.SMALL_FONT,
    #         bg=UIStyle.WHITE,
    #         anchor='center',
    #         relief=tk.SOLID,
    #         bd=1
    #     )
    #     temp_label.pack(side=tk.LEFT, padx=0, pady=0)
    #
    #     # 绑定点击事件
    #     def on_item_click(event, rect_id=rect_id, index=index):
    #         # 阻止事件冒泡，避免点击触发滚动等副作用
    #         try:
    #             event.widget.focus_set()
    #         except Exception:
    #             pass
    #
    #         # 檢測是否按住修飾鍵
    #         # state & 0x0001 表示 Shift 鍵被按下
    #         # state & 0x0004 表示 Ctrl 鍵被按下
    #         shift_pressed = (event.state & 0x0001) != 0
    #         ctrl_pressed = (event.state & 0x0004) != 0
    #
    #         if shift_pressed and self.last_selected_index is not None:
    #             # Shift + 點擊：範圍選擇
    #             self.select_range(self.last_selected_index, index)
    #         elif ctrl_pressed:
    #             # Ctrl + 點擊：跳選（toggle 選中狀態）
    #             self.toggle_select_item(rect_id, index)
    #         else:
    #             # 一般點擊：單選
    #             self.select_rect_item(rect_id, item_frame)
    #             self.last_selected_index = index
    #
    #     # 绑定双击事件
    #     def on_item_double_click(event, rect_id=rect_id):
    #         self.open_edit_area_dialog(rect_id)
    #
    #     # 绑定事件
    #     item_frame.bind("<Button-1>", on_item_click)
    #     item_frame.bind("<Double-Button-1>", on_item_double_click)
    #     name_label.bind("<Button-1>", on_item_click)
    #     name_label.bind("<Double-Button-1>", on_item_double_click)
    #     desc_label.bind("<Button-1>", on_item_click)
    #     desc_label.bind("<Double-Button-1>", on_item_double_click)
    #     temp_label.bind("<Button-1>", on_item_click)
    #     temp_label.bind("<Double-Button-1>", on_item_double_click)
    #
    #     # 移除下拉按钮
    #
    #     # 存储列表项信息
    #     list_item = {
    #         'frame': item_frame,
    #         'name_label': name_label,
    #         'desc_label': desc_label,
    #         'temp_label': temp_label,
    #         'rect_id': rect_id
    #     }
    #     self.rect_list_items.append(list_item)

    # 🗑️ 已廢棄：此方法使用舊的 rect_list_items API，已被 Treeview 版本取代
    # def select_rect_item(self, rect_id, item_frame):
    #     """选中列表项并高亮对应的矩形框"""
    #     print(f"🔍🔍🔍 select_rect_item被调用: rect_id={rect_id}")
    #     # 清除之前的选择（列表与canvas）
    #     self.clear_all_selections()
    #
    #     # 设置新的选择
    #     self.selected_rect_id = rect_id
    #     print(f"🔍🔍🔍 设置selected_rect_id = {self.selected_rect_id}")
    #
    #     # 从配置中读取选中颜色
    #     from config import GlobalConfig
    #     config = GlobalConfig()
    #     selected_color = config.get("heat_selected_color", "#4A90E2")
    #
    #     # 高亮当前选中的列表项
    #     item_frame.config(bg=selected_color)
    #
    #     # 更新删除按钮状态
    #     self.update_delete_button_state()
    #
    #     # 确保对话框可以接收键盘事件
    #     self.dialog.focus_set()
    #     for child in item_frame.winfo_children():
    #         if isinstance(child, (tk.Label, tk.Entry)):
    #             child.config(bg=selected_color, fg='white')
    #         elif isinstance(child, tk.Button):
    #             child.config(bg=selected_color, fg='white', activebackground=selected_color, activeforeground='white')
    #
    #     # 确保焦点回到对话框，以便接收Delete键事件
    #     self.dialog.after(10, lambda: self.dialog.focus_set())
    #
    #     # 高亮canvas中的矩形框，其他清空
    #     self.highlight_rect_in_canvas(rect_id)
    #     # 确保选中项滚动到可见区域
    #     # 不自动滚动到顶部，保持当前滚动位置，避免跳动
    pass  # 佔位符，防止語法錯誤

    # 🗑️ 已廢棄：此方法使用舊的 rect_list_items API，已被 Treeview 版本取代
    # def select_range(self, start_index, end_index):
    #     """Shift + 點擊：選擇範圍內的所有項目（包含頭尾）"""
    #     print(f"📋 範圍選擇: 從索引 {start_index} 到 {end_index}")
    #
    #     # 確保索引順序正確（小 -> 大）
    #     if start_index > end_index:
    #         start_index, end_index = end_index, start_index
    #
    #     # 清除之前的選擇
    #     self.clear_all_selections()
    #
    #     # 選擇範圍內的所有項目
    #     selected_rect_ids = []
    #     for i in range(start_index, end_index + 1):
    #         if i < len(self.rect_list_items):
    #             list_item = self.rect_list_items[i]
    #             rect_id = list_item['rect_id']
    #             selected_rect_ids.append(rect_id)
    #
    #     # 高亮所有選中的項目
    #     self.select_multiple_rect_items(selected_rect_ids)
    #
    #     # 更新最後選中的索引
    #     self.last_selected_index = end_index
    pass  # 佔位符

    # 🗑️ 已廢棄：此方法使用舊的 rect_list_items API，已被 Treeview 版本取代
    # def toggle_select_item(self, rect_id, index):
    #     """Ctrl + 點擊：跳選（toggle 該項目的選中狀態）"""
    #     print(f"🔘 跳選: rect_id={rect_id}, index={index}")
    #
    #     # 從配置中讀取選中顏色
    #     from config import GlobalConfig
    #     config = GlobalConfig()
    #     selected_color = config.get("heat_selected_color", "#4A90E2")
    #
    #     # 檢查該項目是否已選中
    #     if rect_id in self.selected_rect_ids:
    #         # 已選中 -> 取消選中
    #         self.selected_rect_ids.remove(rect_id)
    #         print(f"  ➖ 取消選中 {rect_id}")
    #     else:
    #         # 未選中 -> 添加選中
    #         self.selected_rect_ids.add(rect_id)
    #         print(f"  ➕ 添加選中 {rect_id}")
    #
    #     # 更新最後選中的索引
    #     self.last_selected_index = index
    #
    #     # 更新列表項的視覺效果
    #     for list_item in self.rect_list_items:
    #         frame = list_item['frame']
    #         item_rect_id = list_item['rect_id']
    #
    #         if item_rect_id in self.selected_rect_ids:
    #             # 選中狀態：藍色背景
    #             frame.config(bg=selected_color)
    #             for child in frame.winfo_children():
    #                 if isinstance(child, (tk.Label, tk.Entry)):
    #                     child.config(bg=selected_color, fg='white')
    #                 elif isinstance(child, tk.Button):
    #                     child.config(bg=selected_color, fg='white', activebackground=selected_color, activeforeground='white')
    #         else:
    #             # 未選中狀態：白色背景
    #             frame.config(bg='white')
    #             for child in frame.winfo_children():
    #                 if isinstance(child, (tk.Label, tk.Entry)):
    #                     child.config(bg='white', fg='black')
    #                 elif isinstance(child, tk.Button):
    #                     child.config(bg='#f0f0f0', fg='black', activebackground='#e0e0e0', activeforeground='black')
    #
    #     # 更新 canvas 上的高亮效果
    #     if len(self.selected_rect_ids) > 0:
    #         self.highlight_multiple_rects_in_canvas(list(self.selected_rect_ids))
    #     else:
    #         # 如果沒有選中任何項目，清除所有高亮
    #         self.set_all_rects_unselected()
    #         if hasattr(self, 'editor_rect') and self.editor_rect:
    #             self.editor_rect.delete_anchors()
    #
    #     # 更新刪除按鈕狀態
    #     self.update_delete_button_state()
    #
    #     # 確保焦點回到對話框
    #     self.dialog.focus_set()
    pass  # 佔位符

    # 🗑️ 已廢棄：此方法使用舊的 rect_list_items API，已被 handle_multi_select (Treeview版本) 取代
    # def select_multiple_rect_items(self, rect_ids):
    #     """選中多個列表項並高亮對應的矩形框"""
    #     print(f"🔍 多選模式：選中 {len(rect_ids)} 個項目")
    #
    #     # 清除之前的選擇
    #     self.clear_list_selections()
    #
    #     # 更新選中的 ID 集合
    #     self.selected_rect_ids = set(rect_ids)
    #
    #     # 從配置中讀取選中顏色
    #     from config import GlobalConfig
    #     config = GlobalConfig()
    #     selected_color = config.get("heat_selected_color", "#4A90E2")
    #
    #     # 高亮所有選中的列表項
    #     for list_item in self.rect_list_items:
    #         if list_item['rect_id'] in rect_ids:
    #             frame = list_item['frame']
    #             frame.config(bg=selected_color)
    #
    #             for child in frame.winfo_children():
    #                 if isinstance(child, (tk.Label, tk.Entry)):
    #                     child.config(bg=selected_color, fg='white')
    #                 elif isinstance(child, tk.Button):
    #                     child.config(bg=selected_color, fg='white', activebackground=selected_color, activeforeground='white')
    #
    #     # 高亮 canvas 中的所有矩形框
    #     self.highlight_multiple_rects_in_canvas(rect_ids)
    #
    #     # 更新刪除按鈕狀態
    #     self.update_delete_button_state()
    #
    #     # 確保焦點回到對話框
    #     self.dialog.focus_set()
    pass  # 佔位符

    def clear_list_selections(self):
        """只清除列表项的選中狀態（使用 Treeview）"""
        # 🔥 修復：使用 Treeview API 清除選取
        if hasattr(self, 'tree') and self.tree:
            try:
                self.tree.selection_remove(self.tree.selection())
            except Exception as e:
                print(f"✗ 清除 Treeview 選取時出錯: {e}")

        # 清除選中狀態並更新刪除按鈕（支持單選和多選）
        self.selected_rect_id = None
        self.selected_rect_ids.clear()
        self.update_delete_button_state()

    def clear_all_selections(self):
        """清除所有选择状态"""
        # 清除列表项的选中状态
        self.clear_list_selections()
        
        # 清除canvas中的锚点，恢复所有矩形为灰色边框
        if hasattr(self, 'editor_rect') and self.editor_rect:
            self.editor_rect.delete_anchors()
            # 将所有矩形设置为未选中状态（灰色边框）
            self.set_all_rects_unselected()
            # 清除选中状态
            self.editor_rect.drag_data["rectId"] = None
            self.editor_rect.drag_data["nameId"] = None
            self.editor_rect.drag_data["triangleId"] = None
            self.editor_rect.drag_data["tempTextId"] = None
            print("✓ 已清除所有锚点和选中状态，恢复灰色边框")
        
        # 清除选中状态并更新删除按钮
        self.selected_rect_id = None
        self.last_selected_index = None  # 重置最後選中的索引
        self.update_delete_button_state()

    def set_all_rects_unselected(self):
        """将所有矩形设置为未选中状态（灰色边框）"""
        if hasattr(self, 'editor_rect') and self.editor_rect:
            # 从配置中读取矩形框颜色和粗细
            from config import GlobalConfig
            config = GlobalConfig()
            rect_color = config.get("heat_rect_color", "#BCBCBC")
            rect_width = config.get("heat_rect_width", 2)

            # 遍历所有矩形，确保都设置为未选中状态（修复多个蓝色框问题）
            for rect in self.editor_rect.rectangles:
                rect_id = rect.get('rectId')
                if rect_id:
                    try:
                        # 设置为配置的矩形框颜色和粗细
                        self.canvas.itemconfig(rect_id, outline=rect_color, width=rect_width)
                    except tk.TclError:
                        # 如果矩形不存在，忽略错误
                        continue

    def set_canvas_selection_only(self, rect_id):
        """仅设置canvas选中状态，不清除其他状态（避免重复操作）"""
        if hasattr(self, 'editor_rect') and self.editor_rect:
            # 先将所有矩形设置为未选中状态（灰色边框）
            self.set_all_rects_unselected()
            
            # 设置选中的矩形ID（如果还没有设置的话）
            if self.editor_rect.drag_data["rectId"] != rect_id:
                self.editor_rect.drag_data["rectId"] = rect_id
                
                # 找到对应的矩形数据，设置其他相关ID
                for rect in self.editor_rect.rectangles:
                    if rect.get('rectId') == rect_id:
                        self.editor_rect.drag_data["nameId"] = rect.get("nameId")
                        self.editor_rect.drag_data["triangleId"] = rect.get("triangleId")
                        self.editor_rect.drag_data["tempTextId"] = rect.get("tempTextId")
                        break
            
            # 从配置中读取选中矩形框颜色和粗细
            from config import GlobalConfig
            config = GlobalConfig()
            selected_color = config.get("heat_selected_color", "#4A90E2")
            rect_width = config.get("heat_rect_width", 2)

            # 设置选中矩形为配置的选中颜色边框
            self.canvas.itemconfig(rect_id, outline=selected_color, width=rect_width)

            # 不重新创建锚点，因为RectEditor已经创建了
            # 将矩形框移到最前面
            self.canvas.tag_raise(rect_id)
            print(f"✓ 仅设置canvas选中状态: 矩形 {rect_id}")

    def clear_rect_highlight(self):
        """清除矩形框高亮（保留向后兼容）"""
        self.clear_all_selections()

    def highlight_rect_in_canvas(self, rect_id):
        """在canvas中选中指定矩形：显示8个锚点，设置蓝色边框"""
        if hasattr(self, 'editor_rect') and self.editor_rect:
            # 先将所有矩形设置为未选中状态（灰色边框）
            self.set_all_rects_unselected()
            
            # 清除所有锚点
            self.editor_rect.delete_anchors()
            # 设置选中的矩形ID
            self.editor_rect.drag_data["rectId"] = rect_id
            
            # 找到对应的矩形数据，设置其他相关ID
            for rect in self.editor_rect.rectangles:
                if rect.get('rectId') == rect_id:
                    self.editor_rect.drag_data["nameId"] = rect.get("nameId")
                    self.editor_rect.drag_data["triangleId"] = rect.get("triangleId")
                    self.editor_rect.drag_data["tempTextId"] = rect.get("tempTextId")
                    break
            
            # 从配置中读取选中矩形框颜色和粗细
            from config import GlobalConfig
            config = GlobalConfig()
            selected_color = config.get("heat_selected_color", "#4A90E2")
            rect_width = config.get("heat_rect_width", 2)

            # 设置选中矩形为配置的选中颜色边框
            self.canvas.itemconfig(rect_id, outline=selected_color, width=rect_width)

            # 为选中的矩形创建锚点（传递rect_id，create_anchors会从canvas获取坐标）
            self.editor_rect.create_anchors(rect_id)
            # 将矩形框移到最前面
            self.canvas.tag_raise(rect_id)
            print(f"✓ 已为矩形 {rect_id} 创建锚点并设置选中颜色边框")

    def highlight_multiple_rects_in_canvas(self, rect_ids):
        """在 canvas 中高亮多個矩形框（Shift + 點擊批量選擇）"""
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        # 先將所有矩形設置為未選中狀態
        self.set_all_rects_unselected()

        # 清除所有錨點（多選模式不顯示錨點）
        self.editor_rect.delete_anchors()

        # 從配置中讀取選中顏色和粗細
        from config import GlobalConfig
        config = GlobalConfig()
        selected_color = config.get("heat_selected_color", "#4A90E2")
        rect_width = config.get("heat_rect_width", 2)

        # 高亮所有選中的矩形框
        for rect_id in rect_ids:
            self.canvas.itemconfig(rect_id, outline=selected_color, width=rect_width)
            # 將矩形框移到最前面
            self.canvas.tag_raise(rect_id)

        print(f"✓ 已高亮 {len(rect_ids)} 個矩形框")

    def update_selected_item(self, rect_id):
        """只更新选中的列表项，不刷新整个列表（使用 Treeview API）"""
        if not hasattr(self, 'tree') or not self.tree:
            return

        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        # 🔥 將 Canvas rectId 轉換為列表索引並獲取矩形數據
        list_index = None
        target_rect = None
        for i, rect in enumerate(self.editor_rect.rectangles):
            if rect.get('rectId') == rect_id:
                list_index = i
                target_rect = rect
                break

        if list_index is not None and target_rect:
            item_id = str(list_index)
            if self.tree.exists(item_id):
                # 更新點位名稱和溫度
                new_name = target_rect.get('name', 'Unknown')
                description = target_rect.get('description', '')
                new_temp = target_rect.get('max_temp', 0)
                temp_text = f"{new_temp:.1f}°C"

                self.tree.item(item_id, values=(new_name, description, temp_text))
                print(f"✓ 已更新列表項 index={list_index}: 點位名稱={new_name}, 溫度={temp_text}")

    def update_rect_name(self, rect_id, new_name):
        """更新矩形框名称"""
        if hasattr(self, 'editor_rect') and self.editor_rect:
            for rect in self.editor_rect.rectangles:
                if rect.get('rectId') == rect_id:
                    rect['name'] = new_name
                    # 更新canvas中的名称显示
                    if 'nameId' in rect:
                        self.canvas.itemconfig(rect['nameId'], text=new_name)
                    print(f"✓ 已更新矩形 {rect_id} 的名称为: {new_name}")
                    break

    def show_name_dropdown(self, entry, var, rect_id):
        """显示名称推荐下拉菜单"""
        # 创建下拉菜单
        dropdown_menu = tk.Menu(self.dialog, tearoff=0)
        
        # 添加推荐名称选项
        for suggestion in self.name_suggestions:
            dropdown_menu.add_command(
                label=suggestion,
                command=lambda name=suggestion: self.select_name_suggestion(name, var, rect_id)
            )
        
        # 获取按钮位置并显示菜单
        try:
            # 获取entry的位置
            x = entry.winfo_rootx()
            y = entry.winfo_rooty() + entry.winfo_height()
            dropdown_menu.post(x, y)
        except:
            # 如果获取位置失败，在鼠标位置显示
            dropdown_menu.post(entry.winfo_pointerx(), entry.winfo_pointery())

    def select_name_suggestion(self, name, var, rect_id):
        """选择名称推荐"""
        var.set(name)
        self.update_rect_name(rect_id, name)

    def update_rect_temp_display(self, rect_id):
        """更新特定矩形框的温度显示（使用 Treeview API）"""
        # 🔥 修復：使用 Treeview API 更新溫度顯示
        if not hasattr(self, 'tree') or not self.tree:
            return

        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        # 🔥 將 Canvas rectId 轉換為列表索引
        list_index = None
        new_temp = None
        for i, rect in enumerate(self.editor_rect.rectangles):
            if rect.get('rectId') == rect_id:
                list_index = i
                new_temp = rect.get('max_temp', 0)
                break

        if list_index is not None and new_temp is not None:
            item_id = str(list_index)
            if self.tree.exists(item_id):
                # 獲取當前的項目值
                current_values = self.tree.item(item_id, 'values')
                if current_values and len(current_values) >= 3:
                    # 更新溫度顯示（保持點位名稱和描述不變）
                    name = current_values[0]
                    description = current_values[1]
                    temp_text = f"{new_temp:.1f}°C"
                    self.tree.item(item_id, values=(name, description, temp_text))
                    print(f"✓ 已更新列表溫度顯示，index={list_index}, temp={temp_text}")
            else:
                print(f"⚠️ Treeview 中找不到 index={list_index} 的項目")

    def scroll_to_item(self, rect_id):
        """滚动列表使指定的item可见（使用 Treeview API）"""
        if not hasattr(self, 'tree') or not self.tree:
            return

        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        try:
            # 🔥 將 Canvas rectId 轉換為列表索引
            list_index = None
            for i, rect in enumerate(self.editor_rect.rectangles):
                if rect.get('rectId') == rect_id:
                    list_index = i
                    break

            if list_index is not None:
                item_id = str(list_index)
                if self.tree.exists(item_id):
                    # 使用 Treeview 的 see() 方法滾動到項目
                    self.tree.see(item_id)
                    print(f"✓ 已滾動到 item index={list_index}")
        except Exception as e:
            print(f"✗ 滾動到 item 錯誤: {e}")

    def on_rect_change(self, rect_id=None, change_type=None):
        """矩形框变化时的回调函数"""
        if change_type == "before_modify":
            # 移動/縮放前：儲存快照供復原
            self._push_undo()
            return
        if change_type == "temp_update" and rect_id:
            # 只更新特定矩形框的温度显示
            self.update_rect_temp_display(rect_id)
        elif change_type == "select":
            # Canvas选中某个矩形 -> 列表也高亮对应项，并滚动到可见位置
            self.selected_rect_id = rect_id

            # 更新删除按钮状态
            self.update_delete_button_state()

            # 确保对话框可以接收键盘事件
            self.dialog.focus_set()

            # 🔥 修復：使用 Treeview API 選取項目
            if hasattr(self, 'tree') and self.tree and hasattr(self, 'editor_rect'):
                try:
                    # 清除之前的選取
                    self.tree.selection_remove(self.tree.selection())

                    # 🔥 將 Canvas rectId 轉換為列表索引
                    # rect_id 是 Canvas 繪圖物件的 ID，需要找到對應的矩形在列表中的索引
                    list_index = None
                    for i, rect in enumerate(self.editor_rect.rectangles):
                        if rect.get('rectId') == rect_id:
                            list_index = i
                            break

                    if list_index is not None:
                        item_id = str(list_index)
                        if self.tree.exists(item_id):
                            self.tree.selection_set(item_id)
                            self.tree.see(item_id)  # 滾動到可見位置
                            print(f"✓ 列表已選取元器件，rect_id={rect_id}, list_index={list_index}")
                        else:
                            print(f"⚠️ 列表中找不到 index={list_index} 的項目")
                    else:
                        print(f"⚠️ 無法在 rectangles 列表中找到 rectId={rect_id}")
                except Exception as e:
                    print(f"✗ 選取列表項目時出錯: {e}")

            # 设置canvas选中状态（避免重复清除操作）
            self.set_canvas_selection_only(rect_id)
            # 更新删除按钮状态
            self.update_delete_button_state()
            # 更新形狀轉換按鈕狀態
            self.update_shape_buttons_state()
            # 更新旋轉控制狀態
            self._update_rotation_state_for_selection()
        elif change_type == "clear_select":
            self.clear_all_selections()
            # 更新删除按钮状态
            self.update_delete_button_state()
            # 停用旋轉控制
            self.update_rotation_ui_state(False)
        elif change_type == "delete":
            # 清空选中状态
            self.selected_rect_id = None
            # 重建列表（刪除後索引會變，需完整重建）
            self.update_rect_list()
            # 更新删除按钮状态
            self.update_delete_button_state()
            print(f"✓ 矩形框 {rect_id} 已从Canvas和列表中删除")
        elif change_type == "dialog_update":
            # 双击对话框更新后，只更新选中的item，不刷新整个列表
            self.update_selected_item(rect_id)
            print(f"✓ 双击对话框更新完成，已同步选中项显示")
        elif change_type == "multi_select":
            # 多选模式：rect_id 是一个包含多个ID的列表
            self.handle_multi_select(rect_id)
        elif change_type == "multi_delete":
            # 批量删除：rect_id 是一个包含多个ID的列表
            self.handle_multi_delete(rect_id)
        else:
            # 完全更新列表
            self.update_rect_list()

    def handle_multi_select(self, rect_ids):
        """處理多選事件（使用 Treeview）"""
        if not rect_ids:
            return

        # 清除之前的選擇
        self.clear_list_selections()

        # 設置多選狀態
        self.selected_rect_ids = set(rect_ids)
        self.selected_rect_id = None  # 多選時清空單選ID

        # 從配置中讀取選中顏色和粗細
        from config import GlobalConfig
        config = GlobalConfig()
        selected_color = config.get("heat_selected_color", "#4A90E2")
        rect_width = config.get("heat_rect_width", 2)

        # 🔥 修復：使用 Treeview API 高亮所有選中的列表項
        # rect_ids 是 Canvas rectId 列表，需要轉換為列表索引
        if hasattr(self, 'tree') and self.tree and hasattr(self, 'editor_rect'):
            try:
                for rect_id in self.selected_rect_ids:
                    # 🔥 將 rectId 轉換為列表索引
                    for i, rect in enumerate(self.editor_rect.rectangles):
                        if rect.get('rectId') == rect_id:
                            item_id = str(i)
                            if self.tree.exists(item_id):
                                self.tree.selection_add(item_id)
                            break
                print(f"✓ Treeview 已選取 {len(self.selected_rect_ids)} 個項目")
            except Exception as e:
                print(f"✗ Treeview 多選時出錯: {e}")

        # 高亮canvas中的矩形框
        if hasattr(self, 'editor_rect') and self.editor_rect:
            self.set_all_rects_unselected()
            for rect_id in self.selected_rect_ids:
                self.canvas.itemconfig(rect_id, outline=selected_color, width=rect_width)

        # 更新刪除按鈕狀態
        self.update_delete_button_state()

        # 更新旋轉控制狀態
        self._update_rotation_state_for_selection()

        # 確保對話框可以接收鍵盤事件
        self.dialog.focus_set()

        print(f"✓ 多選高亮了 {len(self.selected_rect_ids)} 個矩形框")

    def handle_multi_delete(self, rect_ids):
        """处理批量删除事件"""
        if not rect_ids:
            return

        # 清空选中状态
        self.selected_rect_id = None
        self.selected_rect_ids.clear()

        # 重新整理列表（Treeview iid 是列表索引，刪除後索引會變，需完整重建）
        self.update_rect_list()

        # 更新删除按钮状态
        self.update_delete_button_state()

        print(f"✓ 批量删除了 {len(rect_ids)} 个矩形框")
    
    def on_click(self, event):
        print("xxxxxxxxxxxxxxxxx")

    def on_resize(self, event):
        # 每当窗口大小发生变化时，调整背景图片和Canvas的尺寸
        # 只有在canvas已经创建后才调用update_bg_image
        if hasattr(self, 'canvas') and self.canvas is not None:
            self.update_bg_image()

    def update_bg_image(self):
        # 检查dialog和canvas属性是否存在
        if not hasattr(self, 'dialog') or self.dialog is None:
            return
        if not hasattr(self, 'canvas') or self.canvas is None:
            return
            
        # 获取canvas_frame的可用尺寸，而不是整个窗口尺寸
        canvas_frame = self.canvas.master
        if not canvas_frame.winfo_exists():
            return
        canvas_frame.update_idletasks()
        frame_width = canvas_frame.winfo_width()
        frame_height = canvas_frame.winfo_height()

        if frame_width <= 1 or frame_height <= 1:
            return
        
        if self.last_window_width == frame_width:
            return

        # 计算缩放比例，让图像在canvas_frame内最大化显示
        width_ratio = frame_width / self.original_width
        height_ratio = frame_height / self.original_height
        scale_ratio = min(width_ratio, height_ratio)  # 取较小的比例，保证图片完全显示在框架内
        
        # 保存当前的显示缩放比例
        self.current_display_scale = scale_ratio

        # 计算缩放后的尺寸
        new_width = int(self.original_width * scale_ratio)
        new_height = int(self.original_height * scale_ratio)

        # 重新缩放背景图像
        resized_image = self.bg_image.resize((new_width, new_height), Image.LANCZOS)

        # 这里保持对图像的引用
        _bg_image = ImageTk.PhotoImage(resized_image)
        self.tk_bg_image = _bg_image

        # 更新 Canvas 的大小，使其与图像大小匹配
        self.canvas.config(width=new_width, height=new_height)

        # 使用grid布局让Canvas在框架中居中，不需要手动计算偏移
        # Canvas已经通过grid布局自动居中，这里不需要place

        # 更新背景图像位置和大小
        if self.bg_image_id:
            self.canvas.itemconfig(self.bg_image_id, image=_bg_image)
        else:
            # 创建背景图像项
            self.bg_image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=_bg_image)
        
        # 檢查是否啟用了放大模式
        if hasattr(self, 'magnifier_enabled') and self.magnifier_enabled and hasattr(self, 'editor_rect') and self.editor_rect:
            # 記住舊的 min_zoom，判斷使用者是否處於 fit 顯示狀態
            old_min_zoom = self.editor_rect.min_zoom
            was_at_fit = abs(self.editor_rect.zoom_scale - old_min_zoom) < 0.01
            # 放大模式：以實際 canvas 尺寸重新計算 fit_scale
            self.editor_rect.calculate_fit_scale(new_width, new_height)
            # 如果使用者原本在 fit 顯示或縮放小於新的 min_zoom，重置為 fit
            if was_at_fit or self.editor_rect.zoom_scale < self.editor_rect.min_zoom:
                self.editor_rect.zoom_scale = self.editor_rect.min_zoom
                self.editor_rect.canvas_offset_x = 0
                self.editor_rect.canvas_offset_y = 0
            # 觸發重新繪製
            self.on_zoom_change()
        else:
            # 非放大模式：使用原有邏輯
            self.update_editor_display_scale()

        self.last_window_width = frame_width
    
    def update_editor_display_scale(self):
        """计算并更新editor_rect的显示缩放比例"""
        if hasattr(self, 'editor_rect') and self.editor_rect is not None and hasattr(self, 'current_display_scale'):
            # 使用update_bg_image中计算的显示缩放比例
            self.editor_rect.update_display_scale(self.current_display_scale)
            print(f"EditorCanvas: 更新显示缩放比例 {self.current_display_scale:.3f}")
    
    def create_vertical_toolbar(self, parent):
        """创建右侧竖向操作条"""
        # 创建操作条框架，宽度与左侧列表一致(200px)，样式与左侧保持一致
        toolbar_frame = tk.Frame(parent, width=200, bg=UIStyle.VERY_LIGHT_BLUE)
        toolbar_frame.grid(row=0, column=1, sticky="ns", padx=5, pady=5)
        toolbar_frame.grid_propagate(False)  # 保持固定宽度

        # 配置右侧工具栏的grid属性
        toolbar_frame.grid_rowconfigure(0, weight=0)  # 标题行，固定高度
        toolbar_frame.grid_rowconfigure(1, weight=1)  # 可滾動按鈕區域，自適應高度
        toolbar_frame.grid_columnconfigure(0, weight=1)  # 单列，占满宽度

        # 添加工具栏标题，样式与左侧列表标题保持一致
        title_label = tk.Label(toolbar_frame, text="工具栏", font=UIStyle.TITLE_FONT, bg=UIStyle.VERY_LIGHT_BLUE, fg=UIStyle.BLACK)
        title_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        # 可滾動的工具列區域：Canvas + Scrollbar
        toolbar_canvas = tk.Canvas(toolbar_frame, bg=UIStyle.VERY_LIGHT_BLUE, highlightthickness=0)
        toolbar_scrollbar = ttk.Scrollbar(toolbar_frame, orient="vertical", command=toolbar_canvas.yview)
        toolbar_canvas.configure(yscrollcommand=toolbar_scrollbar.set)

        toolbar_canvas.grid(row=1, column=0, sticky="nsew")
        toolbar_scrollbar.grid(row=1, column=1, sticky="ns")
        toolbar_frame.grid_columnconfigure(1, weight=0)

        # 按鈕容器放在 Canvas 內部
        button_container = tk.Frame(toolbar_canvas, bg=UIStyle.VERY_LIGHT_BLUE)
        toolbar_canvas_window = toolbar_canvas.create_window((0, 0), window=button_container, anchor="nw")

        # 當按鈕容器大小改變時更新滾動區域
        def _on_button_container_configure(event):
            bbox = toolbar_canvas.bbox("all")
            if bbox:
                # 強制 scrollregion 從 y=0 開始，避免上方出現空白
                toolbar_canvas.configure(scrollregion=(0, 0, bbox[2], bbox[3]))
        button_container.bind('<Configure>', _on_button_container_configure)

        # 當 Canvas 寬度改變時同步按鈕容器寬度
        def _on_toolbar_canvas_configure(event):
            toolbar_canvas.itemconfig(toolbar_canvas_window, width=event.width)
        toolbar_canvas.bind('<Configure>', _on_toolbar_canvas_configure)

        # 在工具列區域內啟用滑鼠滾輪滾動
        def _on_toolbar_mousewheel(event):
            # 內容未超出可視區域時不捲動
            bbox = toolbar_canvas.bbox("all")
            if bbox and (bbox[3] - bbox[1]) <= toolbar_canvas.winfo_height():
                return
            toolbar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        toolbar_canvas.bind('<MouseWheel>', _on_toolbar_mousewheel)
        button_container.bind('<MouseWheel>', _on_toolbar_mousewheel)
        # 為所有子元件遞迴綁定滾輪事件
        def _bind_mousewheel_recursive(widget):
            widget.bind('<MouseWheel>', _on_toolbar_mousewheel)
            for child in widget.winfo_children():
                _bind_mousewheel_recursive(child)
        # 延遲綁定，等所有按鈕建立完成
        self.dialog.after(300, lambda: _bind_mousewheel_recursive(button_container))

        # 配置按钮容器的grid属性，按钮固定高度，不拉伸
        for r in range(18):
            button_container.grid_rowconfigure(r, weight=0)
        button_container.grid_columnconfigure(0, weight=1)  # 单列，占满宽度

        # ========== Row 0: 保存並關閉 + ⓘ ==========
        save_close_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        save_close_frame.grid(row=0, column=0, pady=(0, 3), padx=10, sticky="ew")
        self._save_close_button = tk.Button(
            save_close_frame,
            text="保存並關閉",
            font=UIStyle.BUTTON_FONT,
            height=1,
            bg=UIStyle.SUCCESS_GREEN,
            fg=UIStyle.WHITE,
            relief=UIStyle.BUTTON_RELIEF,
            bd=UIStyle.BUTTON_BORDER_WIDTH,
            command=self.on_window_close
        )
        self._save_close_button.pack(side='left', expand=True, fill='x')
        save_close_info_label = tk.Label(
            save_close_frame, text="ⓘ", font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE, fg=UIStyle.PRIMARY_BLUE, cursor="hand2"
        )
        save_close_info_label.pack(side='left', padx=(4, 0))
        Tooltip(
            save_close_info_label,
            "保存並關閉功能：\n"
            "• 保存目前所有編輯結果\n"
            "• 關閉編輯器並返回主介面\n"
            "• 主介面的熱力圖會即時更新"
        )

        # ========== Row 1: 回到起點 + ⓘ ==========
        reset_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        reset_frame.grid(row=1, column=0, pady=(0, 3), padx=10, sticky="ew")
        self._reset_button = tk.Button(
            reset_frame,
            text="回到起點",
            font=UIStyle.BUTTON_FONT,
            height=1,
            bg=UIStyle.GRAY,
            fg=UIStyle.DARK_GRAY,
            relief=UIStyle.BUTTON_RELIEF,
            bd=UIStyle.BUTTON_BORDER_WIDTH,
            command=self.on_reset,
            state=tk.DISABLED
        )
        self._reset_button.pack(side='left', expand=True, fill='x')
        reset_info_label = tk.Label(
            reset_frame, text="ⓘ", font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE, fg=UIStyle.PRIMARY_BLUE, cursor="hand2"
        )
        reset_info_label.pack(side='left', padx=(4, 0))
        Tooltip(
            reset_info_label,
            "回到起點功能：\n"
            "• 無視任何編輯與保存結果，直接恢復為溫度篩選後的原始辨識狀態\n"
            "• 即使關閉編輯器後重新開啟，仍可恢復至最初辨識的完整元器件列表\n"
            "• 此操作會清除所有修改紀錄"
        )

        # ========== Row 2: 回到上一步 + ⓘ ==========
        undo_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        undo_frame.grid(row=2, column=0, pady=(0, 3), padx=10, sticky="ew")
        self._undo_button = tk.Button(
            undo_frame,
            text="回到上一步 (0/3)",
            font=UIStyle.BUTTON_FONT,
            height=1,
            bg=UIStyle.GRAY,
            fg=UIStyle.BLACK,
            relief=UIStyle.BUTTON_RELIEF,
            bd=UIStyle.BUTTON_BORDER_WIDTH,
            command=self.on_undo,
            state=tk.DISABLED
        )
        self._undo_button.pack(side='left', expand=True, fill='x')
        undo_info_label = tk.Label(
            undo_frame, text="ⓘ", font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE, fg=UIStyle.PRIMARY_BLUE, cursor="hand2"
        )
        undo_info_label.pack(side='left', padx=(4, 0))
        Tooltip(
            undo_info_label,
            "回到上一步功能：\n"
            "• 復原最近一次操作（最多保留 3 步）\n"
            "• 快捷鍵：Ctrl+Z"
        )

        # ========== Row 3: 已選取 N 個 提示標籤 ==========
        self.selection_count_label = tk.Label(
            button_container,
            text="",
            font=("Arial", 9, "bold"),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE
        )
        self.selection_count_label.grid(row=3, column=0, pady=(2, 2), padx=10, sticky="w")

        # ========== Row 4: 合併 + ⓘ ==========
        merge_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        merge_frame.grid(row=4, column=0, pady=(0, 3), padx=10, sticky="ew")
        self.merge_button = tk.Button(
            merge_frame,
            text="合并 ➕",
            font=UIStyle.BUTTON_FONT,
            height=1,
            bg=UIStyle.GRAY,
            fg=UIStyle.DARK_GRAY,
            relief=UIStyle.BUTTON_RELIEF,
            bd=UIStyle.BUTTON_BORDER_WIDTH,
            command=self.on_merge_rects,
            state=tk.DISABLED
        )
        self.merge_button.pack(side='left', expand=True, fill='x')
        merge_info_label = tk.Label(
            merge_frame, text="ⓘ", font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE, fg=UIStyle.PRIMARY_BLUE, cursor="hand2"
        )
        merge_info_label.pack(side='left', padx=(4, 0))
        Tooltip(
            merge_info_label,
            "合併功能：\n"
            "• 將多選的元器件合併為一個\n"
            "• 需先選取 2 個以上元器件"
        )

        # ========== Row 5: 刪除 + ⓘ ==========
        delete_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        delete_frame.grid(row=5, column=0, pady=(0, 3), padx=10, sticky="ew")
        self.delete_button = tk.Button(
            delete_frame,
            text="删除 ❌",
            font=UIStyle.BUTTON_FONT,
            height=1,
            bg=UIStyle.GRAY,
            fg=UIStyle.DARK_GRAY,
            relief=UIStyle.BUTTON_RELIEF,
            bd=UIStyle.BUTTON_BORDER_WIDTH,
            command=self.on_delete_rect,
            state=tk.DISABLED
        )
        self.delete_button.pack(side='left', expand=True, fill='x')
        delete_info_label = tk.Label(
            delete_frame, text="ⓘ", font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE, fg=UIStyle.PRIMARY_BLUE, cursor="hand2"
        )
        delete_info_label.pack(side='left', padx=(4, 0))
        Tooltip(
            delete_info_label,
            "刪除功能：\n"
            "• 刪除選取的元器件\n"
            "• 快捷鍵：Delete / BackSpace"
        )

        # ========== Row 6: 形狀轉換標籤 + ⓘ ==========
        shape_label_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        shape_label_frame.grid(row=6, column=0, pady=(8, 2), padx=10, sticky="w")

        shape_label = tk.Label(
            shape_label_frame,
            text="形狀轉換",
            font=("Arial", 9),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.DARK_GRAY
        )
        shape_label.pack(side=tk.LEFT)

        shape_info_label = tk.Label(
            shape_label_frame,
            text=" ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        shape_info_label.pack(side=tk.LEFT, padx=(2, 0))

        Tooltip(
            shape_info_label,
            "形狀轉換功能：\n"
            "• 矩形 ↔ 圓形 互相轉換\n"
            "• 圓點：縮為極小標記點，僅顯示名稱與溫度\n"
            "• 轉換後會重新查找圈選形狀範圍內的最高溫度\n"
            "• 圓形只計算圓形內部的溫度點（排除四角）\n"
            "• 支援多選批次轉換",
            delay=200
        )

        # ========== Row 7: 矩形 + 圓形 + 圓點（同一列） ==========
        shape_btn_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        shape_btn_frame.grid(row=7, column=0, pady=(0, 3), padx=10, sticky="ew")

        self.convert_to_rect_button = tk.Button(
            shape_btn_frame,
            text="矩形 ⬜",
            font=("Arial", 8),
            width=6,
            height=1,
            bg=UIStyle.GRAY,
            fg=UIStyle.DARK_GRAY,
            relief=UIStyle.BUTTON_RELIEF,
            bd=UIStyle.BUTTON_BORDER_WIDTH,
            command=lambda: self.on_convert_shape("rectangle"),
            state=tk.DISABLED
        )
        self.convert_to_rect_button.pack(side='left', expand=True, fill='x', padx=(0, 2))

        self.convert_to_circle_button = tk.Button(
            shape_btn_frame,
            text="圓形 ⚪",
            font=("Arial", 8),
            width=6,
            height=1,
            bg=UIStyle.GRAY,
            fg=UIStyle.DARK_GRAY,
            relief=UIStyle.BUTTON_RELIEF,
            bd=UIStyle.BUTTON_BORDER_WIDTH,
            command=lambda: self.on_convert_shape("circle"),
            state=tk.DISABLED
        )
        self.convert_to_circle_button.pack(side='left', expand=True, fill='x', padx=(2, 2))

        self.convert_to_dot_button = tk.Button(
            shape_btn_frame,
            text="圓點 •",
            font=("Arial", 8),
            width=6,
            height=1,
            bg=UIStyle.GRAY,
            fg=UIStyle.DARK_GRAY,
            relief=UIStyle.BUTTON_RELIEF,
            bd=UIStyle.BUTTON_BORDER_WIDTH,
            command=lambda: self.on_convert_shape("dot"),
            state=tk.DISABLED
        )
        self.convert_to_dot_button.pack(side='left', expand=True, fill='x', padx=(2, 0))

        # ========== Row 8: 名稱位置標籤 + ⓘ ==========
        name_dir_label_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        name_dir_label_frame.grid(row=8, column=0, pady=(8, 2), padx=10, sticky="w")

        name_dir_label = tk.Label(
            name_dir_label_frame,
            text="名稱位置",
            font=("Arial", 9),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.DARK_GRAY
        )
        name_dir_label.pack(side=tk.LEFT)

        name_dir_info_label = tk.Label(
            name_dir_label_frame,
            text=" ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        name_dir_info_label.pack(side=tk.LEFT, padx=(2, 0))
        Tooltip(
            name_dir_info_label,
            "名稱文字位置功能：\n"
            "• 設定元器件名稱相對於框線的方向\n"
            "• 點擊八個方位按鈕即可調整\n"
            "• 中心為框線位置（不可點擊）\n"
            "• 支援多選批次設定",
            delay=200
        )

        # ========== Row 9: 名稱位置九宮格 ==========
        name_grid_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        name_grid_frame.grid(row=9, column=0, pady=(2, 5), padx=10)

        name_dir_map = [
            ("↖", "TL", 0, 0), ("↑", "T", 0, 1), ("↗", "TR", 0, 2),
            ("←", "L",  1, 0), ("■", None, 1, 1), ("→", "R",  1, 2),
            ("↙", "BL", 2, 0), ("↓", "B", 2, 1), ("↘", "BR", 2, 2),
        ]

        self.name_dir_buttons = {}
        self.current_name_dir = None

        for label, code, r, c in name_dir_map:
            if code is None:
                center_label = tk.Label(
                    name_grid_frame, text=label, width=3, height=1,
                    font=("Arial", 14),
                    bg=UIStyle.GRAY, fg=UIStyle.DARK_GRAY,
                    relief=tk.SUNKEN, bd=1
                )
                center_label.grid(row=r, column=c, padx=1, pady=1)
            else:
                btn = tk.Button(
                    name_grid_frame, text=label, width=3, height=1,
                    font=("Arial", 12),
                    bg=UIStyle.WHITE, fg=UIStyle.BLACK,
                    relief=tk.RAISED, bd=1,
                    command=lambda d=code: self.on_name_dir_click(d),
                    state=tk.DISABLED
                )
                btn.grid(row=r, column=c, padx=1, pady=1)
                self.name_dir_buttons[code] = btn

        # ========== Row 10: 溫度位置標籤 + ⓘ ==========  (was Row 9)
        temp_dir_label_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        temp_dir_label_frame.grid(row=10, column=0, pady=(8, 2), padx=10, sticky="w")

        temp_dir_label = tk.Label(
            temp_dir_label_frame,
            text="溫度位置",
            font=("Arial", 9),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.DARK_GRAY
        )
        temp_dir_label.pack(side=tk.LEFT)

        temp_dir_info_label = tk.Label(
            temp_dir_label_frame,
            text=" ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        temp_dir_info_label.pack(side=tk.LEFT, padx=(2, 0))
        Tooltip(
            temp_dir_info_label,
            "溫度文字位置功能：\n"
            "• 設定溫度數值相對於三角形標記的方向\n"
            "• 點擊八個方位按鈕即可調整\n"
            "• 中心為三角形位置（不可點擊）\n"
            "• 支援多選批次設定",
            delay=200
        )

        # ========== Row 11: 溫度位置九宮格 ==========  (was Row 10)
        grid_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        grid_frame.grid(row=11, column=0, pady=(2, 5), padx=10)

        dir_map = [
            ("↖", "TL", 0, 0), ("↑", "T", 0, 1), ("↗", "TR", 0, 2),
            ("←", "L",  1, 0), ("▲", None, 1, 1), ("→", "R",  1, 2),
            ("↙", "BL", 2, 0), ("↓", "B", 2, 1), ("↘", "BR", 2, 2),
        ]

        self.temp_dir_buttons = {}
        self.current_temp_dir = None

        btn_size = 40
        for label, code, r, c in dir_map:
            if code is None:
                center_label = tk.Label(
                    grid_frame, text=label, width=3, height=1,
                    font=("Arial", 14),
                    bg=UIStyle.GRAY, fg=UIStyle.DARK_GRAY,
                    relief=tk.SUNKEN, bd=1
                )
                center_label.grid(row=r, column=c, padx=1, pady=1)
            else:
                btn = tk.Button(
                    grid_frame, text=label, width=3, height=1,
                    font=("Arial", 12),
                    bg=UIStyle.WHITE, fg=UIStyle.BLACK,
                    relief=tk.RAISED, bd=1,
                    command=lambda d=code: self.on_temp_dir_click(d),
                    state=tk.DISABLED
                )
                btn.grid(row=r, column=c, padx=1, pady=1)
                self.temp_dir_buttons[code] = btn

        # ========== Row 13: 旋轉角度標籤 + ⓘ ==========  (was Row 11)
        rotation_label_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        rotation_label_frame.grid(row=13, column=0, pady=(8, 2), padx=10, sticky="w")

        rotation_label = tk.Label(
            rotation_label_frame,
            text="旋轉角度",
            font=("Arial", 9),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.DARK_GRAY
        )
        rotation_label.pack(side=tk.LEFT)

        rotation_info_label = tk.Label(
            rotation_label_frame,
            text=" ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        rotation_info_label.pack(side=tk.LEFT, padx=(2, 0))
        Tooltip(
            rotation_info_label,
            "旋轉角度功能：\n"
            "• 矩形框以幾何中心為軸逆時針旋轉\n"
            "• 點選預設角度或輸入自訂角度\n"
            "• 旋轉後最高溫度會在新區域內重新查找\n"
            "• 圓形不支援旋轉\n"
            "• 支援多選批次旋轉",
            delay=200
        )

        # ========== Row 14: 預設角度按鈕 ==========  (was Row 12)
        rotation_btn_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        rotation_btn_frame.grid(row=14, column=0, pady=(2, 2), padx=10, sticky="ew")

        self.rotation_buttons = {}
        self.current_rotation_angle = 0
        preset_angles = [0, 45, 90, 135]
        for i, a in enumerate(preset_angles):
            btn = tk.Button(
                rotation_btn_frame,
                text=f"{a}°",
                font=("Arial", 9),
                width=4,
                bg=UIStyle.WHITE,
                fg=UIStyle.BLACK,
                relief=tk.RAISED,
                bd=1,
                command=lambda angle=a: self.on_rotation_click(angle),
                state=tk.DISABLED
            )
            btn.pack(side=tk.LEFT, padx=1)
            self.rotation_buttons[a] = btn

        # ========== Row 15: 自訂角度輸入 ==========  (was Row 13)
        custom_rotation_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        custom_rotation_frame.grid(row=15, column=0, pady=(2, 5), padx=10, sticky="ew")

        self.custom_rotation_entry = tk.Entry(
            custom_rotation_frame,
            width=6,
            font=("Arial", 9),
            state=tk.DISABLED
        )
        self.custom_rotation_entry.pack(side=tk.LEFT, padx=(0, 2))

        tk.Label(
            custom_rotation_frame,
            text="°",
            font=("Arial", 9),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.BLACK
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.custom_rotation_apply_btn = tk.Button(
            custom_rotation_frame,
            text="套用",
            font=("Arial", 9),
            bg=UIStyle.SUCCESS_GREEN,
            fg=UIStyle.WHITE,
            relief=tk.RAISED,
            bd=1,
            command=self.on_rotation_custom_apply,
            state=tk.DISABLED
        )
        self.custom_rotation_apply_btn.pack(side=tk.LEFT)

        # ========== Row 16: 放大模式 + ⓘ ==========  (was Row 14)
        magnifier_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        magnifier_frame.grid(row=16, column=0, pady=(8, 8), padx=10, sticky="ew")

        self.magnifier_var = tk.BooleanVar(value=True)
        self.magnifier_checkbox = tk.Checkbutton(
            magnifier_frame,
            text="放大模式",
            variable=self.magnifier_var,
            font=UIStyle.BUTTON_FONT,
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.BLACK,
            activebackground=UIStyle.VERY_LIGHT_BLUE,
            activeforeground=UIStyle.BLACK,
            selectcolor=UIStyle.WHITE,
            command=self.toggle_magnifier_mode
        )
        self.magnifier_checkbox.pack(side='left')

        magnifier_info_label = tk.Label(
            magnifier_frame,
            text="ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        magnifier_info_label.pack(side='left', padx=(2, 0))
        Tooltip(
            magnifier_info_label,
            "放大模式說明：\n"
            "• 勾選後可用滾輪放大/縮小熱力圖\n"
            "• 右鍵拖動可平移檢視區域\n"
            "• 滾輪縮小到最小即回到預設大小\n"
            "• 取消勾選自動恢復預設顯示"
        )

        # ========== Row 17: 溫度座標 + ⓘ ==========  (was Row 15)
        realtime_temp_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        realtime_temp_frame.grid(row=17, column=0, pady=(0, 8), padx=10, sticky="ew")

        self.realtime_temp_var = tk.BooleanVar(value=True)
        self.realtime_temp_checkbox = tk.Checkbutton(
            realtime_temp_frame,
            text="溫度座標",
            variable=self.realtime_temp_var,
            font=UIStyle.BUTTON_FONT,
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.BLACK,
            activebackground=UIStyle.VERY_LIGHT_BLUE,
            activeforeground=UIStyle.BLACK,
            selectcolor=UIStyle.WHITE,
            command=self.toggle_realtime_temp_mode
        )
        self.realtime_temp_checkbox.pack(side='left', anchor='w')

        realtime_temp_info_label = tk.Label(
            realtime_temp_frame,
            text="ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        realtime_temp_info_label.pack(side='left', padx=(2, 0))
        Tooltip(
            realtime_temp_info_label,
            "溫度座標功能說明：\n"
            "勾選後，將滑鼠移動到熱力圖上\n"
            "即可在游標旁邊顯示該位置的溫度與座標\n"
            "格式：溫度(X, Y)\n\n"
            "座標根據溫度篩選設定的起始座標方向計算\n"
            "例如：設定「左下」則左下角為 (0, 0)\n"
            "X 向右遞增、Y 向上遞增\n\n"
            "標籤會自動跟隨游標移動\n"
            "靠近邊界時自動翻轉顯示方向\n"
            "移出熱力圖範圍後會自動隱藏"
        )

        # ========== Row 18: 多選模式 + ⓘ ==========  (was Row 16)
        multi_select_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        multi_select_frame.grid(row=18, column=0, pady=(0, 8), padx=10, sticky="ew")

        self.multi_select_var = tk.BooleanVar(value=True)
        self.multi_select_checkbox = tk.Checkbutton(
            multi_select_frame,
            text="多选模式",
            variable=self.multi_select_var,
            font=UIStyle.BUTTON_FONT,
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.BLACK,
            activebackground=UIStyle.VERY_LIGHT_BLUE,
            activeforeground=UIStyle.BLACK,
            selectcolor=UIStyle.WHITE,
            command=self.toggle_multi_select_mode
        )
        self.multi_select_checkbox.pack(side='left')

        multi_select_info_label = tk.Label(
            multi_select_frame,
            text="ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        multi_select_info_label.pack(side='left', padx=(2, 0))
        Tooltip(
            multi_select_info_label,
            "多選模式說明：\n"
            "• 勾選後可在列表中選取多個元器件\n"
            "• 支援 Ctrl+點擊 逐一加選\n"
            "• 支援 Shift+點擊 範圍選取\n"
            "• 選取多個後可批次轉換形狀或刪除"
        )
        
        # ========== Row 19: 加回元器件 + ⓘ ==========  (was Row 17)
        add_back_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        add_back_frame.grid(row=19, column=0, pady=(0, 8), padx=10, sticky="ew")

        self.add_back_var = tk.BooleanVar(value=False)
        self.add_back_checkbox = tk.Checkbutton(
            add_back_frame,
            text="加回元器件",
            variable=self.add_back_var,
            font=UIStyle.BUTTON_FONT,
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.BLACK,
            activebackground=UIStyle.VERY_LIGHT_BLUE,
            activeforeground=UIStyle.BLACK,
            selectcolor=UIStyle.WHITE,
            command=self.toggle_add_back_mode
        )
        self.add_back_checkbox.pack(side='left')

        add_back_info_label = tk.Label(
            add_back_frame,
            text="ⓘ",
            font=("Arial", 12),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            cursor="hand2"
        )
        add_back_info_label.pack(side='left', padx=(2, 0))
        Tooltip(
            add_back_info_label,
            "加回元器件說明：\n"
            "• 勾選後，移動游標至熱力圖上\n"
            "• 任何不在左側列表中的元器件\n"
            "  都可透過此功能加回\n"
            "• 游標移至對應位置時顯示元器件資訊\n"
            "• 雙擊即可加回熱力圖和列表"
        )

        # ========== Row 20: 加回元器件資訊框 ==========  (was Row 18)
        self.add_back_info_frame = tk.LabelFrame(
            button_container,
            text="可加回元器件(雙擊加回)",
            font=("Arial", 9, "bold"),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.DARK_BLUE,
        )
        self.add_back_info_frame.grid(row=20, column=0, pady=(0, 8), padx=10, sticky="ew")

        # 元器件名稱（大字、藍色）
        self.add_back_name_label = tk.Label(
            self.add_back_info_frame,
            text="",
            font=("Arial", 11, "bold"),
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.DARK_BLUE,
            anchor='w',
        )
        self.add_back_name_label.pack(fill='x', padx=6, pady=(6, 2))

        # 分隔線
        self.add_back_sep = tk.Frame(self.add_back_info_frame, height=1, bg=UIStyle.GRAY)
        self.add_back_sep.pack(fill='x', padx=6, pady=2)

        # 詳細資訊（多行）
        self.add_back_detail_label = tk.Label(
            self.add_back_info_frame,
            text="移動游標至熱力圖\n查看可加回的元器件",
            font=UIStyle.LABEL_FONT,
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.DARK_GRAY,
            justify='left',
            anchor='nw',
            wraplength=160,
        )
        self.add_back_detail_label.pack(fill='x', padx=6, pady=(2, 6))

        # 預設隱藏資訊框
        self.add_back_info_frame.grid_remove()

        # 初始化加回元器件狀態
        self._current_hover_component = None

        # 初始化按钮状态
        self.update_delete_button_state()
        self.update_merge_button_state()

        # 键盘事件已在__init__中绑定，这里不需要重复绑定
    
    def toggle_multi_select_mode(self):
        """切换多选模式"""
        self.multi_select_enabled = self.multi_select_var.get()
        
        # 同步到 editor_rect
        if hasattr(self, 'editor_rect') and self.editor_rect:
            self.editor_rect.multi_select_enabled = self.multi_select_enabled
        
        # 清除当前的多选状态（如果关闭多选模式）
        if not self.multi_select_enabled:
            if len(self.selected_rect_ids) > 0:
                self.selected_rect_ids.clear()
                self.update_delete_button_state()
                # 清除canvas中的高亮
                if hasattr(self, 'editor_rect') and self.editor_rect:
                    self.set_all_rects_unselected()
        
        status = "启用" if self.multi_select_enabled else "禁用"
        print(f"✓ 多选模式已{status}")

    def toggle_add_back_mode(self):
        """切換「加回元器件」模式"""
        if self.add_back_var.get():
            # 每次啟用時重新計算（反映刪除/新增後的最新列表狀態）
            self._compute_excluded_components()
            self.add_back_info_frame.grid()
            self.canvas.bind('<Motion>', self._on_canvas_motion_add_back)
            self.canvas.bind('<Double-Button-1>', self._on_canvas_double_click_add_back)
            self._current_hover_component = None
            print("✓ 加回元器件模式已啟用")
        else:
            self.add_back_info_frame.grid_remove()
            # 恢復 editor_rect 原始的 Motion 與 Double-Click 綁定
            if hasattr(self, 'editor_rect') and self.editor_rect:
                self.canvas.bind('<Motion>', self.editor_rect.on_mouse_move)
                self.canvas.bind('<Double-Button-1>', self.editor_rect.on_double_click)
            else:
                self.canvas.unbind('<Motion>')
                self.canvas.unbind('<Double-Button-1>')
            self._clear_add_back_preview()
            self._current_hover_component = None
            self._reset_add_back_info()
            print("✓ 加回元器件模式已關閉")

    def _canvas_to_image_coords(self, canvas_x, canvas_y):
        """將 Canvas 座標轉換為熱力圖像素座標（共用邏輯）

        Returns:
            tuple|None: (img_x, img_y) 或 None（超出範圍）
        """
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            return None
        if not hasattr(self.editor_rect, 'display_scale'):
            return None

        if (hasattr(self.editor_rect, 'magnifier_mode_enabled') and
                self.editor_rect.magnifier_mode_enabled and
                abs(self.editor_rect.zoom_scale - 1.0) > 0.001):
            img_x = int((canvas_x - self.editor_rect.canvas_offset_x) / self.editor_rect.zoom_scale)
            img_y = int((canvas_y - self.editor_rect.canvas_offset_y) / self.editor_rect.zoom_scale)
        else:
            img_x = int(canvas_x / self.editor_rect.display_scale)
            img_y = int(canvas_y / self.editor_rect.display_scale)

        # 檢查是否在圖像範圍內
        if hasattr(self.editor_rect, 'original_img') and self.editor_rect.original_img:
            img_width, img_height = self.editor_rect.original_img.size
            if img_x < 0 or img_x >= img_width or img_y < 0 or img_y >= img_height:
                return None

        return (img_x, img_y)

    def _on_canvas_motion_add_back(self, event):
        """滑鼠移動時檢測排除元器件並顯示資訊"""
        try:
            canvas_x = event.x
            canvas_y = event.y

            result = self._canvas_to_image_coords(canvas_x, canvas_y)
            if result is None:
                if self._current_hover_component is not None:
                    self._clear_add_back_preview()
                    self._current_hover_component = None
                    self._reset_add_back_info()
                return

            img_x, img_y = result

            # 遍歷排除元器件，檢查座標是否在 bounding box 內
            matched = None
            if hasattr(self, 'excluded_components'):
                for comp in self.excluded_components:
                    if (comp['ar1_left'] <= img_x <= comp['ar1_right'] and
                            comp['ar1_top'] <= img_y <= comp['ar1_bottom']):
                        matched = comp
                        break

            if matched:
                # 避免重複更新相同的元器件
                if self._current_hover_component is not matched:
                    self._current_hover_component = matched
                    # 更新資訊框 — 名稱
                    self.add_back_name_label.config(text=matched['RefDes'])
                    # 更新資訊框 — 詳細資訊
                    desc = matched['Description']
                    detail_lines = [
                        f"Layout元器件中心:",
                        f"({matched['X']}, {matched['Y']})",
                        f"長: {matched['L']}",
                        f"寬: {matched['W']}",
                        f"高: {matched['T']}",
                        f"旋轉: {matched.get('Orient.', 0)}°",
                    ]
                    if desc:
                        detail_lines.append(f"描述:")
                        detail_lines.append(f"{desc}")
                    self.add_back_detail_label.config(
                        text="\n".join(detail_lines), fg=UIStyle.BLACK)

                    # 繪製虛線預覽框
                    self._draw_add_back_preview(matched)
            else:
                if self._current_hover_component is not None:
                    self._clear_add_back_preview()
                    self._current_hover_component = None
                    self._reset_add_back_info()

        except Exception as e:
            print(f"加回元器件 motion 錯誤: {e}")

    def _draw_add_back_preview(self, comp):
        """在 Canvas 上繪製虛線預覽框"""
        self.canvas.delete('add_back_preview')

        # 圖像座標 → Canvas 座標
        if (hasattr(self.editor_rect, 'magnifier_mode_enabled') and
                self.editor_rect.magnifier_mode_enabled and
                abs(self.editor_rect.zoom_scale - 1.0) > 0.001):
            scale = self.editor_rect.zoom_scale
            offset_x = self.editor_rect.canvas_offset_x
            offset_y = self.editor_rect.canvas_offset_y
        else:
            scale = self.editor_rect.display_scale
            offset_x = 0
            offset_y = 0

        cx1 = comp['ar1_left'] * scale + offset_x
        cy1 = comp['ar1_top'] * scale + offset_y
        cx2 = comp['ar1_right'] * scale + offset_x
        cy2 = comp['ar1_bottom'] * scale + offset_y

        orient = comp.get('Orient.', 0)
        if orient and orient != 0:
            from rotation_utils import get_rotated_corners, corners_to_flat
            geo_cx = (cx1 + cx2) / 2
            geo_cy = (cy1 + cy2) / 2
            half_w = (cx2 - cx1) / 2
            half_h = (cy2 - cy1) / 2
            corners = get_rotated_corners(geo_cx, geo_cy, half_w, half_h, orient)
            flat = corners_to_flat(corners)
            self.canvas.create_polygon(
                flat, outline='lime', fill='', width=2, dash=(6, 4),
                tags='add_back_preview'
            )
        else:
            self.canvas.create_rectangle(
                cx1, cy1, cx2, cy2,
                outline='lime', width=2, dash=(6, 4),
                tags='add_back_preview'
            )

    def _on_canvas_double_click_add_back(self, event):
        """雙擊加回元器件"""
        if self._current_hover_component is None:
            return

        comp = self._current_hover_component

        try:
            # 儲存 undo 快照
            self._push_undo()

            # 從 temp_data 取得 bounding box 區域的最高溫及座標
            max_temp_value = 0.0
            max_temp_cx = (comp['ar1_left'] + comp['ar1_right']) // 2
            max_temp_cy = (comp['ar1_top'] + comp['ar1_bottom']) // 2

            if hasattr(self.parent, 'tempALoader') and self.parent.tempALoader:
                temp_data = self.parent.tempALoader.get_tempA()
                if temp_data is not None:
                    y1 = max(0, comp['ar1_top'])
                    y2 = min(temp_data.shape[0], comp['ar1_bottom'] + 1)
                    x1 = max(0, comp['ar1_left'])
                    x2 = min(temp_data.shape[1], comp['ar1_right'] + 1)
                    if y2 > y1 and x2 > x1:
                        region = temp_data[y1:y2, x1:x2]
                        import numpy as np
                        max_idx = np.unravel_index(np.argmax(region), region.shape)
                        max_temp_value = float(region[max_idx])
                        max_temp_cy = y1 + max_idx[0]
                        max_temp_cx = x1 + max_idx[1]

            # 構建 newRect
            newRect = {
                "x1": comp['ar1_left'], "y1": comp['ar1_top'],
                "x2": comp['ar1_right'], "y2": comp['ar1_bottom'],
                "cx": max_temp_cx, "cy": max_temp_cy,
                "max_temp": max_temp_value,
                "name": comp['RefDes'],
                "description": comp['Description'],
                "add_new": True,
                "angle": comp.get('Orient.', 0),
            }

            # 建立矩形並加入列表
            self.editor_rect.add_rect(newRect)
            self.update_rect_list()

            # 從排除列表移除
            self.excluded_components.remove(comp)

            # 清除預覽
            self._clear_add_back_preview()
            self._current_hover_component = None

            # 更新資訊框
            self.add_back_name_label.config(text=f"已加回: {comp['RefDes']}")
            self.add_back_detail_label.config(
                text=f"最高溫: {max_temp_value:.1f}°C",
                fg=UIStyle.SUCCESS_GREEN,
            )

            print(f"✓ 已加回元器件: {comp['RefDes']}（最高溫 {max_temp_value:.1f}°C）")

        except Exception as e:
            print(f"加回元器件失敗: {e}")

    def _clear_add_back_preview(self):
        """清除 Canvas 上的加回元器件虛線預覽框"""
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.delete('add_back_preview')

    def _reset_add_back_info(self):
        """重設資訊框為預設提示狀態"""
        self.add_back_name_label.config(text="")
        self.add_back_detail_label.config(
            text="移動游標至熱力圖\n查看可加回的元器件",
            fg=UIStyle.DARK_GRAY,
        )

    def _add_deleted_to_excluded(self, deleted_names):
        """將被刪除的元器件加入排除列表（若存在於 layout_data 中）"""
        if not deleted_names:
            return
        if not self.layout_query or not hasattr(self.parent, 'layout_data') or not self.parent.layout_data:
            return
        if not hasattr(self, 'excluded_components'):
            self.excluded_components = []

        # 已在排除列表中的名稱（避免重複）
        existing_names = {c['RefDes'] for c in self.excluded_components}

        for comp in self.parent.layout_data:
            refdes = comp['RefDes']
            if refdes not in deleted_names or refdes in existing_names:
                continue

            cr1 = self.layout_query.convert_pcb_to_layout(comp['left'], comp['top'], comp['right'], comp['bottom'])
            if cr1 is None:
                continue
            ar1 = self.layout_query.convert_layout_to_thermal(*cr1)
            if ar1 is None:
                continue

            ar1_left, ar1_top, ar1_right, ar1_bottom = [int(v) for v in ar1]
            self.excluded_components.append({
                'RefDes': refdes,
                'X': comp.get('X', 0), 'Y': comp.get('Y', 0),
                'L': comp.get('L', 0), 'W': comp.get('W', 0), 'T': comp.get('T', 0),
                'Orient.': comp.get('Orient.', 0),
                'Description': comp.get('Description', ''),
                'ar1_left': ar1_left, 'ar1_top': ar1_top,
                'ar1_right': ar1_right, 'ar1_bottom': ar1_bottom,
            })
            print(f"  已加入排除列表: {refdes}")

    def toggle_realtime_temp_mode(self):
        """切換溫度座標顯示模式"""
        self.realtime_temp_enabled = self.realtime_temp_var.get()

        if self.realtime_temp_enabled:
            # 啟用溫度座標顯示 - 綁定滑鼠移動事件到整個對話框
            if hasattr(self, 'dialog') and self.dialog:
                self.dialog.bind('<Motion>', self.on_canvas_motion_show_temp, add='+')
        else:
            # 關閉溫度座標顯示 - 解除綁定
            if hasattr(self, 'dialog') and self.dialog:
                try:
                    self.dialog.unbind('<Motion>')
                except:
                    pass
            # 清除溫度標籤
            if hasattr(self, 'canvas') and hasattr(self, 'temp_label_id') and self.temp_label_id:
                self.canvas.delete(self.temp_label_id)
                self.canvas.delete('temp_label_bg')
                self.temp_label_id = None

    def update_status_label(self, text):
        """更新狀態標籤（已移除UI，此方法保留以避免錯誤）"""
        pass  # 不再顯示調試信息

    def toggle_magnifier_mode(self):
        """切換放大模式"""
        old_enabled = self.magnifier_enabled if hasattr(self, 'magnifier_enabled') else False
        self.magnifier_enabled = self.magnifier_var.get()

        status = "啟用" if self.magnifier_enabled else "關閉"
        print(f"✓ 放大模式已{status}")

        # 在 set_magnifier_mode 重置參數前，先檢查是否真的有放大過
        need_restore = False
        if hasattr(self, 'editor_rect') and self.editor_rect:
            if old_enabled and not self.magnifier_enabled:
                # _zoom_was_active 在 on_zoom_change() 中設為 True
                need_restore = getattr(self, '_zoom_was_active', False)
            self.editor_rect.set_magnifier_mode(self.magnifier_enabled)
            # 啟用放大模式時，以當前 canvas 尺寸重新計算 min_zoom（= display_scale）
            if not old_enabled and self.magnifier_enabled:
                cw = self.canvas.winfo_width()
                ch = self.canvas.winfo_height()
                self.editor_rect.calculate_fit_scale(cw, ch)

        # 只有真的放大過才需要恢復 default 顯示
        if need_restore:
            self._restore_default_view()
            self._zoom_was_active = False

    def _restore_default_view(self):
        """從放大狀態恢復到 default 顯示大小（保留所有編輯狀態）

        on_zoom_change() 期間 canvas.delete("all") 導致所有 canvas item ID 失效，
        此方法透過 update_bg_image() 重建背景圖（使用正確的 current_display_scale），
        再逐一重建所有矩形/圓形標記。
        """
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        # 清空 Canvas（zoom 模式建立的 canvas item 都需要重建）
        self.canvas.delete("all")
        self.bg_image_id = None

        # 繞過 last_window_width guard，強制 update_bg_image 重新執行
        self.last_window_width = -1
        self.update_bg_image()

        # update_bg_image → update_editor_display_scale → redraw_all_rectangles
        # 但 redraw_all_rectangles 用 canvas.coords() 更新已刪除的 item 會靜默失敗
        # 需要用 _redraw_single_rect 重新建立所有標記
        for rect in self.editor_rect.rectangles:
            self.editor_rect._redraw_single_rect(rect)

    # ========== 快照 / 復原系統 ==========

    def _create_snapshot(self):
        """建立目前所有矩形框的純資料快照（不含 Canvas ID）。"""
        import copy
        canvas_id_keys = {
            "rectId", "nameId", "triangleId", "tempTextId",
            "nameOutlineIds", "tempOutlineIds", "triangleOutlineIds",
            "_font_scale",
        }
        return {
            "rectangles": copy.deepcopy([
                {k: v for k, v in r.items() if k not in canvas_id_keys}
                for r in self.editor_rect.rectangles
            ]),
            "add_new_count": self.editor_rect.add_new_count,
            "delete_origin_count": self.editor_rect.delete_origin_count,
            "modify_origin_set": copy.copy(self.editor_rect.modify_origin_set),
        }

    def _push_undo(self):
        """將目前狀態推入復原歷史堆疊（操作前呼叫）。"""
        snapshot = self._create_snapshot()
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > 3:
            self._undo_stack.pop(0)
        self._update_undo_button_state()
        self._update_reset_button_state()

    def on_undo(self):
        """回到上一步：從歷史堆疊彈出最後一筆快照並恢復。"""
        if not self._undo_stack:
            return
        snapshot = self._undo_stack.pop()

        # 恢復矩形資料
        self.editor_rect.restore_from_snapshot(
            snapshot["rectangles"],
            {
                "add_new_count": snapshot["add_new_count"],
                "delete_origin_count": snapshot["delete_origin_count"],
                "modify_origin_set": snapshot["modify_origin_set"],
            },
        )

        # 清空選取狀態
        self.selected_rect_id = None
        self.selected_rect_ids.clear()
        self.update_delete_button_state()

        # 清空篩選條件並恢復灰色提示詞
        self.filter_name_entry.set("")
        self.filter_desc_entry.set("")
        self.filter_temp_entry.set("")

        # 刷新篩選狀態與 Treeview
        self.apply_filters()
        self.update_rect_list()
        self._update_undo_button_state()
        print(f"↩ 回到上一步，剩餘 {len(self._undo_stack)} 步")

    def on_reset(self):
        """回到起點：優先恢復為原始辨識結果，否則恢復為編輯器開啟時的初始狀態。"""
        from tkinter import messagebox
        # 優先使用原始辨識快照（跨 session 恢復）
        target_snapshot = getattr(self, '_origin_snapshot', None) or self._initial_snapshot
        if target_snapshot is None:
            return
        msg = ("將所有元器件恢復為最初辨識的完整結果。\n\n確定要回到起點嗎？"
               if getattr(self, '_origin_snapshot', None)
               else "將所有元器件恢復為編輯器開啟時的初始狀態。\n\n確定要回到起點嗎？")
        result = messagebox.askyesno(
            "確認回到起點",
            msg,
            parent=self.dialog,
        )
        if not result:
            return

        # 恢復快照
        import copy
        snapshot = copy.deepcopy(target_snapshot)
        self.editor_rect.restore_from_snapshot(
            snapshot["rectangles"],
            {
                "add_new_count": snapshot["add_new_count"],
                "delete_origin_count": snapshot["delete_origin_count"],
                "modify_origin_set": snapshot["modify_origin_set"],
            },
        )

        # 清空復原堆疊與選取
        self._undo_stack.clear()
        self.selected_rect_id = None
        self.selected_rect_ids.clear()
        self.update_delete_button_state()

        # 清空篩選條件並恢復灰色提示詞
        self.filter_name_entry.set("")
        self.filter_desc_entry.set("")
        self.filter_temp_entry.set("")

        # 刷新篩選狀態與 Treeview
        self.apply_filters()
        self.update_rect_list()
        self._update_undo_button_state()
        self._update_reset_button_state()
        print("↩ 已回到起點")

    def _update_undo_button_state(self):
        """更新復原按鈕的啟用狀態、計數顯示與顏色。"""
        if not hasattr(self, '_undo_button'):
            return
        n = len(self._undo_stack)
        if n > 0:
            self._undo_button.config(
                text=f"回到上一步 ({n}/3)",
                state=tk.NORMAL,
                bg=UIStyle.SUCCESS_GREEN,
                fg=UIStyle.WHITE,
            )
        else:
            self._undo_button.config(
                text=f"回到上一步 ({n}/3)",
                state=tk.DISABLED,
                bg=UIStyle.GRAY,
                fg=UIStyle.BLACK,
            )

    def _update_reset_button_state(self):
        """更新回到起點按鈕的啟用狀態：有編輯動作或與原始辨識不同時綠色，否則灰色。"""
        if not hasattr(self, '_reset_button'):
            return
        # 有 undo 歷史 代表當次 session 有過編輯動作
        has_edits = len(self._undo_stack) > 0
        # 檢查是否與原始辨識結果不同（跨 session 偵測）
        if not has_edits and getattr(self, '_origin_snapshot', None) is not None:
            origin_names = {r.get('name', '') for r in self._origin_snapshot["rectangles"]}
            current_names = {r.get('name', '') for r in self.editor_rect.rectangles} if hasattr(self, 'editor_rect') and self.editor_rect else {r.get('name', '') for r in self.mark_rect}
            if origin_names != current_names:
                has_edits = True
        if has_edits:
            self._reset_button.config(
                state=tk.NORMAL,
                bg=UIStyle.SUCCESS_GREEN,
                fg=UIStyle.WHITE,
            )
        else:
            self._reset_button.config(
                state=tk.DISABLED,
                bg=UIStyle.GRAY,
                fg=UIStyle.DARK_GRAY,
            )

    def _has_active_filter(self):
        """檢查是否有篩選條件正在生效"""
        if hasattr(self, 'filter_name_entry') and hasattr(self, 'filter_desc_entry') and hasattr(self, 'filter_temp_entry'):
            name_filter = self.filter_name_entry.get().strip()
            desc_filter = self.filter_desc_entry.get().strip()
            temp_filter = self.filter_temp_entry.get().strip()
            return bool(name_filter or desc_filter or temp_filter)
        return False

    def _show_filter_confirm_dialog(self):
        """篩選條件生效時，詢問使用者是否刪除其他。
        Returns:
            None: 無篩選條件（可直接繼續操作）
            True: 使用者選擇「是」（已刪除其他，可繼續操作）
            False: 使用者選擇「否」（已取消篩選，應中止操作）
        """
        if not self._has_active_filter():
            return None

        from tkinter import messagebox
        filtered_count = len(self.filtered_rectangles) if hasattr(self, 'filtered_rectangles') else 0
        total_count = len(self.editor_rect.rectangles) if hasattr(self, 'editor_rect') and self.editor_rect else 0
        delete_count = total_count - filtered_count

        result = messagebox.askyesno(
            "篩選保留",
            f"目前有篩選條件正在生效。\n\n"
            f"篩選保留 {filtered_count} 筆，其餘 {delete_count} 筆。\n\n"
            f"是否要刪除篩選結果以外的元器件？\n\n"
            f"• 是：刪除不符合篩選條件的 {delete_count} 筆元器件\n"
            f"• 否：取消篩選，恢復顯示所有元器件",
            parent=self.dialog,
        )
        if result:
            # 是：執行刪除其他
            self._push_undo()
            all_rects = self.editor_rect.rectangles
            filtered = self.filtered_rectangles if hasattr(self, 'filtered_rectangles') else all_rects
            filtered_ids = set(r.get('rectId') for r in filtered if r.get('rectId'))
            to_delete_ids = [r.get('rectId') for r in all_rects if r.get('rectId') and r.get('rectId') not in filtered_ids]
            if to_delete_ids:
                self.editor_rect.delete_rectangles_by_ids(to_delete_ids)
                for rect_id in to_delete_ids:
                    self.remove_list_item_by_id(rect_id)
                self.selected_rect_id = None
                self.selected_rect_ids.clear()
                self.update_delete_button_state()
            self.filter_name_entry.set("")
            self.filter_desc_entry.set("")
            self.filter_temp_entry.set("")
            self.apply_filters()
            self.update_rect_list()
            self.update_canvas_visibility()
            print(f"✓ 篩選保留後刪除：已刪除 {len(to_delete_ids)} 筆")
            return True
        else:
            # 否：取消篩選，清空輸入框，恢復顯示所有元器件
            self.filter_name_entry.set("")
            self.filter_desc_entry.set("")
            self.filter_temp_entry.set("")
            self.apply_filters()
            self.update_rect_list()
            self.update_canvas_visibility()
            return False

    def _on_right_click_with_filter_check(self, event):
        """右鍵點擊時檢查是否有篩選條件生效，若有則詢問使用者處理方式"""
        if self._show_filter_confirm_dialog() is not None:
            return
        self.editor_rect.on_right_click_start(event)

    def _on_mousewheel_with_filter_check(self, event):
        """滾輪縮放時檢查是否有篩選條件生效，若有則詢問使用者處理方式"""
        # 只在放大鏡模式啟用時才需要攔截（非放大鏡模式滾輪不觸發縮放）
        if not (hasattr(self, 'editor_rect') and self.editor_rect and self.editor_rect.magnifier_mode_enabled):
            return self.editor_rect.on_mouse_wheel(event) if hasattr(self, 'editor_rect') and self.editor_rect else None
        if self._show_filter_confirm_dialog() is not None:
            return "break"
        return self.editor_rect.on_mouse_wheel(event)

    def on_zoom_change(self):
        """縮放變化時的回調，重新繪製 Canvas"""
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        # 標記已進行過縮放操作（供 toggle_magnifier_mode 判斷是否需要恢復）
        self._zoom_was_active = True

        # 獲取縮放變換參數
        transform = self.editor_rect.get_zoom_transform()
        zoom_scale = transform['zoom_scale']
        offset_x = transform['offset_x']
        offset_y = transform['offset_y']

        # 清空 Canvas
        self.canvas.delete("all")

        # 縮放並繪製背景圖像
        scaled_w = int(self.bg_image.width * zoom_scale)
        scaled_h = int(self.bg_image.height * zoom_scale)
        scaled_img = self.bg_image.resize((scaled_w, scaled_h), Image.LANCZOS)
        self.tk_bg_image = ImageTk.PhotoImage(scaled_img)

        self.bg_image_id = self.canvas.create_image(
            offset_x, offset_y,
            anchor="nw",
            image=self.tk_bg_image
        )

        # 重新繪製所有矩形/圓形框（使用 draw_canvas_item）
        from draw_rect import draw_canvas_item
        base_scale = self.current_display_scale if hasattr(self, 'current_display_scale') else 1.0
        self.editor_rect._base_font_scale = base_scale
        for rect in self.editor_rect.rectangles:
            # 應用縮放變換到座標
            transformed_rect = rect.copy()
            transformed_rect["x1"] = rect["x1"] * zoom_scale + offset_x
            transformed_rect["y1"] = rect["y1"] * zoom_scale + offset_y
            transformed_rect["x2"] = rect["x2"] * zoom_scale + offset_x
            transformed_rect["y2"] = rect["y2"] * zoom_scale + offset_y
            transformed_rect["cx"] = rect.get("cx", (rect["x1"] + rect["x2"]) / 2) * zoom_scale + offset_x
            transformed_rect["cy"] = rect.get("cy", (rect["y1"] + rect["y2"]) / 2) * zoom_scale + offset_y

            # 使用 draw_canvas_item 繪製（它會處理形狀類型）
            # font_scale 使用基礎顯示縮放比例，使文字大小不隨放大倍率變化
            rectId, triangleId, tempTextId, nameId = draw_canvas_item(
                self.canvas,
                transformed_rect,
                1.0,  # imageScale = 1.0，因為座標已手動縮放
                (0, 0),  # offset = (0, 0)
                0,  # imageIndex
                font_scale=base_scale  # 字體保持基礎縮放比例，不隨放大而變大
            )

            # 更新原始 rect 的 Canvas ID（含描邊 ID）
            rect["rectId"] = rectId
            rect["triangleId"] = triangleId
            rect["tempTextId"] = tempTextId
            rect["nameId"] = nameId
            rect["tempOutlineIds"] = transformed_rect.get("tempOutlineIds")
            rect["nameOutlineIds"] = transformed_rect.get("nameOutlineIds")
            rect["triangleOutlineIds"] = transformed_rect.get("triangleOutlineIds")

        # 清除錨點和選擇狀態（因為 Canvas ID 已改變）
        if hasattr(self.editor_rect, 'delete_anchors'):
            self.editor_rect.delete_anchors()
        if hasattr(self.editor_rect, 'reset_drag_data'):
            self.editor_rect.reset_drag_data()
        # 清除多選狀態
        if hasattr(self.editor_rect, 'selected_rect_ids'):
            self.editor_rect.selected_rect_ids.clear()
        # 清除單選狀態
        self.selected_rect_id = None
        # 更新按鈕狀態
        if hasattr(self, 'update_delete_button_state'):
            self.update_delete_button_state()

    def on_convert_shape(self, target_shape):
        """轉換選中的形狀

        Args:
            target_shape (str): "rectangle" 或 "circle"
        """
        from tkinter import messagebox

        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        # 獲取選中的項目
        selected_ids = list(self.selected_rect_ids) if self.selected_rect_ids else []
        if self.selected_rect_id and self.selected_rect_id not in selected_ids:
            selected_ids.append(self.selected_rect_id)

        if not selected_ids:
            messagebox.showwarning("提示", "請先選擇要轉換的元器件")
            return

        # 🔥 在轉換前記錄列表索引（而不是 rectId）
        # 因為轉換過程會重新繪製，rectId 會改變，但列表索引不變
        selected_indices = []
        for rect_id in selected_ids:
            for i, rect in enumerate(self.editor_rect.rectangles):
                if rect.get('rectId') == rect_id:
                    selected_indices.append(i)
                    break

        # 執行批次轉換
        self._push_undo()
        converted_count = self.editor_rect.convert_shapes_batch(
            selected_ids, target_shape
        )

        # 更新列表顯示
        self.update_rect_list()

        # 恢復選取狀態（Treeview + Canvas 高亮）
        self._restore_selection_by_indices(selected_indices)

        # 更新形狀按鈕狀態
        self.update_shape_buttons_state()
        # 更新旋轉控制狀態
        self._update_rotation_state_for_selection()

    def update_shape_buttons_state(self):
        """更新形狀轉換按鈕的啟用/禁用狀態與顏色"""
        has_selection = (
            (self.selected_rect_id is not None) or
            (len(self.selected_rect_ids) > 0)
        )

        if has_selection:
            btn_state, bg, fg = tk.NORMAL, UIStyle.SUCCESS_GREEN, UIStyle.WHITE
        else:
            btn_state, bg, fg = tk.DISABLED, UIStyle.GRAY, UIStyle.DARK_GRAY

        if hasattr(self, 'convert_to_rect_button'):
            self.convert_to_rect_button.config(state=btn_state, bg=bg, fg=fg)
        if hasattr(self, 'convert_to_circle_button'):
            self.convert_to_circle_button.config(state=btn_state, bg=bg, fg=fg)
        if hasattr(self, 'convert_to_dot_button'):
            self.convert_to_dot_button.config(state=btn_state, bg=bg, fg=fg)

    # ========== 九宮格溫度位置控制 ==========

    def on_temp_dir_click(self, direction):
        """九宮格方向按鈕點擊事件"""
        # 收集所有選取的 rect_id
        rect_ids = []
        if self.selected_rect_ids:
            rect_ids = list(self.selected_rect_ids)
        elif self.selected_rect_id is not None:
            rect_ids = [self.selected_rect_id]

        if not rect_ids or not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        # 呼叫 editor_rect 設定方向
        self._push_undo()
        self.editor_rect.set_temp_text_dir(rect_ids, direction)

        # 更新九宮格按鈕高亮
        self._update_temp_dir_highlight(direction)

    def _update_temp_dir_highlight(self, direction=None):
        """更新九宮格按鈕的高亮狀態

        Args:
            direction (str|None): 要高亮的方向，None 表示不高亮任何按鈕
        """
        if not hasattr(self, 'temp_dir_buttons'):
            return

        self.current_temp_dir = direction

        for code, btn in self.temp_dir_buttons.items():
            if code == direction:
                btn.config(bg=UIStyle.PRIMARY_BLUE, fg=UIStyle.WHITE)
            else:
                btn.config(bg=UIStyle.WHITE, fg=UIStyle.BLACK)

    def update_temp_dir_buttons_state(self):
        """根據選取狀態更新九宮格按鈕的啟用/禁用和高亮"""
        if not hasattr(self, 'temp_dir_buttons'):
            return

        has_selection = (
            (self.selected_rect_id is not None) or
            (len(self.selected_rect_ids) > 0)
        )

        state = tk.NORMAL if has_selection else tk.DISABLED
        for code, btn in self.temp_dir_buttons.items():
            btn.config(state=state)

        if not has_selection:
            # 無選取：清除高亮
            self._update_temp_dir_highlight(None)
            return

        # 讀取選取元器件的方向
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            self._update_temp_dir_highlight(None)
            return

        rect_ids = []
        if self.selected_rect_ids:
            rect_ids = list(self.selected_rect_ids)
        elif self.selected_rect_id is not None:
            rect_ids = [self.selected_rect_id]

        directions = set()
        for rect in self.editor_rect.rectangles:
            if rect.get("rectId") in rect_ids:
                directions.add(rect.get("temp_text_dir", "T"))

        if len(directions) == 1:
            # 所有選取元器件方向一致：高亮該方向
            self._update_temp_dir_highlight(directions.pop())
        else:
            # 方向不一致：不高亮
            self._update_temp_dir_highlight(None)

    # ========== 九宮格名稱位置控制 ==========

    def on_name_dir_click(self, direction):
        """名稱位置九宮格方向按鈕點擊事件"""
        rect_ids = []
        if self.selected_rect_ids:
            rect_ids = list(self.selected_rect_ids)
        elif self.selected_rect_id is not None:
            rect_ids = [self.selected_rect_id]

        if not rect_ids or not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        self._push_undo()
        self.editor_rect.set_name_text_dir(rect_ids, direction)
        self._update_name_dir_highlight(direction)

    def _update_name_dir_highlight(self, direction=None):
        """更新名稱位置九宮格按鈕的高亮狀態"""
        if not hasattr(self, 'name_dir_buttons'):
            return

        self.current_name_dir = direction

        for code, btn in self.name_dir_buttons.items():
            if code == direction:
                btn.config(bg=UIStyle.PRIMARY_BLUE, fg=UIStyle.WHITE)
            else:
                btn.config(bg=UIStyle.WHITE, fg=UIStyle.BLACK)

    def update_name_dir_buttons_state(self):
        """根據選取狀態更新名稱位置九宮格按鈕的啟用/禁用和高亮"""
        if not hasattr(self, 'name_dir_buttons'):
            return

        has_selection = (
            (self.selected_rect_id is not None) or
            (len(self.selected_rect_ids) > 0)
        )

        state = tk.NORMAL if has_selection else tk.DISABLED
        for code, btn in self.name_dir_buttons.items():
            btn.config(state=state)

        if not has_selection:
            self._update_name_dir_highlight(None)
            return

        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            self._update_name_dir_highlight(None)
            return

        rect_ids = []
        if self.selected_rect_ids:
            rect_ids = list(self.selected_rect_ids)
        elif self.selected_rect_id is not None:
            rect_ids = [self.selected_rect_id]

        directions = set()
        for rect in self.editor_rect.rectangles:
            if rect.get("rectId") in rect_ids:
                directions.add(rect.get("name_text_dir", "T"))

        if len(directions) == 1:
            self._update_name_dir_highlight(directions.pop())
        else:
            self._update_name_dir_highlight(None)

    # ========== 旋轉角度控制 ==========

    def on_rotation_click(self, angle):
        """預設角度按鈕點擊事件"""
        self._apply_rotation(angle)

    def on_rotation_custom_apply(self):
        """自訂角度套用按鈕點擊事件"""
        if not hasattr(self, 'custom_rotation_entry'):
            return
        text = self.custom_rotation_entry.get().strip()
        if not text:
            return
        try:
            angle = float(text)
        except ValueError:
            from tkinter import messagebox
            messagebox.showwarning("提示", "請輸入有效的角度數值")
            return
        self._apply_rotation(angle)

    def _apply_rotation(self, angle):
        """執行旋轉並同步更新 Treeview，並保留選取狀態。

        Args:
            angle (float): 逆時針旋轉角度（度）
        """
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        # 收集選取的 rect_id
        rect_ids = []
        if self.selected_rect_ids:
            rect_ids = list(self.selected_rect_ids)
        elif self.selected_rect_id is not None:
            rect_ids = [self.selected_rect_id]

        if not rect_ids:
            return

        # 記錄選取的矩形在列表中的索引（索引在重繪後不會變，rectId 會變）
        selected_indices = []
        for rect_id in rect_ids:
            for i, rect in enumerate(self.editor_rect.rectangles):
                if rect.get('rectId') == rect_id:
                    selected_indices.append(i)
                    break

        # 呼叫 editor_rect 設定旋轉角度（內部會重繪，rectId 會改變）
        self._push_undo()
        self.editor_rect.set_rotation_angle(rect_ids, angle)

        # 更新旋轉按鈕高亮
        self._update_rotation_button_highlight(angle)

        # 更新左側 Treeview 溫度同步
        self.update_rect_list()

        # 用穩定的索引恢復選取狀態（Treeview + Canvas 高亮）
        self._restore_selection_by_indices(selected_indices)

    def _restore_selection_by_indices(self, indices):
        """用矩形列表索引恢復完整的選取狀態（Treeview + Canvas 高亮）。

        因為旋轉等操作會重繪 Canvas 物件導致 rectId 改變，
        所以用穩定的列表索引來找到新的 rectId 後恢復選取。
        """
        if not indices or not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        # 從穩定索引取得新的 rectId
        new_rect_ids = []
        for idx in indices:
            if 0 <= idx < len(self.editor_rect.rectangles):
                rect = self.editor_rect.rectangles[idx]
                rect_id = rect.get('rectId')
                if rect_id:
                    new_rect_ids.append(rect_id)

        if not new_rect_ids:
            return

        try:
            if len(new_rect_ids) == 1:
                # 單選：恢復 Treeview 選取 + Canvas 高亮 + 錨點
                rect_id = new_rect_ids[0]
                self.selected_rect_id = rect_id
                self.selected_rect_ids.clear()

                item_id = str(indices[0])
                if hasattr(self, 'tree') and self.tree and self.tree.exists(item_id):
                    self.tree.selection_set(item_id)
                    self.tree.see(item_id)

                self.highlight_rect_in_canvas(rect_id)
            else:
                # 多選：恢復 Treeview 選取 + Canvas 高亮（無錨點）
                self.selected_rect_id = None
                self.selected_rect_ids = set(new_rect_ids)

                if hasattr(self, 'tree') and self.tree:
                    for idx in indices:
                        item_id = str(idx)
                        if self.tree.exists(item_id):
                            self.tree.selection_add(item_id)

                self.highlight_multiple_rects_in_canvas(new_rect_ids)

            # 更新刪除按鈕狀態
            self.update_delete_button_state()
        except Exception as e:
            print(f"✗ 恢復選取狀態時出錯: {e}")

    def _update_rotation_button_highlight(self, angle=None):
        """更新旋轉按鈕的高亮狀態"""
        if not hasattr(self, 'rotation_buttons'):
            return

        self.current_rotation_angle = angle

        for a, btn in self.rotation_buttons.items():
            if btn.cget('state') == tk.DISABLED:
                continue
            if angle is not None and abs(a - angle) < 0.01:
                btn.config(bg=UIStyle.PRIMARY_BLUE, fg=UIStyle.WHITE)
            else:
                btn.config(bg=UIStyle.WHITE, fg=UIStyle.BLACK)

    def _update_rotation_state_for_selection(self):
        """根據目前選取的元器件更新旋轉控制的啟用/停用和角度高亮。"""
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            self.update_rotation_ui_state(False)
            return

        # 收集選取的 rect_id
        rect_ids = []
        if self.selected_rect_ids:
            rect_ids = list(self.selected_rect_ids)
        elif self.selected_rect_id is not None:
            rect_ids = [self.selected_rect_id]

        if not rect_ids:
            self.update_rotation_ui_state(False)
            return

        # 檢查是否全部都是圓形（圓形不支援旋轉）
        all_circle = True
        angles = set()
        for rect in self.editor_rect.rectangles:
            if rect.get("rectId") in rect_ids:
                if rect.get("shape", "rectangle") != "circle":
                    all_circle = False
                    angles.add(rect.get("angle", 0))

        if all_circle:
            self.update_rotation_ui_state(False)
            return

        # 如果所有非圓形元器件角度一致，高亮該角度
        if len(angles) == 1:
            self.update_rotation_ui_state(True, angles.pop())
        else:
            self.update_rotation_ui_state(True, None)

    def update_rotation_ui_state(self, enable, current_angle=None):
        """啟用/停用旋轉控制

        Args:
            enable (bool): True=啟用, False=停用
            current_angle (float|None): 目前選取元器件的旋轉角度
        """
        state = tk.NORMAL if enable else tk.DISABLED

        if hasattr(self, 'rotation_buttons'):
            for btn in self.rotation_buttons.values():
                btn.config(state=state)
                if not enable:
                    btn.config(bg=UIStyle.WHITE, fg=UIStyle.BLACK)

        if hasattr(self, 'custom_rotation_entry'):
            self.custom_rotation_entry.config(state=state)
        if hasattr(self, 'custom_rotation_apply_btn'):
            self.custom_rotation_apply_btn.config(state=state)

        if enable:
            self._update_rotation_button_highlight(current_angle)
        else:
            self._update_rotation_button_highlight(None)

    def _get_pcb_params(self):
        """取得 PCB 物理尺寸與座標原點設定。
        Returns: (p_w, p_h, p_origin)
        """
        if hasattr(self, '_pcb_params_cache'):
            return self._pcb_params_cache

        p_w, p_h, p_origin = 100.0, 80.0, "左下"
        if hasattr(self, 'parent') and hasattr(self.parent, 'get_pcb_config'):
            pcb_config = self.parent.get_pcb_config()
            p_w = pcb_config.get('p_w', 100.0)
            p_h = pcb_config.get('p_h', 80.0)
            p_origin = pcb_config.get('p_origin', '左下')
        elif hasattr(self, 'parent') and hasattr(self.parent, 'temp_config') and self.parent.temp_config:
            config = self.parent.temp_config
            p_w = config.get('p_w', 100.0)
            p_h = config.get('p_h', 80.0)
            p_origin = config.get('p_origin', '左下')

        self._pcb_params_cache = (p_w, p_h, p_origin)
        return self._pcb_params_cache

    def _pixel_to_physical_coord(self, img_x, img_y):
        """將熱力圖像素座標轉換為資料座標。
        座標值直接對應溫度資料的儲存格位置（像素座標）。
        根據 temp_config 的 p_origin 設定決定座標系方向。
        Returns: (x, y) or None
        """
        if not hasattr(self, 'bg_image') or not self.bg_image:
            return None
        img_width, img_height = self.bg_image.size
        if img_width == 0 or img_height == 0:
            return None

        _, _, p_origin = self._get_pcb_params()

        if p_origin == "左下":
            x = img_x
            y = img_height - 1 - img_y
        elif p_origin == "左上":
            x = img_x
            y = img_y
        elif p_origin == "右下":
            x = img_width - 1 - img_x
            y = img_height - 1 - img_y
        elif p_origin == "右上":
            x = img_width - 1 - img_x
            y = img_y
        else:
            x = img_x
            y = img_height - 1 - img_y

        return (x, y)

    def on_canvas_motion_show_temp(self, event):
        """滑鼠移動時顯示溫度座標"""
        if not hasattr(self, 'realtime_temp_enabled') or not self.realtime_temp_enabled:
            return

        try:
            # 檢查滑鼠是否在 canvas 上
            if not hasattr(self, 'canvas') or not self.canvas:
                return

            # 將對話框座標轉換為 canvas 座標
            try:
                canvas_x_root = self.canvas.winfo_rootx()
                canvas_y_root = self.canvas.winfo_rooty()
                event_x_root = event.x_root
                event_y_root = event.y_root

                # 計算相對於 canvas 的座標
                canvas_x = event_x_root - canvas_x_root
                canvas_y = event_y_root - canvas_y_root

                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()

                # 檢查是否在 canvas 範圍內
                if canvas_x < 0 or canvas_y < 0 or canvas_x > canvas_width or canvas_y > canvas_height:
                    # 滑鼠不在 canvas 上，隱藏溫度標籤
                    if hasattr(self, 'temp_label_id') and self.temp_label_id:
                        self.canvas.delete(self.temp_label_id)
                        self.canvas.delete('temp_label_bg')
                        self.temp_label_id = None
                    return

            except Exception:
                return

            # 轉換為圖像座標
            if not hasattr(self, 'editor_rect') or not self.editor_rect:
                return

            # 獲取縮放比例
            if not hasattr(self.editor_rect, 'display_scale'):
                return

            # 計算圖像座標（考慮縮放和放大模式）
            if (hasattr(self.editor_rect, 'magnifier_mode_enabled') and
                    self.editor_rect.magnifier_mode_enabled and
                    abs(self.editor_rect.zoom_scale - 1.0) > 0.001):
                # 放大模式：canvas 座標需先減去偏移，再除以 zoom_scale
                img_x = int((canvas_x - self.editor_rect.canvas_offset_x) / self.editor_rect.zoom_scale)
                img_y = int((canvas_y - self.editor_rect.canvas_offset_y) / self.editor_rect.zoom_scale)
            else:
                # 正常模式：canvas 座標除以 display_scale
                img_x = int(canvas_x / self.editor_rect.display_scale)
                img_y = int(canvas_y / self.editor_rect.display_scale)

            # 檢查座標是否在圖像範圍內
            if hasattr(self.editor_rect, 'original_img') and self.editor_rect.original_img:
                img_width, img_height = self.editor_rect.original_img.size
                if img_x < 0 or img_x >= img_width or img_y < 0 or img_y >= img_height:
                    # 超出圖像範圍，隱藏溫度標籤
                    if hasattr(self, 'temp_label_id') and self.temp_label_id:
                        self.canvas.delete(self.temp_label_id)
                        self.canvas.delete('temp_label_bg')
                        self.temp_label_id = None
                    return

            # 獲取該位置的溫度
            temperature = self.get_temperature_at_position(img_x, img_y)

            if temperature is not None:
                # 計算物理座標並顯示溫度座標標籤
                coord = self._pixel_to_physical_coord(img_x, img_y)
                self.show_temp_label(canvas_x, canvas_y, temperature, coord)
            else:
                # 無法獲取溫度，隱藏標籤
                if hasattr(self, 'temp_label_id') and self.temp_label_id:
                    self.canvas.delete(self.temp_label_id)
                    self.canvas.delete('temp_label_bg')
                    self.temp_label_id = None
        except Exception:
            # 靜默處理錯誤，避免干擾使用者操作
            pass

    def on_canvas_leave_hide_temp(self, event):
        """滑鼠離開 Canvas 時隱藏溫度標籤"""
        if hasattr(self, 'temp_label_id') and self.temp_label_id:
            self.canvas.delete(self.temp_label_id)
            self.canvas.delete('temp_label_bg')
            self.temp_label_id = None

    def get_temperature_at_position(self, x, y):
        """獲取指定位置的溫度值"""
        try:
            # 從 parent 的 tempALoader 獲取溫度數據
            if hasattr(self, 'parent') and hasattr(self.parent, 'tempALoader') and self.parent.tempALoader:
                temp_data = self.parent.tempALoader.get_tempA()
                if temp_data is not None:
                    # temp_data 是一個 numpy 數組 [y, x]
                    if 0 <= y < temp_data.shape[0] and 0 <= x < temp_data.shape[1]:
                        temperature = float(temp_data[y, x])
                        return temperature
        except Exception:
            pass

        return None

    def show_temp_label(self, canvas_x, canvas_y, temperature, coord=None):
        """在游標附近顯示溫度座標標籤。
        coord: (x_mm, y_mm) 物理座標，可為 None
        """
        try:
            # 清除舊的標籤和背景
            if hasattr(self, 'temp_label_id') and self.temp_label_id:
                self.canvas.delete(self.temp_label_id)
            self.canvas.delete('temp_label_bg')  # 清除所有舊的背景

            # 組合顯示文字
            if coord:
                temp_text = f"{temperature:.1f}°C({coord[0]}, {coord[1]})"
            else:
                temp_text = f"{temperature:.1f}°C"

            # 估算標籤大小
            text_width = len(temp_text) * 8  # 估算文字寬度
            text_height = 18
            padding = 5
            total_w = text_width + padding * 2
            total_h = text_height + padding * 2

            # 預設偏移：右上方
            offset_x = 15
            offset_y = -25
            label_x = canvas_x + offset_x
            label_y = canvas_y + offset_y

            # 邊界翻轉：右邊超出 → 改左側
            canvas_width = self.canvas.winfo_width()
            if label_x + total_w > canvas_width:
                label_x = canvas_x - offset_x - text_width

            # 邊界翻轉：上方超出 → 改下方
            if label_y - padding < 0:
                label_y = canvas_y + 15

            # 創建背景框
            self.canvas.create_rectangle(
                label_x - padding,
                label_y - padding,
                label_x + text_width + padding,
                label_y + text_height + padding,
                fill="yellow",
                outline="red",
                width=3,
                tags="temp_label_bg"
            )

            # 創建文字標籤
            self.temp_label_id = self.canvas.create_text(
                label_x + text_width // 2,
                label_y + text_height // 2,
                text=temp_text,
                font=("Arial", 12, "bold"),
                fill="red",
                tags="temp_label"
            )

            # 確保標籤在最上層
            self.canvas.tag_raise('temp_label_bg')
            self.canvas.tag_raise('temp_label')

        except Exception:
            pass

    def on_merge_rects(self):
        """合并多个矩形框"""
        print(f"🔗 on_merge_rects被调用，选中了 {len(self.selected_rect_ids)} 个矩形框")
        
        # 检查是否选中了多于1个矩形框
        if len(self.selected_rect_ids) <= 1:
            print("⚠️ 需要选中多于1个矩形框才能合并")
            return
        
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            print("⚠️ EditorRect未初始化，无法合并")
            return
        
        # 调用editor_rect的合并方法
        self._push_undo()
        merged_rect_id = self.editor_rect.merge_rectangles_by_ids(list(self.selected_rect_ids))
        
        if merged_rect_id:
            # 合并成功，更新列表
            self.update_rect_list()
            
            # 选中新合并的矩形框
            self.selected_rect_ids.clear()
            self.selected_rect_id = merged_rect_id
            
            # 🔥 使用 Treeview API 高亮列表中的新矩形框
            # 將 Canvas rectId 轉換為列表索引
            list_index = None
            for i, rect in enumerate(self.editor_rect.rectangles):
                if rect.get('rectId') == merged_rect_id:
                    list_index = i
                    break

            if list_index is not None and hasattr(self, 'tree') and self.tree:
                item_id = str(list_index)
                if self.tree.exists(item_id):
                    # 選取並滾動到該項目
                    self.tree.selection_set(item_id)
                    self.tree.see(item_id)
                    print(f"✓ 合併後已選取列表項 index={list_index}")

            # 高亮canvas中的矩形框并创建锚点
            self.highlight_rect_in_canvas(merged_rect_id)
            
            # 更新按钮状态
            self.update_delete_button_state()
            
            # 确保对话框可以接收键盘事件
            self.dialog.focus_set()
            
            print(f"✓ 合并成功，新矩形框ID: {merged_rect_id}")
        else:
            print("✗ 合并失败")
    
    def on_delete_rect(self, event=None):
        """删除矩形框按钮点击事件或键盘Delete键事件"""
        # 🔥 若鍵盤事件來自文字輸入框（篩選框等），不執行刪除
        if event and hasattr(event, 'widget') and event.widget:
            if isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text)):
                return

        # 检查是否有选中的矩形框（支持单选和多选）
        if not self.selected_rect_id and len(self.selected_rect_ids) == 0:
            print("⚠️⚠️⚠️ 没有选中的矩形框，无法删除")
            return
            
        print(f"🔍🔍🔍 检查editor_rect: hasattr={hasattr(self, 'editor_rect')}")
        if hasattr(self, 'editor_rect'):
            print(f"🔍🔍🔍 editor_rect is not None: {self.editor_rect is not None}")
            
        if hasattr(self, 'editor_rect') and self.editor_rect is not None:
            # 处理多选删除
            if len(self.selected_rect_ids) > 0:
                print(f"🔍🔍🔍 开始批量删除 {len(self.selected_rect_ids)} 个矩形框")

                # 記錄被刪除的元器件名稱（刪除前）
                deleted_names = set()
                for rect in self.editor_rect.rectangles:
                    if rect.get('rectId') in self.selected_rect_ids:
                        deleted_names.add(rect.get('name', ''))

                self._push_undo()
                # 批量删除（內部會觸發 multi_delete 回調，自動更新列表）
                self.editor_rect.delete_rectangles_by_ids(list(self.selected_rect_ids))

                # 若加回元器件模式開啟，將被刪除的元器件加入排除列表
                self._add_deleted_to_excluded(deleted_names)

                # 确保焦点回到对话框
                self.dialog.focus_set()
                return

            # 处理单选删除
            print(f"🔍🔍🔍 开始删除矩形框 {self.selected_rect_id}")

            # 检查矩形框是否存在
            rect_exists = False
            deleted_name = ''
            for rect in self.editor_rect.rectangles:
                if rect.get('rectId') == self.selected_rect_id:
                    rect_exists = True
                    deleted_name = rect.get('name', '')
                    print(f"🔍🔍🔍 找到要删除的矩形框: {rect}")
                    break

            if not rect_exists:
                print(f"⚠️⚠️⚠️ 矩形框 {self.selected_rect_id} 不存在于editor_rect.rectangles中")
                print(f"⚠️⚠️⚠️ 当前所有矩形框: {[r.get('rectId') for r in self.editor_rect.rectangles]}")
                return

            # 删除选中的矩形框（內部會觸發 delete 回調，自動更新列表）
            self._push_undo()
            self.editor_rect.delete_rectangle_by_id(self.selected_rect_id)

            # 若加回元器件模式開啟，將被刪除的元器件加入排除列表
            if deleted_name:
                self._add_deleted_to_excluded({deleted_name})

            # 确保焦点回到对话框
            self.dialog.focus_set()
        else:
            print("⚠️⚠️⚠️ EditorRect未初始化，无法删除")
            print(f"⚠️⚠️⚠️ hasattr(self, 'editor_rect'): {hasattr(self, 'editor_rect')}")
            if hasattr(self, 'editor_rect'):
                print(f"⚠️⚠️⚠️ self.editor_rect: {self.editor_rect}")
    
    def remove_list_item_by_id(self, rect_id):
        """根据矩形框ID删除对应的列表项（Treeview版本）"""
        if not hasattr(self, 'tree'):
            return

        # 在 Treeview 中刪除對應項目（iid 就是 rect_id 的字符串形式）
        try:
            iid = str(rect_id)
            if self.tree.exists(iid):
                self.tree.delete(iid)
                print(f"✓ 已從 Treeview 刪除項目: {iid}")
        except Exception as e:
            print(f"⚠️ 刪除 Treeview 項目時出錯: {e}")
    
    def _update_scroll_region(self):
        """更新滚动区域"""
        try:
            if hasattr(self, 'list_canvas') and self.list_canvas:
                # 更新滚动区域
                self.list_canvas.update_idletasks()
                bbox = self.list_canvas.bbox("all")
                if bbox:
                    self.list_canvas.configure(scrollregion=bbox)
                    print(f"滚动区域已更新: {bbox}")
        except Exception as e:
            print(f"更新滚动区域错误: {e}")
    
    def open_edit_area_dialog(self, rect_id):
        """打开编辑区域对话框"""
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            print("⚠️ EditorRect未初始化，无法打开编辑对话框")
            return
        
        # 查找对应的矩形框
        target_rect = None
        for rect in self.editor_rect.rectangles:
            if rect.get('rectId') == rect_id:
                target_rect = rect
                break
        
        if not target_rect:
            print(f"⚠️ 未找到矩形框 {rect_id}")
            return
        
        # 创建编辑对话框，传递正确的parent（使用self.dialog作为parent）
        from dialog_component_setting import ComponentSettingDialog
        dialog = ComponentSettingDialog(self.dialog, target_rect, lambda new_rect: self.update_rect_from_dialog(rect_id, new_rect))
    
    def update_rect_from_dialog(self, rect_id, new_rect):
        """从编辑对话框更新矩形框"""
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            return
        
        # 更新editor_rect中的矩形框数据
        self._push_undo()
        for rect in self.editor_rect.rectangles:
            if rect.get('rectId') == rect_id:
                rect.update(new_rect)
                break
        
        # 更新列表显示
        self.update_rect_list()
        print(f"✓ 已更新矩形框 {rect_id} 的信息")
    
    def update_title_count(self):
        """更新標題數量顯示（Treeview版本）"""
        # 從 Treeview 獲取當前項目數量
        count = 0
        if hasattr(self, 'tree'):
            count = len(self.tree.get_children())

        # 更新標題標籤
        if hasattr(self, 'title_label'):
            self.title_label.config(text=f"元器件列表({count})")
    
    def toggle_sort_by_name(self):
        """切換按點位名稱排序"""
        if self.sort_mode == "name_asc":
            # 已經是名稱升序，不需要切換（保持當前狀態）
            return
        else:
            # 切換到點位名稱升序
            self.sort_mode = "name_asc"
            self.apply_sort()
            self.update_sort_indicators()

    def toggle_sort_by_temp(self):
        """切換按溫度排序"""
        if self.sort_mode == "temp_desc":
            # 已經是溫度降序，不需要切換（保持當前狀態）
            return
        else:
            # 切換到溫度降序
            self.sort_mode = "temp_desc"
            self.apply_sort()
            self.update_sort_indicators()

    def toggle_sort_by_desc(self):
        """切換按描述排序"""
        if self.sort_mode == "desc_asc":
            # 已經是描述升序，不需要切換（保持當前狀態）
            return
        else:
            # 切換到描述升序
            self.sort_mode = "desc_asc"
            self.apply_sort()
            self.update_sort_indicators()

    def apply_sort(self):
        """應用當前的排序模式"""
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            print("⚠️ EditorRect未初始化，无法排序")
            return

        # 获取当前所有矩形框
        rectangles = self.editor_rect.rectangles
        if not rectangles:
            print("⚠️ 没有矩形框数据，无法排序")
            return

        # 定義排序函數
        if self.sort_mode == "name_asc":
            # 按點位名稱升序排序（A~Z）
            def sort_key(rect):
                return rect.get('name', '').upper()  # 轉大寫以忽略大小寫
            reverse = False
        elif self.sort_mode == "desc_asc":
            # 按描述升序排序（A~Z）
            def sort_key(rect):
                return rect.get('description', '').upper()  # 轉大寫以忽略大小寫
            reverse = False
        elif self.sort_mode == "temp_desc":
            # 按溫度降序排序（大到小）
            def sort_key(rect):
                if 'max_temp' in rect:
                    return rect['max_temp']
                elif 'temp' in rect:
                    return rect['temp']
                else:
                    return 0.0
            reverse = True
        else:
            sort_key = None
            reverse = False

        # 對完整列表排序
        if sort_key:
            sorted_rectangles = sorted(rectangles, key=sort_key, reverse=reverse)
        else:
            sorted_rectangles = rectangles

        # 更新EditorRect中的矩形框順序
        self.editor_rect.rectangles = sorted_rectangles

        # 如果有篩選後的列表，也需要排序
        if hasattr(self, 'filtered_rectangles') and self.filtered_rectangles is not None and len(self.filtered_rectangles) > 0:
            if sort_key:
                self.filtered_rectangles = sorted(self.filtered_rectangles, key=sort_key, reverse=reverse)

        # 重新更新列表
        self.update_rect_list()

    def update_sort_indicators(self):
        """更新排序指示符號（Treeview 表頭）"""
        if not hasattr(self, 'tree'):
            return

        # 更新 Treeview 表頭
        if self.sort_mode == "name_asc":
            self.tree.heading('name', text='點位名稱 ▼')
            self.tree.heading('desc', text='描述')
            self.tree.heading('temp', text='溫度')
        elif self.sort_mode == "desc_asc":
            self.tree.heading('name', text='點位名稱')
            self.tree.heading('desc', text='描述 ▼')
            self.tree.heading('temp', text='溫度')
        elif self.sort_mode == "temp_desc":
            self.tree.heading('name', text='點位名稱')
            self.tree.heading('desc', text='描述')
            self.tree.heading('temp', text='溫度 ▼')
        else:
            self.tree.heading('name', text='點位名稱')
            self.tree.heading('desc', text='描述')
            self.tree.heading('temp', text='溫度')

    # def sort_by_temperature(self):
    #     """按温度降序排序列表（保留此方法以兼容舊代碼）"""
    #     self.sort_mode = "temp_desc"
    #     self.apply_sort()
    #     self.update_sort_indicators()
        
    #     # 恢复选中状态
    #     if current_selected:
    #         self.selected_rect_id = current_selected
    #         # 从配置中读取选中颜色
    #         from config import GlobalConfig
    #         config = GlobalConfig()
    #         selected_color = config.get("heat_selected_color", "#4A90E2")
            
    #         # 重新高亮选中的项
    #         for list_item in self.rect_list_items:
    #             if list_item.get('rect_id') == current_selected:
    #                 list_item['frame'].config(bg=selected_color)
    #                 for child in list_item['frame'].winfo_children():
    #                     if isinstance(child, (tk.Label, tk.Entry)):
    #                         child.config(bg=selected_color, fg='white')
    #                 break
        
    #     # 显示排序结果
    #     temp_list = [f"{r.get('name', 'Unknown')}({get_temperature(r):.1f}°C)" for r in sorted_rectangles[:3]]
    #     print(f"✓ 列表已按温度降序排序: {temp_list}")
    
    def sort_rectangles_by_name_before_close(self):
        """关闭前按器件名称排序矩形框（字母优先、自然排序、不区分大小写）"""
        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            print("⚠️ EditorRect未初始化，无法排序")
            return
            
        # 获取当前所有矩形框
        rectangles = self.editor_rect.rectangles
        if not rectangles:
            print("⚠️ 没有矩形框数据，无需排序")
            return
        
        # 自然排序键：
        # 1) 首字符类别：字母开头=0，数字开头=1，其它=2（字母优先，再数字）
        # 2) 名称分段：将字母与数字拆分，数字按数值比较，字母按不区分大小写比较
        import re

        def split_alpha_num(text):
            # 将字符串拆分为字母块和数字块，例如 'R0402_003' -> ['R', 402, '_', 3]
            parts = re.findall(r"\d+|\D+", text)
            normalized = []
            for p in parts:
                if p.isdigit():
                    # 数字按整数比较
                    normalized.append(int(p))
                else:
                    # 字母及其它按小写比较，保持原次序
                    normalized.append(p.lower())
            return normalized

        def name_key(rect):
            name = rect.get('name') or rect.get('refdes') or ''
            if not name:
                return (3, [])  # 空名最后
            first = name[0]
            if first.isdigit():
                cat = 0  # 数字优先
            elif first.isalpha():
                cat = 1  # 其次字母
            else:
                cat = 2  # 其他最后
            return (cat, split_alpha_num(name))

        sorted_rectangles = sorted(rectangles, key=name_key)
        
        # 更新EditorRect中的矩形框顺序
        self.editor_rect.rectangles = sorted_rectangles
        
        # 显示排序结果
        name_list = [r.get('name', r.get('refdes', 'Unknown')) for r in sorted_rectangles[:3]]
        print(f"✓ 关闭前已按器件名称排序: {name_list}")
    
    def update_delete_button_state(self):
        """更新删除按钮的状态（有选中时可用，无选中时灰色）"""
        if hasattr(self, 'delete_button'):
            # 支持单选和多选两种模式
            has_selection = (self.selected_rect_id is not None) or (len(self.selected_rect_ids) > 0)
            if has_selection:
                # 有选中的矩形框，按钮可用（绿色）
                self.delete_button.config(state='normal', bg=UIStyle.SUCCESS_GREEN, fg=UIStyle.WHITE)
            else:
                # 无选中的矩形框，按钮灰色不可用
                self.delete_button.config(state='disabled', bg=UIStyle.GRAY, fg=UIStyle.DARK_GRAY)

        # 更新已選取數量提示
        self.update_selection_count_label()
        # 同时更新合并按钮、形狀轉換按鈕和溫度位置按鈕狀態
        self.update_merge_button_state()
        self.update_shape_buttons_state()
        self.update_temp_dir_buttons_state()
        self.update_name_dir_buttons_state()

    def update_merge_button_state(self):
        """更新合并按钮的状态（选中>1个矩形框时可用）"""
        if hasattr(self, 'merge_button'):
            # 只有选中多于1个矩形框时才可用
            if len(self.selected_rect_ids) > 1:
                # 有多个选中的矩形框，按钮可用（绿色）
                self.merge_button.config(state='normal', bg=UIStyle.SUCCESS_GREEN, fg=UIStyle.WHITE)
            else:
                # 选中≤1个矩形框，按钮灰色不可用
                self.merge_button.config(state='disabled', bg=UIStyle.GRAY, fg=UIStyle.DARK_GRAY)

    def update_selection_count_label(self):
        """更新已選取數量提示標籤"""
        if not hasattr(self, 'selection_count_label'):
            return
        # 計算選取數量（多選 + 單選）
        count = len(self.selected_rect_ids)
        if count == 0 and self.selected_rect_id is not None:
            count = 1
        if count > 0:
            self.selection_count_label.config(text=f"已選取 {count} 個")
        else:
            self.selection_count_label.config(text="")

    def on_filter_changed(self, event=None):
        """篩選條件變化時的回調"""
        # 應用篩選並重新顯示列表
        self.apply_filters()
        self.update_rect_list()

    def apply_filters(self):
        """根據三個篩選條件過濾矩形框列表"""
        # 獲取所有矩形框（未經篩選）
        if hasattr(self, 'editor_rect') and self.editor_rect:
            all_rects = self.editor_rect.rectangles
        elif hasattr(self, 'mark_rect') and self.mark_rect:
            all_rects = self.mark_rect
        else:
            all_rects = []

        # 保存完整列表
        self.all_rectangles = all_rects

        # 獲取三個篩選條件的值
        name_filter = self.filter_name_entry.get().strip().upper() if hasattr(self, 'filter_name_entry') else ""
        desc_filter = self.filter_desc_entry.get().strip().upper() if hasattr(self, 'filter_desc_entry') else ""
        temp_filter = self.filter_temp_entry.get().strip() if hasattr(self, 'filter_temp_entry') else ""

        # 如果所有篩選條件都為空，返回完整列表
        if not name_filter and not desc_filter and not temp_filter:
            self.filtered_rectangles = all_rects
            self._update_delete_others_btn_state(has_filter=False)
            return

        # 根據篩選條件過濾列表
        filtered = []
        for rect in all_rects:
            # 檢查點位名稱篩選（支持多值 OR 匹配）
            if name_filter:
                rect_name = rect.get('name', '').upper()
                name_values = self._parse_multi_values(name_filter)
                # 檢查是否有任一值匹配（OR 邏輯）
                if not any(value in rect_name for value in name_values):
                    continue  # 不符合點位名稱條件，跳過

            # 檢查描述篩選（支持多值 OR 匹配）
            if desc_filter:
                rect_desc = rect.get('description', '').upper()
                desc_values = self._parse_multi_values(desc_filter)
                # 檢查是否有任一值匹配（OR 邏輯）
                if not any(value in rect_desc for value in desc_values):
                    continue  # 不符合描述條件，跳過

            # 檢查溫度篩選
            if temp_filter:
                rect_temp = rect.get('max_temp', 0)
                if not self._check_temperature_condition(rect_temp, temp_filter):
                    continue  # 不符合溫度條件，跳過

            # 通過所有篩選條件，加入結果列表
            filtered.append(rect)

        self.filtered_rectangles = filtered
        self._update_delete_others_btn_state(has_filter=True, filtered_count=len(filtered), total_count=len(all_rects))

    def _update_delete_others_btn_state(self, has_filter=False, filtered_count=0, total_count=0):
        """更新「刪除其他」按鈕狀態：有篩選條件且篩選結果少於全部時才啟用"""
        if not hasattr(self, 'delete_others_btn'):
            return
        if has_filter and filtered_count < total_count:
            self.delete_others_btn.config(state='normal', bg=UIStyle.SUCCESS_GREEN, fg=UIStyle.WHITE)
        else:
            self.delete_others_btn.config(state='disabled', bg=UIStyle.GRAY, fg=UIStyle.DARK_GRAY)

    def on_delete_others(self):
        """刪除篩選結果以外的所有元器件（不在目前列表中的資料都移除）"""
        from tkinter import messagebox

        if not hasattr(self, 'editor_rect') or not self.editor_rect:
            return

        all_rects = self.editor_rect.rectangles
        filtered = self.filtered_rectangles if hasattr(self, 'filtered_rectangles') else all_rects

        # 找出要刪除的項目（不在篩選結果中的）
        filtered_ids = set(r.get('rectId') for r in filtered if r.get('rectId'))
        to_delete_ids = [r.get('rectId') for r in all_rects if r.get('rectId') and r.get('rectId') not in filtered_ids]

        if not to_delete_ids:
            return

        # 確認對話框
        result = messagebox.askyesno(
            "確認刪除",
            f"篩選保留 {len(filtered_ids)} 筆，將刪除其餘 {len(to_delete_ids)} 筆元器件。\n\n確定要刪除嗎？",
            parent=self.dialog
        )
        if not result:
            return

        # 記錄被刪除的元器件名稱（刪除前）
        deleted_names = set()
        for rect in all_rects:
            if rect.get('rectId') in set(to_delete_ids):
                deleted_names.add(rect.get('name', ''))

        # 批量刪除
        self._push_undo()
        self.editor_rect.delete_rectangles_by_ids(to_delete_ids)

        # 若加回元器件模式開啟，將被刪除的元器件加入排除列表
        self._add_deleted_to_excluded(deleted_names)

        # 從 Treeview 移除
        for rect_id in to_delete_ids:
            self.remove_list_item_by_id(rect_id)

        # 清空選中狀態
        self.selected_rect_id = None
        self.selected_rect_ids.clear()
        self.update_delete_button_state()

        # 清空篩選條件並恢復灰色提示詞
        self.filter_name_entry.set("")
        self.filter_desc_entry.set("")
        self.filter_temp_entry.set("")
        self.apply_filters()
        self.update_rect_list()

        # 更新標題數量
        self.update_title_count()

        print(f"✓ 刪除其他：已刪除 {len(to_delete_ids)} 筆，保留 {len(filtered_ids)} 筆")

    def _parse_multi_values(self, input_str):
        """
        解析多值篩選條件（支持逗號分隔）。

        支持的格式：
        - "C","HA"  : 引號包圍的多個值
        - C,HS      : 未引號的多個值
        - C         : 單一值

        Args:
            input_str (str): 輸入字符串

        Returns:
            list: 解析後的值列表（已轉大寫）
        """
        import re

        if not input_str:
            return []

        # 移除前後空白
        input_str = input_str.strip()

        # 嘗試匹配引號包圍的多值格式："C","HA"
        quoted_pattern = r'"([^"]+)"'
        quoted_matches = re.findall(quoted_pattern, input_str)

        if quoted_matches:
            # 找到引號格式，使用引號內的值
            return [v.strip().upper() for v in quoted_matches if v.strip()]

        # 否則按逗號分割（支持 C,HS 格式）
        values = [v.strip().upper() for v in input_str.split(',') if v.strip()]

        return values if values else [input_str.upper()]

    def _check_temperature_condition(self, temp_value, condition_str):
        """
        檢查溫度值是否符合條件式。

        支持的條件式格式：
        - >60   : 大於 60
        - <75   : 小於 75
        - >=60.5: 大於等於 60.5
        - <=70  : 小於等於 70
        - =60   : 等於 60
        - 60    : 等於 60（兼容舊版）

        Args:
            temp_value (float): 要檢查的溫度值
            condition_str (str): 條件式字符串

        Returns:
            bool: 是否符合條件
        """
        import re

        condition_str = condition_str.strip()
        if not condition_str:
            return True

        # 嘗試匹配條件式：運算符 + 數字
        # 支持 >=, <=, >, <, =
        match = re.match(r'^\s*(>=|<=|>|<|=)?\s*([0-9]+\.?[0-9]*)\s*$', condition_str)

        if not match:
            # 無法解析，不符合條件
            return False

        operator = match.group(1) or '='  # 如果沒有運算符，默認為等於
        try:
            threshold = float(match.group(2))
        except ValueError:
            # 無法轉換為數字
            return False

        # 根據運算符進行比較
        if operator == '>':
            return temp_value > threshold
        elif operator == '<':
            return temp_value < threshold
        elif operator == '>=':
            return temp_value >= threshold
        elif operator == '<=':
            return temp_value <= threshold
        elif operator == '=':
            # 等於比較，允許小數點後1位的誤差
            return abs(temp_value - threshold) < 0.1
        else:
            return False

    # def on_search_changed(self, event=None):
    #     """搜索框内容变化时的回调"""
    #     if not hasattr(self, 'search_entry'):
    #         return

    #     search_text = self.search_entry.get().strip().lower()
    #     self.filter_rect_list(search_text)

    # def clear_search(self):
    #     """清除搜索内容"""
    #     if hasattr(self, 'search_entry'):
    #         self.search_entry.clear()
    #         self.filter_rect_list("")

    # def filter_rect_list(self, search_text):
    #     """根据搜索文本过滤矩形框列表（使用 Treeview API）"""
    #     if hasattr(self, 'filter_name_entry'):
    #         current_desc = self.filter_desc_entry.get() if hasattr(self, 'filter_desc_entry') else ""
    #         current_temp = self.filter_temp_entry.get() if hasattr(self, 'filter_temp_entry') else ""
    #         self.filter_name_entry.delete(0, tk.END)
    #         if search_text:
    #             self.filter_name_entry.insert(0, search_text)
    #         self.apply_filter()
    #     else:
    #         self.update_rect_list()
    
    def initialize_layout_query(self):
        """初始化Layout查询器，用于智能识别元器件名称"""
        try:
            print("\n" + "="*80)
            print("🚀 开始初始化Layout查询器...")
            print("="*80)
            print(f"Parent类型: {type(self.parent).__name__}")
            
            # 检查父窗口是否有必要的映射数据
            if not hasattr(self.parent, 'layout_data') or not self.parent.layout_data:
                print("警告：没有Layout数据，无法启用智能元器件识别")
                print(f"layout_data存在: {hasattr(self.parent, 'layout_data')}")
                if hasattr(self.parent, 'layout_data'):
                    print(f"layout_data内容: {self.parent.layout_data}")
                return
            
            if not hasattr(self.parent, 'point_transformer') or self.parent.point_transformer is None:
                print("警告：没有点转换器，无法启用智能元器件识别")
                print(f"point_transformer存在: {hasattr(self.parent, 'point_transformer')}")
                if hasattr(self.parent, 'point_transformer'):
                    print(f"point_transformer内容: {self.parent.point_transformer}")
                return
            
            if not hasattr(self.parent, 'tempALoader') or self.parent.tempALoader is None:
                print("警告：没有温度加载器，无法启用智能元器件识别")
                print(f"tempALoader存在: {hasattr(self.parent, 'tempALoader')}")
                return
            
            # 导入Layout查询器
            try:
                from .layout_temperature_query_optimized import LayoutTemperatureQueryOptimized
            except ImportError:
                from layout_temperature_query_optimized import LayoutTemperatureQueryOptimized
            
            # 获取PCB参数（从父窗口的配置中获取）
            # 尝试从不同的配置源获取PCB参数
            pcb_config = {}
            
            # 方法1：从get_pcb_config方法获取
            if hasattr(self.parent, 'get_pcb_config'):
                pcb_config = self.parent.get_pcb_config()
            # 方法2：从temp_config获取
            elif hasattr(self.parent, 'temp_config') and self.parent.temp_config:
                config_manager = self.parent.temp_config
                pcb_config = {
                    'p_w': config_manager.get('p_w', 100.0),
                    'p_h': config_manager.get('p_h', 80.0),
                    'p_origin': config_manager.get('p_origin', '左下'),
                    'p_origin_offset_x': config_manager.get('p_origin_offset_x', 0),
                    'p_origin_offset_y': config_manager.get('p_origin_offset_y', 0),
                    'c_padding_left': config_manager.get('c_padding_left', 0),
                    'c_padding_top': config_manager.get('c_padding_top', 0),
                    'c_padding_right': config_manager.get('c_padding_right', 0),
                    'c_padding_bottom': config_manager.get('c_padding_bottom', 0),
                }
            
            # 设置默认PCB参数
            p_w = pcb_config.get('p_w', 100.0)  # PCB宽度(mm)
            p_h = pcb_config.get('p_h', 80.0)   # PCB高度(mm)
            p_origin = pcb_config.get('p_origin', '左下')  # 坐标原点
            p_origin_offset_x = pcb_config.get('p_origin_offset_x', 0)  # 原点偏移X
            p_origin_offset_y = pcb_config.get('p_origin_offset_y', 0)  # 原点偏移Y
            c_padding_left = pcb_config.get('c_padding_left', 0)   # Layout图左padding
            c_padding_top = pcb_config.get('c_padding_top', 0)     # Layout图上padding
            c_padding_right = pcb_config.get('c_padding_right', 0) # Layout图右padding
            c_padding_bottom = pcb_config.get('c_padding_bottom', 0) # Layout图下padding
            
            # 获取温度数据
            temp_data = self.parent.tempALoader.get_tempA() if hasattr(self.parent, 'tempALoader') and self.parent.tempALoader else None
            
            # 获取Layout图像（如果有的话）
            layout_image = getattr(self.parent, 'imageB', None)
            
            # 打印配置参数
            print(f"\n📋 PCB配置参数:")
            print(f"  PCB尺寸: {p_w}mm x {p_h}mm")
            print(f"  坐标原点: {p_origin}")
            print(f"  原点偏移: ({p_origin_offset_x}, {p_origin_offset_y})")
            print(f"  Layout图padding: 左={c_padding_left}, 上={c_padding_top}, 右={c_padding_right}, 下={c_padding_bottom}")
            print(f"  Layout数据量: {len(self.parent.layout_data)} 个元器件")
            print(f"  温度数据形状: {temp_data.shape if temp_data is not None else 'None'}")
            print(f"  Layout图像: {layout_image.size if layout_image else 'None'}")
            
            # 创建Layout查询器
            self.layout_query = LayoutTemperatureQueryOptimized(
                layout_data=self.parent.layout_data,
                temp_data=temp_data,
                point_transformer=self.parent.point_transformer,
                p_w=p_w, p_h=p_h, p_origin=p_origin,
                p_origin_offset_x=p_origin_offset_x, p_origin_offset_y=p_origin_offset_y,
                c_padding_left=c_padding_left, c_padding_top=c_padding_top,
                c_padding_right=c_padding_right, c_padding_bottom=c_padding_bottom,
                layout_image=layout_image
            )
            
            print(f"\n✅ Layout查询器初始化成功，已启用智能元器件识别功能")
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"✗ Layout查询器初始化失败: {e}")
            print("将使用默认的矩形框创建方式（显示弹窗）")
            self.layout_query = None

    def show_context_menu(self, event):
        """显示右键选单"""
        print(f">>> show_context_menu 被调用，位置: ({event.x_root}, {event.y_root})")
        context_menu = tk.Menu(self.dialog, tearoff=0)

        # 字体大小调整功能已移至主界面的「设置」对话框
        # 用户可以通过 main.py 的「设置」按钮统一调整字体大小

        # 显示选单（目前为空，可在此添加其他右键菜单选项）
        # context_menu.post(event.x_root, event.y_root)
        print(f">>> 右键选单已禁用（字体设置请使用主界面的「设置」按钮）")

    def on_window_close(self):
        # 篩選條件生效時，詢問使用者是否刪除其他
        if self._has_active_filter():
            result = self._show_filter_confirm_dialog()
            if result is False:
                # 使用者選「否」→ 已取消篩選，中止關閉讓使用者重新檢視
                return

        # 检查editor_rect属性是否存在
        if hasattr(self, 'editor_rect') and self.editor_rect is not None:
            # 关闭前先按器件名称排序
            self.sort_rectangles_by_name_before_close()
            
            # 调用外部的关闭回调方法
            ret = self.editor_rect.get_mark_rect()
            add_new_count, delete_new_count, modify_origin_set = self.editor_rect.get_modify_log_count()
            if self.on_close_callback:
                self.on_close_callback(ret, add_new_count, delete_new_count, modify_origin_set) #编辑窗口与主页面窗口大小不一样，还得转换一次坐标
        else:
            # 如果editor_rect不存在，传递空值
            if self.on_close_callback:
                self.on_close_callback([], 0, 0, set())
        
        # 安全地销毁对话框
        if hasattr(self, 'dialog') and self.dialog is not None:
            self.dialog.destroy()



# 外部传入的回调函数
def on_window_close():
    print("Window is closing, data is being passed!")

if __name__ == "__main__":
    root = tk.Tk()
    # 使用背景图路径和回调函数创建窗口
    mark_rect = []
    app = EditorCanvas(root, image=Image.open("imageA.jpg"), mark_rect=mark_rect, on_close_callback=on_window_close)
    root.mainloop()
