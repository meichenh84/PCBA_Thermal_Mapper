from ultralytics import YOLO
import cv2
import numpy as np
import time
import torch

class YOLOv8Instance:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(YOLOv8Instance, cls).__new__(cls)

            print("正在加载 YOLOv8 模型...")
            start_time = time.time()
            
            # 检查是否有GPU可用
            device = 'cpu' #'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"使用设备: {device}")
            
            # 加载模型并指定设备
            cls._instance.model = YOLO('../models/yolo/best.pt')  # 加载YOLOv8模型
            cls._instance.model.to(device)
            
            # 预热模型（第一次推理通常较慢）
            print("正在预热模型...")
            dummy_input = torch.randn(1, 3, 640, 640).to(device)
            with torch.no_grad():
                _ = cls._instance.model(dummy_input, verbose=False)
            
            load_time = time.time() - start_time
            print(f"YOLOv8 模型加载完成，耗时: {load_time:.2f} 秒")
            # cls._instance.model = YOLO('../models/yolo/best.pt')  # 加载YOLOv8模型
        return cls._instance

    def detect(self, image):
        """进行物体检测并返回结果"""
        results = self.model(image)
        return results

    def process_image(self, image_path):
        """加载图像并进行检测，返回检测结果"""
        # 使用numpy读取支持中文路径
        img_array = np.fromfile(image_path, dtype=np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        results = self.detect(image)
        return results

    def process_pil_image(self, pil_image):
        """处理PIL图像并进行检测，返回检测结果"""
        # 将PIL图像转换为NumPy数组
        image = np.array(pil_image)

        # 如果使用的是RGB模式，需要将其转换为BGR模式
        if pil_image.mode == 'RGB':
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # 进行检测
        results = self.detect(image)
        return results
    
    def process_cv_image(self, cv_image):
        """处理OpenCV格式图像并进行检测，返回检测结果"""
        # 进行检测
        results = self.detect(cv_image)
        return results

if __name__ == "__main__":
    yolov8_instance = YOLOv8Instance()
    
    # 示例用法：从文件中读取图像进行识别
    results = yolov8_instance.process_image('imageB.jpg')
    
    # 打印检测结果
    for bbox in results[0].boxes:
        print(f'Class: {int(bbox.cls[0])}, Confidence: {bbox.conf[0]}, BBox: {bbox.xyxy[0]}')
