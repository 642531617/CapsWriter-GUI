import os
import shutil
import subprocess
import sys

# 定义打包配置
TARGETS = [
    # (脚本名, 是否隐藏控制台, 图标路径)
    ("capswriter_gui.py", True, "assets/icon.ico"),  # GUI 主程序 (隐藏黑窗口)
    ("core_server.py", True, "assets/icon.ico"),  # 服务端 (由 GUI 启动，隐藏黑窗口)
    ("core_client.py", True, "assets/icon.ico"),  # 客户端 (由 GUI 启动，隐藏黑窗口)
]

DIST_DIR = "CapsWriter_Release"


def run_command(cmd):
    print(f"执行命令: {cmd}")
    subprocess.check_call(cmd, shell=True)


def main():
    print("=== 开始构建 CapsWriter Offline ===")

    # 1. 安装 PyInstaller
    print("正在检查/安装 PyInstaller...")
    run_command(f"{sys.executable} -m pip install pyinstaller")

    # 清理旧文件
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    if os.path.exists("build"):
        shutil.rmtree("build")

    os.makedirs(DIST_DIR, exist_ok=True)

    # 2. 分别打包三个程序
    # 我们使用 -F (单文件模式)，这样生成出来的就是三个干净的 exe
    for script, no_console, icon in TARGETS:
        print(f"\n正在打包: {script} ...")

        cmd = [
            "pyinstaller",
            "-F",  # 生成单文件 exe
            "--distpath", DIST_DIR,  # 输出目录
            "--clean",
            "-y"
        ]

        if no_console:
            cmd.append("-w")  # 隐藏控制台窗口

        if os.path.exists(icon):
            cmd.extend(["-i", icon])

        cmd.append(script)

        run_command(" ".join(cmd))

    # 3. 复制必要的资源文件
    print("\n正在复制配置文件和资源...")
    files_to_copy = [
        "config.py",
        "hot-zh.txt",
        "hot-en.txt",
        "hot-rule.txt",
        "keywords.txt",
        "readme.md"
    ]

    for f in files_to_copy:
        if os.path.exists(f):
            shutil.copy(f, os.path.join(DIST_DIR, f))
            print(f"已复制: {f}")

    # 复制 assets 文件夹
    if os.path.exists("assets"):
        shutil.copytree("assets", os.path.join(DIST_DIR, "assets"))
        print("已复制: assets 文件夹")

    print("\n" + "=" * 30)
    print(f"构建完成！输出目录: {os.path.abspath(DIST_DIR)}")
    print("注意：你需要手动将 'models' 文件夹复制到输出目录中！(因为模型太大了)")
    print("=" * 30)


if __name__ == "__main__":
    main()
# 尝试自动复制 models
    if os.path.exists("models"):
        print("\n正在复制 models 文件夹 (这可能需要几分钟)...")
        # 忽略掉可能存在的 git 文件夹或其他垃圾文件
        shutil.copytree("models", os.path.join(DIST_DIR, "models"), dirs_exist_ok=True)
        print("已复制: models 文件夹")
    else:
        print("\n" + "!" * 30)
        print("警告：未检测到 'models' 文件夹！")
        print("请务必手动将 models 文件夹复制到输出目录：")
        print(os.path.abspath(DIST_DIR))
        print("!" * 30)

    print("\n" + "=" * 30)
    print(f"构建完成！输出目录: {os.path.abspath(DIST_DIR)}")
    print("=" * 30)