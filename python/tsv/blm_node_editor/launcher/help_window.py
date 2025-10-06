import tkinter as tk
from tkinter import ttk, scrolledtext
import webbrowser
from pathlib import Path

class HelpWindow:
    def __init__(self, parent=None):
        self.root = tk.Toplevel(parent)
        self.root.title("LACCS - Node Manager 帮助")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        self.setup_fonts()
        
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_overview_tab()
        self.create_basic_operations_tab()
        self.create_advanced_operations_tab()
        self.create_status_check_tab()
        self.create_shortcuts_tab()
        self.create_troubleshooting_tab()
        
        if parent:
            self.root.transient(parent)
            self.center_window(parent)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def setup_fonts(self):
        try:
            self.default_font = ("SimHei", 10)
            self.title_font = ("SimHei", 12, "bold")
            self.section_font = ("SimHei", 11, "bold")
        except:
            self.default_font = ("Arial", 10)
            self.title_font = ("Arial", 12, "bold")
            self.section_font = ("Arial", 11, "bold")
    
    def center_window(self, parent):
        self.root.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_overview_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="概述")
        
        text_area = scrolledtext.ScrolledText(tab, wrap=tk.WORD, font=self.default_font)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        content = """LACCS - Node Manager 是一个用于管理 BDBLM 节点的图形化工具，主要功能包括：
        
1. 节点数据管理
   - 加载和保存节点配置信息（从 NODES.tsv 文件）
   - 编辑节点参数
   - 添加和删除节点

2. 服务控制
   - 启动、停止、重启服务
   - 部署服务到远程节点
   - 查看服务状态

3. 远程操作
   - 通过 SSH 连接到节点
   - 通过 Putty 连接到节点
   - 更新共享库文件

4. 其他功能
   - 启动 BDBLM.exe 程序
   - 加载服务参数（从 BDMap.json 文件）
   - 日志记录和过滤

本工具主要用于管理分布在不同服务器上的 BDBLM 节点，提供了便捷的图形界面来执行各种操作，
无需手动登录到每个服务器进行操作。
"""
        
        text_area.insert(tk.END, content)
        text_area.config(state=tk.DISABLED)
    
    def create_basic_operations_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="基本操作")
        
        text_area = scrolledtext.ScrolledText(tab, wrap=tk.WORD, font=self.default_font)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        content = """基本操作指南
        
1. 打开节点文件
   - 程序启动时会自动尝试加载默认的 NODES.tsv 文件
   - 如果文件不存在，可以通过菜单选择其他位置的 NODES.tsv 文件
   - 也可以通过右键菜单中的 "Open FileDB" 选项打开新文件

2. 查看节点信息
   - 主界面上方的表格显示所有节点的详细信息
   - 下方的状态表格显示节点的运行状态

3. 编辑节点参数
   - 双击节点表格中的任意行可以编辑节点参数
   - 编辑完成后点击 "Save Changes" 按钮保存修改
   - 未保存的修改会在窗口标题显示 "*" 标记

4. 添加和删除节点
   - 右键点击节点表格，选择 "Add TSV Item" 添加新节点
   - 选择一个节点后，右键点击选择 "Delete TSV Item" 删除节点

5. 保存更改
   - 点击 "Save Changes" 按钮保存所有修改
   - 使用快捷键 Ctrl+S 也可以保存更改
        
"""
        
        text_area.insert(tk.END, content)
        text_area.config(state=tk.DISABLED)
    
    def create_advanced_operations_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="高级操作")
        
        text_area = scrolledtext.ScrolledText(tab, wrap=tk.WORD, font=self.default_font)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        content = """高级操作指南
        
1. 服务控制
   - 选择一个节点后，右键点击选择 "Start Service" 启动服务
   - 选择一个节点后，右键点击选择 "Stop Service" 停止服务
   - 选择一个节点后，右键点击选择 "Restart Service" 重启服务
   - 可以通过 "Stop Service All" 停止所有节点的服务

2. 部署服务
   - 选择一个节点后，右键点击选择 "Deploy Service" 部署服务
   - 部署过程会将必要的文件复制到远程节点

3. 启动 BDBLM
   - 选择一个节点后，右键点击选择 "Launch BDBLM" 启动 BDBLM.exe
   - 系统会使用该节点的参数启动 BDBLM 程序

4. 加载服务参数
   - 通过右键菜单选择 "Load Service Parameter" 从 BDMap.json 文件加载参数
   - 系统会自动匹配节点名称并更新参数

5. 更新共享库
   - 选择一个节点后，右键点击选择 "Update Shared Lib" 更新该节点的共享库
   - 可以通过 "Update Shared Lib All" 更新所有节点的共享库
        
"""
        
        text_area.insert(tk.END, content)
        text_area.config(state=tk.DISABLED)
    
    def create_status_check_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="状态检查")
        
        text_area = scrolledtext.ScrolledText(tab, wrap=tk.WORD, font=self.default_font)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        content = """状态检查功能
        
1. 自动状态检查
   - 程序启动后会自动启动一个线程定期检查所有节点的状态
   - 状态包括：Running（运行中）、Stopped（已停止）、Error（错误）、Unknown（未知）
   - 不同状态以不同颜色显示在状态表格中

2. 手动刷新状态
   - 点击日志区域上方的 "Refresh Status" 按钮可以手动刷新所有节点的状态
   - 也可以通过右键菜单选择相应选项

3. 超时处理
   - 对于连接超时的节点，系统会自动标记，避免重复连接尝试
   - 连接失败后不会重试，以提高整体检查效率

4. 日志查看
   - 所有操作和状态变化都会记录在下方的日志区域
   - 可以通过日志过滤框筛选日志内容
   - 点击 "Clear Log" 按钮可以清空日志
        
"""
        
        text_area.insert(tk.END, content)
        text_area.config(state=tk.DISABLED)
    
    def create_shortcuts_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="快捷键")
        
        columns = ("action", "shortcut")
        tree = ttk.Treeview(tab, columns=columns, show="headings")
        
        tree.heading("action", text="操作")
        tree.heading("shortcut", text="快捷键")
        tree.column("action", width=300, anchor="w")
        tree.column("shortcut", width=100, anchor="center")
        
        shortcuts = [
            ("保存更改", "Ctrl+S"),
            ("编辑节点参数", "双击节点行"),
            ("查看右键菜单", "右键点击节点行"),
        ]
        
        for action, shortcut in shortcuts:
            tree.insert("", tk.END, values=(action, shortcut))
        
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_troubleshooting_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="故障排除")
        
        text_area = scrolledtext.ScrolledText(tab, wrap=tk.WORD, font=self.default_font)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        content = """常见问题及解决方法
        
1. 连接超时错误
   - 症状：[WinError 10060] 连接尝试失败
   - 解决方法：检查目标节点的网络连接和SSH服务是否正常运行
   - 注意：系统现在设置为连接失败后不再重试，以提高性能

2. 文件找不到错误
   - 症状：无法找到 NODES.tsv 或 BDMap.json 文件
   - 解决方法：使用程序提供的文件选择功能选择正确的文件位置

3. 服务启动失败
   - 症状：服务状态显示为 Error
   - 解决方法：检查节点的日志文件，确认配置是否正确

4. SSH 认证失败
   - 症状：无法连接到远程节点，显示认证错误
   - 解决方法：在认证面板中输入正确的用户名和密码，然后点击 "Apply Authentication"

5. 未保存的更改
   - 症状：窗口标题显示 "*" 标记
   - 解决方法：点击 "Save Changes" 按钮或使用 Ctrl+S 保存更改
        
"""
        
        text_area.insert(tk.END, content)
        text_area.config(state=tk.DISABLED)
    
    def on_close(self):
        self.root.destroy()
    
    def show(self):
        self.root.grab_set()
        self.root.wait_window()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    help_window = HelpWindow(root)
    help_window.show()
    root.mainloop()