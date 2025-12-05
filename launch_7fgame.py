import os
import subprocess
import sys
import ctypes


  = r"D:\Game\7fgame\7FGame.exe"


def is_process_running(exe_name: str) -> bool:
    """通过 tasklist 检查是否已运行（Windows）。"""
    try:
        output = subprocess.check_output(["tasklist"], encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return exe_name.lower() in output.lower()


def run_elevated(exe_path: str, cwd: str) -> bool:
    """
    使用 ShellExecuteW 的 'runas' 动作以提升权限启动程序。
    返回 True 表示已成功调用（注意无法获得 Popen 对象）。
    """
    try:
        # SW_SHOWNORMAL = 1
        hinst = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, None, cwd, 1)
        return int(hinst) > 32
    except Exception:
        return False


def start_7fgame(wait: bool = False) -> subprocess.Popen:
    """
    启动 7FGame.exe 并返回 Popen 对象（如果使用 ShellExecute 提升则返回 None）。
    如果已在运行，则不重复启动。
    参数 wait=True 会在启动后阻塞直到进程结束（仅对 Popen 有效）。
    """
    if not os.path.isfile(EXE_PATH):
        raise FileNotFoundError(f"找不到可执行文件: {EXE_PATH}")

    exe_name = os.path.basename(EXE_PATH)
    if is_process_running(exe_name):
        print(f"{exe_name} 已在运行，跳过启动。")
        return None

    cwd = os.path.dirname(EXE_PATH)
    try:
        # 使用 Popen 启动，设置 cwd 为 exe 所在目录
        proc = subprocess.Popen([EXE_PATH], cwd=cwd)
        print(f"已启动 {exe_name} (pid={proc.pid})")
        if wait:
            proc.wait()
        return proc
    except OSError as e:
        # WinError 740: 需要提升（管理员权限）
        if getattr(e, "winerror", None) == 740:
            print("检测到需要提升权限，尝试以管理员身份启动...")
            ok = run_elevated(EXE_PATH, cwd)
            if ok:
                print("已使用提升权限启动程序（无法获取 pid）。")
                return None
            else:
                raise RuntimeError("尝试以管理员身份启动失败。") from e
        raise


if __name__ == "__main__":
    # 命令行支持：python launch_7fgame.py [--wait]
    wait_flag = "--wait" in sys.argv
    start_7fgame(wait=wait_flag)