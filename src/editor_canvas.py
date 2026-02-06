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
from PIL import Image, ImageTk, ImageGrab

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

    def __init__(self, parent, image, mark_rect, on_close_callback=None, temp_file_path=None):
        """初始化溫度編輯畫布對話框。

        Args:
            parent (tk.Widget): 父元件
            image (PIL.Image): 背景影像
            mark_rect (list): 元器件標記資料列表
            on_close_callback (callable|None): 視窗關閉時的回呼函式
            temp_file_path (str|None): 溫度資料檔案路徑
        """
        super().__init__()

        self.on_close_callback = on_close_callback
        self.parent = parent
        # 使用深拷贝避免修改主页面的原始数据
        import copy
        self.mark_rect = copy.deepcopy(mark_rect)
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
        dialog.geometry("1500x768")  # 增加宽度以容纳左侧列表
        dialog.bind("<Configure>", self.on_resize)
        dialog.protocol("WM_DELETE_WINDOW", self.on_window_close)

        # 初始化列表相关变量
        self.rect_list_items = []  # 存储列表项
        self.selected_rect_id = None  # 当前选中的矩形ID
        self.selected_rect_ids = set()  # 多选模式下选中的矩形ID集合
        self.multi_select_enabled = False  # 多选模式启用标志（默认关闭）
        self.last_selected_index = None  # 記錄最後一次選中的項目索引（用於 Shift + 點擊範圍選擇）

        # 排序相关变量
        self.sort_mode = "name_asc"  # 排序模式: "name_asc"=名称升序(默认), "temp_desc"=温度降序, "desc_asc"=描述升序

        # 篩選相關變量
        self.all_rectangles = []  # 保存所有矩形框（未經篩選）
        self.filtered_rectangles = []  # 保存篩選後的矩形框

        # 先设置dialog属性
        self.dialog = dialog

        # 创建主框架，使用三列布局：左侧列表 + 中间canvas + 右侧操作条
        main_frame = tk.Frame(dialog)
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 配置dialog的grid属性
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_columnconfigure(0, weight=1)
        
        # 配置列权重：左侧列表固定宽度，中间canvas自适应，右侧操作条固定100px
        main_frame.grid_columnconfigure(0, weight=0)  # 左侧列表，固定宽度
        main_frame.grid_columnconfigure(1, weight=1)  # 中间canvas，自适应
        main_frame.grid_columnconfigure(2, weight=0)  # 右侧操作条，固定宽度
        main_frame.grid_rowconfigure(0, weight=1)

        # 创建左侧列表面板
        self.create_rect_list_panel(main_frame)

        # 创建中间canvas区域，使用grid布局
        canvas_frame = tk.Frame(main_frame, bg='white')  # 白色背景
        canvas_frame.grid(row=0, column=1, sticky="nsew")
        
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
        self.create_vertical_toolbar(main_frame)
        
        # 绑定键盘Delete键和BackSpace键到对话框和Canvas
        print("🔍🔍🔍 绑定Delete键和BackSpace键事件到对话框和Canvas")
        # 尝试多种Delete键事件名称
        self.dialog.bind('<Delete>', self.on_delete_rect)
        self.dialog.bind('<KeyPress-Delete>', self.on_delete_rect)
        self.dialog.bind('<Key-Delete>', self.on_delete_rect)
        self.dialog.bind('<KP_Delete>', self.on_delete_rect)
        # 添加BackSpace键绑定
        self.dialog.bind('<BackSpace>', self.on_delete_rect)
        self.dialog.bind('<KeyPress-BackSpace>', self.on_delete_rect)
        self.canvas.bind('<Delete>', self.on_delete_rect)
        self.canvas.bind('<KeyPress-Delete>', self.on_delete_rect)
        self.canvas.bind('<Key-Delete>', self.on_delete_rect)
        self.canvas.bind('<KP_Delete>', self.on_delete_rect)
        # 添加BackSpace键绑定
        self.canvas.bind('<BackSpace>', self.on_delete_rect)
        self.canvas.bind('<KeyPress-BackSpace>', self.on_delete_rect)
        
        # 添加一个测试事件来验证绑定是否生效
        def test_key(event):
            print(f"🔍🔍🔍 测试按键事件被触发: {event.char}, keysym: {event.keysym}, keycode: {event.keycode}")
            # 检查是否是Delete键或BackSpace键
            if (event.keysym == 'Delete' or event.keycode == 46 or  # Delete键
                event.keysym == 'BackSpace' or event.keycode == 8):  # BackSpace键
                print(f"🔍🔍🔍 检测到删除键！keysym: {event.keysym}, keycode: {event.keycode}")
                self.on_delete_rect(event)
        
        self.dialog.bind('<Key>', test_key)
        self.canvas.bind('<Key>', test_key)
        
        print("🔍🔍🔍 Delete键事件绑定完成")
        
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
        
        # 初始化Layout查询器（用于智能识别元器件名称）
        self.layout_query = None
        self.initialize_layout_query()
        
        # 延迟设置显示缩放比例和更新列表，确保canvas完全初始化
        self.dialog.after(100, self.delayed_initialization)

    def delayed_initialization(self):
        """延迟初始化，确保canvas尺寸正确"""
        # 首先更新背景图像，确保canvas尺寸正确
        self.update_bg_image()
        # 然后设置显示缩放比例
        self.update_editor_display_scale()
        # 同步多选模式状态到 editor_rect
        if hasattr(self, 'editor_rect') and self.editor_rect:
            self.editor_rect.multi_select_enabled = self.multi_select_enabled
        # 應用預設排序（名稱 A~Z）
        self.apply_sort()
        # 最后更新列表（apply_sort 內部已經調用了 update_rect_list，這裡可以移除）
        # self.update_rect_list()

    def create_rect_list_panel(self, parent):
        """创建左侧矩形框列表面板"""
        # 创建左侧面板框架
        left_panel = tk.Frame(parent, width=400, bg=UIStyle.VERY_LIGHT_BLUE)
        left_panel.grid(row=0, column=0, sticky="ns", padx=5, pady=5)
        left_panel.grid_propagate(False)  # 保持固定宽度
        
        # 配置左侧面板的grid属性
        left_panel.grid_rowconfigure(0, weight=0)  # 标题行，固定高度
        left_panel.grid_rowconfigure(1, weight=0)  # 搜索框行，固定高度
        left_panel.grid_rowconfigure(2, weight=0)  # 篩選條件行，固定高度
        left_panel.grid_rowconfigure(3, weight=0)  # 标题欄位行，固定高度
        left_panel.grid_rowconfigure(4, weight=1)  # 滚动区域，自适应高度
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
            "• Shift + 點擊：選擇連續範圍\n"
            "• Ctrl + 點擊：跳選個別項目"
        )

        # 搜索框容器
        search_frame = tk.Frame(left_panel, bg=UIStyle.VERY_LIGHT_BLUE)
        search_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        search_frame.grid_columnconfigure(1, weight=1)  # 输入框占满中间部分
        
        # 搜索图标标签
        search_label = tk.Label(search_frame, text="🔍", font=("Arial", 12), bg=UIStyle.VERY_LIGHT_BLUE, fg=UIStyle.PRIMARY_BLUE)
        search_label.grid(row=0, column=0, sticky="w", padx=(0, 3))  # 减少右边距
        
        # 搜索输入框（使用占位符控件）
        from placeholder_entry import PlaceholderEntry
        self.search_entry = PlaceholderEntry(
            search_frame,
            placeholder="搜索器件名称",
            placeholder_color="gray",
            font=UIStyle.SMALL_FONT
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 3))  # 减少右边距，让输入框占满中间
        
        # 清除搜索按钮（放大）
        clear_button = tk.Button(
            search_frame,
            text="✕",
            font=("Arial", 10, "bold"),
            width=3,
            height=1,
            bg=UIStyle.VERY_LIGHT_BLUE,
            fg=UIStyle.PRIMARY_BLUE,
            relief='flat',
            bd=0,
            command=self.clear_search
        )
        clear_button.grid(row=0, column=2, sticky="e")

        # 绑定搜索事件
        self.search_entry.bind('<KeyRelease>', self.on_search_changed)

        # 篩選條件輸入框框架（在表頭上方）
        filter_frame = tk.Frame(left_panel, bg=UIStyle.VERY_LIGHT_BLUE)
        filter_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))

        # 名稱篩選輸入框（使用 PlaceholderEntry）
        self.filter_name_entry = PlaceholderEntry(
            filter_frame,
            placeholder='輸入"C"',
            placeholder_color="gray",
            font=("Arial", 9),
            width=10,
            bg=UIStyle.WHITE,
            relief="solid",
            bd=1
        )
        self.filter_name_entry.pack(side=tk.LEFT, padx=4, pady=3)
        self.filter_name_entry.bind('<KeyRelease>', self.on_filter_changed)

        # 描述篩選輸入框（使用 PlaceholderEntry）
        self.filter_desc_entry = PlaceholderEntry(
            filter_frame,
            placeholder='輸入"EC"',
            placeholder_color="gray",
            font=("Arial", 9),
            width=12,
            bg=UIStyle.WHITE,
            relief="solid",
            bd=1
        )
        self.filter_desc_entry.pack(side=tk.LEFT, padx=4, pady=3)
        self.filter_desc_entry.bind('<KeyRelease>', self.on_filter_changed)

        # 溫度篩選輸入框（使用 PlaceholderEntry）
        self.filter_temp_entry = PlaceholderEntry(
            filter_frame,
            placeholder='<75',
            placeholder_color="gray",
            font=("Arial", 9),
            width=8,
            bg=UIStyle.WHITE,
            relief="solid",
            bd=1
        )
        self.filter_temp_entry.pack(side=tk.RIGHT, padx=4, pady=3)
        self.filter_temp_entry.bind('<KeyRelease>', self.on_filter_changed)

        # 欄位標頭（名稱和溫度，可點擊排序）
        header_frame = tk.Frame(left_panel, bg=UIStyle.LIGHT_GRAY, relief="solid", bd=1)
        header_frame.grid(row=3, column=0, sticky="ew", pady=(0, 5))

        # 名称欄位標頭（可點擊）- 使用 pack 佈局與列表項對齊
        self.name_header_btn = tk.Button(
            header_frame,
            text="名稱 ▼",
            font=("Arial", 10, "bold"),
            bg=UIStyle.LIGHT_GRAY,
            fg=UIStyle.PRIMARY_BLUE,
            relief="flat",
            bd=0,
            anchor="w",
            width=10,
            command=self.toggle_sort_by_name
        )
        self.name_header_btn.pack(side=tk.LEFT, padx=4, pady=3)

        # 描述欄位標頭（可點擊）- 使用 pack 佈局與列表項對齊
        self.desc_header_btn = tk.Button(
            header_frame,
            text="描述",
            font=("Arial", 10),
            bg=UIStyle.LIGHT_GRAY,
            fg=UIStyle.BLACK,
            relief="flat",
            bd=0,
            anchor="w",
            width=12,
            command=self.toggle_sort_by_desc
        )
        self.desc_header_btn.pack(side=tk.LEFT, padx=4, pady=3)

        # 溫度欄位標頭（可點擊）- 使用 pack 佈局與列表項對齊
        self.temp_header_btn = tk.Button(
            header_frame,
            text="溫度",
            font=("Arial", 10),
            bg=UIStyle.LIGHT_GRAY,
            fg=UIStyle.BLACK,
            relief="flat",
            bd=0,
            anchor="w",
            width=8,
            command=self.toggle_sort_by_temp
        )
        self.temp_header_btn.pack(side=tk.RIGHT, padx=4, pady=3)

        # 创建滚动框架
        scroll_frame = tk.Frame(left_panel, bg=UIStyle.VERY_LIGHT_BLUE)
        scroll_frame.grid(row=4, column=0, sticky="nsew")

        # 创建Canvas和滚动条 - 使用明显的颜色标记滚动条
        self.list_canvas = tk.Canvas(scroll_frame, bg='white', highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_frame, orient="vertical", command=self.list_canvas.yview, 
                                width=20, bg='#ff6b6b', troughcolor='#f0f0f0', 
                                activebackground='#ff4757', highlightbackground='#ff6b6b')
        self.scrollable_frame = tk.Frame(self.list_canvas, bg='white')

        # 配置滚动区域 - 优化性能，减少频繁更新
        def configure_scroll_region(event=None):
            # 延迟更新滚动区域，避免频繁刷新
            if hasattr(self, '_scroll_update_after'):
                self.list_canvas.after_cancel(self._scroll_update_after)
            
            def update_scroll_region():
                try:
                    bbox = self.list_canvas.bbox("all")
                    if bbox:
                        self.list_canvas.configure(scrollregion=bbox)
                        print(f"滚动区域已更新: {bbox}")
                    else:
                        # 如果bbox为空，设置一个默认区域
                        self.list_canvas.configure(scrollregion=(0, 0, 0, 100))
                except Exception as e:
                    print(f"更新滚动区域错误: {e}")
            
            self._scroll_update_after = self.list_canvas.after(50, update_scroll_region)

        self.scrollable_frame.bind("<Configure>", configure_scroll_region)

        self._list_window_id = self.list_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.list_canvas.configure(yscrollcommand=scrollbar.set)

        # 使用grid布局确保滚动条可见
        self.list_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 配置grid权重
        scroll_frame.grid_rowconfigure(0, weight=1)
        scroll_frame.grid_columnconfigure(0, weight=1)
        scroll_frame.grid_columnconfigure(1, weight=0)
        
        # 确保内部窗口宽度自适应
        def on_canvas_configure(e):
            # 自适应内部窗口宽度，同时刷新scrollregion，确保滚动条可拖动
            self.list_canvas.itemconfig(self._list_window_id, width=e.width)
            self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))
        self.list_canvas.bind("<Configure>", on_canvas_configure)

        # 绑定鼠标滚轮事件 - 使用更直接的方法
        # 保存控件引用供后续使用
        self._scroll_widgets = [left_panel, scroll_frame, self.list_canvas, self.scrollable_frame]
        
        # 绑定滚轮事件 - 使用更可靠的方法
        def bind_mousewheel(widget):
            # Windows系统滚轮事件
            widget.bind("<MouseWheel>", self._on_mousewheel)
            # Linux系统滚轮事件  
            widget.bind("<Button-4>", self._on_mousewheel)
            widget.bind("<Button-5>", self._on_mousewheel)
            # 只对主要控件设置焦点，避免频繁切换
            if widget in [self.list_canvas, self.scrollable_frame]:
                def on_enter(e):
                    widget.focus_set()
                widget.bind("<Enter>", on_enter)
        
        # 绑定到所有相关控件
        for widget in self._scroll_widgets:
            bind_mousewheel(widget)
        
        # 额外绑定到整个对话框作为备选
        self._bind_to_dialog_later = True
        
        # 绑定点击空白区域清除选择
        self.list_canvas.bind("<Button-1>", self.on_canvas_click)

        # 移除名称推荐下拉框

        # 初始化列表（應用預設排序：名稱 A~Z）
        # 注意：update_rect_list() 會自動調用 update_sort_indicators()
        self.update_rect_list()

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
        """更新矩形框列表"""
        # 清除现有列表項
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.rect_list_items.clear()

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
        
        for i, rect in enumerate(rectangles):
            self.create_list_item(rect, i)
        
        # 优化滚动区域更新 - 减少白屏问题
        def delayed_scroll_update():
            try:
                self.scrollable_frame.update_idletasks()
                bbox = self.list_canvas.bbox("all")
                if bbox:
                    self.list_canvas.configure(scrollregion=bbox)
                    print(f"列表更新完成，滚动区域: {bbox}")
                else:
                    # 强制计算bbox
                    self.list_canvas.update()
                    bbox = self.list_canvas.bbox("all")
                    if bbox:
                        self.list_canvas.configure(scrollregion=bbox)
            except Exception as e:
                print(f"延迟滚动更新错误: {e}")
        
        # 延迟更新，避免白屏
        self.list_canvas.after(10, delayed_scroll_update)
        
        # 确保所有矩形都是灰色边框（未选中状态）
        self.list_canvas.after(20, self.set_all_rects_unselected)
        
        # 更新标题数量
        try:
            self.title_label.config(text=f"元器件列表({len(rectangles)})")
        except Exception:
            pass
        
        # 应用当前的搜索过滤
        if hasattr(self, 'search_entry'):
            search_text = self.search_entry.get().strip().lower()
            self.filter_rect_list(search_text)

        # 更新排序指示符號
        self.update_sort_indicators()

        # 根據篩選結果更新 Canvas 上的顯示
        self.update_canvas_visibility()

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
                    except:
                        pass
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
                except:
                    pass
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

    def create_list_item(self, rect, index):
        """创建单个列表项"""
        # 创建列表项框架
        item_frame = tk.Frame(self.scrollable_frame, bg=UIStyle.WHITE, relief=tk.RAISED, bd=1)
        item_frame.pack(fill=tk.X, padx=2, pady=1)
        
        # 获取矩形框数据
        rect_name = rect.get('name', f'AR{index+1}')
        max_temp = rect.get('max_temp', 0)
        rect_id = rect.get('rectId', index)
        description = rect.get('description', '')  # 獲取描述資訊

        # 不可编辑的名称标签
        name_label = tk.Label(item_frame, text=rect_name, width=10, font=UIStyle.SMALL_FONT, bg=UIStyle.WHITE, anchor='w')
        name_label.pack(side=tk.LEFT, padx=4, pady=3)

        # 创建描述标签（在名称和温度之间）
        desc_label = tk.Label(item_frame, text=description, width=12, font=UIStyle.SMALL_FONT, bg=UIStyle.WHITE, anchor='w')
        desc_label.pack(side=tk.LEFT, padx=4, pady=3)

        # 创建温度标签
        temp_text = f"{max_temp:.1f}°C"
        temp_label = tk.Label(item_frame, text=temp_text, font=UIStyle.SMALL_FONT, bg=UIStyle.WHITE)
        temp_label.pack(side=tk.RIGHT, padx=4, pady=3)
        
        # 绑定点击事件
        def on_item_click(event, rect_id=rect_id, index=index):
            # 阻止事件冒泡，避免点击触发滚动等副作用
            try:
                event.widget.focus_set()
            except Exception:
                pass

            # 檢測是否按住修飾鍵
            # state & 0x0001 表示 Shift 鍵被按下
            # state & 0x0004 表示 Ctrl 鍵被按下
            shift_pressed = (event.state & 0x0001) != 0
            ctrl_pressed = (event.state & 0x0004) != 0

            if shift_pressed and self.last_selected_index is not None:
                # Shift + 點擊：範圍選擇
                self.select_range(self.last_selected_index, index)
            elif ctrl_pressed:
                # Ctrl + 點擊：跳選（toggle 選中狀態）
                self.toggle_select_item(rect_id, index)
            else:
                # 一般點擊：單選
                self.select_rect_item(rect_id, item_frame)
                self.last_selected_index = index
        
        # 绑定双击事件
        def on_item_double_click(event, rect_id=rect_id):
            self.open_edit_area_dialog(rect_id)
        
        # 绑定事件
        item_frame.bind("<Button-1>", on_item_click)
        item_frame.bind("<Double-Button-1>", on_item_double_click)
        name_label.bind("<Button-1>", on_item_click)
        name_label.bind("<Double-Button-1>", on_item_double_click)
        desc_label.bind("<Button-1>", on_item_click)
        desc_label.bind("<Double-Button-1>", on_item_double_click)
        temp_label.bind("<Button-1>", on_item_click)
        temp_label.bind("<Double-Button-1>", on_item_double_click)

        # 移除下拉按钮

        # 存储列表项信息
        list_item = {
            'frame': item_frame,
            'name_label': name_label,
            'desc_label': desc_label,
            'temp_label': temp_label,
            'rect_id': rect_id
        }
        self.rect_list_items.append(list_item)

    def select_rect_item(self, rect_id, item_frame):
        """选中列表项并高亮对应的矩形框"""
        print(f"🔍🔍🔍 select_rect_item被调用: rect_id={rect_id}")
        # 清除之前的选择（列表与canvas）
        self.clear_all_selections()
        
        # 设置新的选择
        self.selected_rect_id = rect_id
        print(f"🔍🔍🔍 设置selected_rect_id = {self.selected_rect_id}")
        
        # 从配置中读取选中颜色
        from config import GlobalConfig
        config = GlobalConfig()
        selected_color = config.get("heat_selected_color", "#4A90E2")
        
        # 高亮当前选中的列表项
        item_frame.config(bg=selected_color)
        
        # 更新删除按钮状态
        self.update_delete_button_state()
        
        # 确保对话框可以接收键盘事件
        self.dialog.focus_set()
        for child in item_frame.winfo_children():
            if isinstance(child, (tk.Label, tk.Entry)):
                child.config(bg=selected_color, fg='white')
            elif isinstance(child, tk.Button):
                child.config(bg=selected_color, fg='white', activebackground=selected_color, activeforeground='white')
        
        # 确保焦点回到对话框，以便接收Delete键事件
        self.dialog.after(10, lambda: self.dialog.focus_set())
        
        # 高亮canvas中的矩形框，其他清空
        self.highlight_rect_in_canvas(rect_id)
        # 确保选中项滚动到可见区域
        # 不自动滚动到顶部，保持当前滚动位置，避免跳动

    def select_range(self, start_index, end_index):
        """Shift + 點擊：選擇範圍內的所有項目（包含頭尾）"""
        print(f"📋 範圍選擇: 從索引 {start_index} 到 {end_index}")

        # 確保索引順序正確（小 -> 大）
        if start_index > end_index:
            start_index, end_index = end_index, start_index

        # 清除之前的選擇
        self.clear_all_selections()

        # 選擇範圍內的所有項目
        selected_rect_ids = []
        for i in range(start_index, end_index + 1):
            if i < len(self.rect_list_items):
                list_item = self.rect_list_items[i]
                rect_id = list_item['rect_id']
                selected_rect_ids.append(rect_id)

        # 高亮所有選中的項目
        self.select_multiple_rect_items(selected_rect_ids)

        # 更新最後選中的索引
        self.last_selected_index = end_index

    def toggle_select_item(self, rect_id, index):
        """Ctrl + 點擊：跳選（toggle 該項目的選中狀態）"""
        print(f"🔘 跳選: rect_id={rect_id}, index={index}")

        # 從配置中讀取選中顏色
        from config import GlobalConfig
        config = GlobalConfig()
        selected_color = config.get("heat_selected_color", "#4A90E2")

        # 檢查該項目是否已選中
        if rect_id in self.selected_rect_ids:
            # 已選中 -> 取消選中
            self.selected_rect_ids.remove(rect_id)
            print(f"  ➖ 取消選中 {rect_id}")
        else:
            # 未選中 -> 添加選中
            self.selected_rect_ids.add(rect_id)
            print(f"  ➕ 添加選中 {rect_id}")

        # 更新最後選中的索引
        self.last_selected_index = index

        # 更新列表項的視覺效果
        for list_item in self.rect_list_items:
            frame = list_item['frame']
            item_rect_id = list_item['rect_id']

            if item_rect_id in self.selected_rect_ids:
                # 選中狀態：藍色背景
                frame.config(bg=selected_color)
                for child in frame.winfo_children():
                    if isinstance(child, (tk.Label, tk.Entry)):
                        child.config(bg=selected_color, fg='white')
                    elif isinstance(child, tk.Button):
                        child.config(bg=selected_color, fg='white', activebackground=selected_color, activeforeground='white')
            else:
                # 未選中狀態：白色背景
                frame.config(bg='white')
                for child in frame.winfo_children():
                    if isinstance(child, (tk.Label, tk.Entry)):
                        child.config(bg='white', fg='black')
                    elif isinstance(child, tk.Button):
                        child.config(bg='#f0f0f0', fg='black', activebackground='#e0e0e0', activeforeground='black')

        # 更新 canvas 上的高亮效果
        if len(self.selected_rect_ids) > 0:
            self.highlight_multiple_rects_in_canvas(list(self.selected_rect_ids))
        else:
            # 如果沒有選中任何項目，清除所有高亮
            self.set_all_rects_unselected()
            if hasattr(self, 'editor_rect') and self.editor_rect:
                self.editor_rect.delete_anchors()

        # 更新刪除按鈕狀態
        self.update_delete_button_state()

        # 確保焦點回到對話框
        self.dialog.focus_set()

    def select_multiple_rect_items(self, rect_ids):
        """選中多個列表項並高亮對應的矩形框"""
        print(f"🔍 多選模式：選中 {len(rect_ids)} 個項目")

        # 清除之前的選擇
        self.clear_list_selections()

        # 更新選中的 ID 集合
        self.selected_rect_ids = set(rect_ids)

        # 從配置中讀取選中顏色
        from config import GlobalConfig
        config = GlobalConfig()
        selected_color = config.get("heat_selected_color", "#4A90E2")

        # 高亮所有選中的列表項
        for list_item in self.rect_list_items:
            if list_item['rect_id'] in rect_ids:
                frame = list_item['frame']
                frame.config(bg=selected_color)

                for child in frame.winfo_children():
                    if isinstance(child, (tk.Label, tk.Entry)):
                        child.config(bg=selected_color, fg='white')
                    elif isinstance(child, tk.Button):
                        child.config(bg=selected_color, fg='white', activebackground=selected_color, activeforeground='white')

        # 高亮 canvas 中的所有矩形框
        self.highlight_multiple_rects_in_canvas(rect_ids)

        # 更新刪除按鈕狀態
        self.update_delete_button_state()

        # 確保焦點回到對話框
        self.dialog.focus_set()

    def clear_list_selections(self):
        """只清除列表项的选中状态"""
        for list_item in self.rect_list_items:
            frame = list_item['frame']
            frame.config(bg='white')
            for child in frame.winfo_children():
                if isinstance(child, (tk.Label, tk.Entry)):
                    child.config(bg='white', fg='black')
                elif isinstance(child, tk.Button):
                    child.config(bg='#f0f0f0', fg='black', activebackground='#e0e0e0', activeforeground='black')
        
        # 清除选中状态并更新删除按钮（支持单选和多选）
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
            # 从配置中读取矩形框颜色
            from config import GlobalConfig
            config = GlobalConfig()
            rect_color = config.get("heat_rect_color", "#BCBCBC")
            
            # 遍历所有矩形，确保都设置为未选中状态（修复多个蓝色框问题）
            for rect in self.editor_rect.rectangles:
                rect_id = rect.get('rectId')
                if rect_id:
                    try:
                        # 设置为配置的矩形框颜色，宽度2
                        self.canvas.itemconfig(rect_id, outline=rect_color, width=2)
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
            
            # 从配置中读取选中矩形框颜色
            from config import GlobalConfig
            config = GlobalConfig()
            selected_color = config.get("heat_selected_color", "#4A90E2")
            
            # 设置选中矩形为配置的选中颜色边框
            self.canvas.itemconfig(rect_id, outline=selected_color, width=2)
            
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
            
            # 从配置中读取选中矩形框颜色
            from config import GlobalConfig
            config = GlobalConfig()
            selected_color = config.get("heat_selected_color", "#4A90E2")
            
            # 设置选中矩形为配置的选中颜色边框
            self.canvas.itemconfig(rect_id, outline=selected_color, width=2)
            
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

        # 從配置中讀取選中顏色
        from config import GlobalConfig
        config = GlobalConfig()
        selected_color = config.get("heat_selected_color", "#4A90E2")

        # 高亮所有選中的矩形框
        for rect_id in rect_ids:
            self.canvas.itemconfig(rect_id, outline=selected_color, width=2)
            # 將矩形框移到最前面
            self.canvas.tag_raise(rect_id)

        print(f"✓ 已高亮 {len(rect_ids)} 個矩形框")

    def update_selected_item(self, rect_id):
        """只更新选中的列表项，不刷新整个列表"""
        if hasattr(self, 'editor_rect') and self.editor_rect:
            # 找到对应的矩形数据
            target_rect = None
            for rect in self.editor_rect.rectangles:
                if rect.get('rectId') == rect_id:
                    target_rect = rect
                    break
            
            if target_rect:
                # 找到对应的列表项并更新
                for list_item in self.rect_list_items:
                    if list_item['rect_id'] == rect_id:
                        # 更新名称
                        new_name = target_rect.get('name', 'Unknown')
                        list_item['name_label'].config(text=new_name)
                        
                        # 更新温度显示
                        new_temp = target_rect.get('max_temp', 0)
                        temp_text = f"{new_temp:.1f}°C"
                        list_item['temp_label'].config(text=temp_text)
                        
                        print(f"✓ 已更新列表项 {rect_id}: 名称={new_name}, 温度={temp_text}")
                        break

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
        """更新特定矩形框的温度显示"""
        # 查找对应的列表项
        for list_item in self.rect_list_items:
            if list_item['rect_id'] == rect_id:
                # 获取最新的温度数据
                if hasattr(self, 'editor_rect') and self.editor_rect:
                    for rect in self.editor_rect.rectangles:
                        if rect.get('rectId') == rect_id:
                            new_temp = rect.get('max_temp', 0)
                            # 更新温度标签显示
                            temp_text = f"{new_temp:.1f}°C"
                            list_item['temp_label'].config(text=temp_text)
                            break
                break

    def scroll_to_item(self, rect_id):
        """滚动列表使指定的item可见"""
        try:
            # 找到对应的列表项
            target_item = None
            item_index = -1
            for i, list_item in enumerate(self.rect_list_items):
                if list_item['rect_id'] == rect_id:
                    target_item = list_item
                    item_index = i
                    break
            
            if target_item and item_index >= 0:
                total_items = len(self.rect_list_items)
                if total_items > 0:
                    # 对于新增的项（通常在最底部），直接滚动到底部
                    if item_index >= total_items - 3:  # 最后3项，直接滚动到底部
                        self.list_canvas.yview_moveto(1.0)
                        print(f"✓ 新增项在底部，直接滚动到底部: {item_index}/{total_items}")
                    else:
                        # 计算相对位置 (0.0 到 1.0)
                        relative_pos = item_index / max(1, total_items - 1)
                        # 滚动到该位置，稍微向上偏移以确保可见
                        scroll_pos = max(0.0, relative_pos - 0.1)
                        self.list_canvas.yview_moveto(scroll_pos)
                        print(f"✓ 已滚动到item {rect_id}，位置: {item_index}/{total_items}, 滚动位置: {scroll_pos:.2f}")
        except Exception as e:
            print(f"滚动到item错误: {e}")

    def on_rect_change(self, rect_id=None, change_type=None):
        """矩形框变化时的回调函数"""
        if change_type == "temp_update" and rect_id:
            # 只更新特定矩形框的温度显示
            self.update_rect_temp_display(rect_id)
        elif change_type == "select":
            # Canvas选中某个矩形 -> 列表也高亮对应项，并滚动到可见位置
            # 只清除列表选中状态，不清除canvas锚点
            self.clear_list_selections()
            self.selected_rect_id = rect_id
            
            # 更新删除按钮状态
            self.update_delete_button_state()
            
            # 确保对话框可以接收键盘事件
            self.dialog.focus_set()
            
            # 从配置中读取选中颜色
            from config import GlobalConfig
            config = GlobalConfig()
            selected_color = config.get("heat_selected_color", "#4A90E2")
            
            # 高亮对应的列表项
            for list_item in self.rect_list_items:
                if list_item['rect_id'] == rect_id:
                    list_item['frame'].config(bg=selected_color)
                    for child in list_item['frame'].winfo_children():
                        if isinstance(child, (tk.Label, tk.Entry)):
                            child.config(bg=selected_color, fg='white')
                    # 自动滚动到选中的item
                    self.scroll_to_item(rect_id)
                    break
            
            # 设置canvas选中状态（避免重复清除操作）
            self.set_canvas_selection_only(rect_id)
            # 更新删除按钮状态
            self.update_delete_button_state()
        elif change_type == "clear_select":
            self.clear_all_selections()
            # 更新删除按钮状态
            self.update_delete_button_state()
        elif change_type == "delete":
            # 删除矩形框后，从列表中移除对应项
            self.remove_list_item_by_id(rect_id)
            # 清空选中状态
            self.selected_rect_id = None
            # 更新删除按钮状态
            self.update_delete_button_state()
            # 更新标题中的数量
            self.update_title_count()
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
        """处理多选事件"""
        if not rect_ids:
            return
        
        # 清除之前的选择
        self.clear_list_selections()
        
        # 设置多选状态
        self.selected_rect_ids = set(rect_ids)
        self.selected_rect_id = None  # 多选时清空单选ID
        
        # 从配置中读取选中颜色
        from config import GlobalConfig
        config = GlobalConfig()
        selected_color = config.get("heat_selected_color", "#4A90E2")
        
        # 高亮所有选中的列表项
        for list_item in self.rect_list_items:
            if list_item['rect_id'] in self.selected_rect_ids:
                list_item['frame'].config(bg=selected_color)
                for child in list_item['frame'].winfo_children():
                    if isinstance(child, (tk.Label, tk.Entry)):
                        child.config(bg=selected_color, fg='white')
                    elif isinstance(child, tk.Button):
                        child.config(bg=selected_color, fg='white', activebackground=selected_color, activeforeground='white')
        
        # 高亮canvas中的矩形框
        if hasattr(self, 'editor_rect') and self.editor_rect:
            self.set_all_rects_unselected()
            for rect_id in self.selected_rect_ids:
                self.canvas.itemconfig(rect_id, outline=selected_color, width=2)
        
        # 更新删除按钮状态
        self.update_delete_button_state()
        
        # 确保对话框可以接收键盘事件
        self.dialog.focus_set()
        
        print(f"✓ 多选高亮了 {len(self.selected_rect_ids)} 个矩形框")
    
    def handle_multi_delete(self, rect_ids):
        """处理批量删除事件"""
        if not rect_ids:
            return
        
        # 批量删除列表项
        for rect_id in rect_ids:
            self.remove_list_item_by_id(rect_id)
        
        # 清空选中状态
        self.selected_rect_id = None
        self.selected_rect_ids.clear()
        
        # 更新删除按钮状态
        self.update_delete_button_state()
        
        # 更新标题中的数量
        self.update_title_count()
        
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
        
        # 更新editor_rect的显示缩放比例
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
        toolbar_frame.grid(row=0, column=2, sticky="ns", padx=5, pady=5)
        toolbar_frame.grid_propagate(False)  # 保持固定宽度
        
        # 配置右侧工具栏的grid属性
        toolbar_frame.grid_rowconfigure(0, weight=0)  # 标题行，固定高度
        toolbar_frame.grid_rowconfigure(1, weight=1)  # 按钮区域，自适应高度
        toolbar_frame.grid_columnconfigure(0, weight=1)  # 单列，占满宽度
        
        # 添加工具栏标题，样式与左侧列表标题保持一致
        title_label = tk.Label(toolbar_frame, text="工具栏", font=UIStyle.TITLE_FONT, bg=UIStyle.VERY_LIGHT_BLUE, fg=UIStyle.BLACK)
        title_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        
        # 配置按钮容器，样式与左侧列表保持一致
        button_container = tk.Frame(toolbar_frame, bg=UIStyle.VERY_LIGHT_BLUE)
        button_container.grid(row=1, column=0, sticky="nsew", pady=10)
        
        # 配置按钮容器的grid属性，按钮固定高度，不拉伸
        button_container.grid_rowconfigure(0, weight=0)  # 多选开关行，固定高度
        button_container.grid_rowconfigure(1, weight=0)  # 合并按钮行，固定高度
        button_container.grid_rowconfigure(2, weight=0)  # 删除按钮行，固定高度
        button_container.grid_columnconfigure(0, weight=1)  # 单列，占满宽度
        
        # 多选模式开关 - 使用复选框
        multi_select_frame = tk.Frame(button_container, bg=UIStyle.VERY_LIGHT_BLUE)
        multi_select_frame.grid(row=0, column=0, pady=(0, 8), padx=10, sticky="ew")
        
        self.multi_select_var = tk.BooleanVar(value=False)  # 默认关闭
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
        self.multi_select_checkbox.pack(anchor='w')
        
        # 合并按钮 - 固定高度30px
        self.merge_button = tk.Button(
            button_container,
            text="🔗 合并",
            font=UIStyle.BUTTON_FONT,
            width=10,
            height=2,
            bg=UIStyle.PRIMARY_BLUE,
            fg=UIStyle.WHITE,
            relief=UIStyle.BUTTON_RELIEF,
            bd=UIStyle.BUTTON_BORDER_WIDTH,
            command=self.on_merge_rects
        )
        self.merge_button.grid(row=1, column=0, pady=8, padx=10, sticky="ew")
        
        # 删除按钮 - 固定高度30px
        self.delete_button = tk.Button(
            button_container,
            text="🗑️ 删除",
            font=UIStyle.BUTTON_FONT,
            width=10,
            height=2,  # 调整高度以适应30px
            bg=UIStyle.DANGER_RED,
            fg=UIStyle.WHITE,
            relief=UIStyle.BUTTON_RELIEF,
            bd=UIStyle.BUTTON_BORDER_WIDTH,
            command=self.on_delete_rect
        )
        self.delete_button.grid(row=2, column=0, pady=8, padx=10, sticky="ew")
        
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
        merged_rect_id = self.editor_rect.merge_rectangles_by_ids(list(self.selected_rect_ids))
        
        if merged_rect_id:
            # 合并成功，更新列表
            self.update_rect_list()
            
            # 选中新合并的矩形框
            self.selected_rect_ids.clear()
            self.selected_rect_id = merged_rect_id
            
            # 从配置中读取选中颜色
            from config import GlobalConfig
            config = GlobalConfig()
            selected_color = config.get("heat_selected_color", "#4A90E2")
            
            # 高亮列表中的新矩形框
            for list_item in self.rect_list_items:
                if list_item['rect_id'] == merged_rect_id:
                    list_item['frame'].config(bg=selected_color)
                    for child in list_item['frame'].winfo_children():
                        if isinstance(child, (tk.Label, tk.Entry)):
                            child.config(bg=selected_color, fg='white')
                    # 滚动到该项
                    self.scroll_to_item(merged_rect_id)
                    break
            
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
        print(f"🔍🔍🔍 on_delete_rect被调用: event={event}, selected_rect_id={self.selected_rect_id}, selected_rect_ids={self.selected_rect_ids}")
        print(f"🔍🔍🔍 事件类型: {type(event)}")
        if event:
            print(f"🔍🔍🔍 事件详情: {event}")
            print(f"🔍🔍🔍 事件字符: {getattr(event, 'char', 'N/A')}")
            print(f"🔍🔍🔍 事件键码: {getattr(event, 'keycode', 'N/A')}")
        
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
                
                # 批量删除
                self.editor_rect.delete_rectangles_by_ids(list(self.selected_rect_ids))
                
                # 批量删除列表项
                for rect_id in list(self.selected_rect_ids):
                    self.remove_list_item_by_id(rect_id)
                
                # 清空选中状态
                self.selected_rect_ids.clear()
                self.selected_rect_id = None
                
                # 更新删除按钮状态
                self.update_delete_button_state()
                
                # 更新标题中的数量
                self.update_title_count()
                
                print(f"✓✓✓ 通过{'键盘Delete键' if event else '删除按钮'}批量删除了矩形框")
                
                # 确保焦点回到对话框
                self.dialog.focus_set()
                return
            
            # 处理单选删除
            print(f"🔍🔍🔍 开始删除矩形框 {self.selected_rect_id}")
            
            # 检查矩形框是否存在
            rect_exists = False
            for rect in self.editor_rect.rectangles:
                if rect.get('rectId') == self.selected_rect_id:
                    rect_exists = True
                    print(f"🔍🔍🔍 找到要删除的矩形框: {rect}")
                    break
            
            if not rect_exists:
                print(f"⚠️⚠️⚠️ 矩形框 {self.selected_rect_id} 不存在于editor_rect.rectangles中")
                print(f"⚠️⚠️⚠️ 当前所有矩形框: {[r.get('rectId') for r in self.editor_rect.rectangles]}")
                return
            
            # 删除选中的矩形框
            print(f"🔍🔍🔍 调用delete_rectangle_by_id({self.selected_rect_id})")
            self.editor_rect.delete_rectangle_by_id(self.selected_rect_id)
            print(f"🔍🔍🔍 delete_rectangle_by_id调用完成")
            
            # 只删除对应的列表项，不刷新整个列表
            print(f"🔍🔍🔍 调用remove_list_item_by_id({self.selected_rect_id})")
            self.remove_list_item_by_id(self.selected_rect_id)
            print(f"🔍🔍🔍 remove_list_item_by_id调用完成")
            
            # 清空选中状态
            self.selected_rect_id = None
            # 更新删除按钮状态
            self.update_delete_button_state()
            
            # 更新标题中的数量
            self.update_title_count()
            
            print(f"✓✓✓ 通过{'键盘Delete键' if event else '删除按钮'}删除了矩形框")
            
            # 确保焦点回到对话框
            self.dialog.focus_set()
        else:
            print("⚠️⚠️⚠️ EditorRect未初始化，无法删除")
            print(f"⚠️⚠️⚠️ hasattr(self, 'editor_rect'): {hasattr(self, 'editor_rect')}")
            if hasattr(self, 'editor_rect'):
                print(f"⚠️⚠️⚠️ self.editor_rect: {self.editor_rect}")
    
    def remove_list_item_by_id(self, rect_id):
        """根据矩形框ID删除对应的列表项"""
        for item in self.rect_list_items:
            if item.get('rect_id') == rect_id:
                # 删除列表项的UI元素
                if 'frame' in item:
                    item['frame'].destroy()
                # 从列表中移除
                self.rect_list_items.remove(item)
                break
        
        # 重新配置滚动区域 - 使用延迟更新避免性能问题
        if hasattr(self, 'list_canvas') and self.list_canvas:
            self.list_canvas.after(10, self._update_scroll_region)
    
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
        for rect in self.editor_rect.rectangles:
            if rect.get('rectId') == rect_id:
                rect.update(new_rect)
                break
        
        # 更新列表显示
        self.update_rect_list()
        print(f"✓ 已更新矩形框 {rect_id} 的信息")
    
    def update_title_count(self):
        """更新标题中的数量显示"""
        if hasattr(self, 'title_label'):
            count = len(self.rect_list_items)
            self.title_label.config(text=f"元器件列表({count})")
    
    def toggle_sort_by_name(self):
        """切換按名稱排序"""
        if self.sort_mode == "name_asc":
            # 已經是名稱升序，不需要切換（保持當前狀態）
            return
        else:
            # 切換到名稱升序
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
            # 按名稱升序排序（A~Z）
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
        """更新排序指示符號"""
        if not hasattr(self, 'name_header_btn') or not hasattr(self, 'temp_header_btn') or not hasattr(self, 'desc_header_btn'):
            return

        # 更新名稱欄位標頭
        if self.sort_mode == "name_asc":
            self.name_header_btn.config(text="名稱 ▼", fg=UIStyle.PRIMARY_BLUE, font=("Arial", 10, "bold"))
            self.desc_header_btn.config(text="描述", fg=UIStyle.BLACK, font=("Arial", 10))
            self.temp_header_btn.config(text="溫度   ", fg=UIStyle.BLACK, font=("Arial", 10))
        elif self.sort_mode == "desc_asc":
            self.name_header_btn.config(text="名稱", fg=UIStyle.BLACK, font=("Arial", 10))
            self.desc_header_btn.config(text="描述 ▼", fg=UIStyle.PRIMARY_BLUE, font=("Arial", 10, "bold"))
            self.temp_header_btn.config(text="溫度   ", fg=UIStyle.BLACK, font=("Arial", 10))
        elif self.sort_mode == "temp_desc":
            self.name_header_btn.config(text="名稱", fg=UIStyle.BLACK, font=("Arial", 10))
            self.desc_header_btn.config(text="描述", fg=UIStyle.BLACK, font=("Arial", 10))
            self.temp_header_btn.config(text="溫度 ▼ ", fg=UIStyle.PRIMARY_BLUE, font=("Arial", 10, "bold"))
        else:
            self.name_header_btn.config(text="名稱", fg=UIStyle.BLACK, font=("Arial", 10))
            self.desc_header_btn.config(text="描述", fg=UIStyle.BLACK, font=("Arial", 10))
            self.temp_header_btn.config(text="溫度", fg=UIStyle.BLACK, font=("Arial", 10))

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
                # 有选中的矩形框，按钮可用（红色）
                self.delete_button.config(state='normal', bg=UIStyle.DANGER_RED, fg=UIStyle.WHITE)
            else:
                # 无选中的矩形框，按钮灰色不可用
                self.delete_button.config(state='disabled', bg=UIStyle.GRAY, fg=UIStyle.DARK_GRAY)
        
        # 同时更新合并按钮状态
        self.update_merge_button_state()
    
    def update_merge_button_state(self):
        """更新合并按钮的状态（选中>1个矩形框时可用）"""
        if hasattr(self, 'merge_button'):
            # 只有选中多于1个矩形框时才可用
            if len(self.selected_rect_ids) > 1:
                # 有多个选中的矩形框，按钮可用（蓝色）
                self.merge_button.config(state='normal', bg=UIStyle.PRIMARY_BLUE, fg=UIStyle.WHITE)
            else:
                # 选中≤1个矩形框，按钮灰色不可用
                self.merge_button.config(state='disabled', bg=UIStyle.GRAY, fg=UIStyle.DARK_GRAY)

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
            return

        # 根據篩選條件過濾列表
        filtered = []
        for rect in all_rects:
            # 檢查名稱篩選
            if name_filter:
                rect_name = rect.get('name', '').upper()
                if name_filter not in rect_name:
                    continue  # 不符合名稱條件，跳過

            # 檢查描述篩選
            if desc_filter:
                rect_desc = rect.get('description', '').upper()
                if desc_filter not in rect_desc:
                    continue  # 不符合描述條件，跳過

            # 檢查溫度篩選
            if temp_filter:
                rect_temp = rect.get('max_temp', 0)
                if not self._check_temperature_condition(rect_temp, temp_filter):
                    continue  # 不符合溫度條件，跳過

            # 通過所有篩選條件，加入結果列表
            filtered.append(rect)

        self.filtered_rectangles = filtered

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

    def on_search_changed(self, event=None):
        """搜索框内容变化时的回调"""
        if not hasattr(self, 'search_entry'):
            return

        search_text = self.search_entry.get().strip().lower()
        self.filter_rect_list(search_text)
    
    def clear_search(self):
        """清除搜索内容"""
        if hasattr(self, 'search_entry'):
            self.search_entry.clear()
            self.filter_rect_list("")
    
    def filter_rect_list(self, search_text):
        """根据搜索文本过滤矩形框列表"""
        if not hasattr(self, 'rect_list_items'):
            return
            
        # 获取所有矩形框数据
        rectangles = []
        if hasattr(self, 'editor_rect') and self.editor_rect:
            rectangles = self.editor_rect.rectangles
        
        # 如果没有搜索文本，显示所有项目
        if not search_text:
            for list_item in self.rect_list_items:
                list_item['frame'].pack(fill=tk.X, padx=2, pady=1)
        else:
            # 根据搜索文本过滤
            for list_item in self.rect_list_items:
                rect_id = list_item['rect_id']
                # 查找对应的矩形框数据
                target_rect = None
                for rect in rectangles:
                    if rect.get('rectId') == rect_id:
                        target_rect = rect
                        break
                
                if target_rect:
                    rect_name = target_rect.get('name', '').lower()
                    # 如果名称包含搜索文本，显示该项目
                    if search_text in rect_name:
                        list_item['frame'].pack(fill=tk.X, padx=2, pady=1)
                    else:
                        list_item['frame'].pack_forget()  # 隐藏不匹配的项目
                else:
                    list_item['frame'].pack_forget()  # 隐藏找不到数据的项目
        
        # 更新滚动区域
        self.list_canvas.update_idletasks()
        self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))
    
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
            temp_data = self.parent.tempALoader.get_temp_data() if hasattr(self.parent.tempALoader, 'get_temp_data') else None
            
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
