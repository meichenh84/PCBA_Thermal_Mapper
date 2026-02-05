import tkinter as tk
from tkinter import messagebox


class ComponentSettingDialog(tk.Toplevel):
    def __init__(self, parent, oldRect, callback):
        super().__init__(parent)
        self.title("Edit Area")
        # self.window_width = 350
        # self.window_height = 320
        
        # 设置窗口大小并使其居中
        # self.geometry("300x400")
        # self.center_window()
        # 创建根窗口
        # root = tk.Tk()
        # 设置窗口的外边距
        frame = tk.Frame(self, padx=20, pady=20)  # 通过 Frame 设置内边距
        frame.pack(fill=tk.BOTH, expand=True)

        # 创建字段标签和输入框（只显示器件名称和最高温度）
        self.fields = [
            ("name", "器件名称: ", tk.Entry(frame)),
            ("max_temp", "最高温度: ", tk.Entry(frame)),
            # 其他字段暂时注释掉
            # ("cx", "最高温度 x坐标: ", tk.Entry(frame)),
            # ("cy", "最高温度 y坐标: ", tk.Entry(frame)),
            # ("x1", "左上角 x坐标: ", tk.Entry(frame)),
            # ("y1", "左上角 y坐标: ", tk.Entry(frame)),
            # ("x2", "右下角 x坐标: ", tk.Entry(frame)),
            # ("y2", "右下角 y坐标: ", tk.Entry(frame))
        ]
        # print("xxx ", oldRect, callback)
        self.oldRect  = oldRect
        self.callback = callback

        # 创建输入字段布局
        for idx, (key, label, entry) in enumerate(self.fields):
            tk.Label(frame, text=label).grid(row=idx, column=0, padx=10, pady=5, sticky="e")
            if oldRect:
                entry.insert(0, oldRect[key])  # 将 oldRect[key] 的值插入到 entry 中
                if key == "max_temp":  # 最高温度字段设为只读
                    entry.config(state='readonly')
            entry.grid(row=idx, column=1, padx=10, pady=5)

        # 创建确认按钮
        self.confirm_button = tk.Button(frame, text="   确认   ", command=self.on_confirm)
        self.confirm_button.grid(row=len(self.fields), column=0, columnspan=2, pady=(20, 0))

    def center_window(self):
        # 获取屏幕宽高
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width - self.window_width) // 2
        y = (screen_height - self.window_height) // 2

        # 设置窗口位置
        self.geometry(f'{self.window_width}x{self.window_height}+{x}+{y}')

    def on_confirm(self):
        # 获取输入的值并验证
        values = {}
        for key, label, entry in self.fields:
            value = entry.get()
            if key == "name":  # 对"器件名称"字段不做类型转换，保留字符串
                values[key] = value
            else:
                try:
                    # 尝试转换为float，如果失败，则提示错误
                    values[key] = float(value)
                except ValueError:
                    messagebox.showerror("输入错误", f"'{label}' 必须是数字类型！")
                    return
        
        # 🔥 重要：保留原始矩形框的所有坐标数据
        # 对话框只允许修改name和max_temp，其他字段保持不变
        if self.oldRect:
            # 保留oldRect中所有未在对话框中显示的字段
            for key, value in self.oldRect.items():
                if key not in values:
                    values[key] = value
        
        # 由于只显示器件名称和最高温度，不需要坐标验证
        # 注释掉坐标验证逻辑
        # if values["x1"] >= values["x2"]:
        #     messagebox.showerror("输入错误", "左上角x坐标必须小于右下角x坐标")
        #     return
        # 
        # if values["y1"] >= values["y2"]:
        #     messagebox.showerror("输入错误", "左上角y坐标必须小于右下角y坐标")
        #     return

        # 输出所有输入的数据
        print("输入的数据：")
        for key, value in values.items():
            print(f"{key}: {value}")
        # 调用外部回调函数，并传递结果

        if self.callback:
            self.callback(values)

        # 关闭对话框
        self.destroy()


if __name__ == "__main__":
    dialog = ComponentSettingDialog()
    dialog.grab_set()  # 禁用主窗口，确保只能与对话框交互
    dialog.mainloop()
