import json
import os
import threading
from pathlib import Path

class TemperatureConfigManager:
    def __init__(self, folder_path=None):
        """初始化温度配置管理器"""
        print(f"初始化温度配置管理器，文件夹路径: {folder_path}")
        self.folder_path = folder_path
        self.config_data = {}
        self.current_files = {}
        
        # 默认配置 - 移除废弃字段，添加文件路径配置
        self.default_config = {
            # 温度过滤参数
            "min_temp": 50.0,
            "max_temp": 80.0,
            "min_width": 10.0,
            "min_height": 10.0,
            "p_w": 237.0,
            "p_h": 194.0,
            "p_origin": "左下",
            "p_origin_offset_x": 0.0,
            "p_origin_offset_y": 0.0,
            "c_padding_left": 0.0,
            "c_padding_top": 0.0,
            "c_padding_right": 0.0,
            "c_padding_bottom": 0.0,
            # 文件路径配置
            "current_heat_file": None,
            "current_pcb_file": None,
            "current_temp_file": None,
            "current_layout_file": None,
            "current_layout_data_file": None
        }
        
        if folder_path:
            self.set_folder_path(folder_path)
        else:
            # 如果没有提供文件夹路径，使用默认配置
            self.config_data = self.default_config.copy()
            print("使用默认配置初始化配置管理器")
    
    def set_folder_path(self, folder_path):
        """设置文件夹路径并加载配置"""
        print(f"TemperatureConfigManager: 开始设置文件夹路径 {folder_path}")
        try:
            self.folder_path = folder_path
            print(f"set_folder_path: 开始处理文件夹路径 {folder_path}")
            
            # 创建配置目录
            config_dir = os.path.join(folder_path, "config")
            print(f"set_folder_path: 配置目录 {config_dir}")
            
            # 检查配置目录是否存在
            if not os.path.exists(config_dir):
                print(f"set_folder_path: 检查配置目录是否存在")
                os.makedirs(config_dir, exist_ok=True)
                print(f"创建配置目录: {config_dir}")
            
            # 加载配置
            print(f"set_folder_path: 开始加载配置")
            self.load_config()
            print(f"set_folder_path: 配置加载完成")
            
            print(f"TemperatureConfigManager: 文件夹路径设置完成")
        except Exception as e:
            print(f"设置文件夹路径时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if not self.folder_path:
                print("没有文件夹路径，使用默认配置")
                self.config_data = self.default_config.copy()
                return
            
            config_file = os.path.join(self.folder_path, "config", "temperature_config.json")
            print(f"load_config: 开始加载配置文件 {config_file}")
            
            if os.path.exists(config_file):
                print(f"load_config: 配置文件存在，开始读取")
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                print(f"加载温度过滤配置: {config_file}")
            else:
                print(f"配置文件不存在，使用默认配置")
                self.config_data = self.default_config.copy()
                self.save_config()
            
            print(f"load_config: 配置加载完成")
        except Exception as e:
            print(f"加载配置时出错: {e}")
            import traceback
            traceback.print_exc()
            self.config_data = self.default_config.copy()
    
    def save_config(self):
        """保存配置文件"""
        try:
            if not self.folder_path:
                print("没有文件夹路径，无法保存配置")
                return
            
            config_file = os.path.join(self.folder_path, "config", "temperature_config.json")
            print(f"保存温度过滤配置: {config_file}")
            
            # 确保配置目录存在
            config_dir = os.path.dirname(config_file)
            os.makedirs(config_dir, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            
            print(f"配置保存成功")
        except Exception as e:
            print(f"保存配置时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def get(self, key, default=None):
        """获取配置值"""
        return self.config_data.get(key, default)
    
    def set(self, key, value):
        """设置配置值"""
        self.config_data[key] = value
    
    def get_current_files(self):
        """获取当前文件信息"""
        return self.current_files.copy()
    
    def set_current_files(self, files):
        """设置当前文件信息"""
        self.current_files = files.copy()
    
    def get_relative_path(self, file_path):
        """获取相对路径"""
        if not file_path or not self.folder_path:
            return file_path
        
        try:
            return os.path.relpath(file_path, self.folder_path)
        except:
            return file_path
    
    def get_file_info_display(self):
        """获取文件信息显示文本"""
        try:
            if not self.current_files:
                return "未加载文件"
            
            info_lines = []
            for file_type, file_path in self.current_files.items():
                if file_path:
                    relative_path = self.get_relative_path(file_path)
                    info_lines.append(f"{file_type}: {relative_path}")
                else:
                    info_lines.append(f"{file_type}: 未选择")
            
            return "\n".join(info_lines)
        except Exception as e:
            print(f"get_file_info_display: 获取文件信息时出错: {e}")
            return "未加载文件"
    
    def get_all_parameters(self):
        """获取所有参数"""
        return self.config_data.copy()
    
    def save_parameters(self, params):
        """保存参数"""
        try:
            print(f"保存参数: {params}")
            self.config_data.update(params)
            self.save_config()
            print(f"参数保存成功")
        except Exception as e:
            print(f"保存参数时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def update(self, **kwargs):
        """更新配置"""
        self.config_data.update(kwargs)
        self.save_config()
    
    def set_file_path(self, file_type, file_path):
        """设置文件路径"""
        if file_type in ["current_heat_file", "current_pcb_file", "current_temp_file", "current_layout_file", "current_layout_data_file"]:
            self.config_data[file_type] = file_path
            self.save_config()
            print(f"设置文件路径: {file_type} = {file_path}")
        else:
            print(f"不支持的文件类型: {file_type}")
    
    def get_file_path(self, file_type):
        """获取文件路径"""
        return self.config_data.get(file_type, None)
    
    def get_all_file_paths(self):
        """获取所有文件路径"""
        return {
            "current_heat_file": self.config_data.get("current_heat_file"),
            "current_pcb_file": self.config_data.get("current_pcb_file"),
            "current_temp_file": self.config_data.get("current_temp_file"),
            "current_layout_file": self.config_data.get("current_layout_file"),
            "current_layout_data_file": self.config_data.get("current_layout_data_file")
        }
    
    def clear_file_paths(self):
        """清空所有文件路径"""
        for file_type in ["current_heat_file", "current_pcb_file", "current_temp_file", "current_layout_file", "current_layout_data_file"]:
            self.config_data[file_type] = None
        self.save_config()
        print("已清空所有文件路径")
