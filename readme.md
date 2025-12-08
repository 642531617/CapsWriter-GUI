# CapsWriter Offline GUI - 离线语音输入法 (图形界面版)

**CapsWriter Offline GUI** 是基于 [CapsWriter-Offline](https://github.com/HaujetZhao/CapsWriter-Offline) 的图形化封装版本。它保留了原版强大的离线语音识别能力（基于阿里 Paraformer 模型），并增加了一个用户友好的图形界面，使得配置、监控和文件转录变得更加简单直观。

> **核心特性：** 完全离线、无限时长、低延迟、高准确率、数据隐私安全。

![image-20251124014859787](C:\Users\Administrator\AppData\Roaming\Typora\typora-user-images\image-20251124014859787.png)

## 🌟 主要功能

* **🎙️ 全局语音输入**：在任何软件中，按下键盘快捷键（默认 `CapsLock`）说话，松开即可自动输入文字。
* **🖱️ 图形化控制台**：一键启动/停止服务，实时查看服务端与客户端的运行日志。
* **📂 离线文件转录**：支持拖拽音频/视频文件进行批量离线转录，生成 SRT 字幕文件。
* **📝 热词管理**：内置热词编辑器，可随时修改中文/英文热词、替换规则及日记关键词。
* **⚙️ 简易配置**：直接在界面中修改配置文件，调整快捷键、静默阈值等参数。
* **⚡ 极速启动**：针对 Windows 优化，无黑框干扰，退出后自动清理后台进程。

---

## 🚀 使用指南 (普通用户)

### 1. 安装与准备
本软件为绿色免安装版，但依赖离线模型文件。

1.  下载解压程序包 `CapsWriter_Release`。
2.  **【重要】** 确保目录中包含 `models` 文件夹（需包含 `paraformer-offline-zh`、`punc_ct-transformer_cn-en`模型数据）。如果缺少该文件夹，软件将无法启动。
    * *模型约1.1GB，需单独下载，下载页面地址(models.zip)：https://github.com/HaujetZhao/CapsWriter-Offline/releases*
    * *百度盘: https://pan.baidu.com/s/1zNHstoWZDJVynCBz2yS9vg 提取码: eu4c*
3.  双击运行 **`capswriter_gui.exe`**。

### 2. 语音输入
1.  点击界面左上角的 **“启动服务 (Start)”** 按钮。
2.  等待 **服务端日志** 显示 `Service Ready!`，且 **客户端日志** 显示 `已载入 x 条热词`。
3.  将光标移入任意输入框（如 Word、微信、记事本）。
4.  **长按** 键盘上的 `CapsLock` 键（大写锁定键）开始说话，**松开** 即可上屏。
    * *(默认行为可在 `设置 (Config)` 标签页中修改为单击模式)*

### 3. 文件转录 (字幕生成)
1.  切换到 **“文件转录”** 标签页。
2.  确保服务已启动。
3.  将音频或视频文件（mp3, wav, mp4 等）**拖拽** 到列表中。
4.  点击 **“开始转录”**。
5.  转录完成后，SRT 字幕文件将自动生成在源文件同级目录下。

### 4. 热词与配置
* **热词管理**：在标签页中编辑 `hot-zh.txt` 等文件，点击“保存”后，**无需重启**，下次识别自动生效（客户端会自动热更新）。
* **设置 (Config)**：修改 `config.py` 中的参数（如快捷键、端口号），修改后需要点击 **“停止服务”** 再 **“启动服务”** 才能生效。

---

## 🛠️ 常见问题 (FAQ)

**Q: 点击“启动服务”后，日志提示“端口被占用”？**
A: 这通常是因为上次退出不彻底。请尝试重启软件，或者在任务管理器中手动结束 `core_server.exe` 进程。现在的 GUI 版本已包含自动清理功能，正常关闭窗口即可。

**Q: 按下 CapsLock 没有任何反应？**
A: 
1. 请检查“运行监控”中的客户端日志，确认是否显示“服务端未连接”。
2. 某些安全软件（如 360）可能会拦截键盘监听，请将程序加入白名单。
3. 如果是 MacOS 用户，需要以管理员权限（sudo）运行。

**Q: 识别速度很慢或一直在加载？**
A: 离线识别依赖 CPU 运算。请确保你的电脑不是处于高负载状态。首次启动时加载模型需要几秒钟时间，请耐心等待 `Service Ready` 提示。

**Q: 如何彻底关闭软件？**
A: 直接关闭主窗口即可。程序会自动清理所有后台的 Server 和 Client 进程，不会残留。

---

## 💻 开发者构建指南

如果你想自己从源码构建 exe 版本：

1.  **环境准备**：
    * Python 3.8+
    * 安装依赖：`pip install -r requirements.txt`
    * 安装 PyInstaller：`pip install pyinstaller`

2.  **构建命令**：
    在源码根目录下运行：
    ```bash
    python build_dist.py
    ```

3.  **构建产物**：
    构建完成后，生成文件位于 `CapsWriter_Release` 目录。
    *注意：构建脚本会自动尝试复制 `models` 文件夹，但请务必检查最终产物中是否包含该文件夹。*

---

## 📄 版权与致谢

* **核心算法与原版项目**：[HaujetZhao/CapsWriter-Offline](https://github.com/HaujetZhao/CapsWriter-Offline)
* **语音模型**：阿里巴巴 Paraformer (FunASR)
* **GUI 封装与打包**：[Your Name/ID]

本项目仅供学习与交流使用，请遵守相关开源协议。