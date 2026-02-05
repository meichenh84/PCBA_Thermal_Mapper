#!/usr/bin/env python3
"""
坐标转换工具
支持不同原点之间的坐标转换
"""

import numpy as np

class CoordinateConverter:
    """坐标转换器类"""
    
    # 原点位置定义
    ORIGIN_POSITIONS = {
        "左上角": "top_left",
        "右上角": "top_right", 
        "右下角": "bottom_right",
        "左下角": "bottom_left"
    }
    
    def __init__(self, image_width, image_height):
        """
        初始化坐标转换器
        
        Args:
            image_width (int): 图像宽度
            image_height (int): 图像高度
        """
        self.width = image_width
        self.height = image_height
        
    def convert_coordinate(self, x, y, from_origin, to_origin):
        """
        坐标转换主函数
        
        Args:
            x (float): 源坐标x
            y (float): 源坐标y
            from_origin (str): 源原点位置 ["左上角", "右上角", "右下角", "左下角"]
            to_origin (str): 目标原点位置 ["左上角", "右上角", "右下角", "左下角"]
            
        Returns:
            tuple: (x_new, y_new) 转换后的坐标
        """
        # 验证输入
        if from_origin not in self.ORIGIN_POSITIONS:
            raise ValueError(f"无效的源原点位置: {from_origin}")
        if to_origin not in self.ORIGIN_POSITIONS:
            raise ValueError(f"无效的目标原点位置: {to_origin}")
            
        # 如果原点相同，直接返回
        if from_origin == to_origin:
            return x, y
            
        # 先转换为左上角原点坐标
        x_top_left, y_top_left = self._to_top_left_origin(x, y, from_origin)
        
        # 再从左上角原点转换为目标原点坐标
        x_new, y_new = self._from_top_left_origin(x_top_left, y_top_left, to_origin)
        
        return x_new, y_new
    
    def _to_top_left_origin(self, x, y, origin):
        """
        将任意原点坐标转换为左上角原点坐标
        
        Args:
            x (float): 源坐标x
            y (float): 源坐标y
            origin (str): 源原点位置
            
        Returns:
            tuple: (x_top_left, y_top_left) 左上角原点坐标
        """
        if origin == "左上角":
            return x, y
        elif origin == "右上角":
            return self.width - x, y
        elif origin == "右下角":
            return self.width - x, self.height - y
        elif origin == "左下角":
            return x, self.height - y
        else:
            raise ValueError(f"无效的原点位置: {origin}")
    
    def _from_top_left_origin(self, x, y, origin):
        """
        将左上角原点坐标转换为任意原点坐标
        
        Args:
            x (float): 左上角原点坐标x
            y (float): 左上角原点坐标y
            origin (str): 目标原点位置
            
        Returns:
            tuple: (x_new, y_new) 目标原点坐标
        """
        if origin == "左上角":
            return x, y
        elif origin == "右上角":
            return self.width - x, y
        elif origin == "右下角":
            return self.width - x, self.height - y
        elif origin == "左下角":
            return x, self.height - y
        else:
            raise ValueError(f"无效的原点位置: {origin}")
    
    def batch_convert(self, coordinates, from_origin, to_origin):
        """
        批量坐标转换
        
        Args:
            coordinates (list): 坐标列表，格式为 [(x1, y1), (x2, y2), ...]
            from_origin (str): 源原点位置
            to_origin (str): 目标原点位置
            
        Returns:
            list: 转换后的坐标列表
        """
        converted_coords = []
        for x, y in coordinates:
            x_new, y_new = self.convert_coordinate(x, y, from_origin, to_origin)
            converted_coords.append((x_new, y_new))
        return converted_coords
    
    def get_available_origins(self):
        """
        获取可用的原点位置列表
        
        Returns:
            list: 可用的原点位置列表
        """
        return list(self.ORIGIN_POSITIONS.keys())


def demo_coordinate_conversion():
    """坐标转换演示函数"""
    print("=== 坐标转换工具演示 ===\n")
    
    # 创建坐标转换器（假设图像尺寸为800x600）
    converter = CoordinateConverter(800, 600)
    
    # 测试坐标点
    test_coordinates = [
        (100, 100),  # 左上角附近
        (700, 100),  # 右上角附近
        (700, 500),  # 右下角附近
        (100, 500),  # 左下角附近
        (400, 300),  # 中心点
    ]
    
    # 可用的原点位置
    origins = converter.get_available_origins()
    print(f"可用的原点位置: {origins}\n")
    
    # 演示各种转换
    print("坐标转换演示 (图像尺寸: 800x600):")
    print("-" * 80)
    
    for i, (x, y) in enumerate(test_coordinates):
        print(f"\n测试点 {i+1}: 原始坐标 ({x}, {y})")
        
        # 从左上角原点转换到其他原点
        for target_origin in origins[1:]:  # 跳过左上角（相同原点）
            x_new, y_new = converter.convert_coordinate(x, y, "左上角", target_origin)
            print(f"  左上角 → {target_origin}: ({x_new}, {y_new})")
        
        # 从右下角原点转换到其他原点
        x_br, y_br = converter.convert_coordinate(x, y, "左上角", "右下角")
        print(f"  原始点转换为右下角原点: ({x_br}, {y_br})")
        
        for target_origin in ["左上角", "右上角", "左下角"]:
            x_new, y_new = converter.convert_coordinate(x_br, y_br, "右下角", target_origin)
            print(f"  右下角 → {target_origin}: ({x_new}, {y_new})")
    
    # 演示往返转换（验证正确性）
    print(f"\n=== 往返转换验证 ===")
    test_point = (200, 150)
    print(f"测试点: {test_point}")
    
    for origin1 in origins:
        for origin2 in origins:
            if origin1 != origin2:
                # 正向转换
                x1, y1 = converter.convert_coordinate(test_point[0], test_point[1], origin1, origin2)
                # 反向转换
                x2, y2 = converter.convert_coordinate(x1, y1, origin2, origin1)
                # 验证是否回到原点
                error = abs(x2 - test_point[0]) + abs(y2 - test_point[1])
                print(f"  {origin1} → {origin2} → {origin1}: 误差 = {error:.6f}")
    
    # 演示批量转换
    print(f"\n=== 批量转换演示 ===")
    batch_coords = [(100, 100), (200, 200), (300, 300)]
    print(f"原始坐标: {batch_coords}")
    
    converted_batch = converter.batch_convert(batch_coords, "左上角", "右下角")
    print(f"转换为右下角原点: {converted_batch}")
    
    # 再转换回来验证
    back_converted = converter.batch_convert(converted_batch, "右下角", "左上角")
    print(f"转换回左上角原点: {back_converted}")


def quick_convert(x, y, image_width, image_height, from_origin, to_origin):
    """
    快速坐标转换函数（无需创建类实例）
    
    Args:
        x (float): 源坐标x
        y (float): 源坐标y
        image_width (int): 图像宽度
        image_height (int): 图像高度
        from_origin (str): 源原点位置
        to_origin (str): 目标原点位置
        
    Returns:
        tuple: (x_new, y_new) 转换后的坐标
    """
    converter = CoordinateConverter(image_width, image_height)
    return converter.convert_coordinate(x, y, from_origin, to_origin)


if __name__ == "__main__":
    # 运行演示
    demo_coordinate_conversion()
    
    print(f"\n=== 使用示例 ===")
    print("# 创建转换器")
    print("converter = CoordinateConverter(800, 600)")
    print()
    print("# 单个坐标转换")
    print("x_new, y_new = converter.convert_coordinate(100, 100, '左上角', '右下角')")
    print()
    print("# 批量转换")
    print("coords = [(100, 100), (200, 200)]")
    print("converted = converter.batch_convert(coords, '左上角', '右下角')")
    print()
    print("# 快速转换（无需创建实例）")
    print("x_new, y_new = quick_convert(100, 100, 800, 600, '左上角', '右下角')")
