# =============================================================================
# 檔案名稱：circle_ring_draw.py
# 用途：圓形標記繪製模組
# 說明：在圖像上繪製帶編號的圓形標記點（外白色圓環 + 內紅/綠色圓 + 白色編號文字），
#       用於標記熱力圖與 Layout 圖之間的對齊點。
#       使用「先放大再縮小」的技巧（scale_factor 參數）提高繪製精度，
#       避免在小半徑圓形上出現鍮齒或失真的問題。
#
# 在整個應用中的角色：
#       當使用者在熱力圖或 Layout 圖上手動標記對齊點時，本模組負責將這些對齊點
#       以視覺化的圓形標記繪製到 numpy 圖像陣列上，供畫面顯示或匯出使用。
#
# 關聯檔案：
#       - draw_rect.py：另一個繪製模組，負責繪製溫度標記（矩形框 + 三角形 + 文字）
#       - recognize_circle.py：圓形偵測模組，偵測圖像中已有的圓形特徵
#       - 主程式（GUI）會呼叫本模組的函式來更新圖像顯示
# =============================================================================

import cv2
import numpy as np

def draw_circle_ring_text(imageA_np, point, index = "", radius_red = 8, ring_width = 2, scale_factor=8):
    """
    在指定圖像上繪製圓形標記（外白環 + 內圓 + 可選編號文字）。

    繪製流程：
    1. 將圖像放大 scale_factor 倍以提高繪製精度
    2. 在放大後的圖像上繪製白色外圓環與內圓
    3. 若有編號，則在圓心處繪製白色編號文字
    4. 將圖像縮小回原始尺寸

    參數：
        imageA_np (numpy.ndarray): 輸入圖像（BGR 格式的 numpy 陣列）。
        point (tuple): 圓心位置，格式為 (x, y)。
        index (str): 要顯示的編號文字，預設為空字串。
        radius_red (int): 內圓半徑，預設為 8。
        ring_width (int): 外圓環寬度，預設為 2。
        scale_factor (int): 縮放係數，預設為 8。

    回傳：
        numpy.ndarray: 繪製完成後的圖像。
    """
    # 取得原圖尺寸
    original_height, original_width = imageA_np.shape[:2]

    # 將圖像放大以提高圓形繪製精度（避免小圓鍮齒問題）
    imageA_np_resized = cv2.resize(imageA_np, (original_width * scale_factor, original_height * scale_factor))

    # 將圓心座標與半徑同步放大，以匹配放大後的圖像尺寸
    point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    # 繪製外圓（白色實心圓環）
    cv2.circle(imageA_np_resized, point_resized, radius_red_resized + ring_width_resized, (255, 255, 255), thickness=-1)

    # 繪製內圓（紅色實心圓）
    cv2.circle(imageA_np_resized, point_resized, radius_red_resized, (0, 0, 255), thickness=-1)

    if index:
        # cv2.putText(imageA_np_resized, "2", (point_resized[0] - scale_factor * 4 + 2, point_resized[1] + scale_factor * 3 + 2),cv2.FONT_HERSHEY_COMPLEX, 4, (255, 255, 255), 8, cv2.LINE_AA)
        cv2.putText(imageA_np_resized, str(index), (point_resized[0] - scale_factor * 4, point_resized[1] + scale_factor * 4), cv2.FONT_HERSHEY_COMPLEX, 3.5, (255, 255, 255), 10, cv2.LINE_AA)

    # 將圖像縮小回原始尺寸
    imageA_np_resized = cv2.resize(imageA_np_resized, (original_width, original_height))

    # 可選：使用高斯模糊減少鍮齒（目前已停用）
    # imageA_np_resized = cv2.GaussianBlur(imageA_np_resized, (5, 5), 0)

    return imageA_np_resized

def draw_circle_ring(imageA_np, point, radius_red = 8, ring_width = 2, scale_factor=8):
    """
    在指定圖像上繪製圓形標記（外白環 + 內圓 + 可選編號文字）。

    繪製流程：
    1. 將圖像放大 scale_factor 倍以提高繪製精度
    2. 在放大後的圖像上繪製白色外圓環與內圓
    3. 若有編號，則在圓心處繪製白色編號文字
    4. 將圖像縮小回原始尺寸

    參數：
        imageA_np (numpy.ndarray): 輸入圖像（BGR 格式的 numpy 陣列）。
        point (tuple): 圓心位置，格式為 (x, y)。
        index (str): 要顯示的編號文字，預設為空字串。
        radius_red (int): 內圓半徑，預設為 8。
        ring_width (int): 外圓環寬度，預設為 2。
        scale_factor (int): 縮放係數，預設為 8。

    回傳：
        numpy.ndarray: 繪製完成後的圖像。
    """
    # 取得原圖尺寸
    original_height, original_width = imageA_np.shape[:2]

    # 將圖像放大以提高圓形繪製精度（避免小圓鍮齒問題）
    imageA_np_resized = cv2.resize(imageA_np, (original_width * scale_factor, original_height * scale_factor))

    # 將圓心座標與半徑同步放大，以匹配放大後的圖像尺寸
    point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    # 繪製外圓（白色實心圓環）
    cv2.circle(imageA_np_resized, point_resized, radius_red_resized + ring_width_resized, (255, 255, 255), thickness=-1)

    # 繪製內圓（紅色實心圓）
    cv2.circle(imageA_np_resized, point_resized, radius_red_resized, (0, 255, 0), thickness=-1)

    # 將圖像縮小回原始尺寸
    imageA_np_resized = cv2.resize(imageA_np_resized, (original_width, original_height))

    # 可選：使用高斯模糊減少鍮齒（目前已停用）
    # imageA_np_resized = cv2.GaussianBlur(imageA_np_resized, (5, 5), 0)

    return imageA_np_resized


def draw_points_circle_ring_text(imageA_np, points, radius_red = 8, ring_width = 2, scale_factor=8):
    """
    在指定圖像上繪製圓形標記（外白環 + 內圓 + 可選編號文字）。

    繪製流程：
    1. 將圖像放大 scale_factor 倍以提高繪製精度
    2. 在放大後的圖像上繪製白色外圓環與內圓
    3. 若有編號，則在圓心處繪製白色編號文字
    4. 將圖像縮小回原始尺寸

    參數：
        imageA_np (numpy.ndarray): 輸入圖像（BGR 格式的 numpy 陣列）。
        point (tuple): 圓心位置，格式為 (x, y)。
        index (str): 要顯示的編號文字，預設為空字串。
        radius_red (int): 內圓半徑，預設為 8。
        ring_width (int): 外圓環寬度，預設為 2。
        scale_factor (int): 縮放係數，預設為 8。

    回傳：
        numpy.ndarray: 繪製完成後的圖像。
    """
    # 取得原圖尺寸
    original_height, original_width = imageA_np.shape[:2]

    # 將圖像放大以提高圓形繪製精度（避免小圓鍮齒問題）
    imageA_np_resized = cv2.resize(imageA_np, (original_width * scale_factor, original_height * scale_factor))

    # 將圓心座標與半徑同步放大，以匹配放大後的圖像尺寸
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    index = 0
    for point in points:
        index += 1
        point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))

        # 繪製外圓（白色實心圓環）
        cv2.circle(imageA_np_resized, point_resized, radius_red_resized + ring_width_resized, (255, 255, 255), thickness=-1)

        # 繪製內圓（紅色實心圓）
        cv2.circle(imageA_np_resized, point_resized, radius_red_resized, (0, 0, 255), thickness=-1)

        if index:
            # cv2.putText(imageA_np_resized, "2", (point_resized[0] - scale_factor * 4 + 2, point_resized[1] + scale_factor * 3 + 2),cv2.FONT_HERSHEY_COMPLEX, 4, (255, 255, 255), 8, cv2.LINE_AA)
            cv2.putText(imageA_np_resized, str(index), (point_resized[0] - scale_factor * 4, point_resized[1] + scale_factor * 4), cv2.FONT_HERSHEY_COMPLEX, 3.5, (255, 255, 255), 10, cv2.LINE_AA)

    # 將圖像縮小回原始尺寸
    imageA_np_resized = cv2.resize(imageA_np_resized, (original_width, original_height))

    # 可選：使用高斯模糊減少鍮齒（目前已停用）
    # imageA_np_resized = cv2.GaussianBlur(imageA_np_resized, (5, 5), 0)

    return imageA_np_resized

def draw_points_circle_ring(image_np, points, radius_red = 8, ring_width = 2, scale_factor=8):
    """
    在给定图像上绘制内外圆圈，并返回经过处理后的图像。
    
    参数:
    - image_np: 输入图像（numpy 数组）。
    - point: 圆心位置 (x, y)。
    - radius_red: 內圓半徑。
    - ring_width: 外圓環寬度。
    - scale_factor: 缩放系数，默认为 8，用于提高绘制精度。
    
    返回:
    - 处理后的图像（numpy 数组）。
    """

    # 取得原圖尺寸
    original_height, original_width = image_np.shape[:2]

    # 將圖像放大以提高圓形繪製精度（避免小圓鍮齒問題）
    image_np_resized = cv2.resize(image_np, (original_width * scale_factor, original_height * scale_factor))
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    index = 0
    for point in points:
        index += 1

        # 將圓心座標與半徑同步放大，以匹配放大後的圖像尺寸
        point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))

        # 繪製外圓（白色實心圓環）
        cv2.circle(image_np_resized, point_resized, radius_red_resized + ring_width_resized, (255, 255, 255), thickness=-1)

        # 繪製內圓（紅色實心圓）
        cv2.circle(image_np_resized, point_resized, radius_red_resized, (0, 255, 0), thickness=-1)

    # 將圖像縮小回原始尺寸
    image_np_resized = cv2.resize(image_np_resized, (original_width, original_height))

    # 可選：使用高斯模糊減少鍮齒（目前已停用）
    # imageA_np_resized = cv2.GaussianBlur(image_np_resized, (5, 5), 0)
    return image_np_resized



def draw_points(imageA_np, points, radius_red = 8, ring_width = 2, scale_factor=8):
    """
    在指定圖像上繪製圓形標記（外白環 + 內圓 + 可選編號文字）。

    繪製流程：
    1. 將圖像放大 scale_factor 倍以提高繪製精度
    2. 在放大後的圖像上繪製白色外圓環與內圓
    3. 若有編號，則在圓心處繪製白色編號文字
    4. 將圖像縮小回原始尺寸

    參數：
        imageA_np (numpy.ndarray): 輸入圖像（BGR 格式的 numpy 陣列）。
        point (tuple): 圓心位置，格式為 (x, y)。
        index (str): 要顯示的編號文字，預設為空字串。
        radius_red (int): 內圓半徑，預設為 8。
        ring_width (int): 外圓環寬度，預設為 2。
        scale_factor (int): 縮放係數，預設為 8。

    回傳：
        numpy.ndarray: 繪製完成後的圖像。
    """
    # 取得原圖尺寸
    original_height, original_width = imageA_np.shape[:2]

    # 將圖像放大以提高圓形繪製精度（避免小圓鍮齒問題）
    imageA_np_resized = cv2.resize(imageA_np, (original_width * scale_factor, original_height * scale_factor))

    # 將圓心座標與半徑同步放大，以匹配放大後的圖像尺寸
    radius_red_resized = int(radius_red * scale_factor)
    ring_width_resized = int(ring_width * scale_factor)

    index = 0
    for point in points:
        index += 1
        point_resized = (int(point[0] * scale_factor), int(point[1] * scale_factor))

        # 繪製外圓（白色實心圓環）
        cv2.circle(imageA_np_resized, point_resized, radius_red_resized + ring_width_resized, (255, 255, 255), thickness=-1)

        # 繪製內圓（紅色實心圓）
        cv2.circle(imageA_np_resized, point_resized, radius_red_resized, (0, 0, 255), thickness=-1)

        if index:
            # cv2.putText(imageA_np_resized, "2", (point_resized[0] - scale_factor * 4 + 2, point_resized[1] + scale_factor * 3 + 2),cv2.FONT_HERSHEY_COMPLEX, 4, (255, 255, 255), 8, cv2.LINE_AA)
            cv2.putText(imageA_np_resized, str(index), (point_resized[0] - scale_factor * 4, point_resized[1] + scale_factor * 4), cv2.FONT_HERSHEY_COMPLEX, 3.5, (255, 255, 255), 10, cv2.LINE_AA)

    # 將圖像縮小回原始尺寸
    imageA_np_resized = cv2.resize(imageA_np_resized, (original_width, original_height))

    # 可選：使用高斯模糊減少鍮齒（目前已停用）
    # imageA_np_resized = cv2.GaussianBlur(imageA_np_resized, (5, 5), 0)

    return imageA_np_resized

# 使用範例
if __name__ == "__main__":
    # 建立一個黑色空白圖像作為測試用
    height, width = 500, 500
    imageA_np = np.zeros((height, width, 3), dtype=np.uint8)

    # 設定圓心位置和繪製參數
    point = (250, 250)  # 圓心座標
    radius_red = 50  # 內圓半徑
    ring_width = 10  # 外圓環寬度

    # 呼叫函式繪製圓形標記
    result_image = draw_circle_ring(imageA_np, point, radius_red, ring_width, scale_factor=2)

    # 顯示繪製結果
    cv2.imshow("Smooth Circle", result_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
