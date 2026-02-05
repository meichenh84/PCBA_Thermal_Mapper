import json
import os

class GlobalConfig:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
        return cls._instance

    def __init__(self):
        # 配置类初始化时不再重复执行
        if not hasattr(self, '_initialized'):
            self._initialized = True
            if not os.path.exists("config"):
                os.makedirs("config")
            self.load_from_json()
            # 默认配置项，可以根据需要进行调整
            # self._config = {
            #     "debug": True,
            #     "log_level": "INFO",
            #     "theme": "light",
            #     "max_connections": 10,
            #     "magnifier_switch": False,
            #     "circle_switch": False,
            # }

    def set(self, key, value):
        """设置配置项"""
        self._config[key] = value

    def get(self, key, default=None):
        """获取配置项"""
        return self._config.get(key, default)

    def remove(self, key):
        """移除配置项"""
        if key in self._config:
            del self._config[key]

    def clear(self):
        """清空所有配置"""
        self._config.clear()

    def save_to_json(self, filename='config/config.json'):
        """将 self._config 字典保存到 JSON 文件"""
        # 确保配置目录存在
        config_dir = os.path.dirname(filename)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        with open(filename, mode='w', encoding='utf-8') as file:
            json.dump(self._config, file, ensure_ascii=False, indent=2)

    def load_from_json(self, file_path='config/config.json'):
        """从 JSON 文件读取数据并赋值给 self._config"""
        if os.path.exists(file_path):
            try:
                with open(file_path, mode='r', encoding='utf-8') as file:
                    self._config = json.load(file)
                print(f"从JSON文件加载配置: {file_path}")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"加载JSON配置文件失败: {e}，使用默认配置")
                self._config = self._get_default_config()
        else:
            print(f"配置文件不存在: {file_path}，使用默认配置")
            self._config = self._get_default_config()
    
    def _get_default_config(self):
        """获取默认配置"""
        return {
            "magnifier_switch": True,  # 放大镜默认选中
            "circle_switch": False,
            "last_folder_path": None,
            
            # 热力图标记颜色和字体设置
            "heat_rect_color": "#BCBCBC",           # 矩形框颜色
            "heat_name_color": "#FFFFFF",           # 元器件名称颜色
            "heat_name_font_size": 12,              # 元器件名称字体大小
            "heat_temp_color": "#FF0000",           # 最高温度颜色
            "heat_temp_font_size": 10,              # 最高温度字体大小
            "heat_selected_color": "#4A90E2",       # 选中矩形框颜色
            "heat_anchor_color": "#FF0000",         # 选中矩形框锚点颜色
            "heat_anchor_radius": 4,                # 选中矩形框锚点半径
            
            # Layout图标记颜色和字体设置
            "layout_rect_color": "#BCBCBC",         # 矩形框颜色
            "layout_name_color": "#FFFFFF",         # 元器件名称颜色
            "layout_name_font_size": 12,            # 元器件名称字体大小
            "layout_temp_color": "#FF0000",         # 最高温度颜色
            "layout_temp_font_size": 10,            # 最高温度字体大小
        }

    def update(self, newObj):
       self. _config.update(newObj)  # 将newObj的内容覆盖到_config中
       


# 使用示例
# config = GlobalConfig()
# config.set("app_name", "MyApp")

# print(config.get("app_name"))  # 输出: MyApp
# print(config.get("log_level"))  # 输出: INFO
