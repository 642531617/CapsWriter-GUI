import os
import sys
import multiprocessing
import traceback

# ==========================================
# 1. 基础路径修正 (必须最先执行)
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    sys.path.insert(0, BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)


# ==========================================
# 2. 定义双向日志类 (先定义，暂不启用)
# ==========================================
class DualLogger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        # 使用 'a' (追加模式) 稍微安全一点，虽然主要是通过位置修复
        self.log = open(filename, "a", encoding='utf-8', buffering=1)

    def write(self, message):
        try:
            # 写到屏幕 (给 GUI 抓取)
            self.terminal.write(message)
            self.terminal.flush()
            # 写到文件 (留存证据)
            self.log.write(message)
            self.log.flush()
        except Exception:
            pass

    def flush(self):
        try:
            self.terminal.flush()
            self.log.flush()
        except:
            pass


# ==========================================
# 3. 导入业务模块
# ==========================================
try:
    import asyncio
    from platform import system
    import websockets

    from config import ServerConfig as Config
    from util.server_cosmic import Cosmic, console
    from util.server_check_model import check_model
    from util.server_ws_recv import ws_recv
    from util.server_ws_send import ws_send
    from util.server_init_recognizer import init_recognizer
    from util.empty_working_set import empty_current_working_set

except Exception as e:
    # 如果导入都失败了，直接打印并退出
    print(f"CRITICAL IMPORT ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)


# ==========================================
# 4. 主逻辑
# ==========================================
async def main():
    try:
        check_model()

        print(f'\n项目地址：https://github.com/HaujetZhao/CapsWriter-Offline')
        print(f'绑定的服务地址：{Config.addr}:{Config.port}\n')

        # 初始化跨进程列表
        Cosmic.sockets_id = multiprocessing.Manager().list()

        # 启动识别子进程
        recognize_process = multiprocessing.Process(
            target=init_recognizer,
            args=(Cosmic.queue_in, Cosmic.queue_out, Cosmic.sockets_id),
            daemon=True
        )
        recognize_process.start()

        # 等待子进程准备就绪 (模型加载)
        # 这里的 get() 之前会卡死，现在解除了文件锁，应该能正常通过
        Cosmic.queue_out.get()
        print('Service Ready! (开始服务)')

        if system() == 'Windows':
            empty_current_working_set()

        recv = websockets.serve(ws_recv,
                                Config.addr,
                                Config.port,
                                subprotocols=["binary"],
                                max_size=None)

        send = ws_send()
        await asyncio.gather(recv, send)

    except Exception as e:
        print(f"RUNTIME ERROR: {e}")
        traceback.print_exc()


def init():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Init Error: {e}")
    finally:
        # 尝试安全退出
        try:
            Cosmic.queue_out.put(None)
        except:
            pass
        sys.exit(0)


if __name__ == "__main__":
    # 【核心修复】多进程支持必须放在第一行
    multiprocessing.freeze_support()

    # 【核心修复】只在主进程中接管 stdout，防止子进程死锁
    if getattr(sys, 'frozen', False):
        try:
            log_path = os.path.join(BASE_DIR, 'server_run.log')
            # 只有主进程才去占用这个文件
            sys.stdout = DualLogger(log_path)
            sys.stderr = sys.stdout
        except Exception as e:
            print(f"Logging setup failed: {e}")

    print(f"--- Server Process Starting (PID: {os.getpid()}) ---")

    init()