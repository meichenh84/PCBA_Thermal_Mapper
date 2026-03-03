#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layout 圖元器件溫度查詢模組（最佳化版）(layout_temperature_query_optimized.py)

用途：
    根據 Layout 圖（C_info）中的元器件座標資訊，查詢對應到
    熱力圖上的最高溫度值。直接遍歷 Layout 資料中的每個元器件，
    將其實體座標（mm）轉換為 Layout 圖像素座標，再透過仿射變換
    映射到熱力圖座標系，最終從溫度矩陣中取得該區域的最高溫度。

    相較於「先遍歷溫度點再反查元器件」的方法，本最佳化版本直接
    遍歷元器件列表，效率更高。

在整個應用中的角色：
    - 當使用者匯入 Layout 資料（C_info CSV）時被呼叫
    - 將 Layout 中每個元器件對應到熱力圖上的最高溫度
    - 回傳的結果用於在兩張圖上建立矩形標記

關聯檔案：
    - main.py：呼叫本模組查詢溫度
    - point_transformer.py：提供座標轉換功能
    - temperature_config_manager.py：提供 PCB 參數和 padding 設定
"""

import numpy as np
import cv2
import pandas as pd
from point_transformer import PointTransformer


class LayoutTemperatureQueryOptimized:
    """最佳化版 Layout 元器件溫度查詢器。

    直接遍歷 Layout 資料中的元器件，將實體座標轉換為影像座標，
    再查詢對應的溫度值。

    屬性：
        layout_data (pandas.DataFrame): Layout 元器件資訊（C_info 資料）
        temp_data (numpy.ndarray): 溫度矩陣
        point_transformer (PointTransformer): 座標轉換器
        p_w (float): PCB 長度（mm）
        p_h (float): PCB 寬度（mm）
        p_origin (str): 座標原點位置（如 "左下"）
        p_origin_offset_x (float): 原點 X 方向偏移（像素）
        p_origin_offset_y (float): 原點 Y 方向偏移（像素）
        c_padding_left/top/right/bottom (float): Layout 圖四邊 padding
        layout_image: Layout 圖像（用於取得實際尺寸）
        c_p_coord: 座標轉換參數
    """

    def __init__(self, layout_data, temp_data, point_transformer,
                 p_w, p_h, p_origin, p_origin_offset_x, p_origin_offset_y,
                 c_padding_left, c_padding_top, c_padding_right, c_padding_bottom,
                 layout_image=None):
        """初始化溫度查詢器。

        Args:
            layout_data: C_info 資料，包含元器件資訊
            temp_data (numpy.ndarray): 溫度矩陣
            point_transformer (PointTransformer): 座標轉換器
            p_w (float): PCB 長度（mm）
            p_h (float): PCB 寬度（mm）
            p_origin (str): 座標原點位置
            p_origin_offset_x (float): 原點 X 偏移
            p_origin_offset_y (float): 原點 Y 偏移
            c_padding_left/top/right/bottom (float): Layout 圖 padding
            layout_image: Layout 圖像（PIL.Image 或 numpy.ndarray）
        """
        self.layout_data = layout_data
        self.temp_data = temp_data
        self.point_transformer = point_transformer
        self.p_w = p_w
        self.p_h = p_h
        self.p_origin = p_origin
        self.p_origin_offset_x = p_origin_offset_x
        self.p_origin_offset_y = p_origin_offset_y
        self.c_padding_left = c_padding_left
        self.c_padding_top = c_padding_top
        self.c_padding_right = c_padding_right
        self.c_padding_bottom = c_padding_bottom
        self.layout_image = layout_image
        
        # 计算转换参数
        self.c_p_coord = None
        self.calculate_coordinate_transform()
    
    def calculate_coordinate_transform(self):
        """計算 Layout 圖像素座標到 PCB 實體座標（mm）的轉換參數。"""
        # 从实际Layout图像获取尺寸，如果没有提供则使用默认值
        if self.layout_image is not None:
            # 处理PIL Image对象
            if hasattr(self.layout_image, 'size'):
                # PIL Image对象
                c_width, c_height = self.layout_image.size  # (width, height)
                print(f"使用实际Layout图像尺寸: {c_width}x{c_height}")
            elif hasattr(self.layout_image, 'shape'):
                # numpy数组对象
                c_width = self.layout_image.shape[1]  # 图像宽度
                c_height = self.layout_image.shape[0]  # 图像高度
                print(f"使用实际Layout图像尺寸: {c_width}x{c_height}")
            else:
                # 未知类型，使用默认尺寸
                c_width = 1280
                c_height = 960
                print(f"未知图像类型，使用默认Layout图像尺寸: {c_width}x{c_height}")
        else:
            # 如果没有提供Layout图像，使用默认尺寸
            c_width = 1280
            c_height = 960
            print(f"使用默认Layout图像尺寸: {c_width}x{c_height}")
        
        # 计算有效区域尺寸
        effective_width = c_width - self.c_padding_left - self.c_padding_right
        effective_height = c_height - self.c_padding_top - self.c_padding_bottom
        
        # 计算像素到毫米的转换比例
        pixels_per_mm_x = effective_width / self.p_w
        pixels_per_mm_y = effective_height / self.p_h
        
        # 根据坐标原点计算坐标转换参数，考虑原点偏移
        if self.p_origin == "左下":
            # 左下为原点，Y轴向上为正
            self.c_p_coord = {
                'offset_x': self.c_padding_left + self.p_origin_offset_x,
                'offset_y': self.c_padding_bottom + self.p_origin_offset_y,
                'scale_x': pixels_per_mm_x,
                'scale_y': -pixels_per_mm_y,  # Y轴反向
                'c_height': c_height
            }
        elif self.p_origin == "左上":
            # 左上为原点，Y轴向下为正
            self.c_p_coord = {
                'offset_x': self.c_padding_left + self.p_origin_offset_x,
                'offset_y': self.c_padding_top + self.p_origin_offset_y,
                'scale_x': pixels_per_mm_x,
                'scale_y': pixels_per_mm_y,
                'c_height': c_height
            }
        elif self.p_origin == "右上":
            # 右上为原点，Y轴向下为正，X轴向左为正
            self.c_p_coord = {
                'offset_x': c_width - self.c_padding_right - self.p_origin_offset_x,
                'offset_y': self.c_padding_top + self.p_origin_offset_y,
                'scale_x': -pixels_per_mm_x,  # X轴反向
                'scale_y': pixels_per_mm_y,
                'c_height': c_height
            }
        elif self.p_origin == "右下":
            # 右下为原点，Y轴向上为正，X轴向左为正
            self.c_p_coord = {
                'offset_x': c_width - self.c_padding_right - self.p_origin_offset_x,
                'offset_y': c_height - self.c_padding_bottom - self.p_origin_offset_y,
                'scale_x': -pixels_per_mm_x,  # X轴反向
                'scale_y': -pixels_per_mm_y,  # Y轴反向
                'c_height': c_height
            }
        else:
            raise ValueError(f"不支持的坐标原点: {self.p_origin}")
    
    def query_temperature_by_layout_optimized(self, min_temp, max_temp):
        """最佳化版溫度查詢：直接遍歷 C_info 中的元器件。

        演算法流程：
        1. 遍歷 C_info 中的所有元器件
        2. 將每個元器件的 PCB 座標 (PR1) 轉換為 Layout 圖座標 (CR1)
        3. 將 Layout 圖座標 (CR1) 轉換為熱力圖座標 (AR1)
        4. 在熱力圖中查詢 AR1 區域的最高溫度
        5. 若溫度在過濾範圍內，則記錄該元器件

        Args:
            min_temp (float): 最低溫度閾值
            max_temp (float): 最高溫度閾值

        Returns:
            tuple: (rectA_arr, rectB_arr) 熱力圖和 Layout 圖的矩形區域列表
        """
        rectA_arr = []  # 热力图矩形区域
        rectB_arr = []  # Layout图矩形区域
        
        if not self.layout_data or self.temp_data is None or self.temp_data.size == 0:
            print("警告：Layout数据或温度数据为空")
            return rectA_arr, rectB_arr
        
        print(f"开始优化版温度查询，共{len(self.layout_data)}个元器件")
        print(f"温度数据形状: {self.temp_data.shape}")
        print(f"温度数据范围: {np.min(self.temp_data):.2f} - {np.max(self.temp_data):.2f}°C")
        print(f"温度数据中大于{min_temp}°C的点数: {np.sum(self.temp_data > min_temp)}")
        
        # 检查点转换器
        if self.point_transformer is None:
            print("警告：点转换器为None，无法进行Layout到热力图的坐标转换")
            return rectA_arr, rectB_arr
        
        # 遍历所有元器件
        processed_count = 0
        for index, component in enumerate(self.layout_data):
            try:
                refdes = component['RefDes']
                left = component['left']
                top = component['top']
                right = component['right']
                bottom = component['bottom']
                
                # 调试前几个元器件
                if index < 3:
                    print(f"\n处理元器件 {index+1}: {refdes}")
                    print(f"  PCB坐标: ({left:.2f}, {top:.2f}, {right:.2f}, {bottom:.2f})")
                
                # 步骤1: PR1 -> CR1 (PCB坐标转Layout图坐标)
                cr1_coords = self.convert_pcb_to_layout(left, top, right, bottom)
                if cr1_coords is None:
                    if index < 3:
                        print(f"  PCB坐标转换失败")
                    continue
                
                cr1_left, cr1_top, cr1_right, cr1_bottom = cr1_coords
                if index < 3:
                    print(f"  Layout坐标: ({cr1_left:.2f}, {cr1_top:.2f}, {cr1_right:.2f}, {cr1_bottom:.2f})")
                
                # 步骤2: CR1 -> AR1 (Layout图坐标转热力图坐标)
                ar1_coords = self.convert_layout_to_thermal(cr1_left, cr1_top, cr1_right, cr1_bottom)
                if ar1_coords is None:
                    if index < 3:
                        print(f"  Layout坐标转换失败")
                    continue
                
                ar1_left, ar1_top, ar1_right, ar1_bottom = ar1_coords
                if index < 3:
                    print(f"  热力图坐标: ({ar1_left:.2f}, {ar1_top:.2f}, {ar1_right:.2f}, {ar1_bottom:.2f})")
                
                # 确保坐标在温度数据范围内
                ar1_left = max(0, min(int(ar1_left), self.temp_data.shape[1] - 1))
                ar1_top = max(0, min(int(ar1_top), self.temp_data.shape[0] - 1))
                ar1_right = max(0, min(int(ar1_right), self.temp_data.shape[1] - 1))
                ar1_bottom = max(0, min(int(ar1_bottom), self.temp_data.shape[0] - 1))
                
                # 确保至少有一个像素的宽度和高度
                if ar1_left >= ar1_right:
                    ar1_right = min(ar1_left + 1, self.temp_data.shape[1] - 1)
                if ar1_top >= ar1_bottom:
                    ar1_bottom = min(ar1_top + 1, self.temp_data.shape[0] - 1)
                
                # 步骤3: 查询AR1区域的最高温度
                thermal_region = self.temp_data[ar1_top:ar1_bottom, ar1_left:ar1_right]
                if thermal_region.size == 0:
                    if index < 3:
                        print(f"  热力图区域为空")
                    continue
                
                max_temp_value = np.max(thermal_region)
                if index < 3:
                    print(f"  区域最高温度: {max_temp_value:.2f}°C")
                
                # 步骤4: 检查温度是否在过滤范围内
                if min_temp <= max_temp_value <= max_temp:
                    processed_count += 1
                    # 🔥 关键修复：计算最高温度点的坐标，而不是中心点坐标
                    max_temp_index = np.argmax(thermal_region)
                    max_temp_coords = np.unravel_index(max_temp_index, thermal_region.shape)
                    # 转换为全局坐标（相对于整个热力图）
                    ar1_cy = ar1_top + max_temp_coords[0]  # 注意：numpy数组是[row, col]，对应[y, x]
                    ar1_cx = ar1_left + max_temp_coords[1]
                    
                    # 将热力图坐标转换为Layout图坐标
                    cr1_x, cr1_y = self.point_transformer.A2B(ar1_cx, ar1_cy)
                    cr1_cx = int(cr1_x)
                    cr1_cy = int(cr1_y)
                    
                    # 添加到结果列表
                    rectA_arr.append({
                        "x1": ar1_left,
                        "y1": ar1_top,
                        "x2": ar1_right,
                        "y2": ar1_bottom,
                        "cx": ar1_cx,
                        "cy": ar1_cy,
                        "max_temp": max_temp_value,
                        "name": refdes,
                        "refdes": refdes
                    })
                    
                    rectB_arr.append({
                        "x1": int(cr1_left),
                        "y1": int(cr1_top),
                        "x2": int(cr1_right),
                        "y2": int(cr1_bottom),
                        "cx": int(cr1_cx),
                        "cy": int(cr1_cy),
                        "max_temp": max_temp_value,
                        "name": refdes,
                        "refdes": refdes
                    })
                    
                    print(f"找到高温元器件: {refdes} (Ar{index + 1}), 温度: {max_temp_value:.2f}°C")
                
            except Exception as e:
                print(f"处理元器件 {component.get('RefDes', 'Unknown')} 时出错: {e}")
                continue
        
        # 按温度值从高到低排序
        if rectA_arr and rectB_arr:
            # 创建温度索引列表，按温度降序排序
            temp_indices = sorted(range(len(rectA_arr)), 
                                key=lambda i: rectA_arr[i]['max_temp'], 
                                reverse=True)
            
            # 重新排序两个列表
            rectA_arr = [rectA_arr[i] for i in temp_indices]
            rectB_arr = [rectB_arr[i] for i in temp_indices]
            
            print(f"结果已按温度从高到低排序")
            if len(rectA_arr) > 0:
                print(f"最高温度: {rectA_arr[0]['max_temp']:.2f}°C ({rectA_arr[0]['name']})")
                if len(rectA_arr) > 1:
                    print(f"最低温度: {rectA_arr[-1]['max_temp']:.2f}°C ({rectA_arr[-1]['name']})")
        
        print(f"\n优化版温度查询完成:")
        print(f"  处理元器件总数: {len(self.layout_data)}")
        print(f"  成功处理元器件数: {processed_count}")
        print(f"  找到高温元器件数: {len(rectA_arr)}")
        return rectA_arr, rectB_arr
    
    def query_temperature_by_layout_smart_filter(self, min_temp, max_temp):
        """智慧過濾版溫度查詢：避免重複偵測相同熱區域。

        演算法流程：
        1. 遍歷所有元器件，按溫度降序排列
        2. 對每個矩形框，將 tempA 中對應區域標為 0
        3. 重新計算區域內溫度，過濾不符合條件的矩形框
        4. 最終按溫度重新排序返回

        Args:
            min_temp (float): 最低溫度閾值
            max_temp (float): 最高溫度閾值

        Returns:
            tuple: (rectA_arr, rectB_arr) 熱力圖和 Layout 圖的矩形區域列表
        """
        print(f"开始智能过滤版温度查询，共{len(self.layout_data)}个元器件")
        print(f"温度数据形状: {self.temp_data.shape}")
        print(f"温度数据范围: {np.min(self.temp_data):.2f} - {np.max(self.temp_data):.2f}°C")
        
        # 创建温度数据的副本，用于标记已处理的区域
        temp_data_copy = self.temp_data.copy()
        
        # 第一轮：获取所有符合条件的矩形框，按温度降序排列
        all_rects = []
        processed_count = 0
        
        for index, component in enumerate(self.layout_data):
            try:
                refdes = component['RefDes']
                left = component['left']
                top = component['top']
                right = component['right']
                bottom = component['bottom']
                
                # PCB坐标转Layout图坐标
                cr1_coords = self.convert_pcb_to_layout(left, top, right, bottom)
                if cr1_coords is None:
                    continue
                
                cr1_left, cr1_top, cr1_right, cr1_bottom = cr1_coords
                
                # Layout图坐标转热力图坐标
                ar1_coords = self.convert_layout_to_thermal(cr1_left, cr1_top, cr1_right, cr1_bottom)
                if ar1_coords is None:
                    continue
                
                ar1_left, ar1_top, ar1_right, ar1_bottom = ar1_coords
                
                # 确保坐标在温度数据范围内
                ar1_left = max(0, min(int(ar1_left), self.temp_data.shape[1] - 1))
                ar1_top = max(0, min(int(ar1_top), self.temp_data.shape[0] - 1))
                ar1_right = max(0, min(int(ar1_right), self.temp_data.shape[1] - 1))
                ar1_bottom = max(0, min(int(ar1_bottom), self.temp_data.shape[0] - 1))
                
                # 确保至少有一个像素的宽度和高度
                if ar1_left >= ar1_right:
                    ar1_right = min(ar1_left + 1, self.temp_data.shape[1] - 1)
                if ar1_top >= ar1_bottom:
                    ar1_bottom = min(ar1_top + 1, self.temp_data.shape[0] - 1)
                
                # 查询AR1区域的最高温度
                thermal_region = self.temp_data[ar1_top:ar1_bottom, ar1_left:ar1_right]
                if thermal_region.size == 0:
                    continue
                
                max_temp_value = np.max(thermal_region)
                
                # 检查温度是否在过滤范围内
                if min_temp <= max_temp_value <= max_temp:
                    # 计算最高温度点的坐标
                    max_temp_index = np.argmax(thermal_region)
                    max_temp_coords = np.unravel_index(max_temp_index, thermal_region.shape)
                    ar1_cy = ar1_top + max_temp_coords[0]
                    ar1_cx = ar1_left + max_temp_coords[1]
                    
                    # 将热力图坐标转换为Layout图坐标
                    cr1_x, cr1_y = self.point_transformer.A2B(ar1_cx, ar1_cy)
                    cr1_cx = int(cr1_x)
                    cr1_cy = int(cr1_y)
                    
                    # 從 component 中取得描述資訊
                    description = component.get('Description', '')

                    # 添加到候选列表
                    all_rects.append({
                        'rectA': {
                            "x1": ar1_left,
                            "y1": ar1_top,
                            "x2": ar1_right,
                            "y2": ar1_bottom,
                            "cx": ar1_cx,
                            "cy": ar1_cy,
                            "max_temp": max_temp_value,
                            "name": refdes,
                            "refdes": refdes,
                            "description": description
                        },
                        'rectB': {
                            "x1": int(cr1_left),
                            "y1": int(cr1_top),
                            "x2": int(cr1_right),
                            "y2": int(cr1_bottom),
                            "cx": int(cr1_cx),
                            "cy": int(cr1_cy),
                            "max_temp": max_temp_value,
                            "name": refdes,
                            "refdes": refdes,
                            "description": description
                        },
                        'temp': max_temp_value
                    })
                    processed_count += 1
                    
            except Exception as e:
                print(f"处理元器件 {component.get('RefDes', 'Unknown')} 时出错: {e}")
                continue
        
        # 按温度降序排序
        all_rects.sort(key=lambda x: x['temp'], reverse=True)
        print(f"第一轮筛选完成，找到 {len(all_rects)} 个候选矩形框")
        
        # 第二轮：智能过滤，避免重复检测
        final_rectA_arr = []
        final_rectB_arr = []
        
        for i, rect_info in enumerate(all_rects):
            rectA = rect_info['rectA']
            rectB = rect_info['rectB']
            
            # 获取当前矩形框的热力图坐标
            ar1_left = rectA['x1']
            ar1_top = rectA['y1']
            ar1_right = rectA['x2']
            ar1_bottom = rectA['y2']
            
            # 检查当前区域是否已被标记为0（已被其他矩形框处理过）
            current_region = temp_data_copy[ar1_top:ar1_bottom, ar1_left:ar1_right]
            if current_region.size == 0:
                print(f"矩形框 {rectA['name']} 区域为空，跳过")
                continue
            
            # 重新计算当前区域的最高温度（可能已被其他矩形框影响）
            current_max_temp = np.max(current_region)
            
            # 检查重新计算后的温度是否仍然符合条件
            if min_temp <= current_max_temp <= max_temp:
                # 更新最高温度点坐标
                max_temp_index = np.argmax(current_region)
                max_temp_coords = np.unravel_index(max_temp_index, current_region.shape)
                ar1_cy = ar1_top + max_temp_coords[0]
                ar1_cx = ar1_left + max_temp_coords[1]
                
                # 更新矩形框数据
                rectA['cx'] = ar1_cx
                rectA['cy'] = ar1_cy
                rectA['max_temp'] = current_max_temp
                
                # 将热力图坐标转换为Layout图坐标
                cr1_x, cr1_y = self.point_transformer.A2B(ar1_cx, ar1_cy)
                cr1_cx = int(cr1_x)
                cr1_cy = int(cr1_y)
                
                rectB['cx'] = cr1_cx
                rectB['cy'] = cr1_cy
                rectB['max_temp'] = current_max_temp
                
                # 添加到最终结果
                final_rectA_arr.append(rectA)
                final_rectB_arr.append(rectB)
                
                print(f"✓ 矩形框 {rectA['name']} 通过智能过滤，温度: {current_max_temp:.2f}°C")
                
                # 将当前区域在温度数据中标记为0，避免后续矩形框重复检测
                temp_data_copy[ar1_top:ar1_bottom, ar1_left:ar1_right] = 0
            else:
                print(f"✗ 矩形框 {rectA['name']} 重新计算后温度 {current_max_temp:.2f}°C 不符合条件，已过滤")
        
        # 最终按温度重新排序
        if final_rectA_arr and final_rectB_arr:
            # 创建温度索引列表，按温度降序排序
            temp_indices = sorted(range(len(final_rectA_arr)), 
                                key=lambda i: final_rectA_arr[i]['max_temp'], 
                                reverse=True)
            
            # 重新排序两个列表
            final_rectA_arr = [final_rectA_arr[i] for i in temp_indices]
            final_rectB_arr = [final_rectB_arr[i] for i in temp_indices]
            
            print(f"最终结果已按温度从高到低排序")
            if len(final_rectA_arr) > 0:
                print(f"最高温度: {final_rectA_arr[0]['max_temp']:.2f}°C ({final_rectA_arr[0]['name']})")
                if len(final_rectA_arr) > 1:
                    print(f"最低温度: {final_rectA_arr[-1]['max_temp']:.2f}°C ({final_rectA_arr[-1]['name']})")
        
        print(f"\n智能过滤版温度查询完成:")
        print(f"  处理元器件总数: {len(self.layout_data)}")
        print(f"  第一轮候选数: {len(all_rects)}")
        print(f"  最终通过过滤数: {len(final_rectA_arr)}")
        return final_rectA_arr, final_rectB_arr
    
    def convert_pcb_to_layout(self, p_left, p_top, p_right, p_bottom):
        """將 PCB 實體座標（mm）轉換為 Layout 圖像素座標。

        Args:
            p_left, p_top, p_right, p_bottom (float): PCB 座標（毫米）

        Returns:
            tuple|None: (c_left, c_top, c_right, c_bottom) Layout 圖座標（像素），失敗回傳 None
        """
        try:
            # 严格按照test_layout.py中的转换逻辑
            # 参考get_temperature_at_position方法中的转换
            
            # PCB坐标 -> 图C坐标
            # 注意：scale_y是负数，需要正确处理Y轴翻转
            c_left = p_left * self.c_p_coord['scale_x'] + self.c_p_coord['offset_x']
            c_top = self.c_p_coord['c_height'] - (p_top * abs(self.c_p_coord['scale_y']) + self.c_p_coord['offset_y'])
            c_right = p_right * self.c_p_coord['scale_x'] + self.c_p_coord['offset_x']
            c_bottom = self.c_p_coord['c_height'] - (p_bottom * abs(self.c_p_coord['scale_y']) + self.c_p_coord['offset_y'])
            
            # 确保坐标顺序正确
            c_left, c_right = min(c_left, c_right), max(c_left, c_right)
            c_top, c_bottom = min(c_top, c_bottom), max(c_top, c_bottom)
            
            return (c_left, c_top, c_right, c_bottom)
            
        except Exception as e:
            print(f"PCB坐标转换出错: {e}")
            return None
    
    def convert_layout_to_thermal(self, c_left, c_top, c_right, c_bottom):
        """將 Layout 圖像素座標轉換為熱力圖像素座標。

        透視變換（homography）會將矩形扭曲為四邊形，因此需要轉換全部 4 個角點，
        再取軸對齊 bounding box，才能得到正確的熱力圖查詢區域。

        Args:
            c_left, c_top, c_right, c_bottom (float): Layout 圖座標（像素）

        Returns:
            tuple|None: (a_left, a_top, a_right, a_bottom) 熱力圖座標（像素），失敗回傳 None
        """
        try:
            if self.point_transformer is None:
                return None

            # 轉換矩形的 4 個角點（透視變換下矩形→四邊形）
            corners_b = [
                (c_left, c_top),      # TL
                (c_right, c_top),     # TR
                (c_right, c_bottom),  # BR
                (c_left, c_bottom),   # BL
            ]
            xs, ys = [], []
            for bx, by in corners_b:
                ax, ay = self.point_transformer.B2A(bx, by)
                xs.append(ax)
                ys.append(ay)

            # 取軸對齊 bounding box
            return (min(xs), min(ys), max(xs), max(ys))

        except Exception as e:
            print(f"Layout坐标转换出错: {e}")
            return None
    
    def query_component_by_thermal_coord(self, thermal_x, thermal_y):
        """根據熱力圖座標查詢對應的元器件名稱。

        Args:
            thermal_x (float): 熱力圖 X 座標
            thermal_y (float): 熱力圖 Y 座標

        Returns:
            str|None: 元器件名稱，若找不到則回傳 None
        """
        try:
            if not self.layout_data or self.point_transformer is None:
                print("警告：没有Layout数据或点转换器，无法查询元器件")
                return None
            
            print(f"\n{'='*80}")
            print(f"🔍 开始查询热力图坐标 ({thermal_x:.2f}, {thermal_y:.2f}) 对应的元器件")
            print(f"{'='*80}")
            print(f"Layout数据总数: {len(self.layout_data)} 个元器件")
            print(f"点转换器: {self.point_transformer}")
            
            # 记录最接近的5个元器件
            closest_components = []
            
            # 遍历所有元器件，查找包含该坐标的元器件
            for index, component in enumerate(self.layout_data):
                try:
                    refdes = component['RefDes']
                    left = component['left']
                    top = component['top']
                    right = component['right']
                    bottom = component['bottom']
                    
                    # 步骤1: PR1 -> CR1 (PCB坐标转Layout图坐标)
                    cr1_coords = self.convert_pcb_to_layout(left, top, right, bottom)
                    if cr1_coords is None:
                        continue
                    
                    cr1_left, cr1_top, cr1_right, cr1_bottom = cr1_coords
                    
                    # 步骤2: CR1 -> AR1 (Layout图坐标转热力图坐标)
                    ar1_coords = self.convert_layout_to_thermal(cr1_left, cr1_top, cr1_right, cr1_bottom)
                    if ar1_coords is None:
                        continue
                    
                    ar1_left, ar1_top, ar1_right, ar1_bottom = ar1_coords
                    
                    # 计算距离（用于找到最接近的元器件）
                    center_x = (ar1_left + ar1_right) / 2
                    center_y = (ar1_top + ar1_bottom) / 2
                    distance = ((thermal_x - center_x) ** 2 + (thermal_y - center_y) ** 2) ** 0.5
                    
                    # 检查热力图坐标是否在该元器件的区域内
                    is_inside = (ar1_left <= thermal_x <= ar1_right and 
                                ar1_top <= thermal_y <= ar1_bottom)
                    
                    # 保存最接近的元器件信息
                    if len(closest_components) < 5:
                        closest_components.append({
                            'refdes': refdes,
                            'distance': distance,
                            'is_inside': is_inside,
                            'pcb': (left, top, right, bottom),
                            'layout': (cr1_left, cr1_top, cr1_right, cr1_bottom),
                            'thermal': (ar1_left, ar1_top, ar1_right, ar1_bottom)
                        })
                    else:
                        # 替换距离最远的元器件
                        max_dist_idx = max(range(5), key=lambda i: closest_components[i]['distance'])
                        if distance < closest_components[max_dist_idx]['distance']:
                            closest_components[max_dist_idx] = {
                                'refdes': refdes,
                                'distance': distance,
                                'is_inside': is_inside,
                                'pcb': (left, top, right, bottom),
                                'layout': (cr1_left, cr1_top, cr1_right, cr1_bottom),
                                'thermal': (ar1_left, ar1_top, ar1_right, ar1_bottom)
                            }
                    
                    if is_inside:
                        print(f"\n✓✓✓ 找到匹配的元器件: {refdes} ✓✓✓")
                        print(f"  PCB坐标: ({left:.2f}, {top:.2f}, {right:.2f}, {bottom:.2f})")
                        print(f"  Layout坐标: ({cr1_left:.2f}, {cr1_top:.2f}, {cr1_right:.2f}, {cr1_bottom:.2f})")
                        print(f"  热力图坐标: ({ar1_left:.2f}, {ar1_top:.2f}, {ar1_right:.2f}, {ar1_bottom:.2f})")
                        print(f"  点击坐标在区域内！")
                        
                        # 返回元器件名称和热力图坐标边界
                        return {
                            'refdes': refdes,
                            'pcb_bounds': {
                                'left': left, 'top': top, 'right': right, 'bottom': bottom
                            },
                            'layout_bounds': {
                                'left': cr1_left, 'top': cr1_top, 'right': cr1_right, 'bottom': cr1_bottom
                            },
                            'thermal_bounds': {
                                'x1': ar1_left, 'y1': ar1_top, 'x2': ar1_right, 'y2': ar1_bottom,
                                'cx': center_x, 'cy': center_y
                            }
                        }
                        
                except Exception as e:
                    if index < 3:  # 只打印前3个错误
                        print(f"✗ 处理元器件 {component.get('RefDes', 'Unknown')} 时出错: {e}")
                    continue
            
            # 没有找到匹配的元器件，打印最接近的几个
            print(f"\n❌ 未找到匹配的元器件")
            print(f"\n📊 最接近的 {len(closest_components)} 个元器件:")
            print(f"{'-'*80}")
            
            # 按距离排序
            closest_components.sort(key=lambda x: x['distance'])
            
            for i, comp in enumerate(closest_components, 1):
                print(f"\n{i}. {comp['refdes']} (距离: {comp['distance']:.2f} px)")
                print(f"   PCB坐标: ({comp['pcb'][0]:.2f}, {comp['pcb'][1]:.2f}, {comp['pcb'][2]:.2f}, {comp['pcb'][3]:.2f})")
                print(f"   Layout坐标: ({comp['layout'][0]:.2f}, {comp['layout'][1]:.2f}, {comp['layout'][2]:.2f}, {comp['layout'][3]:.2f})")
                print(f"   热力图坐标: ({comp['thermal'][0]:.2f}, {comp['thermal'][1]:.2f}, {comp['thermal'][2]:.2f}, {comp['thermal'][3]:.2f})")
                print(f"   中心点: ({(comp['thermal'][0] + comp['thermal'][2])/2:.2f}, {(comp['thermal'][1] + comp['thermal'][3])/2:.2f})")
                print(f"   点击坐标: ({thermal_x:.2f}, {thermal_y:.2f})")
                if comp['is_inside']:
                    print(f"   ✓ 点在区域内（但未被返回，可能有BUG）")
                else:
                    print(f"   ✗ 点在区域外")
            
            print(f"\n{'='*80}\n")
            return None
            
        except Exception as e:
            print(f"查询元器件时出错: {e}")
            import traceback
            traceback.print_exc()
            return None