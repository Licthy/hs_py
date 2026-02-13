import os
import tkinter as tk
from tkinter import messagebox

def generate_config(dir_path: str, module_name: str, desc: str) -> None:
    """核心功能函数：生成指定格式的配置文件"""
    # 输入合法性检查
    if not dir_path or not module_name or not desc:
        raise ValueError("地址、模块名、描述均不能为空！")
    
    # 模块名转大写
    upper_module = module_name.upper()
    
    # 拼接配置内容
    str_content = f"""%%{desc}
{{local, {upper_module}, z_lib, to_atom, [GameProject, "/{module_name}"]}}.
{{template, _FILE_TABLE, {{{module_name}, {upper_module}}}}}.
"""
    
    # 构造目标文件路径（跨平台兼容）
    file_name = f"{module_name}_db.cfg"
    file_path = os.path.join(dir_path, file_name)
    
    # 确保目标目录存在（如果不存在则创建）
    os.makedirs(dir_path, exist_ok=True)
    
    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(str_content)

def on_click_generate():
    """按钮点击事件处理函数"""
    # 获取输入框内容（去除首尾空格）
    dir_path = entry_dir.get().strip()
    module_name = entry_module.get().strip()
    desc = entry_desc.get().strip()
    
    try:
        # 调用生成函数
        generate_config(dir_path, module_name, desc)
        # 提示成功
        messagebox.showinfo("成功", f"配置文件已生成：\n{os.path.join(dir_path, f'{module_name}_db.cfg')}")
        # 清空输入框（可选）
        entry_dir.delete(0, tk.END)
        entry_module.delete(0, tk.END)
        entry_desc.delete(0, tk.END)
    except ValueError as e:
        # 输入错误提示
        messagebox.showerror("输入错误", str(e))
    except Exception as e:
        # 其他异常提示
        messagebox.showerror("生成失败", f"文件生成出错：\n{str(e)}")

# 创建主窗口
root = tk.Tk()
root.title("配置文件生成工具")  # 窗口标题
root.geometry("500x250")       # 窗口大小（宽x高）
root.resizable(False, False)   # 禁止调整窗口大小

# ===== 界面元素布局 =====
# 1. 地址输入区域
label_dir = tk.Label(root, text="保存地址：", font=("微软雅黑", 10))
label_dir.grid(row=0, column=0, padx=10, pady=15, sticky="e")
entry_dir = tk.Entry(root, width=40, font=("微软雅黑", 10))
entry_dir.grid(row=0, column=1, padx=10, pady=15)
# 地址示例提示（可选）
entry_dir.insert(0, "示例：./config 或 D:/game/config")

# 2. 模块名输入区域
label_module = tk.Label(root, text="模块名：", font=("微软雅黑", 10))
label_module.grid(row=1, column=0, padx=10, pady=15, sticky="e")
entry_module = tk.Entry(root, width=40, font=("微软雅黑", 10))
entry_module.grid(row=1, column=1, padx=10, pady=15)
entry_module.insert(0, "示例：user 或 item")

# 3. 描述输入区域
label_desc = tk.Label(root, text="描述信息：", font=("微软雅黑", 10))
label_desc.grid(row=2, column=0, padx=10, pady=15, sticky="e")
entry_desc = tk.Entry(root, width=40, font=("微软雅黑", 10))
entry_desc.grid(row=2, column=1, padx=10, pady=15)
entry_desc.insert(0, "示例：用户模块数据库配置")

# 4. 生成按钮
btn_generate = tk.Button(
    root, 
    text="生成配置文件", 
    font=("微软雅黑", 10, "bold"),
    bg="#4CAF50", 
    fg="white",
    width=20,
    command=on_click_generate  # 绑定点击事件
)
btn_generate.grid(row=3, column=0, columnspan=2, pady=20)

# 运行主循环
if __name__ == "__main__":
    root.mainloop()