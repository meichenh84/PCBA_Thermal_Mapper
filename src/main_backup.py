import sys
import os
# 设置标准输出编码为 UTF-8，避免中文输出问题
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import tkinter as tk
from tkinter import Canvas, filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageTk
from magnifier import ImageMagnifier
from load_tempA import TempLoader
from toast import show_toast  # 使用独立的toast组件
import cv2
import numpy as np
import pandas as pd
import openpyxl
import json
import threading
import time
import math
import argparse
from datetime import datetime
from dialog_template import TemplateDialog
from dialog_setting import SettingDialog
from constants import Constants
from point_transformer import PointTransformer
from config import GlobalConfig

# UI样式常量定义
# 导入UIStyle以保持样式统一
try:
    from .ui_style import UIStyle
except ImportError:
    from ui_style import UIStyle
from circle_ring_draw import draw_points_circle_ring_text, draw_points_circle_ring
from recognize_circle import detect_A_circles, detect_B_circles, find_circle_containing_point
from draw_rect import draw_triangle_and_text, draw_canvas_item, update_canvas_item, draw_numpy_image_item
from editor_canvas import EditorCanvas
from datetime import datetime
import csv
import copy
from layout_temperature_query_optimized import LayoutTemperatureQueryOptimized
from temperature_config_manager import TemperatureConfigManager


DEFAULT_EDIT_LOG = {
    "export_time": ["生成时间", ""],
    "origin_mark": ["自动生成外框数量", 0],
    "final_mark": ["最终导出外框数量", 0],
    "add_new_mark": ["新增外框数量（手动增加导出时没有被删除）", 0],
    "delete_origin_mark": ["删除外框数量（自动生成的外框被删除）", 0],
    "modify_origin_mark": ["调整外框数量（自动生成的外框被调整)", set()],
}

def cv2_imread_unicode(image_path):
    """
    读取含有中文路径的图片文件（解决OpenCV在Windows上无法读取中文路径的问题）
    """
    try:
        # 使用numpy读取文件字节，再用cv2解码
        img_array = np.fromfile(image_path, dtype=np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return image
    except Exception as e:
        print(f"cv2_imread_unicode error: {e}")
        return None

class ResizableImagesApp:
    """
    热力图温度点位自动识别主应用程序
    
    核心功能：
    1. 热力图与布局图的坐标映射
    2. 温度数据的智能查询和过滤
    3. 元器件边界的自动识别
    4. 温度数据的可视化显示
    5. 编辑和导出功能
    """
    def __init__(self, root):
        """
        初始化主应用程序
        
        Args:
            root: Tkinter根窗口对象
        """
        print("V20251011")
        
        # 线程锁，用于保护共享资源
        self.lock = threading.Lock()
        self.root = root
        
        # 设置主窗口属性
        self.root.title("Thermal温度点位自动识别")
        self.root.minsize(width=400, height=500)
        self.root.geometry("1200x600")
        
        # 画布尺寸初始化
        self.canvasA_width = 1
        self.canvasA_height = 1
        
        # 图像对齐状态控制
        self.is_aligning = False  # 状态变量，用于跟踪按钮的当前状态
        
        # 配置管理器
        self.config = GlobalConfig()
        self.temp_config = None  # 温度配置管理器，将在设置文件夹路径时初始化
        
        # 放大镜组件
        self.canvasA_magnifier = None
        self.canvasB_magnifier = None
        
        # 图像对齐相关数据
        self.points_A = []  # 热力图上的对齐点坐标
        self.points_B = []  # 布局图上的对齐点坐标
        
        # 自动识别的圆形区域
        self.recognize_circle_A = []  # 热力图上识别的圆形区域
        self.recognize_circle_B = []  # 布局图上识别的圆形区域
        
        # 温度标记矩形框
        self.mark_rect_A = []  # 热力图上的温度标记矩形框
        
        # 画布背景图像ID
        self.bg_imageA_id = None  # 热力图在画布上的ID
        self.bg_imageB_id = None  # 布局图在画布上的ID
        
        # 坐标变换器（用于热力图与布局图之间的坐标转换）
        self.point_transformer = None
        
        # 图像数据
        self.imageA = None  # 热力图图像数据
        self.imageB = None  # 布局图图像数据
        
        # 状态标志
        self.pont_marked = False  # 点位是否已标记
        self.edit_log = None  # 编辑日志记录
        
        # 文件夹选择相关变量
        self.current_folder_path = None
        self.folder_files = {"heat": [], "layout": [], "heatTemp": [], "layoutData": []}
        self.current_temp_file_path = None  # 全局温度数据文件路径
        self.current_files = {"heat": None, "layout": None, "heatTemp": None, "layoutData": None}  # 当前使用的文件
        
        # Layout数据相关变量
        self.layout_data = None  # 存储解析后的layout数据
        
        # 对话框实例（单例模式）
        self.setting_dialog = None  # 设置对话框实例
        self.editor_canvas = None  # EditorCanvas实例

        # self.save_log_file()

        self.init_UI_flow(root)

        # 初始化时显示图片
        # self.update_images()

        # 绑定窗口大小变化事件
        self.root.bind("<Configure>", self.on_resize)

        # 控制更新的频率
        self.resize_after = None
        # self.root.after(100, self.init_magnifier)  # 延迟100毫秒更新
        # self.background_opt()
        self.root.after(100, self.background_opt)

    def background_opt(self):
        # 加载上次使用的文件夹路径
        self.load_last_folder_path()
        
    def load_last_folder_path(self):
        """加载上次使用的文件夹路径"""
        last_path = self.config.get("last_folder_path")
        if last_path and os.path.exists(last_path):
            print(f"启动时自动加载上次使用的文件夹: {last_path}")
            
            # 保存当前文件夹的文件选择
            self.save_current_files_to_config()
            
            # 清空旧的数据
            self.clear_old_data()
            
            self.current_folder_path = last_path
            
            # 初始化温度配置管理器（重要：必须在scan_folder_files之前）
            self.temp_config = TemperatureConfigManager(last_path)
            print(f"已初始化TemperatureConfigManager，配置文件路径: {last_path}/config/temperature_config.json")
            
            self.scan_folder_files()
            self.update_folder_display()
            self.update_folder_path_label()
            
            # 自动加载图片和点位数据
            self.auto_load_images()
            
            # 更新按钮文字
            folder_name = os.path.basename(last_path)
            self.folder_control_button.config(text=f"隐藏文件夹Tab")
            
            print(f"启动时文件夹自动加载完成: {folder_name}")
        else:
            print("没有找到上次使用的文件夹路径或文件夹不存在")
    
    def save_folder_path(self):
        """保存当前文件夹路径到配置"""
        if self.current_folder_path:
            self.config.set("last_folder_path", self.current_folder_path)
            self.config.save_to_json()
    
    def save_current_files_to_config(self):
        """保存当前选择的文件到配置"""
        if self.current_folder_path:
            # 保存当前选择的文件到temperature_config.json
            if self.temp_config:
                self.temp_config.set_file_path("current_heat_file", self.current_files.get("heat"))
                self.temp_config.set_file_path("current_pcb_file", self.current_files.get("heat"))
                self.temp_config.set_file_path("current_layout_file", self.current_files.get("layout"))
                self.temp_config.set_file_path("current_temp_file", self.current_files.get("heatTemp"))
                self.temp_config.set_file_path("current_layout_data_file", self.current_files.get("layoutData"))
                print(f"已保存当前文件选择到temperature_config.json: 热力图={self.current_files.get('heat')}, Layout图={self.current_files.get('layout')}, 温度数据={self.current_files.get('heatTemp')}, layout数据={self.current_files.get('layoutData')}")
            else:
                print("temp_config未初始化，无法保存文件路径")
    
    def update_temp_config_files(self):
        """更新温度配置管理器中的当前文件信息"""
        print(f"update_temp_config_files: 开始更新文件信息")
        print(f"update_temp_config_files: temp_config存在: {self.temp_config is not None}")
        print(f"update_temp_config_files: current_folder_path: {self.current_folder_path}")
        print(f"update_temp_config_files: current_files: {self.current_files}")
        
        if self.temp_config and self.current_folder_path:
            # 使用新的文件路径管理方法
            self.temp_config.set_file_path("current_heat_file", self.current_files.get("heat"))
            self.temp_config.set_file_path("current_pcb_file", self.current_files.get("heat"))
            self.temp_config.set_file_path("current_temp_file", self.current_files.get("heatTemp"))
            self.temp_config.set_file_path("current_layout_file", self.current_files.get("layout"))
            self.temp_config.set_file_path("current_layout_data_file", self.current_files.get("layoutData"))
            print(f"update_temp_config_files: 文件路径已更新到temperature_config.json")
        else:
            print(f"update_temp_config_files: 跳过更新，条件不满足")
    
    def load_current_files_from_config(self):
        """从配置加载上次选择的文件"""
        if self.current_folder_path:
            # 从temperature_config.json加载上次选择的文件
            if self.temp_config:
                saved_heat = self.temp_config.get_file_path("current_heat_file")
                saved_layout = self.temp_config.get_file_path("current_layout_file")
                saved_temp = self.temp_config.get_file_path("current_temp_file")
                saved_layout_data = self.temp_config.get_file_path("current_layout_data_file")
            else:
                # 如果temp_config未初始化，使用默认值
                saved_heat = saved_layout = saved_temp = saved_layout_data = None
            
            print(f"从配置文件加载的文件路径:")
            print(f"  current_heat_file: {saved_heat}")
            print(f"  current_layout_file: {saved_layout}")
            print(f"  current_temp_file: {saved_temp}")
            print(f"  current_layout_data_file: {saved_layout_data}")
            
            # 验证文件是否仍然存在，如果不存在则执行默认操作
            self._load_or_default_file("heat", saved_heat, "热力图")
            self._load_or_default_file("layout", saved_layout, "Layout图")
            self._load_or_default_file("heatTemp", saved_temp, "温度数据")
            self._load_or_default_file("layoutData", saved_layout_data, "Layout数据")
            
            print(f"文件选择完成: {self.current_files}")
    
    def _load_or_default_file(self, file_type, saved_file, display_name):
        """加载指定文件类型，如果配置的文件不存在则使用默认操作"""
        if saved_file and saved_file in self.folder_files.get(file_type, []):
            # 配置的文件存在，使用配置的文件
            self.current_files[file_type] = saved_file
            print(f"✓ 恢复{display_name}选择: {saved_file}")
        elif self.folder_files.get(file_type):
            # 配置的文件不存在，使用默认操作：选择第一个可用的文件
            self.current_files[file_type] = self.folder_files[file_type][0]
            print(f"⚠ {display_name}配置不存在或文件已删除，自动选择第一个可用文件: {self.current_files[file_type]}")
            
            # 更新配置文件，保存默认选择的文件
            if self.temp_config:
                # 正确的配置键映射
                if file_type == "heat":
                    config_key = "current_heat_file"
                elif file_type == "layout":
                    config_key = "current_layout_file"
                elif file_type == "heatTemp":
                    config_key = "current_temp_file"
                elif file_type == "layoutData":
                    config_key = "current_layout_data_file"
                else:
                    config_key = f"current_{file_type}_file"
                
                self.temp_config.set_file_path(config_key, self.current_files[file_type])
                print(f"已更新配置文件: {config_key} = {self.current_files[file_type]}")
        else:
            # 没有可用的文件
            self.current_files[file_type] = None
            print(f"⚠ 没有可用的{display_name}文件")
    
    def clear_old_data(self):
        """清空内存中的旧数据，切换文件夹时调用（不删除文件）"""
        # 清空点位数据
        self.points_A = []
        self.points_B = []
        
        # 清空点转换器
        self.point_transformer = None
        
        # 清空标记矩形数据
        self.mark_rect_A = []
        self.mark_rect_B = []
        
        # 清空图片数据
        self.imageA = None
        self.imageB = None
        self.resized_imageA = None
        self.resized_imageB = None
        
        # 清空画布显示
        if hasattr(self, 'canvasA'):
            self.canvasA.delete("all")
        if hasattr(self, 'canvasB'):
            self.canvasB.delete("all")
        
        # 清空温度数据
        if hasattr(self, 'tempALoader'):
            self.tempALoader = None
        self.current_temp_file_path = None
        
        # 清空当前文件信息
        self.current_files = {"heat": None, "layout": None, "heatTemp": None, "layoutData": None}
        
        # 清空Layout数据
        self.layout_data = None
        
        print("已清空内存中的旧数据，准备加载新文件夹数据")
    
    
    def select_folder(self):
        """选择文件夹"""
        folder_path = filedialog.askdirectory(title="选择包含热力图和Layout图的文件夹")
        if folder_path:
            # 保存当前文件夹的文件选择
            self.save_current_files_to_config()
            
            # 清空旧的数据
            self.clear_old_data()
            
            self.current_folder_path = folder_path
            # 初始化温度配置管理器
            self.temp_config = TemperatureConfigManager(folder_path)
            self.save_folder_path()
            self.scan_folder_files()
            # 在扫描文件后更新温度配置管理器中的文件信息
            print(f"set_folder_path: 准备调用update_temp_config_files")
            self.update_temp_config_files()
            self.update_folder_display()
            self.update_folder_path_label()
            
            # 重新加载点位数据
            self.load_points()
            
            
            # 更新按钮文字
            folder_name = os.path.basename(folder_path)
            self.folder_control_button.config(text=f"隐藏文件夹Tab")
    
    def scan_folder_files(self):
        """扫描文件夹中的文件并分类"""
        if not self.current_folder_path:
            return
            
        self.folder_files = {"heat": [], "layout": [], "heatTemp": [], "layoutData": []}
        
        try:
            # 收集文件信息（文件名和修改时间）
            file_info = {"heat": [], "layout": [], "heatTemp": [], "layoutData": []}
            
            for filename in os.listdir(self.current_folder_path):
                file_path = os.path.join(self.current_folder_path, filename)
                if os.path.isfile(file_path):
                    # 获取文件修改时间
                    mtime = os.path.getmtime(file_path)
                    
                    # 检查文件扩展名
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        # 先判断是否为Layout图，再判断是否为热力图
                        if self._is_layout_image(file_path):
                            file_info["layout"].append((filename, mtime))
                        elif self._is_heat_image(file_path):
                            file_info["heat"].append((filename, mtime))
                    elif filename.lower().endswith(('.csv', '.xlsx')):
                        # 判断是温度数据还是layout数据
                        if self._is_layout_data_file(file_path):
                            file_info["layoutData"].append((filename, mtime))
                        else:
                            file_info["heatTemp"].append((filename, mtime))
            
            # 按修改时间排序（最新的在前）
            for category in file_info:
                file_info[category].sort(key=lambda x: x[1], reverse=True)
                self.folder_files[category] = [filename for filename, _ in file_info[category]]
                
                # 设置当前使用的文件为最新的文件
                if self.folder_files[category]:
                    self.current_files[category] = self.folder_files[category][0]
            
            # 扫描完成后，自动加载可用的图片
            self.auto_load_images()
            
            # 添加调试信息
            print(f"scan_folder_files: 扫描完成，current_files: {self.current_files}")
        except Exception as e:
            print(f"扫描文件夹时出错: {e}")
    
    def _is_heat_image(self, image_path):
        """判断是否为热力图（颜色丰富的图像）"""
        try:
            image = cv2_imread_unicode(image_path)
            if image is None:
                return False

            # 转换为HSV颜色空间
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # 计算颜色饱和度
            saturation = hsv[:, :, 1]
            avg_saturation = np.mean(saturation)

            # 计算颜色变化
            color_variance = np.var(hsv[:, :, 0])  # 色调方差

            # 热力图通常有较高的饱和度和颜色变化
            return avg_saturation > 80 and color_variance > 1000
        except:
            return False

    def _is_layout_image(self, image_path):
        """判断是否为Layout图（背景大部分是黑色的图像）"""
        try:
            image = cv2_imread_unicode(image_path)
            if image is None:
                return False

            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # 计算黑色像素的比例（阈值设为50）
            black_pixels = np.sum(gray < 50)
            total_pixels = gray.shape[0] * gray.shape[1]
            black_ratio = black_pixels / total_pixels

            # 如果黑色像素比例超过60%，认为是Layout图
            return black_ratio > 0.6
        except:
            return False
    
    def _is_layout_data_file(self, file_path):
        """判断是否为layout数据文件（包含RefDes字段的xlsx文件）"""
        try:
            if not file_path.lower().endswith('.xlsx'):
                return False
            
            # 读取Excel文件的第一行，检查是否包含RefDes字段
            df = pd.read_excel(file_path, nrows=1)
            return 'RefDes' in df.columns
        except:
            return False
    
    def auto_load_images(self):
        """自动加载可用的图片"""
        try:
            # 首先尝试从配置恢复上次选择的文件
            self.load_current_files_from_config()
            
            # 优先加载图片（同步加载，快速显示）
            if self.current_files["heat"]:
                heat_image_path = os.path.join(self.current_folder_path, self.current_files["heat"])
                self.set_image(heat_image_path, 0)
                print(f"自动加载热力图: {self.current_files['heat']}")
            
            if self.current_files["layout"]:
                layout_image_path = os.path.join(self.current_folder_path, self.current_files["layout"])
                self.set_image(layout_image_path, 1)
                print(f"自动加载Layout图: {self.current_files['layout']}")
            
            # 加载点位数据（同步加载，快速显示）
            self.load_points()
            
            # 温度数据异步加载（在子线程中）
            if self.current_files["heatTemp"]:
                temp_file_path = os.path.join(self.current_folder_path, self.current_files["heatTemp"])
                self.load_temperature_file_async(temp_file_path)
            
            # Layout数据异步加载（在子线程中）
            if self.folder_files.get("layoutData"):
                # 自动加载所有layout数据文件
                self.load_all_layout_data_async()
                
        except Exception as e:
            print(f"自动加载图片时出错: {e}")
    
    def update_folder_display(self):
        """更新文件夹文件显示"""
        if hasattr(self, 'folder_tree'):
            # 记录当前展开状态
            expanded_items = []
            for item in self.folder_tree.get_children():
                if self.folder_tree.item(item, "open"):
                    expanded_items.append(self.folder_tree.item(item, "text"))
            
            # 清空现有内容
            for item in self.folder_tree.get_children():
                self.folder_tree.delete(item)
            
            # 添加分类和文件
            for category, files in self.folder_files.items():
                if files:
                    # 统一标题长度，让图标对齐
                    category_names = {"heat": "热力图", "layout": "Layout图", "heatTemp": "温度数据", "layoutData": "layout数据"}
                    category_spaces = {"heat": 31.7, "layout": 32, "heatTemp": 29, "layoutData": 29}
                    category_name = category_names[category]
                    # 父标题显示选择图标在右侧，使用固定宽度确保图标对齐
                    # 为heat和layout添加额外空格，让图标对齐
                    base_text = f"{category_name} ({len(files)})"
                    display_text = f"{base_text:<{category_spaces[category]}}📁"
                    category_item = self.folder_tree.insert("", "end", text=display_text, values=(category, ""))
                    
                    # 自动展开所有分类
                    self.folder_tree.item(category_item, open=True)
                    
                    for filename in files:
                        # 如果这是当前使用的文件，用加粗标记
                        if filename == self.current_files[category]:
                            display_text = filename  # 文件名不显示图标
                            item = self.folder_tree.insert(category_item, "end", text=display_text, values=(category, filename))
                            # 设置加粗样式
                            self.folder_tree.item(item, tags=("bold",))
                        else:
                            display_text = filename  # 文件名不显示图标
                            item = self.folder_tree.insert(category_item, "end", text=display_text, values=(category, filename))
    
    def update_folder_path_label(self):
        """更新文件夹路径标签"""
        if hasattr(self, 'folder_path_label'):
            if self.current_folder_path:
                # 显示文件夹名称而不是完整路径
                folder_name = os.path.basename(self.current_folder_path)
                self.folder_path_label.config(text=f"当前文件夹：{folder_name}")
            else:
                self.folder_path_label.config(text="当前文件夹：未选择")
    def on_file_click(self, event):
        """处理文件单击事件"""
        # 通过点击位置确定实际点击的项目，而不是使用selection()
        item = self.folder_tree.identify_row(event.y)
        if not item:
            return
            
        values = self.folder_tree.item(item, "values")
        item_text = self.folder_tree.item(item, "text")
        
        # 检查是否是父标题项（分类项）
        if len(values) >= 2 and values[0] and not values[1]:  # 父标题项：有category但没有filename
            category = values[0]
            
            # 检查是否点击了选择图标
            if "📁" in item_text:
                # 计算点击位置，判断是否点击在选择图标区域
                bbox = self.folder_tree.bbox(item)
                if bbox:
                    x, y, width, height = bbox
                    # 计算图标位置（在文本的右侧）
                    # 由于使用了固定宽度，图标应该在右侧
                    icon_start_x = x + width - 25  # 图标大约占25像素宽度
                    print(f"点击检测: event.x={event.x}, bbox=({x},{y},{width},{height}), icon_start_x={icon_start_x}")
                    if event.x >= icon_start_x:  # 点击在图标区域
                        print(f"点击了图标，开始选择文件: {category}")
                        # 立即执行文件选择，阻止默认行为
                        self.select_and_replace_current_file(category)
                        return "break"  # 阻止事件继续传播
                    else:
                        print(f"点击了父标题文本区域，执行折叠/展开操作")
                        # 普通点击父标题，执行折叠/展开操作
                        return
        
        # 处理文件项
        elif len(values) >= 2 and values[0] and values[1]:  # 文件项：有category和filename
            category = values[0]
            filename = values[1]
            
            # 🔥 新增：layoutData类型的文件项不可切换，不触发任何动作
            if category == "layoutData":
                print(f"layoutData文件项不可切换: {filename}")
                return "break"  # 阻止事件继续传播
            
            # 处理文件切换（单击文件名区域）
            file_path = os.path.join(self.current_folder_path, filename)
            
            # 更新当前使用的文件
            self.current_files[category] = filename
            
            # 更新温度配置管理器
            self.update_temp_config_files()
            
            # 保存当前选择的文件到配置
            self.save_current_files_to_config()
            
            # 加载新文件
            if category == "heat":
                self.set_image(file_path, 0)
                print(f"切换到热力图: {filename}")
                # 切换热力图后，清空对齐点数据并重新加载
                self.clear_and_reload_points()
            elif category == "layout":
                self.set_image(file_path, 1)
                print(f"切换到Layout图: {filename}")
                # 切换Layout图后，清空对齐点数据并重新加载
                self.clear_and_reload_points()
            elif category == "heatTemp":
                self.load_temperature_file(file_path)
                print(f"切换到温度数据: {filename}")
            elif category == "layoutData":
                self.load_layout_data_async(file_path)
                print(f"切换到layout数据: {filename}")
            
            # 刷新文件夹显示，更新加粗标记
            self.update_folder_display()
    
    def select_and_replace_current_file(self, category):
        """选择新文件并替换当前使用的资源（不删除原文件）"""
        try:
            print(f"select_and_replace_current_file 被调用，category = {category}")
            # 根据分类设置文件类型过滤器
            if category == "heat":
                filetypes = [("图片文件", "*.jpg *.jpeg *.png"), ("所有文件", "*.*")]
                title = "选择热力图文件"
                print(f"设置热力图文件过滤器: {filetypes}")
            elif category == "layout":
                filetypes = [("图片文件", "*.jpg *.jpeg *.png"), ("所有文件", "*.*")]
                title = "选择Layout图文件"
                print(f"设置Layout图文件过滤器: {filetypes}")
            elif category == "heatTemp":
                filetypes = [("数据文件", "*.csv *.xlsx"), ("所有文件", "*.*")]
                title = "选择温度数据文件"
                print(f"设置温度数据文件过滤器: {filetypes}")
            elif category == "layoutData":
                filetypes = [("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
                title = "选择layout数据文件"
                print(f"设置layout数据文件过滤器: {filetypes}")
            else:
                print(f"未知分类: {category}")
                return
            
            # 打开文件选择对话框
            print(f"准备打开文件对话框: title={title}, filetypes={filetypes}")
            file_path = filedialog.askopenfilename(
                title=title,
                filetypes=filetypes,
                initialdir=self.current_folder_path
            )
            print(f"文件对话框返回: {file_path}")
            
            if file_path:
                # 获取新文件名
                new_filename = os.path.basename(file_path)
                new_file_path = os.path.join(self.current_folder_path, new_filename)
                
                # 复制新文件到当前文件夹（如果文件不存在）
                if not os.path.exists(new_file_path):
                    import shutil
                    shutil.copy2(file_path, new_file_path)
                    print(f"已复制新文件: {new_filename} 到当前文件夹")
                else:
                    print(f"文件已存在: {new_filename}")
                
                # 更新当前使用的文件
                self.current_files[category] = new_filename
                
                # 保存当前选择的文件到配置
                self.save_current_files_to_config()
                
                # 重新扫描文件夹文件
                self.scan_folder_files()
                
                # 刷新文件夹显示
                self.update_folder_display()
                
                # 加载新文件到内存（替换当前使用的资源）
                if category == "heat":
                    self.set_image(new_file_path, 0)
                    print(f"已加载热力图: {new_filename}")
                    # 替换热力图后，清空对齐点数据并重新加载
                    self.clear_and_reload_points()
                elif category == "layout":
                    self.set_image(new_file_path, 1)
                    print(f"已加载Layout图: {new_filename}")
                    # 替换Layout图后，清空对齐点数据并重新加载
                    self.clear_and_reload_points()
                elif category == "heatTemp":
                    self.load_temperature_file(new_file_path)
                    print(f"已加载温度数据: {new_filename}")
                elif category == "layoutData":
                    self.load_layout_data_async(new_file_path)
                    print(f"已加载layout数据: {new_filename}")
                
                # 显示成功消息
                show_toast(
                    title='文件替换成功',
                    message=f'已切换到{new_filename}',
                    duration=3000,
                    toast_type='success'
                )
                
        except Exception as e:
            print(f"替换文件时出错: {e}")
            from tkinter import messagebox
            messagebox.showerror("错误", f"替换文件失败: {e}")
    
    def select_and_replace_file(self, category, old_filename):
        """选择新文件并替换当前文件"""
        try:
            # 根据分类设置文件类型过滤器
            if category == "heat":
                filetypes = [("图片文件", "*.jpg *.jpeg *.png"), ("所有文件", "*.*")]
                title = "选择热力图文件"
            elif category == "pcb":
                filetypes = [("图片文件", "*.jpg *.jpeg *.png"), ("所有文件", "*.*")]
                title = "选择Layout图文件"
            elif category == "heatTemp":
                filetypes = [("数据文件", "*.csv *.xlsx"), ("所有文件", "*.*")]
                title = "选择温度数据文件"
            else:
                return
            
            # 打开文件选择对话框
            file_path = filedialog.askopenfilename(
                title=title,
                filetypes=filetypes
            )
            
            if file_path:
                # 获取新文件名
                new_filename = os.path.basename(file_path)
                old_file_path = os.path.join(self.current_folder_path, old_filename)
                new_file_path = os.path.join(self.current_folder_path, new_filename)
                
                # 如果新文件名与旧文件名不同，需要替换
                if new_filename != old_filename:
                    # 删除旧文件
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                        print(f"已删除旧文件: {old_filename}")
                    
                    # 复制新文件到当前文件夹
                    import shutil
                    shutil.copy2(file_path, new_file_path)
                    print(f"已复制新文件: {new_filename} 到当前文件夹")
                else:
                    # 文件名相同，直接覆盖
                    import shutil
                    shutil.copy2(file_path, new_file_path)
                    print(f"已覆盖文件: {new_filename}")
                
                # 更新当前使用的文件
                self.current_files[category] = new_filename
                
                # 保存当前选择的文件到配置
                self.save_current_files_to_config()
                
                # 重新扫描文件夹文件
                self.scan_folder_files()
                
                # 刷新文件夹显示
                self.update_folder_display()
                
                # 加载新文件
                if category == "heat":
                    self.set_image(new_file_path, 0)
                    print(f"已加载热力图: {new_filename}")
                elif category == "pcb":
                    self.set_image(new_file_path, 1)
                    print(f"已加载Layout图: {new_filename}")
                elif category == "heatTemp":
                    self.load_temperature_file(new_file_path)
                    print(f"已加载温度数据: {new_filename}")
                
                # 显示成功消息
                show_toast(
                    title='文件替换成功',
                    message=f'已替换{old_filename}为{new_filename}',
                    duration=3000,
                    toast_type='success'
                )
                
        except Exception as e:
            print(f"替换文件时出错: {e}")
            from tkinter import messagebox
            messagebox.showerror("错误", f"替换文件失败: {e}")
    
    def select_and_copy_file(self, category):
        """选择并复制文件到当前文件夹"""
        try:
            # 根据分类设置文件类型过滤器
            if category == "heat":
                filetypes = [("图片文件", "*.jpg *.jpeg *.png"), ("所有文件", "*.*")]
                title = "选择热力图文件"
            elif category == "pcb":
                filetypes = [("图片文件", "*.jpg *.jpeg *.png"), ("所有文件", "*.*")]
                title = "选择Layout图文件"
            elif category == "heatTemp":
                filetypes = [("数据文件", "*.csv *.xlsx"), ("所有文件", "*.*")]
                title = "选择温度数据文件"
            else:
                return
            
            # 打开文件选择对话框
            file_path = filedialog.askopenfilename(
                title=title,
                filetypes=filetypes
            )
            
            if file_path:
                # 获取文件名
                filename = os.path.basename(file_path)
                target_path = os.path.join(self.current_folder_path, filename)
                
                # 复制文件到当前文件夹
                import shutil
                shutil.copy2(file_path, target_path)
                print(f"已复制文件: {filename} 到当前文件夹")
                
                # 更新当前使用的文件
                self.current_files[category] = filename
                
                # 更新温度配置管理器
                self.update_temp_config_files()
                
                # 保存当前选择的文件到配置
                self.save_current_files_to_config()
                
                # 重新扫描文件夹文件
                self.scan_folder_files()
                
                # 刷新文件夹显示
                self.update_folder_display()
                
                # 加载新复制的文件
                if category == "heat":
                    self.set_image(target_path, 0)
                    print(f"已加载热力图: {filename}")
                elif category == "pcb":
                    self.set_image(target_path, 1)
                    print(f"已加载Layout图: {filename}")
                elif category == "heatTemp":
                    self.load_temperature_file(target_path)
                    print(f"已加载温度数据: {filename}")
                
                # 显示成功消息
                show_toast(
                    title='文件选择成功',
                    message=f'已选择并复制{filename}到当前文件夹',
                    duration=3000,
                    toast_type='success'
                )
                
        except Exception as e:
            print(f"选择文件时出错: {e}")
            from tkinter import messagebox
            messagebox.showerror("错误", f"选择文件失败: {e}")
    
    def load_temperature_file(self, file_path):
        """加载温度数据文件"""
        try:
            if file_path.lower().endswith(('.csv', '.xlsx')):
                # 设置全局温度文件路径
                self.current_temp_file_path = file_path
                # 更新TempLoader的文件路径
                self.tempALoader = TempLoader(file_path)
                print(f"已加载温度数据文件: {file_path}")
            else:
                print(f"不支持的文件格式: {file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"加载温度数据文件失败: {e}")
    
    def load_temperature_file_async(self, file_path):
        """异步加载温度数据文件"""
        def load_temp_data():
            try:
                print(f"开始异步加载温度数据: {file_path}")
                if file_path.lower().endswith(('.csv', '.xlsx')):
                    # 设置全局温度文件路径
                    self.current_temp_file_path = file_path
                    # 更新TempLoader的文件路径
                    self.tempALoader = TempLoader(file_path)
                    print(f"异步加载温度数据完成: {file_path}")
                else:
                    print(f"不支持的文件格式: {file_path}")
            except Exception as e:
                print(f"异步加载温度数据失败: {e}")
                # 在主线程中显示错误信息
                self.root.after(0, lambda: messagebox.showerror("错误", f"加载温度数据文件失败: {e}"))

            # 初始化yolo
            # if not hasattr(self, 'yolo'):
            #     self.yolo = YOLOv8Instance()
        
        # 在子线程中加载温度数据
        temp_thread = threading.Thread(target=load_temp_data, daemon=True)
        temp_thread.start()
    
    def load_layout_data_async(self, file_path):
        """异步加载Layout数据文件"""
        def load_layout_data():
            try:
                print(f"开始异步加载Layout数据: {file_path}")
                self.layout_data = self.parse_layout_data(file_path)
                print(f"异步加载Layout数据完成: {file_path}")
            except Exception as e:
                print(f"异步加载Layout数据失败: {e}")
                # 在主线程中显示错误信息
                self.root.after(0, lambda: messagebox.showerror("错误", f"加载Layout数据文件失败: {e}"))
        
        # 在子线程中加载Layout数据
        layout_thread = threading.Thread(target=load_layout_data, daemon=True)
        layout_thread.start()
    
    def load_all_layout_data_async(self):
        """异步加载所有Layout数据文件"""
        def load_all_layout_data():
            try:
                print(f"开始异步加载所有Layout数据文件...")
                if not self.folder_files.get("layoutData"):
                    print("没有找到Layout数据文件")
                    return
                
                # 收集所有layout数据文件
                layout_files = []
                for layout_file in self.folder_files["layoutData"]:
                    layout_file_path = os.path.join(self.current_folder_path, layout_file)
                    layout_files.append(layout_file_path)
                
                print(f"找到Layout数据文件: {[os.path.basename(f) for f in layout_files]}")
                
                # 解析所有文件并计算C_info
                self.layout_data = self.parse_all_layout_data(layout_files)
                print(f"异步加载所有Layout数据完成，共{len(self.layout_data) if self.layout_data else 0}个元器件")
                
            except Exception as e:
                print(f"异步加载所有Layout数据失败: {e}")
                # 在主线程中显示错误信息
                self.root.after(0, lambda: messagebox.showerror("错误", f"加载Layout数据文件失败: {e}"))
        
        # 在子线程中加载Layout数据
        layout_thread = threading.Thread(target=load_all_layout_data, daemon=True)
        layout_thread.start()
    
    def parse_all_layout_data(self, layout_files):
        """解析所有Layout数据文件，返回C_info数据"""
        try:
            c_file = None
            c_item_file = None
            
            # 读取每个layout数据文件，根据字段内容判断类型
            for file_path in layout_files:
                try:
                    df = pd.read_excel(file_path, nrows=1)
                    columns = df.columns.tolist()
                    
                    # 根据字段内容判断哪个是C文件，哪个是C_item文件
                    if 'Orient.' in columns and 'X' in columns and 'Y' in columns:
                        c_file = file_path
                        print(f"识别为C文件: {os.path.basename(file_path)}")
                    elif 'L' in columns and 'W' in columns and 'T' in columns:
                        c_item_file = file_path
                        print(f"识别为C_item文件: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"读取文件 {os.path.basename(file_path)} 时出错: {e}")
                    continue
            
            if not c_file or not c_item_file:
                print(f"未找到合适的Layout数据文件")
                return None
            
            # 读取C.xlsx文件
            c_df = pd.read_excel(c_file)
            print(f"C文件字段: {c_df.columns.tolist()}")
            
            # 读取C_item.xlsx文件
            c_item_df = pd.read_excel(c_item_file)
            print(f"C_item文件字段: {c_item_df.columns.tolist()}")
            
            # 检查必需字段
            required_c_fields = ['RefDes', 'Orient.', 'X', 'Y']
            required_item_fields = ['RefDes', 'L', 'W', 'T']
            
            for field in required_c_fields:
                if field not in c_df.columns:
                    print(f"C文件缺少必需字段: {field}")
                    return None
            
            for field in required_item_fields:
                if field not in c_item_df.columns:
                    print(f"C_item文件缺少必需字段: {field}")
                    return None
            
            # 解析数据
            c_info = []
            
            for _, row in c_df.iterrows():
                refdes = row['RefDes']
                x = row['X']
                y = row['Y']
                orient = row['Orient.']
                
                # 在C_item文件中查找对应的尺寸信息
                item_match = c_item_df[c_item_df['RefDes'] == refdes]
                if not item_match.empty:
                    item_row = item_match.iloc[0]
                    l = item_row['L']
                    w = item_row['W']
                    t = item_row['T']
                    
                    # 计算边界框（考虑旋转角度）
                    if orient == 0 or pd.isna(orient):
                        # 如果角度为0或NaN，使用简单计算
                        left = x - l/2
                        top = y - w/2
                        right = x + l/2
                        bottom = y + w/2
                    else:
                        # 使用旋转计算
                        left, top, right, bottom = self.calculate_rotated_bounding_box(x, y, l, w, orient)
                    
                    c_info.append({
                        'RefDes': refdes,
                        'left': left,
                        'top': top,
                        'right': right,
                        'bottom': bottom,
                        'X': x,
                        'Y': y,
                        'L': l,
                        'W': w,
                        'T': t,
                        'Orient.': orient
                    })
                # else:
                    # print(f"未找到RefDes {refdes} 对应的尺寸信息，跳过")
            
            print(f"成功解析 {len(c_info)} 个元器件信息")
            return c_info
            
        except Exception as e:
            print(f"解析Layout数据失败: {e}")
            return None
    
    def calculate_rotated_bounding_box(self, x, y, length, width, angle_deg):
        """计算旋转后的边界框
        
        Args:
            x, y: 元器件中心坐标 (mm)
            length, width: 元器件的长和宽 (mm)
            angle_deg: 旋转角度 (度)，正值为顺时针，负值为逆时针
            
        Returns:
            tuple: (left, top, right, bottom) 旋转后的边界框坐标
        """
        import math
        
        # 将角度转换为弧度
        angle_rad = math.radians(angle_deg)
        
        # 计算半长和半宽
        half_length = length / 2
        half_width = width / 2
        
        # 计算四个角点相对于中心的坐标
        corners = [
            (-half_length, -half_width),  # 左下
            (half_length, -half_width),   # 右下
            (half_length, half_width),    # 右上
            (-half_length, half_width)    # 左上
        ]
        
        # 旋转每个角点
        rotated_corners = []
        for corner_x, corner_y in corners:
            # 旋转矩阵计算
            rotated_x = corner_x * math.cos(angle_rad) - corner_y * math.sin(angle_rad)
            rotated_y = corner_x * math.sin(angle_rad) + corner_y * math.cos(angle_rad)
            rotated_corners.append((rotated_x, rotated_y))
        
        # 计算旋转后的边界框
        x_coords = [x + corner[0] for corner in rotated_corners]
        y_coords = [y + corner[1] for corner in rotated_corners]
        
        left = min(x_coords)
        right = max(x_coords)
        top = min(y_coords)
        bottom = max(y_coords)
        
        return left, top, right, bottom
    
    def parse_layout_data(self, file_path):
        """解析Layout数据文件，返回C_info数据"""
        try:
            # 直接使用已经识别出的layout数据文件
            folder_path = os.path.dirname(file_path)
            c_file = None
            c_item_file = None
            
            # 从已经识别的layout数据文件中查找
            if hasattr(self, 'folder_files') and 'layoutData' in self.folder_files:
                layout_files = self.folder_files['layoutData']
                print(f"使用已识别的layout数据文件: {layout_files}")
                
                # 读取每个layout数据文件，根据字段内容判断类型
                for filename in layout_files:
                    file_path_check = os.path.join(folder_path, filename)
                    try:
                        df = pd.read_excel(file_path_check, nrows=1)
                        columns = df.columns.tolist()
                        
                        # 根据字段内容判断哪个是C文件，哪个是C_item文件
                        if 'Orient.' in columns and 'X' in columns and 'Y' in columns:
                            c_file = file_path_check
                            print(f"识别为C文件: {filename}")
                        elif 'L' in columns and 'W' in columns and 'T' in columns:
                            c_item_file = file_path_check
                            print(f"识别为C_item文件: {filename}")
                    except Exception as e:
                        print(f"读取文件 {filename} 时出错: {e}")
                        continue
            
            # 如果还是没有找到，回退到原来的查找方式
            if not c_file or not c_item_file:
                print(f"从已识别文件中未找到合适的文件，回退到文件夹扫描...")
                for filename in os.listdir(folder_path):
                    if filename.lower() == 'c.xlsx':
                        c_file = os.path.join(folder_path, filename)
                    elif filename.lower() == 'c_item.xlsx':
                        c_item_file = os.path.join(folder_path, filename)
            
            if not c_file or not c_item_file:
                print(f"未找到合适的Layout数据文件")
                return None
            
            # 读取C.xlsx文件
            c_df = pd.read_excel(c_file)
            print(f"C.xlsx字段: {c_df.columns.tolist()}")
            
            # 读取C_item.xlsx文件
            c_item_df = pd.read_excel(c_item_file)
            print(f"C_item.xlsx字段: {c_item_df.columns.tolist()}")
            
            # 检查必需字段
            required_c_fields = ['RefDes', 'Orient.', 'X', 'Y']
            required_item_fields = ['RefDes', 'L', 'W', 'T']
            
            for field in required_c_fields:
                if field not in c_df.columns:
                    print(f"C.xlsx缺少必需字段: {field}")
                    return None
            
            for field in required_item_fields:
                if field not in c_item_df.columns:
                    print(f"C_item.xlsx缺少必需字段: {field}")
                    return None
            
            # 解析数据
            c_info = []
            
            for _, row in c_df.iterrows():
                refdes = row['RefDes']
                x = row['X']
                y = row['Y']
                orient = row['Orient.']
                
                # 在C_item中查找对应的RefDes
                item_match = c_item_df[c_item_df['RefDes'] == refdes]
                
                if len(item_match) > 0:
                    item_row = item_match.iloc[0]
                    l = item_row['L']  # 长
                    w = item_row['W']  # 宽
                    t = item_row['T']  # 高
                    
                    # 计算外接矩形的四个角点坐标（考虑旋转）
                    left, top, right, bottom = self.calculate_rotated_rectangle(x, y, l, t, orient)
                    
                    c_info.append({
                        'RefDes': refdes,
                        'left': left,
                        'top': top,
                        'right': right,
                        'bottom': bottom,
                        'X': x,
                        'Y': y,
                        'L': l,
                        'W': w,
                        'T': t,
                        'Orient.': orient
                    })
                # else:
                    # print(f"未找到RefDes {refdes} 对应的尺寸信息，跳过")
            
            print(f"成功解析 {len(c_info)} 个元器件信息")
            return c_info
            
        except Exception as e:
            print(f"解析Layout数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_rotated_rectangle(self, x, y, l, t, orient):
        """计算旋转后的矩形四个角点坐标"""
        try:
            # 将旋转角度转换为弧度
            # orient为.270表示顺时针旋转270度，orient为-270表示逆时针旋转270度
            angle_rad = math.radians(float(orient))
            
            # 计算矩形的半长和半高
            half_l = l / 2
            half_t = t / 2
            
            # 原始矩形的四个角点（相对于中心点）
            corners = [
                (-half_l, -half_t),  # 左下
                (half_l, -half_t),   # 右下
                (half_l, half_t),    # 右上
                (-half_l, half_t)    # 左上
            ]
            
            # 应用旋转变换
            rotated_corners = []
            for corner_x, corner_y in corners:
                # 旋转公式
                new_x = corner_x * math.cos(angle_rad) - corner_y * math.sin(angle_rad)
                new_y = corner_x * math.sin(angle_rad) + corner_y * math.cos(angle_rad)
                rotated_corners.append((new_x + x, new_y + y))
            
            # 计算外接矩形的边界
            x_coords = [corner[0] for corner in rotated_corners]
            y_coords = [corner[1] for corner in rotated_corners]
            
            left = min(x_coords)
            top = min(y_coords)
            right = max(x_coords)
            bottom = max(y_coords)
            
            return left, top, right, bottom
            
        except Exception as e:
            print(f"计算旋转矩形失败: {e}")
            # 如果计算失败，返回未旋转的矩形
            return x - l/2, y - t/2, x + l/2, y + t/2

    def update_magnifier_point(self):
        if hasattr(self, 'canvasA_magnifier') and self.canvasA_magnifier:
            self.canvasA_magnifier.update_points(self.points_A)
        if hasattr(self, 'canvasB_magnifier') and self.canvasB_magnifier:
            self.canvasB_magnifier.update_points(self.points_B)
    def init_magnifier(self):
        self.clean_magnifier()
        # 检查图片是否已加载
        if hasattr(self, 'resized_imageA') and hasattr(self, 'resized_imageB') and self.resized_imageA and self.resized_imageB:
            self.canvasA_magnifier = ImageMagnifier(self.canvasA, self.resized_imageA, self.points_A, 0)
            self.canvasB_magnifier = ImageMagnifier(self.canvasB, self.resized_imageB, self.points_B, 1)
            if self.is_aligning:
                self.canvasA_magnifier.toggle_magnifier(1)
                self.canvasB_magnifier.toggle_magnifier(1)
        else:
            print("图片未加载，跳过初始化放大镜")
    def clean_magnifier(self):     
        if self.canvasA_magnifier:
            self.canvasA_magnifier.toggle_magnifier(0)
            self.canvasA_magnifier = None

        if self.canvasB_magnifier:
            self.canvasB_magnifier.toggle_magnifier(0)
            self.canvasB_magnifier = None
    def update_content(self):
        """更新显示内容 - 简化版本，不再修改原始坐标"""
        # 尺寸未变 不重复渲染
        old_canvas_width = self.canvasA_width
        new_canvas_width = self.canvasA.winfo_width()
        if old_canvas_width == new_canvas_width:
            return
        
        # 检查图片是否已加载
        if not hasattr(self, 'imageA') or not hasattr(self, 'imageB') or not self.imageA or not self.imageB:
            return
        
        # 直接更新图像显示，不修改原始坐标
        self.update_images()
        # 按开关控制放大镜
        if self.config.get("magnifier_switch") and self.is_aligning:
            self.init_magnifier()
        else:
            self.clean_magnifier()
    def update_images(self):
        # 检查图片是否存在，至少需要一张图片
        if not hasattr(self, 'imageA') or not self.imageA:
            print("热力图未加载，跳过更新")
            return
            
        # 获取窗口的当前大小
        canvasA_width = self.canvasA.winfo_width()
        canvasA_height = self.canvasA.winfo_height()
        canvasB_width = self.canvasB.winfo_width()
        canvasB_height = self.canvasB.winfo_height()

        if canvasA_width <= 1 or canvasA_height <= 1:
            return
      
        # 计算每个图片的宽度和高度
        imageA_width = canvasA_width
        imageB_width = canvasB_width
        self.canvasA_width = canvasA_width

        # 计算高度，保持原始宽高比
        aspectA = self.imageA.height / self.imageA.width
        imageA_height = int(imageA_width * aspectA)

        # 缩放热力图
        self.resized_imageA = self.imageA.resize((imageA_width, imageA_height), Image.LANCZOS)
        self.imageA_scale = imageA_width / self.imageA.width

        # 如果有Layout图，也进行缩放
        if hasattr(self, 'imageB') and self.imageB:
            aspectB = self.imageB.height / self.imageB.width
            imageB_height = int(imageB_width * aspectB)
            self.resized_imageB = self.imageB.resize((imageB_width, imageB_height), Image.LANCZOS)
            self.imageB_scale = imageB_width / self.imageB.width
        else:
            # 如果没有Layout图，创建一个空白图片
            imageB_height = imageA_height
            self.resized_imageB = Image.new('RGB', (imageB_width, imageB_height), color='white')
            self.imageB_scale = 1.0

        self.canvasA.delete("all")
        self.canvasB.delete("all")

        if self.is_aligning:
            imageB_np = self.to_numpy_image(self.resized_imageB)
            imageA_np = self.to_numpy_image(self.resized_imageA)

            # 将原始图像坐标转换为显示坐标
            if len(self.points_A) > 0:
                display_points_A = [[point[0] * self.imageA_scale, point[1] * self.imageA_scale] for point in self.points_A]
                imageA_np = draw_points_circle_ring_text(imageA_np, display_points_A)
            
            if len(self.points_B) > 0:
                display_points_B = [[point[0] * self.imageB_scale, point[1] * self.imageB_scale] for point in self.points_B]
                imageB_np = draw_points_circle_ring_text(imageB_np, display_points_B)
            
            self.resized_imageA = Image.fromarray(cv2.cvtColor(imageA_np, cv2.COLOR_BGR2RGB))
            self.resized_imageB = Image.fromarray(cv2.cvtColor(imageB_np, cv2.COLOR_BGR2RGB))

        self.tk_imageA = ImageTk.PhotoImage(self.resized_imageA)
        self.tk_imageB = ImageTk.PhotoImage(self.resized_imageB)
        # 清除画布上的旧图片
        # self.canvasA.delete("all")
        # self.canvasB.delete("all")
        # self.root.update_idletasks()  # 更新屏幕以确保显示效果

        # 更新背景图像位置和大小（基于中心点偏移 + 居中锚点）
        offsetA_x = (self.canvasA.winfo_width() - self.resized_imageA.width) // 2
        offsetA_y = (self.canvasA.winfo_height() - self.resized_imageA.height) // 2
        offsetB_x = (self.canvasB.winfo_width() - self.resized_imageB.width) // 2
        offsetB_y = (self.canvasB.winfo_height() - self.resized_imageB.height) // 2

        self.bg_imageA_id = self.canvasA.create_image(self.canvasA.winfo_width() // 2, self.canvasA.winfo_height() // 2, anchor=tk.CENTER, image=self.tk_imageA)
        self.bg_imageB_id = self.canvasB.create_image(self.canvasB.winfo_width() // 2, self.canvasB.winfo_height() // 2, anchor=tk.CENTER, image=self.tk_imageB)
        self.canvasA_offset = (offsetA_x, offsetA_y)
        self.canvasB_offset = (offsetB_x, offsetB_y)

        if not self.is_aligning and len(self.mark_rect_A) > 0:
            for itemA in self.mark_rect_A:
                draw_canvas_item(self.canvasA, itemA, self.imageA_scale, self.canvasA_offset, 0)
            for itemB in self.mark_rect_B:
                draw_canvas_item(self.canvasB, itemB, self.imageB_scale, self.canvasB_offset, 1)


        # if self.bg_imageA_id:
        #     self.canvasA.itemconfig(self.bg_imageA_id, image=self.tk_imageA)
        #     self.canvasA.coords(self.bg_imageA_id, 0, (canvasA_height - imageA_height) // 2)
        # else:
        #     self.bg_imageA_id = self.canvasA.create_image(0, (canvasA_height - imageA_height) // 2, anchor=tk.NW, image=self.tk_imageA)

        # if self.bg_imageB_id:
        #     self.canvasB.itemconfig(self.bg_imageB_id, image=self.tk_imageB)
        #     self.canvasB.coords(self.bg_imageB_id, 0, (canvasB_height - imageB_height) // 2)
        # else:
        #     self.bg_imageB_id = self.canvasB.create_image(0, (canvasB_height - imageB_height) // 2, anchor=tk.NW, image=self.tk_imageB)

        # # 在 Canvas 上绘制两张图片
        # self.canvasA.create_image(0, (canvasA_height - imageA_height) // 2, anchor=tk.NW, image=self.tk_imageA)
        # self.canvasB.create_image(0, (canvasB_height - imageB_height) // 2, anchor=tk.NW, image=self.tk_imageB)

        #缩放比  当前图片 / 原始图片
        self.canvasA.config(height=imageA_height)  # 重新设置 Canvas 的高度
        self.canvasB.config(height=imageB_height)  # 重新设置 Canvas 的高度

    def on_resize(self, event):
        # 每当窗口尺寸变化时，延迟更新图像，避免频繁触发更新
        if self.resize_after:
            self.root.after_cancel(self.resize_after)
        self.resize_after = self.root.after(20, self.update_content)
    def load_default_imgs(self, showTip = True):
        """加载默认图片或从当前文件夹加载图片"""
        if self.current_folder_path:
            # 如果已经选择了文件夹，从文件夹中加载图片
            self.scan_folder_files()
            if showTip:
                show_toast(
                    title='加载成功',
                    message='已从当前文件夹加载图片',
                    duration=3000,
                    toast_type='success'
                )
        else:
            # 如果没有选择文件夹，尝试加载默认图片
            content = ""
            if os.path.isfile(Constants.imageA_default_path):  # 检查文件是否存在
                self.set_image(Constants.imageA_default_path, 0)
            else:
                content += Constants.imageA_default_path + " "
              
            if os.path.isfile(Constants.imageB_default_path):  # 检查文件是否存在
                self.set_image(Constants.imageB_default_path, 1)
            else:
                content += Constants.imageB_default_path + ""

            if showTip and content:
                show_toast(
                    title='文件不存在',
                    message= content + "文件不存在，\n请检查文件命名",
                    duration=5000,
                    toast_type='error'
                )
    def check_points_finish(self):
        content = ""
        if len(self.points_A) < 3:
        # if not os.path.isfile(Constants.imageA_point_path()):  # 检查文件是否存在
            content += "热力图未完成打点 "
          
        if len(self.points_B) < 3:
        #if not os.path.isfile(Constants.imageB_point_path()):  # 检查文件是否存在
           content += "Layout图未完成打点 "

        if content:
            show_toast(
                title='打点标记未完成',
                message= content + "\n请先对图片进行'打点标记'",
                duration=5000,
                toast_type='warning'
            )
        return content
    def update_points(self, clearAll = False):
        """更新画布上的打点显示 - 将原始图像坐标转换为canvas坐标"""
        if clearAll:
            self.canvasA.delete("points_A")
            self.canvasB.delete("points_B")
            return
        
        if not self.is_aligning:
            return
        
        radius = 4
        self.canvasA.delete("points_A")
        
        # 将原始图像坐标转换为canvas坐标
        offAx, offAy = getattr(self, 'canvasA_offset', (0, 0))
        for point in self.points_A:
            # 原始图像坐标 -> 显示坐标
            display_x = point[0] * self.imageA_scale
            display_y = point[1] * self.imageA_scale
            
            # 显示坐标 -> canvas坐标（中心偏移）
            canvas_x = display_x + offAx
            canvas_y = display_y + offAy
            
            y0 = min(canvas_y - radius, self.canvasA.winfo_height())
            y1 = min(canvas_y + radius, self.canvasA.winfo_height())
            self.canvasA.create_oval(canvas_x - radius, y0, canvas_x + radius, y1, fill="black", tags="points_A")

        self.canvasB.delete("points_B")
        offBx, offBy = getattr(self, 'canvasB_offset', (0, 0))
        for point in self.points_B:
            # 原始图像坐标 -> 显示坐标
            display_x = point[0] * self.imageB_scale
            display_y = point[1] * self.imageB_scale
            
            # 显示坐标 -> canvas坐标（中心偏移）
            canvas_x = display_x + offBx
            canvas_y = display_y + offBy
            
            y0 = min(canvas_y - radius, self.canvasB.winfo_height())
            y1 = min(canvas_y + radius, self.canvasB.winfo_height())
            self.canvasB.create_oval(canvas_x - radius, y0, canvas_x + radius, y1, fill="red", tags="points_B")
    def save_points_json(self):
        """保存打点数据为JSON格式，使用图像坐标"""
        try:
            if len(self.points_A) >= 3 and len(self.points_B) >= 3:
                # 获取原始图像尺寸
                aW, aH = self.imageA.size
                bW, bH = self.imageB.size
                
                # 统一转为可序列化的list（兼容list/ndarray）
                import numpy as _np
                points_A_list = _np.asarray(self.points_A).tolist()
                points_B_list = _np.asarray(self.points_B).tolist()

                points_data = {
                    'points_A': points_A_list,
                    'points_B': points_B_list,
                    'image_A_size': [aW, aH],
                    'image_B_size': [bW, bH],
                    'timestamp': datetime.now().isoformat()
                }
                
                if self.current_folder_path:
                    points_dir = os.path.join(self.current_folder_path, "points")
                    if not os.path.exists(points_dir):
                        os.makedirs(points_dir)
                    # 使用规范命名：热力图文件名 + '_' + Layout文件名 + '.json'
                    heat_filename = self.current_files.get("heat", "")
                    layout_filename = self.current_files.get("layout", "")
                    if not heat_filename or not layout_filename:
                        print("保存打点数据失败：缺少热力图或Layout图文件名")
                        return
                    heat_name = os.path.splitext(heat_filename)[0]
                    layout_name = os.path.splitext(layout_filename)[0]
                    points_file = os.path.join(points_dir, f"{heat_name}_{layout_name}.json")
                    print(f"保存打点数据到: {points_file}")
                    
                    with open(points_file, 'w', encoding='utf-8') as f:
                        json.dump(points_data, f, indent=2, ensure_ascii=False)
                    
                    print("打点数据已保存为JSON格式")
                else:
                    print("没有当前文件夹路径，无法保存打点数据")
            else:
                print(f"打点数量不足，无法保存（A: {len(self.points_A)}, B: {len(self.points_B)}）")
        except Exception as e:
            print(f"保存打点数据失败: {e}")
            import traceback
            traceback.print_exc()

    def save_points_csv(self):
        aW, aH = self.resized_imageA.size
        points_A_save = np.vstack([np.array([[aW, aH]], dtype='float32'), self.points_A])
        # 检查 points_A 的每一行数据是否符合条件
        A_save = True
        # for i in range(0, len(self.points_A)):  # 从第二行开始检查
        #     if self.points_A[i, 0] > aW or self.points_A[i, 1] > aH:
        #         A_save = False
        #         print("Data violation found, returning without saving.")
        #         break 
        if A_save:
            # 使用正确的路径构建方式
            if self.current_folder_path:
                points_dir = os.path.join(self.current_folder_path, "points")
                if not os.path.exists(points_dir):
                    os.makedirs(points_dir)
                
                # 使用新的文件名格式：{热力图文件名}_{Layout图文件名}_imageA.csv
                heat_filename = self.current_files.get("heat", "")
                layout_filename = self.current_files.get("layout", "")
                
                if heat_filename and layout_filename:
                    # 去掉文件扩展名
                    heat_name = os.path.splitext(heat_filename)[0]
                    layout_name = os.path.splitext(layout_filename)[0]
                    
                    # 构建新的点位文件名
                    imageA_points_filename = f"{heat_name}_{layout_name}_imageA.csv"
                    imageA_points_path = os.path.join(points_dir, imageA_points_filename)
                    print(f"save_points_csv: 保存热力图点位到 {imageA_points_path}")
                    np.savetxt(imageA_points_path, points_A_save, delimiter=',', fmt='%d')
                else:
                    print("save_points_csv: 缺少热力图或Layout图文件名，无法保存点位数据")
            else:
                np.savetxt(Constants.imageA_point_path(), points_A_save, delimiter=',', fmt='%d')

        bW, bH = self.resized_imageB.size
        points_B_save = np.vstack([np.array([[bW, bH]], dtype='float32'), self.points_B])
        B_save = True
        # for i in range(0, len(self.points_B)):  # 从第二行开始检查
        #     if self.points_B[i, 0] > bW or self.points_B[i, 1] > bH:
        #         B_save = False
        #         print("Data violation found, returning without saving.")
        #         break 
        if B_save:
            # 使用正确的路径构建方式
            if self.current_folder_path:
                points_dir = os.path.join(self.current_folder_path, "points")
                if not os.path.exists(points_dir):
                    os.makedirs(points_dir)
                
                # 使用新的文件名格式：{热力图文件名}_{Layout图文件名}_imageB.csv
                heat_filename = self.current_files.get("heat", "")
                layout_filename = self.current_files.get("layout", "")
                
                if heat_filename and layout_filename:
                    # 去掉文件扩展名
                    heat_name = os.path.splitext(heat_filename)[0]
                    layout_name = os.path.splitext(layout_filename)[0]
                    
                    # 构建新的点位文件名
                    imageB_points_filename = f"{heat_name}_{layout_name}_imageB.csv"
                    imageB_points_path = os.path.join(points_dir, imageB_points_filename)
                    print(f"save_points_csv: 保存Layout图点位到 {imageB_points_path}")
                    np.savetxt(imageB_points_path, points_B_save, delimiter=',', fmt='%d')
                else:
                    print("save_points_csv: 缺少热力图或Layout图文件名，无法保存点位数据")
            else:
                np.savetxt(Constants.imageB_point_path(), points_B_save, delimiter=',', fmt='%d')
    def get_points(self, points_path, canvas):
         # 如果文件不存在，返回空数组
        if not os.path.exists(points_path):
            return []
        data = np.loadtxt(points_path, delimiter=',', dtype=np.float32)
        if data.shape[0] < 4:
            return []
        w, h = data[0]  # 第一行代表宽（w）和高（h）
        points = data[1:]  # 剩下的3行是坐标点
        scale = canvas.winfo_width() / w   # 当窗口打开时，不是保存时的窗口大小了
        print("get_points -> ", canvas.winfo_width(), w, scale, points * scale)
        return points * scale
    def clear_point_file(self):
        if self.current_folder_path:
            points_dir = os.path.join(self.current_folder_path, "points")
            
            # 使用新的文件名格式
            heat_filename = self.current_files.get("heat", "")
            layout_filename = self.current_files.get("layout", "")
            
            if heat_filename and layout_filename:
                # 去掉文件扩展名
                heat_name = os.path.splitext(heat_filename)[0]
                layout_name = os.path.splitext(layout_filename)[0]
                
                # 构建新的点位文件名
                imageA_points_filename = f"{heat_name}_{layout_name}_imageA.csv"
                imageB_points_filename = f"{heat_name}_{layout_name}_imageB.csv"
                
                imageA_points_path = os.path.join(points_dir, imageA_points_filename)
                imageB_points_path = os.path.join(points_dir, imageB_points_filename)
                
                print(f"clear_point_file: 清除点位文件 - {imageA_points_filename}, {imageB_points_filename}")
                self.remove_file(imageA_points_path)
                self.remove_file(imageB_points_path)
            else:
                print("clear_point_file: 缺少热力图或Layout图文件名，无法清除点位文件")
        else:
            self.remove_file(Constants.imageA_point_path())
            self.remove_file(Constants.imageB_point_path())
    def remove_file(self, file_path):
        try:
            os.remove(file_path)
            # print(f"{file_path} 已成功删除。")
        except FileNotFoundError:
            print(f"文件 {file_path} 未找到。")
        except PermissionError:
            print(f"没有权限删除文件 {file_path}。")
        except Exception as e:
            print(f"删除文件时发生错误: {e}")
    def unbind_point_event(self, canvas):
        # 绑定鼠标事件
        canvas.unbind("<Button-1>")
        canvas.unbind("<Button-3>")
    def bind_point_event(self, canvas, index):
        canvas.bind("<Button-1>", lambda event: self.point_mouse_click(event, index)) # 左键
        canvas.bind("<Button-3>", lambda event: self.point_mouse_click(event, index))  # 右键
        # self.canvasA.bind("<Motion>", self.point_mouse_move)     # 鼠标移动

    def get_click_point(self, circles, x, y):
        if self.config.get("circle_switch"):
            ret = find_circle_containing_point(circles, x, y)
            if ret:
                return [ret[0], ret[1]]
        
        return [x, y]

    def point_mouse_click(self, event, index):
        """处理打点点击事件 - 将canvas坐标转换为原始图像坐标"""
        x, y = event.x, event.y
        range = 16
        
        if index == 0:
            points = self.points_A.copy()
            offx, offy = getattr(self, 'canvasA_offset', (0, 0))
            scale = self.imageA_scale
            recognize_circles = self.recognize_circle_A 
        else:
            points = self.points_B.copy()
            offx, offy = getattr(self, 'canvasB_offset', (0, 0))
            scale = self.imageB_scale
            recognize_circles = self.recognize_circle_B

        # canvas坐标 -> 显示坐标
        display_x = x - offx
        display_y = y - offy
        
        # 显示坐标 -> 原始图像坐标
        original_x = display_x / scale
        original_y = display_y / scale
        
        if event.num == 1:  # 左键点击
            # 允许更多对齐点（提升精度），上限设为8个
            MAX_POINTS = 8
            if len(points) >= MAX_POINTS:
                messagebox.showinfo("提示", f"最多标记{MAX_POINTS}个点")
                return
            # 使用原始图像坐标
            points.append([original_x, original_y])
            self.pont_marked = True
            print(f"左键点击: canvas({x}, {y}) -> 原始图像({original_x:.1f}, {original_y:.1f})")
        elif event.num == 3:  # 右键点击
            print("point_mouse_click1 -> ", points)
            # 在原始图像坐标中查找要删除的点
            points = [[cx, cy] for cx, cy in points if not (original_x - range/scale <= cx <= original_x + range/scale and original_y - range/scale <= cy <= original_y + range/scale)]
            self.pont_marked = True
            print(f"右键点击: canvas({x}, {y}) -> 原始图像({original_x:.1f}, {original_y:.1f})")

        print("point_mouse_click2 -> ", points)
        if index == 0:
            self.points_A = points
        else:
            self.points_B = points

        self.update_images()
        if self.config.get("magnifier_switch") and self.is_aligning:
            self.init_magnifier()
        else:
            self.clean_magnifier()
        # self.update_points()
        # self.update_magnifier_point()
    def start_point_mark(self):
        if self.is_aligning:
            if self.check_points_finish():  # 检查是否打点完成（各≥3）
                return
            # 检查两侧点数是否一致
            if len(self.points_A) != len(self.points_B):
                show_toast(
                    title='打点数量不匹配',
                    message=f'A侧: {len(self.points_A)} 个, B侧: {len(self.points_B)} 个\n请保证两侧点数相同且≥3',
                    duration=5000,
                    toast_type='warning'
                )
                return
            # 先尝试构建转换器，失败则提示并留在打点模式
            try:
                temp_transformer = PointTransformer(self.points_A, self.points_B)
            except Exception as e:
                show_toast(
                    title='对齐失败',
                    message=f'点位异常：{e}\n请检查两侧点的对应关系与数量',
                    duration=6000,
                    toast_type='error'
                )
                return
            
            self.is_aligning = False

            # 重新打点 清除编辑框
            if self.pont_marked:
                self.mark_rect_A = []
                self.mark_rect_B = []
                self.pont_marked = False

            # self.update_points(True)
            # 保存结果
            self.unbind_point_event(self.canvasA)
            self.unbind_point_event(self.canvasB)
            self.save_points_json()
            self.update_images()
            # 保存后立刻刷新对齐按钮可见性
            self.update_align_buttons_visibility()

            # 对齐工具类
            self.point_transformer = temp_transformer

            # 放大镜：结束打点后根据开关关闭
            self.clean_magnifier()

            # self.start_margin()
            self.align_button.config(text="对齐图像开始")  # 切换为结束状态
            # 隐藏清除对齐点按钮
            self.clear_heat_points_button.grid_forget()
            self.clear_layout_points_button.grid_forget()
            # 隐藏Layout图下方的按钮框架
            self.bottom_buttons_frame_B.grid_forget()
            # 显示原来的按钮
            self.margin_before_button.grid(row=0, column=0, padx=5)
            self.margin_after_button.grid(row=0, column=1, padx=5)

        else:
            self.is_aligning = True
            self.bind_point_event(self.canvasA, 0)
            self.bind_point_event(self.canvasB, 1)
            # self.update_points()
            self.update_images()

            if self.config.get("magnifier_switch"):
                self.init_magnifier()

            # if self.config.get("circle_switch"):
            #     self.recognize_circle_A = detect_A_circles(self.to_numpy_image(self.imageA))
            #     self.recognize_circle_B = detect_B_circles(self.to_numpy_image(self.imageB))
            #     print("recognize_circle_A ----->>", len(self.recognize_circle_A), len(self.recognize_circle_B))


            # self.points_B = np.array(np.loadtxt(Constants.imageB_point_path(), delimiter=','), dtype=np.float32) * self.window_scale
            # 读取本地文件
            self.margin_before_button.grid_forget()
            self.margin_after_button.grid_forget()
            # 显示清除对齐点按钮
            self.clear_heat_points_button.grid(row=0, column=0, padx=5, pady=5)
            self.clear_layout_points_button.grid(row=0, column=0, padx=5, pady=5)
            # 显示Layout图下方的按钮框架
            self.bottom_buttons_frame_B.grid(row=2, column=2)
            self.align_button.config(text="对齐图像结束")  # 切换为开始状态
    
    def clear_heat_points(self):
        """清除热力图的对齐点"""
        try:
            # 清除热力图的对齐点数据
            self.points_A = []
            self.mark_rect_A = []
            
            # 清除对应的点位文件
            if self.current_folder_path:
                points_dir = os.path.join(self.current_folder_path, "points")
                heat_filename = self.current_files.get("heat", "")
                pcb_filename = self.current_files.get("pcb", "")
                
                if heat_filename and pcb_filename:
                    # 去掉文件扩展名
                    heat_name = os.path.splitext(heat_filename)[0]
                    pcb_name = os.path.splitext(pcb_filename)[0]
                    
                    # 构建点位文件名
                    imageA_points_filename = f"{heat_name}_{pcb_name}_imageA.csv"
                    imageA_points_path = os.path.join(points_dir, imageA_points_filename)
                    
                    print(f"clear_heat_points: 删除点位文件 {imageA_points_path}")
                    self.remove_file(imageA_points_path)
            
            # 清除画布上的标记
            self.canvasA.delete("all")
            if self.bg_imageA_id:
                self.canvasA.delete(self.bg_imageA_id)
                self.bg_imageA_id = None
            
            # 重新显示图片
            if self.imageA:
                self.update_images()
            
            # 重新初始化放大镜（严格按开关）
            if self.is_aligning and self.config.get("magnifier_switch"):
                self.init_magnifier()
            else:
                self.clean_magnifier()
            
            # 显示成功消息
            show_toast(
                title='清除成功',
                message='已清除热力图对齐点',
                duration=3000,
                toast_type='success'
            )
            print("已清除热力图对齐点")
            
        except Exception as e:
            print(f"清除热力图对齐点时出错: {e}")
            from tkinter import messagebox
            messagebox.showerror("错误", f"清除热力图对齐点失败: {e}")
    
    def clear_layout_points(self):
        """清除Layout图的对齐点"""
        try:
            # 清除Layout图的对齐点数据
            self.points_B = []
            self.mark_rect_B = []
            
            # 清除对应的点位文件
            if self.current_folder_path:
                points_dir = os.path.join(self.current_folder_path, "points")
                heat_filename = self.current_files.get("heat", "")
                layout_filename = self.current_files.get("layout", "")
                
                if heat_filename and layout_filename:
                    # 去掉文件扩展名
                    heat_name = os.path.splitext(heat_filename)[0]
                    layout_name = os.path.splitext(layout_filename)[0]
                    
                    # 构建点位文件名
                    imageB_points_filename = f"{heat_name}_{layout_name}_imageB.csv"
                    imageB_points_path = os.path.join(points_dir, imageB_points_filename)
                    
                    print(f"clear_layout_points: 删除点位文件 {imageB_points_path}")
                    self.remove_file(imageB_points_path)
            
            # 清除画布上的标记
            self.canvasB.delete("all")
            if self.bg_imageB_id:
                self.canvasB.delete(self.bg_imageB_id)
                self.bg_imageB_id = None
            
            # 重新显示图片
            if self.imageB:
                self.update_images()
            
            # 重新初始化放大镜（如果在打点模式下且放大镜开关开启）
            if self.is_aligning and self.config.get("magnifier_switch"):
                self.init_magnifier()
            
            # 显示成功消息
            show_toast(
                title='清除成功',
                message='已清除Layout图对齐点',
                duration=3000,
                toast_type='success'
            )
            print("已清除Layout图对齐点")
            
        except Exception as e:
            print(f"清除Layout图对齐点时出错: {e}")
            from tkinter import messagebox
            messagebox.showerror("错误", f"清除Layout图对齐点失败: {e}")
    
    def load_points(self):
        """加载点位数据，现在从选择的文件夹中加载"""
        print(f"load_points: current_folder_path = {self.current_folder_path}")
        
        if self.current_folder_path:
            # 如果已经选择了文件夹，从文件夹中加载点位数据
            points_dir = os.path.join(self.current_folder_path, "points")
            print(f"load_points: points_dir = {points_dir}, exists = {os.path.exists(points_dir)}")

            if os.path.exists(points_dir):
                # 使用当前选择的热力图和Layout图文件名构建点位文件名（JSON）
                heat_filename = self.current_files.get("heat", "")
                layout_filename = self.current_files.get("layout", "")
                
                if heat_filename and layout_filename:
                    # 去掉文件扩展名
                    heat_name = os.path.splitext(heat_filename)[0]
                    layout_name = os.path.splitext(layout_filename)[0]
                    
                    json_points_path = os.path.join(points_dir, f"{heat_name}_{layout_name}.json")
                    print(f"load_points: 尝试加载 {json_points_path}, exists = {os.path.exists(json_points_path)}")
                    
                    if os.path.exists(json_points_path):
                        with open(json_points_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        self.points_A = data.get('points_A', [])
                        self.points_B = data.get('points_B', [])
                        print(f"load_points: loaded points_A = {self.points_A}")
                        print(f"load_points: loaded points_B = {self.points_B}")
                        
                        if hasattr(self, 'imageA') and hasattr(self, 'imageB') and self.imageA and self.imageB:
                            self.init_point_transformer()
                        # 加载完点位后，立即刷新按钮可见性
                        self.update_align_buttons_visibility()
                    else:
                        print("load_points: 未找到json点位文件")
                else:
                    print("load_points: 缺少热力图或Layout图文件名，无法加载点位数据")
            else:
                print("load_points: points目录不存在")
        else:
            # 如果没有选择文件夹，尝试加载user_data/A/points下的默认点位数据
            print("load_points: 没有选择文件夹，尝试加载默认点位数据")
            default_imageA_path = "user_data/A/points/imageA.jpg_points.csv"
            default_imageB_path = "user_data/A/points/imageB.jpg_points.csv"
            
            print(f"load_points: 尝试加载 {default_imageA_path}, exists = {os.path.exists(default_imageA_path)}")
            print(f"load_points: 尝试加载 {default_imageB_path}, exists = {os.path.exists(default_imageB_path)}")
            
            self.points_A = self.get_points(default_imageA_path, self.canvasA)
            self.points_B = self.get_points(default_imageB_path, self.canvasB)
            
            print(f"load_points: 默认加载 points_A = {self.points_A}")
            print(f"load_points: 默认加载 points_B = {self.points_B}")
            
            if len(self.points_A) > 0 and len(self.points_B) > 0:
                self.init_point_transformer()

    def init_point_transformer(self):
        """初始化点转换器"""
        if len(self.points_A) > 0:
            self.point_transformer = PointTransformer(self.points_A, self.points_B)
    
    def clear_and_reload_points(self):
        """清空当前对齐点数据并重新加载对应文件的点位数据"""
        try:
            print("clear_and_reload_points: 清空当前对齐点数据")
            
            # 清空当前的对齐点数据
            self.points_A = []
            self.points_B = []
            self.mark_rect_A = []
            self.mark_rect_B = []
            self.point_transformer = None
            
            # 清空画布上的标记
            if hasattr(self, 'canvasA'):
                self.canvasA.delete("all")
                if self.bg_imageA_id:
                    self.canvasA.delete(self.bg_imageA_id)
                    self.bg_imageA_id = None
            
            if hasattr(self, 'canvasB'):
                self.canvasB.delete("all")
                if self.bg_imageB_id:
                    self.canvasB.delete(self.bg_imageB_id)
                    self.bg_imageB_id = None
            
            # 重新显示图片（不显示对齐点）
            if hasattr(self, 'imageA') and hasattr(self, 'imageB') and self.imageA and self.imageB:
                self.update_images()
            
            # 尝试加载新文件组合对应的点位数据
            self.load_points()
            
            print("clear_and_reload_points: 完成清空和重新加载")
            
        except Exception as e:
            print(f"clear_and_reload_points 出错: {e}")
            import traceback
            traceback.print_exc()

    def to_mark_rect_B(self, itemA):
        # 初始化一个空字典
        ret = {}
        # 确保有point_transformer对象
        if self.point_transformer:
            # 对特定字段进行转换
            ret["x1"], ret["y1"] = self.point_transformer.A_2_oriB(itemA.get("x1"), itemA.get("y1"))
            ret["x2"], ret["y2"] = self.point_transformer.A_2_oriB(itemA.get("x2"), itemA.get("y2"))
            ret["cx"], ret["cy"] = self.point_transformer.A_2_oriB(itemA.get("cx"), itemA.get("cy"))

        # 复制 itemA 中其他字段到 ret 字典
        for key, value in itemA.items():
            if key not in ret:
                ret[key] = value

        return ret
    def on_close_editor(self, mark_rect_A, add_new_count, delete_new_count, modify_origin_set):
        self.edit_log["add_new_mark"][1] += add_new_count
        self.edit_log["delete_origin_mark"][1] += delete_new_count
        self.edit_log["modify_origin_mark"][1].update(modify_origin_set)

        print("modify_origin_set -------->>> ", self.edit_log, len(modify_origin_set))

        if len(mark_rect_A) > 0:
            self.mark_rect_A = mark_rect_A

            ret = []
            for itemA in mark_rect_A: 
                ret.append(self.to_mark_rect_B(itemA))
            self.mark_rect_B = ret

            self.update_images()
        
        # 清空EditorCanvas实例引用
        self.editor_canvas = None
    def on_template_confirm(self, dialog_result):
        min_temp, max_temp, min_width, min_height, max_ratio, auto_reduce, color = dialog_result.get("min_temp"), dialog_result.get("max_temp"), dialog_result.get("min_width"), \
            dialog_result.get("min_height"), dialog_result.get("max_ratio"), dialog_result.get("auto_reduce"), dialog_result.get("color"), 
        
        # 获取新的PCB参数
        p_w = dialog_result.get("p_w", 237)
        p_h = dialog_result.get("p_h", 194)
        p_origin = dialog_result.get("p_origin", "左下")
        p_origin_offset_x = dialog_result.get("p_origin_offset_x", 0)
        p_origin_offset_y = dialog_result.get("p_origin_offset_y", 0)
        c_padding_left = dialog_result.get("c_padding_left", 0)
        c_padding_top = dialog_result.get("c_padding_top", 0)
        c_padding_right = dialog_result.get("c_padding_right", 0)
        c_padding_bottom = dialog_result.get("c_padding_bottom", 0)
        
        # 检查并初始化point_transformer
        if self.point_transformer is None:
            if len(self.points_A) > 0 and len(self.points_B) > 0:
                self.init_point_transformer()
            else:
                # messagebox.showwarning("警告", "请先进行图像对齐")
                show_toast(
                    title='警告',
                    message= "请先进行图像对齐",
                    duration=5000,
                    toast_type='warning'
                )
                return
        
        # 检查tempALoader是否存在
        if not hasattr(self, 'tempALoader') or self.tempALoader is None:
            print("警告：tempALoader不存在，请先加载温度数据文件")
            messagebox.showwarning("警告", "请先加载温度数据文件")
            return
        
        # 检查Layout数据是否存在
        if not hasattr(self, 'layout_data') or self.layout_data is None:
            print("警告：Layout数据不存在，请先加载Layout数据文件")
            messagebox.showwarning("警告", "请先加载Layout数据文件")
            return
        
        # 检查Layout数据是否为空列表
        if isinstance(self.layout_data, list) and len(self.layout_data) == 0:
            print("警告：Layout数据为空，请检查Layout数据文件")
            messagebox.showwarning("警告", "Layout数据为空，请检查Layout数据文件")
            return
        
        # 使用新的Layout查询方法
        try:
            # 检查必要的数据是否存在
            print("=== 开始Layout温度查询 ===")
            print(f"Layout数据: {self.layout_data is not None and len(self.layout_data) if self.layout_data else 0} 个元器件")
            print(f"温度数据: {self.tempALoader.get_tempA().shape if self.tempALoader and self.tempALoader.get_tempA() is not None else 'None'}")
            print(f"点转换器: {self.point_transformer is not None}")
            print(f"Layout图像: {self.imageB.size if self.imageB else 'None'}")
            
            if self.layout_data is None or len(self.layout_data) == 0:
                raise Exception("Layout数据为空，请先加载Layout数据文件")
            
            if self.tempALoader is None or self.tempALoader.get_tempA() is None:
                raise Exception("温度数据为空，请先加载温度数据文件")
            
            if self.point_transformer is None:
                raise Exception("点转换器未初始化，请先完成图像对齐")
            
            # 使用优化版的温度查询
            layout_query = LayoutTemperatureQueryOptimized(
                layout_data=self.layout_data,
                temp_data=self.tempALoader.get_tempA().copy(),
                point_transformer=self.point_transformer,
                p_w=p_w,
                p_h=p_h,
                p_origin=p_origin,
                p_origin_offset_x=p_origin_offset_x,
                p_origin_offset_y=p_origin_offset_y,
                c_padding_left=c_padding_left,
                c_padding_top=c_padding_top,
                c_padding_right=c_padding_right,
                c_padding_bottom=c_padding_bottom,
                layout_image=self.imageB  # 传递Layout图像
            )
            
            # 执行智能过滤版温度查询
            self.mark_rect_A, self.mark_rect_B = layout_query.query_temperature_by_layout_smart_filter(min_temp, max_temp)
            
            print(f"智能过滤版Layout查询完成，找到 {len(self.mark_rect_A)} 个高温元器件")
            
        except Exception as e:
            print(f"Layout查询出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 不使用YOLO回退，强制使用Layout方法
            print("Layout查询失败，请检查数据完整性")
            messagebox.showerror("错误", f"Layout温度查询失败: {e}\n请检查：\n1. Layout数据是否正确加载\n2. 温度数据是否正确加载\n3. 图像对齐是否完成")
            
            # 清空结果
            self.mark_rect_A = []
            self.mark_rect_B = []

        self.update_images()
        

        # temp_imageA = Image.fromarray(cv2.cvtColor(self.imageA_cv_export, cv2.COLOR_BGR2RGB))
        # cv2.imshow("imageA mark", cv2.resize(imageA_cv, (1024, 768)))
        # cv2.imshow("imageA mark", cv2.resize(imageA_cv, (1024, 768)))
        # EditorCanvas(root, image=Image.open("imageA.jpg"), mark_rect=mark_rect, on_close_callback=on_window_close)
        self.edit_log = copy.deepcopy(DEFAULT_EDIT_LOG)
        # self.edit_log["modify_origin_mark"][1].clear()
        self.edit_log["origin_mark"][1] = len(self.mark_rect_A)
        # EditorCanvas(self.root, self.imageA, self.mark_rect_A, on_close_callback=self.on_close_editor)

    def open_template_dialog(self):
        print("点击温度过滤按钮，开始创建对话框...")
        try:
            print(f"当前文件夹路径: {self.current_folder_path}")
            templateDialog = TemplateDialog(self.root, self.template_filter_button, self.on_template_confirm, self.current_folder_path)
            print("TemplateDialog创建成功，准备打开对话框...")
            
            # 在打开对话框前，同步文件信息到温度配置管理器
            print("同步文件信息到温度配置管理器...")
            self.update_temp_config_files()
            
            templateDialog.open()
            print("对话框打开完成")
        except Exception as e:
            print(f"创建或打开对话框时出错: {e}")
            import traceback
            traceback.print_exc()
        # if self.min_temp:
        #     templateDialog.open(self.min_temp, self.max_temp, self.min_width, self.min_height, self.max_ratio, self.auto_reduce)
        # else:    
        #     templateDialog.open()
    def export_excel(self):
        if self.mark_rect_A:
            # 确定输出目录路径
            if self.current_folder_path:
                output_dir = os.path.join(self.current_folder_path, "output")
            else:
                output_dir = "output"
            
            # 创建输出目录
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 创建一个新的 Excel 工作簿
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "温度报告"
            # 添加标题行
            ws.append(["目标", "最高温度"])
            # 将 rect_arr 中的数据写入到 Excel 文件
            for item in self.mark_rect_A:
                ws.append([item["name"], item["max_temp"]])
               
            # 保存Excel文件到当前文件夹的output目录，如果文件被占用则自动重命名
            excel_path = self.get_available_excel_path(output_dir, "report.xlsx")
            wb.save(excel_path)

            # 保存图片到当前文件夹的output目录
            imageA_input = cv2.cvtColor(np.array(self.imageA), cv2.COLOR_RGB2BGR)
            imageA_output = draw_numpy_image_item(imageA_input, self.mark_rect_A)
            image_path = os.path.join(output_dir, "A.jpg")
            Image.fromarray(cv2.cvtColor(imageA_output, cv2.COLOR_BGR2RGB)).save(image_path)

            #输出日志
            self.edit_log["final_mark"][1] = len(self.mark_rect_A)
            self.save_log_file()

            show_toast(
                title='导出成功',
                message= f"导出报告成功，报告位于 {excel_path}",
                duration=5000,
                toast_type='success'
            )
        else:
            show_toast(
                title='导出失败',
                message= "请先进行'温度过滤'， 找出温度区域",
                duration=5000,
                toast_type='error'
            )
    
    def get_available_excel_path(self, output_dir, base_filename):
        """
        获取可用的Excel文件路径，如果文件被占用则自动重命名
        
        Args:
            output_dir: 输出目录
            base_filename: 基础文件名（如 "report.xlsx"）
            
        Returns:
            str: 可用的文件路径
        """
        import os
        
        # 分离文件名和扩展名
        name, ext = os.path.splitext(base_filename)
        
        # 尝试原始文件名
        original_path = os.path.join(output_dir, base_filename)
        
        # 如果文件不存在，直接返回原始路径
        if not os.path.exists(original_path):
            return original_path
        
        # 如果文件存在，尝试重命名
        counter = 1
        while True:
            new_filename = f"{name}{counter}{ext}"
            new_path = os.path.join(output_dir, new_filename)
            
            if not os.path.exists(new_path):
                print(f"文件 {base_filename} 已存在，使用新文件名: {new_filename}")
                return new_path
            
            counter += 1
            
            # 防止无限循环，最多尝试100次
            if counter > 100:
                print(f"警告：无法找到可用的文件名，使用时间戳")
                import time
                timestamp = int(time.time())
                timestamp_filename = f"{name}_{timestamp}{ext}"
                return os.path.join(output_dir, timestamp_filename)

        # print("xx--> export_excel")
    def open_settings_dialog(self):
        # 使用单例模式，只创建一个SettingDialog实例
        if self.setting_dialog is None:
            self.setting_dialog = SettingDialog(self.root, self.settings_button, None)
        self.setting_dialog.open()
    def load_local_image(self, index):
        img_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.png;*.jpeg")])
        if not img_path:
            return
        self.set_image(img_path, index)
    def set_image(self, path = Constants.imageA_default_path, index = 0):
        try:
            if not os.path.exists(path):
                print(f"图片文件不存在: {path}")
                return
                
            if index == 0:
                self.imageA = Image.open(path)
                self.mark_rect_A = []
                # 切换热力图后，清空对应打点，避免误判有点位
                self.points_A = []
                print(f"成功加载热力图: {path}")
            elif index == 1:
                self.imageB = Image.open(path)
                # 直接使用原图，不再强制缩放
                print(f"Layout图像尺寸: {self.imageB.size}")
                self.mark_rect_B = []
                # 切换Layout图后，清空对应打点，避免误判有点位
                self.points_B = []
                print(f"成功加载Layout图: {path}")

            if self.imageB and self.imageA:
                print(f"图像尺寸 - 热力图: {self.imageA.width}x{self.imageA.height}, Layout图: {self.imageB.width}x{self.imageB.height}")
            
            # 无论是否两个图片都加载完成，都尝试更新显示
            self.update_images()

            # 尝试自动加载与当前文件组合对应的打点JSON
            self.load_points()
            # 根据是否存在打点数据，更新对齐按钮可见性
            if hasattr(self, 'update_align_buttons_visibility'):
                self.update_align_buttons_visibility()
        except Exception as e:
            print(f"加载图片时出错: {e}")
    def margin_before(self):
        try:
            # 检查图像是否存在
            if not hasattr(self, 'resized_imageA') or not hasattr(self, 'resized_imageB') or \
               self.resized_imageA is None or self.resized_imageB is None:
                print("警告：图像数据不存在，无法进行图像混合")
                return
                
            # 将 Pillow 图像对象转换为 NumPy 数组
            imageB_np = np.array(self.resized_imageB)
            imageA_np = np.array(self.resized_imageA)
            
            print(f"margin_before - 原始图像形状 - imageA: {imageA_np.shape}, imageB: {imageB_np.shape}")
            
            # 检查图像尺寸是否匹配
            if imageA_np.shape != imageB_np.shape:
                print(f"警告：图像尺寸不匹配 - imageA: {imageA_np.shape}, imageB: {imageB_np.shape}")
                # 将imageB调整到与imageA相同的尺寸
                imageB_np = cv2.resize(imageB_np, (imageA_np.shape[1], imageA_np.shape[0]))
                print(f"调整后 - imageB: {imageB_np.shape}")
            
            # 如果是 RGB 图像，OpenCV 默认处理 BGR 格式，所以需要转换颜色顺序
            if imageB_np.ndim == 3:  # 这是 RGB 图像
                imageB_np = cv2.cvtColor(imageB_np, cv2.COLOR_RGB2BGR)
                imageA_np = cv2.cvtColor(imageA_np, cv2.COLOR_RGB2BGR)
                print(f"颜色转换后 - imageA: {imageA_np.shape}, imageB: {imageB_np.shape}")
            
            # 最终检查
            if imageA_np.shape != imageB_np.shape:
                print(f"错误：无法使两个图像尺寸匹配 - imageA: {imageA_np.shape}, imageB: {imageB_np.shape}")
                return
            
            print(f"开始图像混合 - imageA: {imageA_np.shape}, imageB: {imageB_np.shape}")
            blended = cv2.addWeighted(imageB_np, 0.33, imageA_np, 0.66, 0)
            cv2.imshow('before margin', blended)
            print("margin_before 图像混合完成")
            
        except Exception as e:
            print(f"margin_before 方法出错: {e}")
            import traceback
            traceback.print_exc()
    def margin_after(self):
        try:
            # 检查point_transformer是否存在
            if self.point_transformer is None:
                print("警告：point_transformer为None，无法进行图像对齐")
                return
                
            # 检查图像是否存在
            if not hasattr(self, 'resized_imageA') or not hasattr(self, 'resized_imageB') or \
               self.resized_imageA is None or self.resized_imageB is None:
                print("警告：图像数据不存在，无法进行图像对齐")
                return
                
            bW, bH = self.resized_imageB.size
            aW, aH = self.resized_imageA.size
            
            print(f"图像尺寸 - imageA: {aW}x{aH}, imageB: {bW}x{bH}")
            
            # 将 Pillow 图像对象转换为 NumPy 数组
            imageB_np = np.array(self.resized_imageB)
            imageA_np = np.array(self.resized_imageA)
            
            print(f"NumPy数组形状 - imageA: {imageA_np.shape}, imageB: {imageB_np.shape}")
            
            # 如果是 RGB 图像，OpenCV 默认处理 BGR 格式，所以需要转换颜色顺序
            if imageB_np.ndim == 3:  # 这是 RGB 图像
                imageB_np = cv2.cvtColor(imageB_np, cv2.COLOR_RGB2BGR)
                imageA_np = cv2.cvtColor(imageA_np, cv2.COLOR_RGB2BGR)
                print(f"颜色转换后 - imageA: {imageA_np.shape}, imageB: {imageB_np.shape}")
            
            # 获取原始坐标系下的 B->A 变换矩阵
            M_ori = self.point_transformer.get_B2A_matrix()
            M_ori = np.asarray(M_ori)
            print(f"原始坐标变换矩阵形状: {M_ori.shape}")

            # 将原始坐标变换矩阵换算到当前显示尺寸（resized）
            sA = float(self.imageA_scale)
            sB = float(self.imageB_scale)
            if M_ori.shape == (2, 3):
                # Affine: pA_ori = A * pB_ori + t
                A = M_ori[:, :2]
                t = M_ori[:, 2:3]
                A_disp = (sA / sB) * A
                t_disp = sA * t
                M_disp = np.hstack([A_disp, t_disp]).astype(np.float32)
                aligned_imageB = cv2.warpAffine(imageB_np, M_disp, (aW, aH))
            elif M_ori.shape == (3, 3):
                # Homography: H_disp = S_A * H_ori * S_B^{-1}
                S_A = np.array([[sA, 0, 0], [0, sA, 0], [0, 0, 1]], dtype=np.float32)
                S_B_inv = np.array([[1.0 / sB, 0, 0], [0, 1.0 / sB, 0], [0, 0, 1]], dtype=np.float32)
                H_disp = (S_A @ M_ori @ S_B_inv).astype(np.float32)
                aligned_imageB = cv2.warpPerspective(imageB_np, H_disp, (aW, aH))
            else:
                print(f"未知的变换矩阵尺寸: {M_ori.shape}")
                return
            print(f"对齐后图像形状: {aligned_imageB.shape}")
            
            # 检查对齐后的图像尺寸是否与imageA匹配
            if aligned_imageB.shape != imageA_np.shape:
                print(f"警告：对齐后图像尺寸不匹配 - aligned_imageB: {aligned_imageB.shape}, imageA: {imageA_np.shape}")
                # 如果仍然不匹配，调整aligned_imageB的尺寸
                aligned_imageB = cv2.resize(aligned_imageB, (imageA_np.shape[1], imageA_np.shape[0]))
                print(f"调整后图像形状: {aligned_imageB.shape}")
            
            # 最终检查两个图像的形状是否完全匹配
            if aligned_imageB.shape != imageA_np.shape:
                print(f"错误：无法使两个图像尺寸匹配 - aligned_imageB: {aligned_imageB.shape}, imageA: {imageA_np.shape}")
                return
            
            print(f"开始图像混合 - aligned_imageB: {aligned_imageB.shape}, imageA: {imageA_np.shape}")
            blended = cv2.addWeighted(aligned_imageB, 0.33, imageA_np, 0.66, 0)
            cv2.imshow('after margin', blended)
            print("图像混合完成")
            
        except Exception as e:
            print(f"margin_after 方法出错: {e}")
            import traceback
            traceback.print_exc()

    def on_double_click(self, event):
        if len(self.mark_rect_A) > 0:
            # 检查EditorCanvas是否已经存在且可见
            if self.editor_canvas is not None and hasattr(self.editor_canvas, 'dialog') and self.editor_canvas.dialog.winfo_exists():
                # 如果EditorCanvas已存在，将其提到前台
                self.editor_canvas.dialog.lift()
                self.editor_canvas.dialog.focus_force()
                return
            
            # 创建新的EditorCanvas实例
            # 传递self作为parent，这样EditorCanvas可以访问到layout_data、point_transformer等属性
            self.editor_canvas = EditorCanvas(self, self.imageA, self.mark_rect_A, self.on_close_editor, self.current_temp_file_path)
    
    def init_UI_flow(self, root):
        # 创建顶部按钮区域
        self.top_buttons_frame = tk.Frame(root, borderwidth=1, relief=tk.SUNKEN, bg=UIStyle.VERY_LIGHT_BLUE)
        self.top_buttons_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.top_buttons_frame.pack_propagate(False)  # 防止自动调整大小
        # 顶部按钮按钮
        self.folder_control_button = tk.Button(self.top_buttons_frame, text="隐藏文件夹Tab", command=self.toggle_folder_panel, 
                                             width=16, bg=UIStyle.SUCCESS_GREEN, fg=UIStyle.WHITE, 
                                             relief=UIStyle.BUTTON_RELIEF, borderwidth=UIStyle.BUTTON_BORDER_WIDTH,
                                             font=UIStyle.BUTTON_FONT)
        self.align_button = tk.Button(self.top_buttons_frame, text="对齐图像开始", command=self.start_point_mark, 
                                     width=16, bg=UIStyle.WARNING_ORANGE, fg=UIStyle.WHITE, 
                                     relief=UIStyle.BUTTON_RELIEF, borderwidth=UIStyle.BUTTON_BORDER_WIDTH,
                                     font=UIStyle.BUTTON_FONT)
        def debug_open_template_dialog():
            print("温度过滤按钮被点击！")
            self.open_template_dialog()
        
        self.template_filter_button = tk.Button(self.top_buttons_frame, text="温度过滤", command=debug_open_template_dialog, 
                                             width=10, bg=UIStyle.PRIMARY_BLUE, fg=UIStyle.WHITE, 
                                             relief=UIStyle.BUTTON_RELIEF, borderwidth=UIStyle.BUTTON_BORDER_WIDTH,
                                             font=UIStyle.BUTTON_FONT)
        self.export_button = tk.Button(self.top_buttons_frame, text="导出", command=self.export_excel, 
                                     width=10, bg=UIStyle.DARK_BLUE, fg=UIStyle.WHITE, 
                                     relief=UIStyle.BUTTON_RELIEF, borderwidth=UIStyle.BUTTON_BORDER_WIDTH,
                                     font=UIStyle.BUTTON_FONT)
        self.settings_button = tk.Button(self.top_buttons_frame, text="设置", command=self.open_settings_dialog, 
                                       width=10, bg=UIStyle.GRAY, fg=UIStyle.WHITE, 
                                       relief=UIStyle.BUTTON_RELIEF, borderwidth=UIStyle.BUTTON_BORDER_WIDTH,
                                       font=UIStyle.BUTTON_FONT)

        self.folder_control_button.grid(row=0, column=0, padx=8, pady=16)
        self.align_button.grid(row=0, column=1, padx=8, pady=16)
        self.template_filter_button.grid(row=0, column=2, padx=8, pady=16)
        self.export_button.grid(row=0, column=3, padx=8, pady=16)
        self.settings_button.grid(row=0, column=4, padx=8, pady=16)

        # 创建文件夹选择区域（固定宽度220像素，不可扩展）
        self.folder_container = tk.Frame(root, bg=UIStyle.VERY_LIGHT_BLUE, relief=tk.SUNKEN, bd=1, width=230)
        self.folder_container.grid(row=1, column=0, sticky="ns", padx=5, pady=5)
        self.folder_container.pack_propagate(False)  # 防止内容改变容器大小
        
        self.folder_frame = tk.Frame(self.folder_container, borderwidth=0, relief=tk.FLAT, bg=UIStyle.WHITE)
        self.folder_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        # 合并的文件夹信息行
        self.folder_info_frame = tk.Frame(self.folder_frame, bg=UIStyle.WHITE)
        self.folder_info_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 左侧：当前文件夹信息（80%宽度，绿色背景）
        self.folder_path_frame = tk.Frame(self.folder_info_frame, bg=UIStyle.SUCCESS_GREEN, relief=tk.FLAT, bd=0)
        self.folder_path_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.folder_path_label = tk.Label(self.folder_path_frame, text="当前文件夹：未选择", 
                                        bg=UIStyle.SUCCESS_GREEN, fg=UIStyle.WHITE, relief=tk.FLAT, bd=0,
                                        font=UIStyle.BUTTON_FONT, anchor=tk.W, wraplength=160, justify=tk.LEFT)
        self.folder_path_label.pack(pady=8, padx=10, fill=tk.BOTH, expand=True)
        
        # 右侧：选择文件夹按钮（20%宽度，无背景色，与顶部按钮高度一致）
        self.folder_button = tk.Button(self.folder_info_frame, text="📂", command=self.select_folder, 
                                     width=3, bg=UIStyle.WHITE, fg=UIStyle.SUCCESS_GREEN, 
                                     relief=tk.FLAT, borderwidth=0,
                                     font=("Arial", 16))
        self.folder_button.pack(side=tk.RIGHT, padx=(5, 0), fill=tk.Y)
        
        # 文件分类树形视图
        self.folder_tree = ttk.Treeview(self.folder_frame, height=10, show="tree")
        
        # 配置Treeview样式，支持加粗标记
        style = ttk.Style()
        style.configure("Treeview", 
                       foreground=UIStyle.BLACK, 
                       background=UIStyle.WHITE,
                       fieldbackground=UIStyle.WHITE,
                       borderwidth=1,
                       relief="solid")
        style.configure("Treeview.Item", 
                       foreground=UIStyle.BLACK,
                       background=UIStyle.WHITE)
        
        # 创建加粗标记的标签样式
        style.configure("Bold.Treeview.Item", 
                       font=UIStyle.BUTTON_FONT,
                       foreground=UIStyle.DARK_BLUE,
                       background=UIStyle.VERY_LIGHT_BLUE)
        
        # 配置选中项样式
        style.map("Treeview", 
                 background=[('selected', UIStyle.LIGHT_BLUE)],
                 foreground=[('selected', UIStyle.WHITE)])
        
        self.folder_tree.pack(pady=10, padx=5, fill=tk.BOTH, expand=True)
        
        # 配置Treeview的标签样式
        self.folder_tree.tag_configure("bold", 
                                      font=UIStyle.BUTTON_FONT,
                                      foreground=UIStyle.DARK_BLUE,
                                      background=UIStyle.VERY_LIGHT_BLUE)
        
        # 绑定单击事件
        self.folder_tree.bind("<Button-1>", self.on_file_click)
        
        # 去除滚动条，让内容占满整个区域
        # folder_scrollbar = ttk.Scrollbar(self.folder_frame, orient="vertical", command=self.folder_tree.yview)
        # folder_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # self.folder_tree.configure(yscrollcommand=folder_scrollbar.set)

        #中间图片区域
        # self.imageA = Image.open(Constants.imageA_default_path)
        # self.imageB = Image.open(Constants.imageB_default_path)
       
        # 创建 Canvas，使用 grid 布局来控制横向排列
        self.canvasA = tk.Canvas(root, bg=UIStyle.WHITE, relief=tk.SUNKEN, bd=1, 
                                highlightthickness=0, highlightbackground=UIStyle.LIGHT_GRAY)
        self.canvasB = tk.Canvas(root, bg=UIStyle.WHITE, relief=tk.SUNKEN, bd=1,
                                highlightthickness=0, highlightbackground=UIStyle.LIGHT_GRAY)

        self.canvasA.grid(row=1, column=1, sticky="nsew")
        self.canvasB.grid(row=1, column=2, sticky="nsew")
        # 让 Grid 布局管理器将列的权重设置为1，使得画布可以在横向上均匀分配空间
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=0)  # 文件夹区域不拉伸
        root.grid_columnconfigure(1, weight=1)  # 画布A拉伸
        root.grid_columnconfigure(2, weight=1)  # 画布B拉伸
        # 设定变量来存储图像引用，避免重复创建
        self.tk_imageA = None
        self.tk_imageB = None

        # 不再默认加载图片，等待用户选择文件夹
        # self.set_image(Constants.imageA_default_path, 0)
        # self.set_image(Constants.imageB_default_path, 1)

         # 创建下方按钮区域
        self.bottom_buttons_frame_A = tk.Frame(root, bg=UIStyle.VERY_LIGHT_BLUE, relief=tk.FLAT, bd=0)
        self.bottom_buttons_frame_A.grid(row=2, column=1, padx=8, pady=16)
        # self.point_imageA_button = tk.Button(self.bottom_buttons_frame_A, text="打点标记", command=self.point_mark_A, width=10)
        self.margin_before_button = tk.Button(self.bottom_buttons_frame_A, text="对齐前图像", command=self.margin_before, 
                                            width=10, bg=UIStyle.PRIMARY_BLUE, fg=UIStyle.WHITE, 
                                            relief=UIStyle.BUTTON_RELIEF, borderwidth=UIStyle.BUTTON_BORDER_WIDTH,
                                            font=UIStyle.BUTTON_FONT)
        self.margin_after_button = tk.Button(self.bottom_buttons_frame_A, text="对齐后图像", command=self.margin_after, 
                                           width=10, bg=UIStyle.PRIMARY_BLUE, fg=UIStyle.WHITE, 
                                           relief=UIStyle.BUTTON_RELIEF, borderwidth=UIStyle.BUTTON_BORDER_WIDTH,
                                           font=UIStyle.BUTTON_FONT)
        
        # 添加清除热力图对齐点按钮
        self.clear_heat_points_button = tk.Button(self.bottom_buttons_frame_A, text="清除热力图对齐点", 
                                                command=self.clear_heat_points, width=15, bg=UIStyle.PRIMARY_BLUE, fg=UIStyle.WHITE, 
                                                relief=UIStyle.BUTTON_RELIEF, borderwidth=UIStyle.BUTTON_BORDER_WIDTH,
                                                font=UIStyle.BUTTON_FONT)
       
        self.bottom_buttons_frame_A.pack_propagate(False)  # 不允许frame自动调整大小
        # 初始根据是否存在打点JSON控制显示
        self.margin_before_button.grid_forget()
        self.margin_after_button.grid_forget()
        self.update_align_buttons_visibility()
        # 初始隐藏清除按钮
        self.clear_heat_points_button.grid_forget()

        self.bottom_buttons_frame_B = tk.Frame(root, bg=UIStyle.VERY_LIGHT_BLUE, relief=tk.FLAT, bd=0)
        self.bottom_buttons_frame_B.grid(row=2, column=2)
        # self.point_imageB_button = tk.Button(self.bottom_buttons_frame_B, text="打点标记", command=self.point_mark_B, width=10)
        
        # 添加清除Layout图对齐点按钮
        self.clear_layout_points_button = tk.Button(self.bottom_buttons_frame_B, text="清除Layout图对齐点", 
                                               command=self.clear_layout_points, width=15, bg=UIStyle.PRIMARY_BLUE, fg=UIStyle.WHITE, 
                                               relief=UIStyle.BUTTON_RELIEF, borderwidth=UIStyle.BUTTON_BORDER_WIDTH,
                                               font=UIStyle.BUTTON_FONT)
        
        self.bottom_buttons_frame_B.pack_propagate(False)  # 不允许frame自动调整大小
        # 初始隐藏清除按钮
        self.clear_layout_points_button.grid_forget()
        # self.point_imageB_button.grid(row=0, column=1, padx=5)    

        # self.imgScalePCB = self.imageB.width / self.imageA.width
        # print("self.imgScalePCB -> ", self.imgScalePCB, self.imageB.width, self.imageA.width)
        # self.root.after(100, self.init_point_transformer)

        self.canvasA.bind("<Double-Button-1>", self.on_double_click) # 左键
    def has_points_json(self):
        try:
            if not self.current_folder_path:
                return False
            points_dir = os.path.join(self.current_folder_path, "points")
            heat_filename = self.current_files.get("heat", "")
            layout_filename = self.current_files.get("layout", "")
            if not heat_filename or not layout_filename:
                # 如果文件名未就绪，但内存中已有足够的点位，也认为可显示
                return len(self.points_A) >= 3 and len(self.points_B) >= 3
            heat_name = os.path.splitext(heat_filename)[0]
            layout_name = os.path.splitext(layout_filename)[0]
            json_points_path = os.path.join(points_dir, f"{heat_name}_{layout_name}.json")
            return os.path.exists(json_points_path) or (len(self.points_A) >= 3 and len(self.points_B) >= 3)
        except Exception:
            return False
    def update_align_buttons_visibility(self):
        if self.has_points_json():
            self.margin_before_button.grid(row=0, column=0, padx=5)
            self.margin_after_button.grid(row=0, column=1, padx=5)
        else:
            self.margin_before_button.grid_forget()
            self.margin_after_button.grid_forget()
    def load_local_data(self):
        """加载本地数据，现在从选择的文件夹中加载"""
        if self.current_folder_path:
            # 如果已经选择了文件夹，从文件夹中加载数据
            self.scan_folder_files()
            # 扫描后刷新按钮显示状态
            self.update_align_buttons_visibility()
        else:
            # 如果没有选择文件夹，加载默认数据
            self.load_points()

    def to_numpy_image(self, image):
        image_np = np.array(image)
        # 如果是 RGB 图像，OpenCV 默认处理 BGR 格式，所以需要转换颜色顺序
        if image_np.ndim == 3:  # 这是 RGB 图像
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        return image_np
    def save_log_file(self):
        # 获取当前时间并格式化为字符串
        current_year = datetime.now().strftime("%Y")
        current_time = datetime.now().strftime("%m-%d %H:%M")

        self.edit_log["export_time"][1] = current_time

        if not os.path.exists("logs"):
            os.makedirs("logs")  # 创建多层目录

        # 生成 CSV 文件名
        csv_filename = "logs/" + f"{current_year}.csv"

        # 检查文件是否存在
        file_exists = os.path.exists(csv_filename)

        # 打开文件并写入 CSV
        with open(csv_filename, mode='a', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)

            # 如果文件不存在，则写入头部
            if not file_exists:
                header = ["export_time", "origin_mark", "final_mark", "add_new_mark", "delete_origin_mark", "modify_origin_mark"]
                writer.writerow(header)  # 写入头部
                header_values = ["生成时间", "自动生成外框数量", "最终导出外框数量", "新增外框数量（手动增加导出时没有被删除）", "删除外框数量（自动生成的外框被删除）", "调整外框数量（自动生成的外框被调整)"]
                writer.writerow(header_values)  # 写入描述行

            # 遍历字典并写入每一行数值
            row = []
            for key, value in self.edit_log.items():
                # 如果是 'modify_origin_mark' 并且 value[1] 是 set，则取 set 的长度
                target_value = None
                if isinstance(value[1], set):
                    target_value = len(value[1])  # 取 set 的大小
                else:
                    target_value = value[1]

                row.append(target_value)

            writer.writerow(row)  # 写入数据行

        print(f"CSV 文件已保存为 {csv_filename}")
    def toggle_folder_panel(self):
        """切换文件夹面板的可见性"""
        if self.folder_container.winfo_ismapped():
            # 隐藏整个文件夹容器
            self.folder_container.grid_forget()
            # 更新按钮文字
            self.folder_control_button.config(text="显示文件夹Tab")
            
            # 使用延迟更新机制，避免卡顿
            self.root.after(100, self._optimize_layout_after_hide)
        else:
            # 显示文件夹容器
            self.folder_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
            # 更新按钮文字
            self.folder_control_button.config(text="隐藏文件夹Tab")
            
            # 使用延迟更新机制，避免卡顿
            self.root.after(100, self._optimize_layout_after_show)
    
    def _optimize_layout_after_hide(self):
        """隐藏文件夹后的布局优化"""
        # 让右边的图片占满空间，使用更平滑的权重变化
        self.root.grid_columnconfigure(0, weight=0)  # 文件夹区域不拉伸
        self.root.grid_columnconfigure(1, weight=1)  # 画布A拉伸
        self.root.grid_columnconfigure(2, weight=1)  # 画布B拉伸
        
        # 延迟更新图片，避免卡顿
        if hasattr(self, 'imageA') and hasattr(self, 'imageB') and self.imageA and self.imageB:
            self.root.after(200, self._delayed_update_images)
    
    def _optimize_layout_after_show(self):
        """显示文件夹后的布局优化"""
        # 恢复原来的列权重设置
        self.root.grid_columnconfigure(0, weight=0)  # 文件夹区域不拉伸
        self.root.grid_columnconfigure(1, weight=1)  # 画布A拉伸
        self.root.grid_columnconfigure(2, weight=1)  # 画布B拉伸
        
        # 延迟更新图片，避免卡顿
        if hasattr(self, 'imageA') and hasattr(self, 'imageB') and self.imageA and self.imageB:
            self.root.after(200, self._delayed_update_images)
    
    def _delayed_update_images(self):
        """延迟更新图片，避免卡顿"""
        try:
            # 检查画布是否已经准备好
            if (hasattr(self, 'canvasA') and hasattr(self, 'canvasB') and 
                self.canvasA.winfo_width() > 1 and self.canvasB.winfo_width() > 1):
                self.update_images()
        except Exception as e:
            print(f"延迟更新图片时出错: {e}")

def setup_logging():
    """设置日志系统，将print输出重定向到日志文件"""
    # 创建logs目录
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 生成日志文件名：年_月_日.txt
    today = datetime.now()
    log_filename = f"{today.year}_{today.month:02d}_{today.day:02d}.txt"
    log_filepath = os.path.join(logs_dir, log_filename)
    
    # 创建日志文件并写入启动信息
    with open(log_filepath, 'a', encoding='utf-8') as log_file:
        log_file.write(f"\n{'='*50}\n")
        log_file.write(f"程序启动时间: {today.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"{'='*50}\n")
    
    # 重定向stdout到日志文件
    class LogWriter:
        def __init__(self, file):
            self.file = file
            self.terminal = sys.stdout
        
        def write(self, message):
            self.terminal.write(message)  # 同时输出到控制台
            self.file.write(message)      # 写入日志文件
            self.file.flush()             # 立即刷新到文件
        
        def flush(self):
            self.terminal.flush()
            self.file.flush()
    
    # 打开日志文件并重定向stdout
    log_file = open(log_filepath, 'a', encoding='utf-8')
    sys.stdout = LogWriter(log_file)
    
    print(f"日志系统已启动，日志文件: {log_filepath}")
    return log_filepath

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Thermal温度点位自动识别系统')
    parser.add_argument('--log', action='store_true', help='启用日志记录功能')
    return parser.parse_args()

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_arguments()
    
    # 如果指定了--log参数，设置日志系统
    log_filepath = None
    if args.log:
        log_filepath = setup_logging()
    
    root = tk.Tk()
    root.configure(bg=UIStyle.VERY_LIGHT_BLUE)
    root.title("Thermal温度点位自动识别系统")
    root.geometry("1400x900")
    app = ResizableImagesApp(root)
    
    # 添加程序退出时的配置保存
    def on_closing():
        if log_filepath:
            print(f"程序退出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        app.save_current_files_to_config()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
