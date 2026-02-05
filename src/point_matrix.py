import cv2
import numpy as np

class PointTransformer:
    def __init__(self, imgScalePCB=3.2, points_imageA=None, points_imageB=None):
        # 默认的缩放比例
        self.imgScalePCB = imgScalePCB
        
        # 如果未提供 points_imageA 和 points_imageB，使用默认值
        if points_imageA is None:
            points_imageA = np.array([[588, 135], [220, 387], [1175, 782]], dtype='float32')
        if points_imageB is None:
            points_imageB = np.array([[563, 160], [234, 396], [1105, 735]], dtype='float32')

        # 计算 B2A 矩阵
        self.B2A_matrix = cv2.getAffineTransform(points_imageB, points_imageA)
        
        # 将 B2A_matrix 转换为 3x3 矩阵
        self.B2A_matrix_full = np.vstack([self.B2A_matrix, [0, 0, 1]])
        
        # 计算 A2B 矩阵
        self.A2B_matrix = np.linalg.inv(self.B2A_matrix_full)

    # 从 A 变换到 B
    def A2B(self, x, y):
        point_A = np.array([x, y], dtype='float32')
        point_A_homogeneous = np.array([point_A[0], point_A[1], 1])
        return (self.A2B_matrix @ point_A_homogeneous)[:2]

    # 从 B 变换到 A
    def B2A(self, x, y):
        point_B = np.array([x / self.imgScalePCB, y / self.imgScalePCB], dtype='float32')
        point_B_homogeneous = np.array([point_B[0], point_B[1], 1])
        return self.B2A_matrix_full @ point_B_homogeneous

    # 将当前 B 坐标转换为原始 B 坐标
    def curB_2_OriB(self, x, y):
        return int(x * self.imgScalePCB), int(y * self.imgScalePCB)

# 示例：外部使用
if __name__ == '__main__':
    # 创建 PointTransformer 类的实例
    transformer = PointTransformer()

    # 调用类方法
    xA, yA = 100, 150
    xB, yB = transformer.A2B(xA, yA)  # 从 A 到 B
    print(f"Point A({xA}, {yA}) converted to B({xB}, {yB})")

    xA2, yA2 = transformer.B2A(xB, yB)  # 从 B 到 A
    print(f"Point B({xB}, {yB}) converted back to A({xA2}, {yA2})")

    # 转换当前 B 坐标到原始 B 坐标
    cur_x, cur_y = 500, 400
    ori_x, ori_y = transformer.curB_2_OriB(cur_x, cur_y)
    print(f"Current B({cur_x}, {cur_y}) converted to Original B({ori_x}, {ori_y})")
