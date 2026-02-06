#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv8 物件偵測模型封裝模組 (yolo_v8.py)

用途：
    封裝 Ultralytics YOLOv8 深度學習模型，提供 PCB 元器件的
    自動偵測功能。使用單例模式確保模型只載入一次（避免重複載入的
    記憶體和時間開銷）。支援從檔案路徑、PIL 影像、OpenCV 影像
    三種輸入格式進行偵測。

在整個應用中的角色：
    - 作為 AI 偵測引擎，被 recognize_image.py 的 yolo_process_pcb_image() 呼叫
    - 使用自訓練的模型權重（../models/yolo/best.pt）偵測 PCB 元器件

關聯檔案：
    - recognize_image.py：呼叫 process_cv_image() 偵測 Layout 圖上的元器件
    - main.py：透過 recognize_image.py 間接使用本模組
    - ../models/yolo/best.pt：自訓練的 YOLOv8 模型權重檔案
"""

from ultralytics import YOLO
import cv2
import numpy as np
import time
import torch


class YOLOv8Instance:
    """YOLOv8 物件偵測模型的單例封裝類別。

    使用單例模式（Singleton Pattern）確保整個應用只載入一次模型。
    首次建立實例時會載入模型權重並進行預熱（warm-up），
    後續呼叫直接返回已載入的實例。

    屬性：
        _instance (YOLOv8Instance): 單例實例（類別變數）
        model (YOLO): YOLOv8 模型實例
    """

    _instance = None

    def __new__(cls):
        """實現單例模式，首次建立時載入模型並預熱。"""
        if cls._instance is None:
            cls._instance = super(YOLOv8Instance, cls).__new__(cls)

            print("正在載入 YOLOv8 模型...")
            start_time = time.time()

            # 檢查是否有 GPU 可用（目前強制使用 CPU）
            device = 'cpu'
            print(f"使用裝置: {device}")

            # 載入自訓練的模型權重
            cls._instance.model = YOLO('../models/yolo/best.pt')
            cls._instance.model.to(device)

            # 預熱模型（第一次推理通常較慢，預熱可加速後續推理）
            print("正在預熱模型...")
            dummy_input = torch.randn(1, 3, 640, 640).to(device)
            with torch.no_grad():
                _ = cls._instance.model(dummy_input, verbose=False)

            load_time = time.time() - start_time
            print(f"YOLOv8 模型載入完成，耗時: {load_time:.2f} 秒")
        return cls._instance

    def detect(self, image):
        """執行物件偵測並回傳結果。

        Args:
            image (numpy.ndarray): 輸入影像（BGR 格式）

        Returns:
            list: YOLOv8 偵測結果列表
        """
        results = self.model(image)
        return results

    def process_image(self, image_path):
        """從檔案路徑載入影像並執行偵測（支援中文路徑）。

        Args:
            image_path (str): 影像檔案路徑

        Returns:
            list: YOLOv8 偵測結果列表
        """
        # 使用 numpy 讀取以支援中文路徑
        img_array = np.fromfile(image_path, dtype=np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        results = self.detect(image)
        return results

    def process_pil_image(self, pil_image):
        """處理 PIL 影像並執行偵測。

        Args:
            pil_image (PIL.Image): PIL 格式的影像

        Returns:
            list: YOLOv8 偵測結果列表
        """
        # 將 PIL 影像轉換為 NumPy 陣列
        image = np.array(pil_image)

        # 若為 RGB 模式，轉換為 BGR（OpenCV 格式）
        if pil_image.mode == 'RGB':
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        results = self.detect(image)
        return results

    def process_cv_image(self, cv_image):
        """處理 OpenCV 格式影像並執行偵測。

        Args:
            cv_image (numpy.ndarray): OpenCV 格式影像（BGR）

        Returns:
            list: YOLOv8 偵測結果列表
        """
        results = self.detect(cv_image)
        return results

if __name__ == "__main__":
    yolov8_instance = YOLOv8Instance()
    
    # 示例用法：从文件中读取图像进行识别
    results = yolov8_instance.process_image('imageB.jpg')
    
    # 打印检测结果
    for bbox in results[0].boxes:
        print(f'Class: {int(bbox.cls[0])}, Confidence: {bbox.conf[0]}, BBox: {bbox.xyxy[0]}')
