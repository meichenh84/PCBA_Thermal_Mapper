#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元器件邊界識別模組 (recognize_component_boundary.py)

用途：
    從指定的中心點向上下左右四個方向擴展搜尋，利用 HSV 色彩遮罩
    判斷元器件的矩形邊界範圍。根據遮罩值（0=元器件區域，255=PCB 基板區域）
    的變化來確定元器件的左、右、上、下邊界座標。
    支援兩種模式：元器件位於非基板區域（tag=0）和元器件位於基板區域（tag=255）。

在整個應用中的角色：
    - 被 recognize_image.py 呼叫，用於自動識別元器件的矩形邊界
    - 識別結果用於在 Layout 圖上繪製矩形標記框

關聯檔案：
    - recognize_image.py：呼叫本函式取得元器件的邊界座標
    - color_range.py：提供 mask_boundary 遮罩資料
    - main.py：透過 recognize_image.py 間接使用本模組
"""


def recognize_component_boundary(center, mask_boundary):
    """從中心點向四個方向擴展搜尋元器件的矩形邊界。

    演算法策略（兩輪擴展）：
    1. 第一輪：先向上下擴展確定垂直範圍，再向左右擴展確定水平範圍
    2. 第二輪：根據第一輪的水平範圍重新向上下擴展，得到更精確的邊界

    擴展時會在多個取樣點檢查遮罩值，使用投票機制決定是否繼續擴展
    （多數取樣點仍在元器件區域內才繼續）。

    Args:
        center (tuple): 搜尋起始的中心點座標 (x, y)
        mask_boundary (numpy.ndarray): HSV 色彩遮罩，0=元器件區域，255=PCB 基板區域

    Returns:
        tuple: (left, right, top, bottom, tag_component)
            - left (int): 左邊界 X 座標
            - right (int): 右邊界 X 座標
            - top (int): 上邊界 Y 座標
            - bottom (int): 下邊界 Y 座標
            - tag_component (int): 中心點的遮罩值（0 或 255），指示元器件類型
    """
    x, y = center
    left, right, top, bottom = x, x, y, y
    multiple = 1.05
    multiple2 = 2
    default_point_count = 5
    default_point_enable_probability = 0.75
    point_count = 1
    point_enable = 2
    pcb_point_count = 0
    # print("recognize_component_boundary start ", x, y)
    tag_component = mask_boundary[y, x]

    if tag_component == 0:
        # 向上扩展
        while top > 0 and mask_boundary[top, x] == 0:
            top -= 1
        top += 1  # 调整边界为最后一个有效像素的下一个位置

        # 向下扩展
        while bottom < mask_boundary.shape[0] - 1 and mask_boundary[bottom, x] == 0:
            bottom += 1
        bottom -= 1  # 调整边界为最后一个有效像素的上一个位置

    
        if y <= top :
            y = top+1
        # 向左扩展
        while left > 0 and [ 
            mask_boundary[y, left], 
            mask_boundary[int(top + (y - top)/multiple), left], 
            mask_boundary[int(y + (bottom - y) / multiple), left],
            mask_boundary[int(top + (y - top)/multiple2), left], 
            mask_boundary[int(y + (bottom - y) / multiple2), left]].count(0) > point_enable :
            left -= 1
        left += 1  # 调整边界为最后一个有效像素的下一个位置


        # 向右扩展``````````````
        if bottom <= y :
            bottom = y+1
        while right < mask_boundary.shape[1] - 1 and [
                mask_boundary[y, right],
                mask_boundary[int(top + (y - top)/multiple), right],
                mask_boundary[int(y + (bottom - y)/multiple), right],
                mask_boundary[int(top + (y - top)/multiple2), right],
                mask_boundary[int(y + (bottom - y)/multiple2), right] ].count(0) > point_enable :
            right += 1
        right -= 1  # 调整边界为最后一个有效像素的上一个位置

        top = y
        bottom = y

        if x <= left :
            x = left+1
        # 向上扩展
        while top > 0 and [ 
            mask_boundary[top, x],
            mask_boundary[top, int(x - (x - left)/multiple)],
            mask_boundary[top, int(x + (right - x)/multiple)],
            mask_boundary[top, int(x - (x - left)/multiple2)],
            mask_boundary[top, int(x + (right - x)/multiple2)] ].count(0) > point_enable :
            top -= 1
        top += 1  # 调整边界为最后一个有效像素的下一个位置

        # 向下扩展
        if right <= x :
            right = x+1
        while bottom < mask_boundary.shape[0] - 1 and [ 
            mask_boundary[bottom, x],
            mask_boundary[bottom, int(x - (x - left)/multiple)],
            mask_boundary[bottom, int(x + (right - x)/multiple)],
            mask_boundary[bottom, int(x - (x - left)/multiple2)],
            mask_boundary[bottom, int(x + (right - x)/multiple2)] ].count(0) > point_enable :
            bottom += 1
        bottom -= 1  # 调整边界为最后一个有效像素的上一个位置

    else:
         # 向上扩展
        while top > 0 and mask_boundary[top, x] == 255:
            top -= 1
        top += 1  # 调整边界为最后一个有效像素的下一个位置

        # 向下扩展
        while bottom < mask_boundary.shape[0] - 1 and mask_boundary[bottom, x] == 255:
            bottom += 1
        bottom -= 1  # 调整边界为最后一个有效像素的上一个位置

    
        if y <= top :
            y = top+1
        # 向左扩展
        while left > 0 and [ 
            mask_boundary[y, left], ].count(255) > pcb_point_count :
            # mask_boundary[int(top + (y - top)/multiple), left], 
            # mask_boundary[int(y + (bottom - y) / multiple), left],
            # mask_boundary[int(top + (y - top)/multiple2), left], 
            # mask_boundary[int(y + (bottom - y) / multiple2), left]
            left -= 1
        left += 1  # 调整边界为最后一个有效像素的下一个位置


        # 向右扩展``````````````
        if bottom <= y :
            bottom = y+1
            #  mask_boundary[int(top + (y - top)/multiple), right],
            #     mask_boundary[int(y + (bottom - y)/multiple), right],
            #     mask_boundary[int(top + (y - top)/multiple2), right],
            #     mask_boundary[int(y + (bottom - y)/multiple2), right] 
        while right < mask_boundary.shape[1] - 1 and [
                mask_boundary[y, right],
               ].count(255) > pcb_point_count :
            right += 1
        right -= 1  # 调整边界为最后一个有效像素的上一个位置

        top = y
        bottom = y

        if x <= left :
            x = left+1
        # 向上扩展
        while top > 0 and [ 
            mask_boundary[top, x],
           ].count(255) > pcb_point_count :
            #  mask_boundary[top, int(x - (x - left)/multiple)],
            # mask_boundary[top, int(x + (right - x)/multiple)],
            # mask_boundary[top, int(x - (x - left)/multiple2)],
            # mask_boundary[top, int(x + (right - x)/multiple2)] 
            top -= 1
        top += 1  # 调整边界为最后一个有效像素的下一个位置

        # 向下扩展
        if right <= x :
            right = x+1
        while bottom < mask_boundary.shape[0] - 1 and [ 
            mask_boundary[bottom, x],
          ].count(255) > pcb_point_count :
            #    mask_boundary[bottom, int(x - (x - left)/multiple)],
            # mask_boundary[bottom, int(x + (right - x)/multiple)],
            # mask_boundary[bottom, int(x - (x - left)/multiple2)],
            # mask_boundary[bottom, int(x + (right - x)/multiple2)]
            bottom += 1
        bottom -= 1  # 调整边界为最后一个有效像素的上一个位置
        

    return left, right, top, bottom, tag_component