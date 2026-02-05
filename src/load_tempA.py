import pandas as pd
import time
import numpy as np
import os

class TempLoader:
    _instance = None  # 单例实例
    _tempA = None  # 存储 tempA 数据
    _current_file_path = None  # 当前文件路径

    def __new__(cls, file_path='tempA.csv'):
        # 如果没有实例或者文件路径改变了，重新创建实例
        if cls._instance is None or cls._current_file_path != file_path:
            cls._instance = super().__new__(cls)
            cls._instance._file_path = file_path
            cls._current_file_path = file_path
            cls._instance._initialize_tempA()
        return cls._instance

    def _initialize_tempA(self):
        """初始化 tempA 数据的加载"""
        print("Initializing tempA...")
        self._load_tempA()

    def _load_tempA(self):
        """加载 tempA 数据，根据文件后缀选择加载方式"""
        file_extension = os.path.splitext(self._file_path)[1].lower()  # 获取文件扩展名并转小写
        
        if file_extension == '.xlsx':
            self._tempA = pd.read_excel(self._file_path).values
            print("-->>> tempA loaded from Excel, size:", self._tempA.shape)
        elif file_extension == '.csv':
            self._tempA = pd.read_csv(self._file_path).values
            print("-->>> tempA loaded from CSV, size:", self._tempA.shape)
        else:
            raise ValueError("Unsupported file type. Please use .xlsx or .csv files.")

    def get_tempA(self):
        """获取 tempA 数据"""
        return self._tempA
    
    #获取区域内最大值
    def get_max_temp(self, x1, y1, x2, y2, scale = 1):
        maxH, maxW = self._tempA.shape
        _x1 = max(0, int(x1 / scale))
        _y1 = max(0, int(y1 / scale))
        _x2 = min(maxW, int(x2 / scale))
        _y2 = min(maxH, int(y2 / scale))
        sub_matrix = self._tempA[_y1:_y2, _x1:_x2]

        if sub_matrix is not None and sub_matrix.size > 0:
            return np.max(sub_matrix)
        return 0
    
    def get_max_temp_coords(self, x1, y1, x2, y2, scale = 1):
        maxH, maxW = self._tempA.shape
        _x1 = max(0, int(x1 / scale))
        _y1 = max(0, int(y1 / scale))
        _x2 = min(maxW, int(x2 / scale))
        _y2 = min(maxH, int(y2 / scale))
        sub_matrix = self._tempA[_y1:_y2, _x1:_x2]

        if sub_matrix is not None and sub_matrix.size > 0:
            max_index = np.argmax(sub_matrix)
            max_coords = np.unravel_index(max_index, sub_matrix.shape)
            return (max_coords[1] + _x1)*scale, (max_coords[0] + _y1)*scale
        return 0, 0


# 外部代码使用示例
# 在程序中其他地方使用时，不需要再次初始化，只需直接调用TempLoader()
# loader = TempLoader('tempA.xlsx')

# 外部代码可以继续执行其他任务，直到需要获取tempA时
# print("Waiting for tempA to load...")

# 获取 tempA 数据（会阻塞直到数据加载完成）
# tempA_data = loader.get_tempA()

# 数据加载完成后，外部代码获得数据并使用
# print("-->>> Retrieved tempA:", tempA_data)
