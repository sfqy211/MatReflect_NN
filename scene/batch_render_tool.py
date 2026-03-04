import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import subprocess
import threading
import xml.etree.ElementTree as ET
import glob
import math
import numpy as np
import cv2
from skimage import metrics, color
import concurrent.futures
from PIL import Image, ImageDraw, ImageFont

# 配置常量
BASE_DIR = r"d:\mitsuba\matpreview"
MITSUBA_DIR = r"d:\mitsuba\dist"
SCENE_XML = os.path.join(BASE_DIR, "scene_merl.xml")

class BatchRendererApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mitsuba 批量渲染工具")
        self.root.geometry("950x750")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.current_process = None
        self.stop_requested = False

        # --- 共享变量 ---
        self.mitsuba_exe = tk.StringVar(value=os.path.join(MITSUBA_DIR, "mitsuba.exe"))
        self.mtsutil_exe = tk.StringVar(value=os.path.join(MITSUBA_DIR, "mtsutil.exe"))
        self.status_var = tk.StringVar(value="准备就绪")
        self.progress_var = tk.DoubleVar(value=0)

        # --- 渲染 Tab 变量 ---
        self.scene_path = tk.StringVar(value=SCENE_XML)
        
        self.auto_convert = tk.BooleanVar(value=True)
        self.skip_existing = tk.BooleanVar(value=False)
        self.render_mode = tk.StringVar(value="brdfs") 
        self.current_input_dir = tk.StringVar()
        self.current_output_dir = tk.StringVar()

        # --- 转换 Tab 变量 ---
        self.conv_input_dir = tk.StringVar(value=os.path.join(BASE_DIR, "outputs", "brdfs", "exr"))
        self.conv_output_dir = tk.StringVar(value=os.path.join(BASE_DIR, "outputs", "brdfs", "png"))

        # --- 评估 Tab 变量 ---
        self.eval_gt_dir = tk.StringVar(value=os.path.join(BASE_DIR, "outputs", "brdfs", "png"))
        self.eval_method1_dir = tk.StringVar(value=os.path.join(BASE_DIR, "outputs", "fullbin", "png"))
        self.eval_method2_dir = tk.StringVar(value=os.path.join(BASE_DIR, "outputs", "npy", "png"))

        # --- 图像工具 Tab 变量 ---
        self.grid_input_dir = tk.StringVar(value=os.path.join(BASE_DIR, "outputs", "brdfs", "png"))
        self.grid_output_file = tk.StringVar(value=os.path.join(BASE_DIR, "outputs", "merged_grid.png"))
        self.grid_show_names = tk.BooleanVar(value=True)
        self.grid_cell_width = tk.IntVar(value=256)
        self.grid_padding = tk.IntVar(value=10)

        # --- 对比拼图 Tab 变量 ---
        self.comp_output_dir = tk.StringVar(value=os.path.join(BASE_DIR, "outputs", "comparisons"))
        self.comp_labels = tk.StringVar(value="Ground Truth,FullBin,Neural BRDF")
        self.comp_show_label = tk.BooleanVar(value=True)
        self.comp_show_filename = tk.BooleanVar(value=True)

        self.create_widgets()
        self.on_mode_change() # 初始化渲染路径

    def create_widgets(self):
        # 1. 顶部通用配置
        top_frame = tk.Frame(self.root, padx=5, pady=5)
        top_frame.pack(fill="x")
        
        tk.Label(top_frame, text="Mitsuba Exe:").pack(side="left")
        tk.Entry(top_frame, textvariable=self.mitsuba_exe, width=40).pack(side="left", padx=5)
        
        tk.Label(top_frame, text="Mtsutil Exe:").pack(side="left", padx=(10, 0))
        tk.Entry(top_frame, textvariable=self.mtsutil_exe, width=40).pack(side="left", padx=5)

        # 2. 选项卡容器
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Tab 1: 批量渲染 ---
        self.tab_render = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_render, text=" 批量渲染 (Batch Render) ")
        self.setup_render_tab()

        # --- Tab 2: EXR 转换 ---
        self.tab_convert = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_convert, text=" EXR 转图片 (EXR to PNG) ")
        self.setup_convert_tab()

        # --- Tab 3: 编译 ---
        self.tab_compile = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_compile, text=" 编译项目 (Compile) ")
        self.setup_compile_tab()

        # --- Tab 4: 量化评估 ---
        self.tab_eval = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_eval, text=" 量化评估 (Evaluation) ")
        self.setup_eval_tab()

        # --- Tab 5: 图像工具 ---
        self.tab_tools = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tools, text=" 图像工具 (Image Tools) ")
        self.setup_tools_tab()

        # 3. 底部进度与日志
        bottom_frame = tk.Frame(self.root, padx=5, pady=5)
        bottom_frame.pack(fill="both", expand=False, side="bottom")

        tk.Label(bottom_frame, textvariable=self.status_var, anchor="w").pack(fill="x")
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=2)

        log_frame = tk.LabelFrame(bottom_frame, text="系统日志", padx=5, pady=5)
        log_frame.pack(fill="both", expand=True, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', height=15, bg="#1e1e1e", fg="#00FF00", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        # 添加右键菜单 (复制功能)
        self.log_menu = tk.Menu(self.log_text, tearoff=0)
        self.log_menu.add_command(label="复制选中 (Copy)", command=self.copy_log_selection)
        self.log_menu.add_command(label="复制全部 (Copy All)", command=self.copy_log_all)
        self.log_menu.add_command(label="清空日志 (Clear)", command=self.clear_log)
        self.log_text.bind("<Button-3>", self.show_log_menu) # 右键弹出

    def show_log_menu(self, event):
        self.log_menu.post(event.x_root, event.y_root)

    def copy_log_selection(self):
        try:
            sel = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(sel)
        except tk.TclError:
            pass # No selection

    def copy_log_all(self):
        all_text = self.log_text.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(all_text)

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state='disabled')

    # ================= 渲染 Tab 逻辑 =================
    def setup_render_tab(self):
        parent = self.tab_render
        
        # 场景配置
        config_frame = tk.LabelFrame(parent, text="场景配置", padx=10, pady=5)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        self.create_entry(config_frame, "场景 XML:", self.scene_path, 0)
        
        # 选项
        opts_frame = tk.Frame(config_frame)
        opts_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=5)
        tk.Checkbutton(opts_frame, text="渲染后自动转换为 PNG", variable=self.auto_convert).pack(side="left", padx=10)
        tk.Checkbutton(opts_frame, text="跳过已存在文件", variable=self.skip_existing).pack(side="left", padx=10)

        # 模式选择
        mode_frame = tk.LabelFrame(parent, text="输入类型 (自动切换路径)", padx=10, pady=5)
        mode_frame.pack(fill="x", padx=10, pady=5)

        modes = [("标准 MERL (.binary)", "brdfs"), ("Full MERL (.fullbin)", "fullbin"), ("Neural BRDF (.npy)", "npy")]
        rb_frame = tk.Frame(mode_frame)
        rb_frame.pack(fill="x")
        for text, mode in modes:
            tk.Radiobutton(rb_frame, text=text, variable=self.render_mode, value=mode, 
                           command=self.on_mode_change, font=("Arial", 10, "bold")).pack(side="left", padx=20)

        # 路径显示
        path_frame = tk.Frame(mode_frame)
        path_frame.pack(fill="x", pady=5)
        tk.Label(path_frame, text="输入:").pack(side="left")
        tk.Entry(path_frame, textvariable=self.current_input_dir, state="readonly", width=50).pack(side="left", padx=5)
        tk.Label(path_frame, text="输出:").pack(side="left", padx=(10,0))
        tk.Entry(path_frame, textvariable=self.current_output_dir, state="readonly", width=50).pack(side="left", padx=5)

        # 文件列表
        list_frame = tk.LabelFrame(parent, text="待渲染文件", padx=10, pady=5)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.render_listbox = tk.Listbox(list_frame, selectmode="multiple", yscrollcommand=scrollbar.set)
        self.render_listbox.pack(fill="both", expand=True)
        scrollbar.config(command=self.render_listbox.yview)

        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(fill="x", pady=2)
        tk.Button(btn_frame, text="全选", command=lambda: self.render_listbox.select_set(0, tk.END)).pack(side="left", padx=5)
        tk.Button(btn_frame, text="全不选", command=lambda: self.render_listbox.selection_clear(0, tk.END)).pack(side="left", padx=5)
        tk.Button(btn_frame, text="刷新", command=self.refresh_render_list).pack(side="left", padx=5)

        # 开始按钮
        btn_frame_action = tk.Frame(parent)
        btn_frame_action.pack(fill="x", padx=10, pady=5)
        
        self.render_btn = tk.Button(btn_frame_action, text="开始批量渲染", command=self.start_render_thread, 
                                    bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=20)
        self.render_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.stop_btn = tk.Button(btn_frame_action, text="停止渲染", command=self.stop_render, 
                                   bg="#F44336", fg="white", font=("Arial", 12, "bold"), state="disabled", width=20)
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))

    def on_mode_change(self):
        mode = self.render_mode.get()
        self.current_input_dir.set(os.path.join(BASE_DIR, "inputs", mode))
        self.current_output_dir.set(os.path.join(BASE_DIR, "outputs", mode))
        self.refresh_render_list()

    def refresh_render_list(self):
        self.render_listbox.delete(0, tk.END)
        input_dir = self.current_input_dir.get()
        if not os.path.exists(input_dir): return
        
        mode = self.render_mode.get()
        if mode == "npy":
            # NBRDF 模式：一个材质包含6个文件(fc1-fc3, b1-b3)，只加载 fc1 作为代表，避免重复
            files = sorted(glob.glob(os.path.join(input_dir, "*fc1.npy")))
        else:
            ext = "*.binary" if mode == "brdfs" else "*.fullbin"
            files = sorted(glob.glob(os.path.join(input_dir, ext)))

        for f in files:
            self.render_listbox.insert(tk.END, os.path.basename(f))
        self.log(f"Render Tab: 加载了 {self.render_listbox.size()} 个文件")

    # ================= 转换 Tab 逻辑 =================
    def setup_convert_tab(self):
        parent = self.tab_convert
        
        # 路径选择
        config_frame = tk.LabelFrame(parent, text="转换路径配置", padx=10, pady=5)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        self.create_entry(config_frame, "EXR 输入目录:", self.conv_input_dir, 0, is_dir=True, cmd=self.refresh_conv_list)
        self.create_entry(config_frame, "PNG 输出目录:", self.conv_output_dir, 1, is_dir=True)

        # 文件列表
        list_frame = tk.LabelFrame(parent, text="待转换 EXR 文件", padx=10, pady=5)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.conv_listbox = tk.Listbox(list_frame, selectmode="multiple", yscrollcommand=scrollbar.set)
        self.conv_listbox.pack(fill="both", expand=True)
        scrollbar.config(command=self.conv_listbox.yview)
        
        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(fill="x", pady=2)
        tk.Button(btn_frame, text="全选", command=lambda: self.conv_listbox.select_set(0, tk.END)).pack(side="left", padx=5)
        tk.Button(btn_frame, text="全不选", command=lambda: self.conv_listbox.selection_clear(0, tk.END)).pack(side="left", padx=5)
        tk.Button(btn_frame, text="刷新", command=self.refresh_conv_list).pack(side="left", padx=5)

        # 开始按钮
        tk.Button(parent, text="开始 EXR -> PNG 转换", command=self.start_conv_thread, bg="#2196F3", fg="white", font=("Arial", 12, "bold")).pack(fill="x", padx=10, pady=5)

    def refresh_conv_list(self):
        self.conv_listbox.delete(0, tk.END)
        input_dir = self.conv_input_dir.get()
        if not os.path.exists(input_dir): return
        
        for f in sorted(glob.glob(os.path.join(input_dir, "*.exr"))):
            self.conv_listbox.insert(tk.END, os.path.basename(f))
        self.log(f"Convert Tab: 加载了 {self.conv_listbox.size()} 个 EXR 文件")

    def start_conv_thread(self):
        threading.Thread(target=self.run_conversion, daemon=True).start()

    # ================= 编译 Tab 逻辑 =================
    def setup_compile_tab(self):
        parent = self.tab_compile
        
        # 编译说明
        info_frame = tk.LabelFrame(parent, text="编译说明", padx=10, pady=5)
        info_frame.pack(fill="x", padx=10, pady=5)
        info_text = (
            "本工具会自动配置 VS2017+ 环境并调用 SCons 进行编译。\n"
            "预设步骤：\n"
            "1. 查找 vswhere.exe 获取 VS 安装路径\n"
            "2. 调用 vcvarsall.bat 初始化 x64 环境\n"
            "3. 激活 Anaconda py27 环境 (需确保 conda 在 PATH 中)\n"
            "4. 设置依赖库 PATH\n"
            "5. 运行 scons --parallelize"
        )
        tk.Label(info_frame, text=info_text, justify="left", font=("Consolas", 9)).pack(anchor="w")

        # 编译配置
        config_frame = tk.LabelFrame(parent, text="编译配置", padx=10, pady=5)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        self.compile_cmd_var = tk.StringVar(value="scons --parallelize")
        self.conda_env_var = tk.StringVar(value="py27")
        
        tk.Label(config_frame, text="编译命令:").grid(row=0, column=0, sticky="e", padx=5)
        tk.Entry(config_frame, textvariable=self.compile_cmd_var, width=40).grid(row=0, column=1, sticky="w", padx=5)
        
        tk.Label(config_frame, text="Conda 环境名:").grid(row=0, column=2, sticky="e", padx=5)
        tk.Entry(config_frame, textvariable=self.conda_env_var, width=15).grid(row=0, column=3, sticky="w", padx=5)

        # 编译操作
        action_frame = tk.Frame(parent, padx=10, pady=10)
        action_frame.pack(fill="x")
        
        self.compile_btn = tk.Button(action_frame, text="开始编译 (Start Compile)", command=self.start_compile_thread, 
                                     bg="#FF9800", fg="white", font=("Arial", 12, "bold"), height=2)
        self.compile_btn.pack(fill="x")

    def start_compile_thread(self):
        self.compile_btn.config(state='disabled')
        threading.Thread(target=self.run_compile, daemon=True).start()

    def run_compile(self):
        try:
            self.log("\n>>> 开始编译流程...")
            
            # 1. 查找 VS 安装路径
            vswhere = os.path.expandvars(r"${ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe")
            if not os.path.exists(vswhere):
                 # 尝试 64位 ProgramFiles
                 vswhere = os.path.expandvars(r"${ProgramFiles}\Microsoft Visual Studio\Installer\vswhere.exe")
            
            if not os.path.exists(vswhere):
                self.log("错误: 未找到 vswhere.exe，无法自动定位 Visual Studio")
                return

            cmd_vswhere = [vswhere, "-latest", "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"]
            vs_path = subprocess.check_output(cmd_vswhere, text=True).strip()
            
            if not vs_path:
                self.log("错误: 未找到安装了 VC++ 工具集的 Visual Studio")
                return
            
            self.log(f"找到 Visual Studio: {vs_path}")
            
            vcvarsall = os.path.join(vs_path, r"VC\Auxiliary\Build\vcvarsall.bat")
            if not os.path.exists(vcvarsall):
                self.log(f"错误: 未找到 vcvarsall.bat: {vcvarsall}")
                return

            # 2. 构建完整的批处理脚本
            # 因为需要在同一个 shell session 中激活环境并运行命令
            # 我们动态生成一个 .bat 文件来执行
            
            compile_cmd = self.compile_cmd_var.get()
            conda_env = self.conda_env_var.get()
            work_dir = os.getcwd() # 或者是 d:\mitsuba，这里假设工具就在根目录或能正确推断
            if "matpreview" in work_dir: # 如果是在子目录运行，切换回根目录
                work_dir = os.path.dirname(work_dir)

            dep_bin = os.path.join(work_dir, "dependencies", "bin")
            dep_lib = os.path.join(work_dir, "dependencies", "lib")
            
            bat_content = f"""
@echo off
cd /d "{work_dir}"
echo [1/5] Setting up VS environment...
call "{vcvarsall}" x64

echo [2/5] Activating Conda environment '{conda_env}'...
call activate {conda_env} || echo Warning: Conda activate failed, trying direct python...

echo [3/5] Setting dependency paths...
set PATH={dep_bin};{dep_lib};%PATH%

echo [4/5] Running SCons...
echo Command: {compile_cmd}
{compile_cmd}
"""
            bat_file = os.path.join(work_dir, "temp_build.bat")
            with open(bat_file, "w") as f:
                f.write(bat_content)
            
            self.log(f"生成构建脚本: {bat_file}")
            
            # 3. 执行脚本
            self.current_process = subprocess.Popen(bat_file, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                                  text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            for line in self.current_process.stdout:
                self.log(line.strip())
            
            self.current_process.wait()
            
            if self.current_process.returncode == 0:
                self.log("\n>>> 编译成功！")
                messagebox.showinfo("成功", "编译完成！")
            else:
                self.log("\n>>> 编译失败，请检查日志。")
                messagebox.showerror("失败", "编译过程中出现错误")
                
            # 清理
            if os.path.exists(bat_file):
                os.remove(bat_file)

        except Exception as e:
            self.log(f"编译异常: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.compile_btn.config(state='normal')
            self.current_process = None

    # ================= 评估 Tab 逻辑 =================
    def setup_eval_tab(self):
        parent = self.tab_eval
        
        # 目录配置
        config_frame = tk.LabelFrame(parent, text="对比数据源配置 (PNG 目录)", padx=10, pady=5)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        self.create_entry(config_frame, "GT (BRDFs):", self.eval_gt_dir, 0, is_dir=True)
        self.create_entry(config_frame, "Method 1 (FullBin):", self.eval_method1_dir, 1, is_dir=True)
        self.create_entry(config_frame, "Method 2 (NPY):", self.eval_method2_dir, 2, is_dir=True)

        # 操作
        action_frame = tk.Frame(parent, padx=10, pady=10)
        action_frame.pack(fill="x")
        
        self.eval_btn = tk.Button(action_frame, text="开始量化评估 (Calculate Metrics)", command=self.start_eval_thread, 
                                  bg="#9C27B0", fg="white", font=("Arial", 12, "bold"), height=2)
        self.eval_btn.pack(fill="x")

        # 说明
        note_frame = tk.Frame(parent, padx=10)
        note_frame.pack(fill="x")
        tk.Label(note_frame, text="注意: 将计算 PSNR, SSIM, Delta E (CIEDE2000)。这可能需要几分钟时间。", 
                 fg="gray").pack(anchor="w")

    def start_eval_thread(self):
        self.eval_btn.config(state='disabled')
        threading.Thread(target=self.run_evaluation, daemon=True).start()

    # ================= 图像工具 Tab 逻辑 =================
    def setup_tools_tab(self):
        parent = self.tab_tools
        
        # 1. 网格拼图配置
        grid_frame = tk.LabelFrame(parent, text="网格拼图 (Grid Image Generator)", padx=10, pady=5)
        grid_frame.pack(fill="x", padx=10, pady=5)
        
        self.create_entry(grid_frame, "图片输入目录:", self.grid_input_dir, 0, is_dir=True)
        self.create_entry(grid_frame, "输出文件路径:", self.grid_output_file, 1, is_dir=False) # is_dir=False for file
        
        opts_frame = tk.Frame(grid_frame)
        opts_frame.grid(row=2, column=1, sticky="w", pady=5)
        
        tk.Checkbutton(opts_frame, text="显示文件名", variable=self.grid_show_names).pack(side="left", padx=5)
        
        tk.Label(opts_frame, text="单图宽度:").pack(side="left", padx=(15, 5))
        tk.Entry(opts_frame, textvariable=self.grid_cell_width, width=8).pack(side="left")
        
        tk.Label(opts_frame, text="间距:").pack(side="left", padx=(15, 5))
        tk.Entry(opts_frame, textvariable=self.grid_padding, width=8).pack(side="left")
        
        # 操作按钮
        btn_frame = tk.Frame(parent, padx=10, pady=10)
        btn_frame.pack(fill="x")
        
        self.grid_btn = tk.Button(btn_frame, text="生成网格大图 (Generate Grid)", command=self.start_grid_thread, 
                                  bg="#009688", fg="white", font=("Arial", 12, "bold"), height=2)
        self.grid_btn.pack(fill="x")

        # 2. 同名对比拼图配置
        comp_frame = tk.LabelFrame(parent, text="同名对比拼图 (Side-by-Side Comparison)", padx=10, pady=5)
        comp_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(comp_frame, text="数据源使用【量化评估】Tab中的配置", fg="gray").grid(row=0, column=0, columnspan=3, sticky="w", pady=2)
        
        self.create_entry(comp_frame, "输出目录:", self.comp_output_dir, 1, is_dir=True)
        
        opts_frame2 = tk.Frame(comp_frame)
        opts_frame2.grid(row=2, column=1, sticky="w", pady=5)
        
        tk.Checkbutton(opts_frame2, text="添加列标题", variable=self.comp_show_label).pack(side="left", padx=5)
        tk.Checkbutton(opts_frame2, text="添加文件名", variable=self.comp_show_filename).pack(side="left", padx=5)
        
        tk.Label(opts_frame2, text="标题文本(逗号分隔):").pack(side="left", padx=5)
        tk.Entry(opts_frame2, textvariable=self.comp_labels, width=40).pack(side="left")

        # 操作按钮
        btn_frame2 = tk.Frame(parent, padx=10)
        btn_frame2.pack(fill="x")
        
        self.comp_btn = tk.Button(btn_frame2, text="生成对比拼图 (Generate Comparisons)", command=self.start_comp_thread, 
                                  bg="#E91E63", fg="white", font=("Arial", 12, "bold"), height=2)
        self.comp_btn.pack(fill="x")

    def start_grid_thread(self):
        self.grid_btn.config(state='disabled')
        threading.Thread(target=self.run_grid_generation, daemon=True).start()

    def start_comp_thread(self):
        self.comp_btn.config(state='disabled')
        threading.Thread(target=self.run_comp_generation, daemon=True).start()

    def run_comp_generation(self):
        try:
            self.log("\n>>> 开始生成对比拼图...")
            
            # 使用 Eval Tab 的输入配置
            dir_gt = self.eval_gt_dir.get()
            dir_m1 = self.eval_method1_dir.get()
            dir_m2 = self.eval_method2_dir.get()
            
            output_dir = self.comp_output_dir.get()
            if not os.path.exists(output_dir): os.makedirs(output_dir)
            
            show_label = self.comp_show_label.get()
            show_filename = self.comp_show_filename.get()
            
            labels = self.comp_labels.get().split(',')
            if len(labels) < 3: labels = ["GT", "Method1", "Method2"] # Fallback

            if not all(os.path.exists(d) for d in [dir_gt, dir_m1, dir_m2]):
                self.log("错误: 输入目录不存在 (请检查量化评估 Tab 的配置)")
                return

            files = sorted(glob.glob(os.path.join(dir_gt, "*.png")))
            total = len(files)
            if total == 0:
                self.log("错误: GT 目录中没有图片")
                return
            
            self.log(f"找到 {total} 组图片，正在生成对比图...")
            
            # 字体
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except IOError:
                font = ImageFont.load_default()

            count = 0
            for idx, f_gt in enumerate(files):
                basename = os.path.basename(f_gt)
                name_root = os.path.splitext(basename)[0]
                
                # 寻找对应文件 (复用逻辑)
                f_m1 = None
                for cand in [basename, f"{name_root}.fullbin.png"]:
                     if os.path.exists(os.path.join(dir_m1, cand)):
                         f_m1 = os.path.join(dir_m1, cand)
                         break
                
                f_m2 = None
                for cand in [basename, f"{name_root}_fc1.png", f"{name_root}.binary.png"]:
                     if os.path.exists(os.path.join(dir_m2, cand)):
                         f_m2 = os.path.join(dir_m2, cand)
                         break
                
                if not f_m1 or not f_m2:
                    self.log(f"跳过 {basename}: 缺失对应文件")
                    continue
                
                try:
                    images = [Image.open(f_gt), Image.open(f_m1), Image.open(f_m2)]
                    # 统一尺寸到 GT
                    w, h = images[0].size
                    images[1] = images[1].resize((w, h), Image.LANCZOS)
                    images[2] = images[2].resize((w, h), Image.LANCZOS)
                    
                    # 布局计算
                    padding = 10
                    label_height = 30 if show_label else 0
                    filename_height = 40 if show_filename else 0
                    
                    comp_w = w * 3 + padding * 4
                    comp_h = h + padding * 2 + label_height + filename_height
                    
                    comp_img = Image.new('RGB', (comp_w, comp_h), (255, 255, 255))
                    draw = ImageDraw.Draw(comp_img)
                    
                    # 绘制文件名 (顶部居中)
                    if show_filename:
                        name_text = name_root
                        # 使用稍大的字体
                        try:
                            title_font = ImageFont.truetype("arial.ttf", 24)
                        except IOError:
                            title_font = font
                            
                        bbox = draw.textbbox((0, 0), name_text, font=title_font)
                        text_w = bbox[2] - bbox[0]
                        text_x = (comp_w - text_w) / 2
                        text_y = padding
                        draw.text((text_x, text_y), name_text, fill=(0, 0, 0), font=title_font)

                    for i, img in enumerate(images):
                        x = padding + i * (w + padding)
                        y = padding + label_height + filename_height
                        comp_img.paste(img, (x, y))
                        
                        if show_label:
                            label_text = labels[i].strip() if i < len(labels) else ""
                            bbox = draw.textbbox((0, 0), label_text, font=font)
                            text_w = bbox[2] - bbox[0]
                            text_x = x + (w - text_w) / 2
                            text_y = padding + filename_height # 在文件名下方
                            draw.text((text_x, text_y), label_text, fill=(0, 0, 0), font=font)
                    
                    out_path = os.path.join(output_dir, f"comp_{basename}")
                    comp_img.save(out_path)
                    count += 1
                    
                    if count % 10 == 0:
                        self.status_var.set(f"正在生成对比图 ({idx+1}/{total})")
                        self.progress_var.set((idx/total)*100)

                except Exception as e:
                    self.log(f"生成失败 {basename}: {e}")

            self.log(f"生成完成！共 {count} 张对比图")
            self.log(f"输出目录: {output_dir}")
            messagebox.showinfo("完成", f"对比图已生成！\n输出目录: {output_dir}")

        except Exception as e:
            self.log(f"异常: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.comp_btn.config(state='normal')
            self.status_var.set("就绪")
            self.progress_var.set(100)

    def run_grid_generation(self):
        try:
            self.log("\n>>> 开始生成网格拼图...")
            input_dir = self.grid_input_dir.get()
            output_path = self.grid_output_file.get()
            show_names = self.grid_show_names.get()
            cell_width = self.grid_cell_width.get()
            padding = self.grid_padding.get()

            if not os.path.exists(input_dir):
                self.log(f"错误: 输入目录不存在 {input_dir}")
                return

            # 获取图片
            exts = ['*.png', '*.jpg', '*.jpeg', '*.bmp']
            files = []
            for ext in exts:
                files.extend(glob.glob(os.path.join(input_dir, ext)))
            files = sorted(files)
            
            count = len(files)
            if count == 0:
                self.log("错误: 未找到图片")
                return
            
            self.log(f"找到 {count} 张图片，正在处理...")
            self.progress_var.set(10)

            # 计算布局
            cols = math.ceil(math.sqrt(count))
            rows = math.ceil(count / cols)
            self.log(f"布局: {cols} 列 x {rows} 行")

            # 预估尺寸
            text_height = 30 if show_names else 0
            cell_height = int(cell_width * 1.0)
            
            # 读取第一张获取比例
            try:
                with Image.open(files[0]) as tmp:
                    aspect = tmp.height / tmp.width
                    cell_height = int(cell_width * aspect)
            except Exception as e:
                self.log(f"读取图片失败: {files[0]}")
                return

            grid_width = cols * cell_width + (cols + 1) * padding
            grid_height = rows * (cell_height + text_height) + (rows + 1) * padding
            
            self.log(f"大图尺寸: {grid_width} x {grid_height}")
            
            # 创建画布
            grid_img = Image.new('RGB', (grid_width, grid_height), color=(255, 255, 255))
            draw = ImageDraw.Draw(grid_img)
            
            try:
                # 尝试系统字体，Win下通常有 arial
                font = ImageFont.truetype("arial.ttf", 14)
            except IOError:
                font = ImageFont.load_default()

            for idx, fpath in enumerate(files):
                try:
                    with Image.open(fpath) as img:
                        img_resized = img.resize((cell_width, cell_height), Image.LANCZOS)
                        
                        col = idx % cols
                        row = idx // cols
                        
                        x = padding + col * (cell_width + padding)
                        y = padding + row * (cell_height + text_height + padding)
                        
                        grid_img.paste(img_resized, (x, y))
                        
                        if show_names:
                            filename = os.path.basename(fpath)
                            name_text = os.path.splitext(filename)[0]
                            if len(name_text) > 25: name_text = name_text[:22] + "..."
                            
                            bbox = draw.textbbox((0, 0), name_text, font=font)
                            text_w = bbox[2] - bbox[0]
                            text_x = x + (cell_width - text_w) / 2
                            text_y = y + cell_height + 5
                            
                            draw.text((text_x, text_y), name_text, fill=(0, 0, 0), font=font)
                    
                    if idx % 10 == 0:
                        self.status_var.set(f"正在拼合 ({idx+1}/{count})")
                        self.progress_var.set((idx/count)*100)

                except Exception as e:
                    self.log(f"处理图片出错 {os.path.basename(fpath)}: {e}")

            # 保存
            self.log("正在保存大图 (可能需要几秒钟)...")
            self.status_var.set("正在保存...")
            grid_img.save(output_path)
            
            self.log(f"成功保存至: {output_path}")
            messagebox.showinfo("成功", f"拼图已生成！\n{output_path}")

        except Exception as e:
            self.log(f"拼图异常: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.grid_btn.config(state='normal')
            self.status_var.set("就绪")
            self.progress_var.set(100)

    def process_single_file(self, f_gt, dir_m1, dir_m2):
        basename = os.path.basename(f_gt)
        name_root = os.path.splitext(basename)[0]
        
        # 寻找 FullBin
        f_m1 = None
        for cand in [basename, f"{name_root}.fullbin.png"]:
                path = os.path.join(dir_m1, cand)
                if os.path.exists(path):
                    f_m1 = path
                    break
        
        # 寻找 NPY
        f_m2 = None
        for cand in [basename, f"{name_root}_fc1.png", f"{name_root}.binary.png"]:
                path = os.path.join(dir_m2, cand)
                if os.path.exists(path):
                    f_m2 = path
                    break
        
        if not f_m1 or not f_m2:
            return None, f"跳过 {basename}: 未找到对应文件"

        # 读取图像
        img_gt = cv2.imread(f_gt)
        img_m1 = cv2.imread(f_m1)
        img_m2 = cv2.imread(f_m2)
        
        if img_gt is None or img_m1 is None or img_m2 is None:
            return None, f"读取失败: {basename}"

        # 尺寸检查
        if img_gt.shape != img_m1.shape or img_gt.shape != img_m2.shape:
            # 尝试 resize m1/m2 到 gt 尺寸
            img_m1 = cv2.resize(img_m1, (img_gt.shape[1], img_gt.shape[0]))
            img_m2 = cv2.resize(img_m2, (img_gt.shape[1], img_gt.shape[0]))

        # BGR 转 RGB
        img_gt_rgb = cv2.cvtColor(img_gt, cv2.COLOR_BGR2RGB)
        img_m1_rgb = cv2.cvtColor(img_m1, cv2.COLOR_BGR2RGB)
        img_m2_rgb = cv2.cvtColor(img_m2, cv2.COLOR_BGR2RGB)

        # 计算指标
        res_gt_m1 = self.calc_single_pair(img_gt_rgb, img_m1_rgb)
        res_gt_m2 = self.calc_single_pair(img_gt_rgb, img_m2_rgb)
        res_m1_m2 = self.calc_single_pair(img_m1_rgb, img_m2_rgb)
        
        return (res_gt_m1, res_gt_m2, res_m1_m2), None

    def run_evaluation(self):
        try:
            self.log("\n>>> 开始量化评估 (多线程并行)...")
            
            dir_gt = self.eval_gt_dir.get()
            dir_m1 = self.eval_method1_dir.get()
            dir_m2 = self.eval_method2_dir.get()
            
            if not all(os.path.exists(d) for d in [dir_gt, dir_m1, dir_m2]):
                self.log("错误: 至少有一个输入目录不存在")
                return

            files = sorted(glob.glob(os.path.join(dir_gt, "*.png")))
            if not files:
                self.log("错误: GT 目录中没有 PNG 文件")
                return
            
            self.log(f"找到 {len(files)} 个基准文件，正在分配任务...")
            
            metrics_gt_m1 = np.zeros(3)
            metrics_gt_m2 = np.zeros(3)
            metrics_m1_m2 = np.zeros(3)
            
            count = 0
            total = len(files)
            
            # 使用 ThreadPoolExecutor 并发执行
            # max_workers 设为 CPU 核心数，或者是其 2 倍
            max_workers = min(32, os.cpu_count() + 4) 
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_file = {
                    executor.submit(self.process_single_file, f, dir_m1, dir_m2): f 
                    for f in files
                }
                
                for idx, future in enumerate(concurrent.futures.as_completed(future_to_file)):
                    f = future_to_file[future]
                    basename = os.path.basename(f)
                    
                    try:
                        results, error_msg = future.result()
                        
                        if error_msg:
                            self.log(error_msg)
                        else:
                            # 累加结果
                            metrics_gt_m1 += results[0]
                            metrics_gt_m2 += results[1]
                            metrics_m1_m2 += results[2]
                            count += 1
                            
                    except Exception as exc:
                        self.log(f"处理异常 {basename}: {exc}")
                    
                    # 更新进度 (在主线程更新 UI)
                    self.status_var.set(f"正在评估 ({idx+1}/{total})")
                    self.progress_var.set(((idx+1)/total)*100)
                    
                    if (idx+1) % 10 == 0:
                        self.log(f"已完成 {idx+1}/{total}...")

            if count == 0:
                self.log("未成功处理任何图片")
                return
            
            # 取平均
            avg_gt_m1 = metrics_gt_m1 / count
            avg_gt_m2 = metrics_gt_m2 / count
            avg_m1_m2 = metrics_m1_m2 / count
            
            # 输出结果表格
            self.log("\n" + "="*60)
            self.log(f"{'Comparison':<20} | {'PSNR (dB)':<10} | {'SSIM':<10} | {'Delta E':<10}")
            self.log("-" * 60)
            self.log(f"{'GT vs FullBin':<20} | {avg_gt_m1[0]:<10.4f} | {avg_gt_m1[1]:<10.4f} | {avg_gt_m1[2]:<10.4f}")
            self.log(f"{'GT vs NPY':<20} | {avg_gt_m2[0]:<10.4f} | {avg_gt_m2[1]:<10.4f} | {avg_gt_m2[2]:<10.4f}")
            self.log(f"{'FullBin vs NPY':<20} | {avg_m1_m2[0]:<10.4f} | {avg_m1_m2[1]:<10.4f} | {avg_m1_m2[2]:<10.4f}")
            self.log("="*60 + "\n")
            
            messagebox.showinfo("完成", "评估完成！请查看日志中的结果表格。")

        except Exception as e:
            self.log(f"评估异常: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.eval_btn.config(state='normal')
            self.status_var.set("评估就绪")
            self.progress_var.set(100)

    def calc_single_pair(self, img1, img2):
        # PSNR
        psnr = metrics.peak_signal_noise_ratio(img1, img2, data_range=255)
        
        # SSIM (multichannel=True is deprecated in newer versions, use channel_axis)
        try:
            ssim = metrics.structural_similarity(img1, img2, data_range=255, channel_axis=2)
        except TypeError:
            # Fallback for older skimage versions
            ssim = metrics.structural_similarity(img1, img2, data_range=255, multichannel=True)
            
        # Delta E
        # Convert to Lab
        lab1 = color.rgb2lab(img1)
        lab2 = color.rgb2lab(img2)
        de_map = color.deltaE_ciede2000(lab1, lab2)
        de = np.mean(de_map)
        
        return np.array([psnr, ssim, de])

    def run_conversion(self):
        indices = self.conv_listbox.curselection()
        if not indices:
            messagebox.showwarning("提示", "请选择要转换的 EXR 文件")
            return
            
        input_dir = self.conv_input_dir.get()
        output_dir = self.conv_output_dir.get()
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        
        mtsutil = self.mtsutil_exe.get()
        env = os.environ.copy() # 确保能找到相关dll
        
        total = len(indices)
        for idx, i in enumerate(indices):
            filename = self.conv_listbox.get(i)
            self.status_var.set(f"正在转换 ({idx+1}/{total}): {filename}")
            self.progress_var.set((idx/total)*100)
            
            in_path = os.path.join(input_dir, filename)
            out_name = os.path.splitext(filename)[0] + ".png"
            out_path = os.path.join(output_dir, out_name)
            
            cmd = [mtsutil, "tonemap", "-o", out_path, in_path]
            try:
                subprocess.run(cmd, env=env, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
                self.log(f"[转换] 成功: {out_name}")
            except subprocess.CalledProcessError:
                self.log(f"[转换] 失败: {filename}")
        
        self.status_var.set("转换完成")
        self.progress_var.set(100)
        messagebox.showinfo("完成", f"转换完成！\n输出目录: {output_dir}")

    # ================= 通用辅助 =================
    def create_entry(self, parent, label, variable, row, is_dir=False, cmd=None):
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=5, pady=2)
        tk.Entry(parent, textvariable=variable, width=70).grid(row=row, column=1, padx=5, pady=2)
        def browse():
            path = filedialog.askdirectory() if is_dir else filedialog.askopenfilename()
            if path: 
                variable.set(path)
                if cmd: cmd()
        tk.Button(parent, text="浏览...", command=browse).grid(row=row, column=2, padx=5)

    def log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def start_render_thread(self):
        self.stop_requested = False
        self.render_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        threading.Thread(target=self.run_render, daemon=True).start()

    def stop_render(self):
        self.stop_requested = True
        if self.current_process:
            self.log("正在停止当前任务...")
            self.current_process.terminate()
        self.status_var.set("正在停止...")

    def on_closing(self):
        self.stop_render()
        self.root.destroy()

    def run_render(self):
        # ... (渲染逻辑保持不变，只需注意 listbox 变量名为 self.render_listbox) ...
        indices = self.render_listbox.curselection()
        if not indices:
            messagebox.showwarning("提示", "请选择要渲染的文件")
            self.render_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            return

        input_dir = self.current_input_dir.get()
        base_output_dir = self.current_output_dir.get()
        mode = self.render_mode.get()
        
        exr_dir = os.path.join(base_output_dir, "exr")
        png_dir = os.path.join(base_output_dir, "png")
        temp_xml_dir = os.path.join(BASE_DIR, "batch_temp_xmls")
        for d in [exr_dir, png_dir, temp_xml_dir]:
            if not os.path.exists(d): os.makedirs(d)

        mitsuba_exe = self.mitsuba_exe.get()
        mtsutil_exe = self.mtsutil_exe.get()
        scene_path = self.scene_path.get()
        env = os.environ.copy()
        env["PATH"] = os.path.dirname(mitsuba_exe) + os.pathsep + env.get("PATH", "")

        try:
            # ... (XML 解析部分) ...
            
            # ... (循环外部分) ...

            total = len(indices)
            tree = ET.parse(scene_path)
            root = tree.getroot()
            scene_dir = os.path.dirname(os.path.abspath(scene_path))

            # 自动修复所有相对路径 (包括 envmap, texture 等)
            for string_node in root.iter('string'):
                if string_node.get('name') == 'filename':
                    val = string_node.get('value')
                    if not os.path.isabs(val):
                        # 尝试相对于场景文件的路径
                        abs_val = os.path.abspath(os.path.join(scene_dir, val))
                        if os.path.exists(abs_val):
                             string_node.set('value', abs_val.replace("\\", "/"))
                        else:
                             # 备选：尝试相对于 BASE_DIR
                             abs_val_2 = os.path.abspath(os.path.join(BASE_DIR, val))
                             if os.path.exists(abs_val_2):
                                 string_node.set('value', abs_val_2.replace("\\", "/"))

            # --- 应用新参数 ---
            # 移除了参数覆盖逻辑，完全使用 XML 中的设置


            target_bsdf = None
            for bsdf in root.iter('bsdf'):
                if bsdf.get('type') in ['merl', 'fullmerl', 'nbrdf_npy']:
                    target_bsdf = bsdf
                    break
            
            if target_bsdf is None:
                self.log("错误: 场景中未找到 bsdf 节点")
                return

            for idx, i in enumerate(indices):
                if self.stop_requested:
                    self.log("渲染已停止")
                    break

                filename = self.render_listbox.get(i)
                # ... (参数设置部分) ...
                file_path = os.path.join(input_dir, filename).replace("\\", "/")
                basename = os.path.splitext(filename)[0]
                
                # 检查是否跳过
                exr_out = os.path.join(exr_dir, f"{basename}.exr")
                png_out = os.path.join(png_dir, f"{basename}.png")
                
                if self.skip_existing.get():
                    # 如果开启了自动转换，则检查 PNG 是否存在；否则只检查 EXR
                    target_file = png_out if self.auto_convert.get() else exr_out
                    if os.path.exists(target_file):
                        self.log(f"[{idx+1}/{total}] 跳过 (已存在): {basename}")
                        self.progress_var.set((idx + 1) / total * 100)
                        continue

                self.status_var.set(f"正在渲染 ({idx+1}/{total}): {filename}")
                self.progress_var.set((idx / total) * 100)
                
                # 清理旧参数
                for child in list(target_bsdf):
                    if child.get('name') in ['filename', 'binary', 'nn_basename']: target_bsdf.remove(child)
                
                # 设置新参数
                if mode == "brdfs":
                    target_bsdf.set('type', 'merl')
                    ET.SubElement(target_bsdf, 'string', {'name': 'binary', 'value': file_path})
                    self.configure_bsdf_smart(target_bsdf, filename)
                elif mode == "fullbin":
                    target_bsdf.set('type', 'fullmerl')
                    ET.SubElement(target_bsdf, 'string', {'name': 'filename', 'value': file_path})
                    self.configure_bsdf_smart(target_bsdf, filename)
                elif mode == "npy":
                    target_bsdf.set('type', 'nbrdf_npy')
                    base_path = os.path.splitext(file_path)[0]
                    for suffix in ["fc1", "fc2", "fc3", "b1", "b2", "b3"]:
                        if base_path.endswith(suffix):
                            base_path = base_path[:-len(suffix)]
                            break
                    ET.SubElement(target_bsdf, 'string', {'name': 'nn_basename', 'value': base_path})
                    for child in list(target_bsdf):
                        if child.tag == 'bsdf': target_bsdf.remove(child)
                    if not any(c.get('name') == 'reflectance' for c in target_bsdf):
                        ET.SubElement(target_bsdf, 'spectrum', {'name': 'reflectance', 'value': '0.5'})

                temp_xml = os.path.join(temp_xml_dir, f"{basename}.xml")
                tree.write(temp_xml)
                
                # exr_out 已经在上面定义了
                cmd = [mitsuba_exe, "-o", exr_out, temp_xml]
                
                self.log(f"[{idx+1}/{total}] 渲染: {filename}")
                self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                      text=True, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
                
                # 实时读取并显示输出
                for line in self.current_process.stdout:
                    self.log(f"  > {line.strip()}")
                self.current_process.wait()
                
                if self.current_process.returncode == 0:
                    self.log(f"  -> EXR 完成")
                    if self.auto_convert.get():
                        # png_out 已经在上面定义了
                        cmd_conv = [mtsutil_exe, "tonemap", "-o", png_out, exr_out]
                        # 转换通常很快，暂不设为可中断，除非需要
                        subprocess.run(cmd_conv, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
                        self.log(f"  -> PNG 完成")
                else:
                    if self.stop_requested:
                        self.log(f"  -> 已终止")
                    else:
                        self.log(f"  -> 失败")
                
                self.current_process = None

            if not self.stop_requested:
                self.status_var.set("全部完成")
                self.progress_var.set(100)
                messagebox.showinfo("完成", f"批量渲染结束！\n输出目录: {base_output_dir}")
            else:
                self.status_var.set("已停止")

        except Exception as e:
            self.log(f"发生异常: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.render_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            self.current_process = None

    def configure_bsdf_smart(self, bsdf_node, filename):
        # 移除旧的 guiding bsdf 子节点
        for child in list(bsdf_node):
            if child.tag == 'bsdf':
                bsdf_node.remove(child)

        name = filename.lower()
        
        # --- 1. 金属材质检测 (Metals) ---
        is_metal = False
        metal_material = "Cu" # 默认铜
        
        # 金属关键词匹配
        if "gold" in name: is_metal = True; metal_material = "Au"
        elif "silver" in name: is_metal = True; metal_material = "Ag"
        elif "aluminium" in name or "alum-" in name: is_metal = True; metal_material = "Al"
        elif "chrome" in name or "steel" in name or "ss440" in name: is_metal = True; metal_material = "Cr"
        elif "nickel" in name: is_metal = True; metal_material = "Cr" # Ni not supported
        elif "tungsten" in name: is_metal = True; metal_material = "W"
        elif "brass" in name or "bronze" in name or "copper" in name: is_metal = True; metal_material = "Cu"
        elif "hematite" in name: is_metal = True; metal_material = "Cr" # 近似
        elif "metallic" in name: is_metal = True; metal_material = "Al" # 泛用金属
            
        if is_metal:
            # 金属使用 roughconductor
            guide = ET.SubElement(bsdf_node, 'bsdf', {'type': 'roughconductor'})
            ET.SubElement(guide, 'string', {'name': 'material', 'value': metal_material})
            # 默认粗糙度 0.1，如果是 brushed 或 matte 金属可以增加
            alpha_val = "0.1"
            if "matte" in name or "brushed" in name or "rough" in name:
                alpha_val = "0.2"
            ET.SubElement(guide, 'float', {'name': 'alpha', 'value': alpha_val})
            return

        # --- 2. 绝缘体/塑料材质 (Dielectrics/Plastics) ---
        # 绝缘体 (塑料, 漆, 织物, 木材等) 使用 roughplastic
        guide = ET.SubElement(bsdf_node, 'bsdf', {'type': 'roughplastic'})
        
        # 2.1 确定 IOR (折射率)
        ior_val = "polypropylene" # 默认 1.49 (通用塑料)
        if "acrylic" in name: ior_val = "acrylic glass"
        elif "diamond" in name: ior_val = "diamond"
        elif "water" in name: ior_val = "water"
        elif "glass" in name or "bk7" in name or "obsidian" in name: ior_val = "bk7"
        elif "teflon" in name: ior_val = "1.35"
        elif "delrin" in name: ior_val = "1.48"
        elif "silicon-nitrade" in name: ior_val = "2.0"
            
        # Check if IOR is numeric
        try:
            float(ior_val)
            ET.SubElement(guide, 'float', {'name': 'intIOR', 'value': ior_val})
        except ValueError:
            ET.SubElement(guide, 'string', {'name': 'intIOR', 'value': ior_val})
        
        # 2.2 确定颜色 (diffuseReflectance)
        # 默认灰色
        color_val = "0.5 0.5 0.5" 
        
        # 颜色关键词匹配 (注意顺序，具体在前)
        if "dark-red" in name: color_val = "0.3 0.05 0.05"
        elif "dark-blue" in name: color_val = "0.05 0.05 0.3"
        elif "light-red" in name: color_val = "0.8 0.3 0.3"
        elif "light-brown" in name: color_val = "0.6 0.4 0.2"
        elif "blue" in name: color_val = "0.1 0.1 0.6"
        elif "red" in name: color_val = "0.6 0.1 0.1"
        elif "green" in name: color_val = "0.1 0.6 0.1"
        elif "white" in name or "alumina" in name or "marble" in name or "pearl" in name or "delrin" in name: color_val = "0.9 0.9 0.9"
        elif "black" in name or "obsidian" in name: color_val = "0.05 0.05 0.05"
        elif "yellow" in name: color_val = "0.8 0.8 0.1"
        elif "pink" in name: color_val = "0.8 0.5 0.5"
        elif "orange" in name: color_val = "0.8 0.4 0.1"
        elif "purple" in name or "violet" in name: color_val = "0.5 0.1 0.5"
        elif "beige" in name: color_val = "0.85 0.75 0.6"
        elif "brown" in name: color_val = "0.4 0.2 0.1"
        elif "maroon" in name: color_val = "0.4 0.0 0.0"
        elif "cyan" in name: color_val = "0.1 0.6 0.6"
        elif "gray" in name or "grey" in name: color_val = "0.5 0.5 0.5"

        # 木材颜色覆盖 (覆盖前面的颜色)
        if "cherry" in name: color_val = "0.55 0.2 0.1"
        elif "maple" in name or "natural" in name: color_val = "0.8 0.7 0.5"
        elif "pine" in name: color_val = "0.8 0.7 0.4"
        elif "oak" in name: color_val = "0.65 0.5 0.3"
        elif "walnut" in name: color_val = "0.35 0.2 0.1"
        elif "fruitwood" in name: color_val = "0.5 0.35 0.2"
        elif "mahogany" in name: color_val = "0.4 0.1 0.05"
        
        ET.SubElement(guide, 'spectrum', {'name': 'diffuseReflectance', 'value': color_val})
        
        # 2.3 确定粗糙度 (alpha)
        alpha_val = "0.1" # 默认光滑
        if "fabric" in name or "matte" in name or "wood" in name or "rubber" in name or "foam" in name:
            alpha_val = "0.3" # 粗糙材质
        elif "felt" in name or "velvet" in name:
            alpha_val = "0.5" # 极粗糙
        elif "wood" in name or "cherry" in name or "maple" in name or "pine" in name or "oak" in name or "walnut" in name:
            alpha_val = "0.2" # 木材稍粗糙
        elif "specular" in name or "obsidian" in name: # 显式指明高光的
            alpha_val = "0.05"
        
        ET.SubElement(guide, 'float', {'name': 'alpha', 'value': alpha_val})

if __name__ == "__main__":
    root = tk.Tk()
    app = BatchRendererApp(root)
    root.mainloop()
