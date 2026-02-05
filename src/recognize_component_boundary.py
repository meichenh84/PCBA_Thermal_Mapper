# 从中心点向四个方向扩展以查找边界
def recognize_component_boundary(center, mask_boundary):
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