# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """
# 座標點仿射變換矩陣模組 (point_matrix.py)

# 用途：
#     提供熱力圖（imageA）與 Layout 圖（imageB）之間的座標轉換功能。
#     使用三組對應點計算仿射變換矩陣，實現兩張圖之間的座標映射。
#     注意：此檔案為早期版本，功能已被 point_transformer.py 取代。

# 在整個應用中的角色：
#     - 早期的座標轉換實作，提供 A2B 和 B2A 基本轉換
#     - 已被功能更完整的 point_transformer.py 取代

# 關聯檔案：
#     - point_transformer.py：功能更完整的新版本（包含 A_2_oriB 等方法）
#     - recognize_image.py：使用座標轉換進行元器件識別
# """

# import cv2
# import numpy as np


# class PointTransformer:
#     """座標點仿射變換器（早期版本）。

#     透過三組對應點計算 2x3 仿射變換矩陣，實現熱力圖（A）與 Layout 圖（B）
#     之間的座標雙向轉換。B 圖座標會先除以 imgScalePCB 縮放比例再進行變換。

#     屬性：
#         imgScalePCB (float): Layout 圖的縮放比例（原始尺寸 / 顯示尺寸）
#         B2A_matrix (numpy.ndarray): B→A 的 2x3 仿射變換矩陣
#         B2A_matrix_full (numpy.ndarray): B→A 的 3x3 齊次座標變換矩陣
#         A2B_matrix (numpy.ndarray): A→B 的 3x3 逆變換矩陣
#     """

#     def __init__(self, imgScalePCB=3.2, points_imageA=None, points_imageB=None):
#         """初始化座標變換器，計算仿射變換矩陣。

#         Args:
#             imgScalePCB (float): Layout 圖的縮放比例（預設 3.2）
#             points_imageA (numpy.ndarray): 熱力圖上的三個對應點座標
#             points_imageB (numpy.ndarray): Layout 圖上的三個對應點座標
#         """
#         self.imgScalePCB = imgScalePCB

#         # 若未提供對應點，使用預設座標
#         if points_imageA is None:
#             points_imageA = np.array([[588, 135], [220, 387], [1175, 782]], dtype='float32')
#         if points_imageB is None:
#             points_imageB = np.array([[563, 160], [234, 396], [1105, 735]], dtype='float32')

#         # 計算 B→A 的 2x3 仿射變換矩陣
#         self.B2A_matrix = cv2.getAffineTransform(points_imageB, points_imageA)

#         # 擴展為 3x3 齊次座標矩陣（加入 [0, 0, 1] 列）
#         self.B2A_matrix_full = np.vstack([self.B2A_matrix, [0, 0, 1]])

#         # 計算 A→B 的逆變換矩陣
#         self.A2B_matrix = np.linalg.inv(self.B2A_matrix_full)

#     def A2B(self, x, y):
#         """將 A 圖（熱力圖）座標轉換為 B 圖（Layout 圖）座標。"""
#         point_A = np.array([x, y], dtype='float32')
#         point_A_homogeneous = np.array([point_A[0], point_A[1], 1])
#         return (self.A2B_matrix @ point_A_homogeneous)[:2]

#     def B2A(self, x, y):
#         """將 B 圖（Layout 圖）座標轉換為 A 圖（熱力圖）座標。
#         B 圖座標會先除以 imgScalePCB 縮放比例再進行變換。"""
#         point_B = np.array([x / self.imgScalePCB, y / self.imgScalePCB], dtype='float32')
#         point_B_homogeneous = np.array([point_B[0], point_B[1], 1])
#         return self.B2A_matrix_full @ point_B_homogeneous

#     def curB_2_OriB(self, x, y):
#         """將目前顯示的 B 圖座標轉換為原始 B 圖座標（乘以縮放比例）。"""
#         return int(x * self.imgScalePCB), int(y * self.imgScalePCB)

# # 示例：外部使用
# if __name__ == '__main__':
#     # 创建 PointTransformer 类的实例
#     transformer = PointTransformer()

#     # 调用类方法
#     xA, yA = 100, 150
#     xB, yB = transformer.A2B(xA, yA)  # 从 A 到 B
#     print(f"Point A({xA}, {yA}) converted to B({xB}, {yB})")

#     xA2, yA2 = transformer.B2A(xB, yB)  # 从 B 到 A
#     print(f"Point B({xB}, {yB}) converted back to A({xA2}, {yA2})")

#     # 转换当前 B 坐标到原始 B 坐标
#     cur_x, cur_y = 500, 400
#     ori_x, ori_y = transformer.curB_2_OriB(cur_x, cur_y)
#     print(f"Current B({cur_x}, {cur_y}) converted to Original B({ori_x}, {ori_y})")
