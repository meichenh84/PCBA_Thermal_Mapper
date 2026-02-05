"""
坐标变换模块

主要功能：
1. 热力图与布局图之间的坐标转换
2. 支持仿射变换和透视变换
3. 智能点匹配算法
4. 双向坐标转换（A->B 和 B->A）
"""

import cv2
import numpy as np

class PointTransformer:
    def __init__(self, points_A=None, points_B=None):
        """
        points_A: 图A上的打点（原始图像坐标）
        points_B: 图B上的打点（原始图像坐标）

        优化用户体验：自动对点进行X轴排序，用户打点顺序不再有要求。
        当点数≥4时，采用单应性（透视变换）；当点数==3时，采用仿射；否则抛错。
        """
        ptsA = np.asarray(points_A, dtype=np.float32)
        ptsB = np.asarray(points_B, dtype=np.float32)

        if ptsA.shape[0] != ptsB.shape[0] or ptsA.shape[0] < 3:
            raise ValueError(f"点数量不足或不匹配，A:{ptsA.shape[0]} B:{ptsB.shape[0]}")

        # 智能点匹配：自动找到最佳的点对应关系
        self.points_A, self.points_B = self._smart_point_matching(ptsA, ptsB)
        
        # 检查点的对应关系是否合理
        self._validate_point_correspondence()

        self.is_homography = False
        self.H_A2B = None
        self.H_B2A = None
        self.A2B_affine = None  # 2x3
        self.B2A_affine = None  # 2x3

        n = ptsA.shape[0]
        if n >= 4:
            # 使用RANSAC估计单应矩阵，使用匹配后的点
            H_A2B, _ = cv2.findHomography(self.points_A, self.points_B, method=cv2.RANSAC, ransacReprojThreshold=3.0)
            H_B2A, _ = cv2.findHomography(self.points_B, self.points_A, method=cv2.RANSAC, ransacReprojThreshold=3.0)
            if H_A2B is None or H_B2A is None:
                raise ValueError("单应矩阵估计失败，请检查打点是否共线或者异常")
            self.is_homography = True
            self.H_A2B = H_A2B
            self.H_B2A = H_B2A
        else:
            # 3点使用精确仿射变换，使用匹配后的点
            A2B = cv2.getAffineTransform(self.points_A[:3], self.points_B[:3])
            B2A = cv2.getAffineTransform(self.points_B[:3], self.points_A[:3])
            self.A2B_affine = A2B  # 2x3
            self.B2A_affine = B2A  # 2x3

    def _validate_point_correspondence(self):
        """
        验证点对应关系是否合理，给用户提示
        """
        print(f"点对应关系验证:")
        for i in range(len(self.points_A)):
            ptA = self.points_A[i]
            ptB = self.points_B[i]
            dist = np.sqrt((ptA[0] - ptB[0])**2 + (ptA[1] - ptB[1])**2)
            print(f"  点{i+1}: A({ptA[0]:.0f}, {ptA[1]:.0f}) <-> B({ptB[0]:.0f}, {ptB[1]:.0f}) 距离: {dist:.1f}")
        
        # 检查是否有异常大的距离
        max_dist = 0
        for i in range(len(self.points_A)):
            ptA = self.points_A[i]
            ptB = self.points_B[i]
            dist = np.sqrt((ptA[0] - ptB[0])**2 + (ptA[1] - ptB[1])**2)
            max_dist = max(max_dist, dist)
        
        if max_dist > 100:  # 如果距离超过100像素，给出警告
            print(f"⚠️  警告：检测到较大的点距离({max_dist:.1f}px)，请检查点对应关系是否正确")
            print(f"💡 提示：如果对齐效果不好，请确保A图和B图的点按相同顺序对应")

    def _smart_point_matching(self, ptsA, ptsB):
        """
        智能点匹配：通过距离最小化找到最佳的点对应关系
        解决用户打点顺序不匹配的问题
        """
        n = len(ptsA)
        if n <= 1:
            return ptsA, ptsB
        
        print(f"智能点匹配：自动匹配最佳点对关系")
        print(f"原始A点: {ptsA}")
        print(f"原始B点: {ptsB}")
        
        # 使用匈牙利算法或暴力搜索找到最佳匹配
        best_matching = None
        min_total_distance = float('inf')
        
        # 生成所有可能的匹配组合
        from itertools import permutations
        for perm in permutations(range(n)):
            total_distance = 0
            for i in range(n):
                ptA = ptsA[i]
                ptB = ptsB[perm[i]]
                dist = np.sqrt((ptA[0] - ptB[0])**2 + (ptA[1] - ptB[1])**2)
                total_distance += dist
            
            if total_distance < min_total_distance:
                min_total_distance = total_distance
                best_matching = perm
        
        # 应用最佳匹配
        matched_ptsA = ptsA.copy()
        matched_ptsB = ptsB[list(best_matching)]
        
        print(f"最佳匹配: {best_matching}")
        print(f"匹配后A点: {matched_ptsA}")
        print(f"匹配后B点: {matched_ptsB}")
        print(f"总距离: {min_total_distance:.1f}")
        
        return matched_ptsA, matched_ptsB

    def _sort_points_by_x(self, ptsA, ptsB):
        """
        智能点排序：通过相对位置关系匹配找到正确的点对应关系
        用户打点顺序不再有要求，系统自动匹配最合理的点对
        """
        n = len(ptsA)
        if n <= 1:
            return ptsA, ptsB
            
        # 方法：按X坐标排序A点，然后通过相对位置关系匹配B点
        sorted_indices_A = np.argsort(ptsA[:, 0])
        sorted_ptsA = ptsA[sorted_indices_A]
        
        # 按X坐标排序B点
        sorted_indices_B = np.argsort(ptsB[:, 0])
        sorted_ptsB = ptsB[sorted_indices_B]
        
        print(f"智能点匹配：按X坐标排序，确保对应关系正确")
        print(f"排序前A点: {ptsA}")
        print(f"排序前B点: {ptsB}")
        print(f"排序后A点: {sorted_ptsA}")
        print(f"排序后B点: {sorted_ptsB}")
        
        # 验证匹配的合理性
        print(f"匹配验证:")
        for i in range(n):
            ptA = sorted_ptsA[i]
            ptB = sorted_ptsB[i]
            print(f"  A点{i+1}({ptA[0]:.0f}, {ptA[1]:.0f}) <-> B点{i+1}({ptB[0]:.0f}, {ptB[1]:.0f})")
        
        return sorted_ptsA, sorted_ptsB

    # 从 A 变换到 B
    def A2B(self, x, y):
        p = np.array([x, y], dtype=np.float32)
        if self.is_homography:
            vec = np.array([p[0], p[1], 1.0], dtype=np.float32)
            res = self.H_A2B @ vec
            w = res[2] if res[2] != 0 else 1.0
            return (res[0] / w, res[1] / w)
        else:
            # 仿射 2x3
            res = self.A2B_affine @ np.array([p[0], p[1], 1.0], dtype=np.float32)
            return (res[0], res[1])

    # 从 B 变换到 A
    def B2A(self, x, y):
        p = np.array([x, y], dtype=np.float32)
        if self.is_homography:
            vec = np.array([p[0], p[1], 1.0], dtype=np.float32)
            res = self.H_B2A @ vec
            w = res[2] if res[2] != 0 else 1.0
            return (res[0] / w, res[1] / w)
        else:
            res = self.B2A_affine @ np.array([p[0], p[1], 1.0], dtype=np.float32)
            return (res[0], res[1])

    def get_B2A_matrix(self):
        # 兼容旧接口
        if self.is_homography:
            return self.H_B2A
        return self.B2A_affine

    # 兼容旧接口：从A坐标（原始图像坐标系）转换到B坐标（原始图像坐标系）
    def A_2_oriB(self, x: float, y: float):
        bx, by = self.A2B(x, y)
        return bx, by

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