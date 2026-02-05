class CanvasRectItem:
    def __init__(self, x1, y1, x2, y2, cx, cy, max_temp, name, rectId = 0, nameId = 0):
        # 初始化类的实例变量
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.cx = cx
        self.cy = cy
        self.max_temp = max_temp
        self.name = name
        self.rectId = rectId
        self.nameId = nameId

    def set_nameId(self, nameId):
        self.nameId = nameId

    def set_rectId(self, rectId):
        self.rectId = rectId

    def set_rect_boundary(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def __repr__(self):
        # 返回类的字符串表示，方便调试和打印
        return (f"RectItem(x1={self.x1}, y1={self.y1}, x2={self.x2}, y2={self.y2}, "
                f"cx={self.cx}, cy={self.cy}, max_temp={self.max_temp}, "
                f"name={self.name}, rectId={self.rectId}, nameId={self.nameId})")

    def to_dict(self):
        # 将类实例转换为字典
        return {
            "x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2,
            "cx": self.cx, "cy": self.cy, "max_temp": self.max_temp,
            "name": self.name, "rectId": self.rectId, "nameId": self.nameId
        }
    
    def get_value(self, key):
        # 使用 getattr 动态获取实例的属性值
        if hasattr(self, key):
            return getattr(self, key)
        else:
            return None  # 或者可以返回一个自定义的错误信息，比如："属性不存在"

# 示例：创建一个 RectItem 实例
rect_item = CanvasRectItem(x1=0, y1=0, x2=10, y2=10, cx=5, cy=5, max_temp=100, name="Rect1", rectId=1, nameId=101)

# 打印 RectItem 实例
print(rect_item)

# 转换为字典
rect_dict = rect_item.to_dict()
print(rect_dict)
