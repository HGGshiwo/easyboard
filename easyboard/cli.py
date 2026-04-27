import argparse
import os
import signal
import socket
import subprocess
import sys
import time
import uuid

import psutil


def find_free_port(start_port):
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                print(f"⚠️ Port {port} is occupied, trying next...")
                port += 1
    raise RuntimeError("No free ports available!")


def run_with_dogtag_and_kill(cmd, env_vars=None):
    """
    带狗牌启动进程，并在被打断时执行全网通缉清理的终极绝杀函数
    """
    # 1. 核心魔法：生成一个独一无二的会话狗牌
    session_id = f"easyboard_{uuid.uuid4().hex[:8]}"

    # 2. 复制环境变量并注入狗牌
    custom_env = os.environ.copy()
    if env_vars:
        custom_env.update(env_vars)
    custom_env["EASYBOARD_SESSION_TAG"] = session_id

    # 3. 准备进程组隔离参数 (兼容 WSL/Linux)
    kwargs = {}
    if os.name == "posix":
        kwargs["preexec_fn"] = os.setsid
    elif os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    # 4. 带着狗牌启动 Streamlit
    process = subprocess.Popen(cmd, env=custom_env, **kwargs)

    # ==========================================
    # 定义“按牌杀人”的绝对清理逻辑
    # ==========================================
    def session_cleanup():
        # \r 覆盖掉终端的 ^C 乱码
        print(f"\n\r🛑 Shutting down EasyBoard...")
        victims_killed = 0

        # 遍历全系统进程，猎杀带有我们狗牌的进程
        for p in psutil.process_iter(["pid", "name", "environ"]):
            try:
                env = p.info.get("environ")
                if env and env.get("EASYBOARD_SESSION_TAG") == session_id:
                    # 发现目标！直接物理击毙 (SIGKILL)，让它连打印报错的机会都没有
                    p.kill()
                    victims_killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 容错：顺手把整个进程组也发一个 SIGKILL，作为最后一道保险
        if os.name == "posix":
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except OSError:
                pass
        else:
            try:
                process.kill()
            except:
                pass

        print(f"✅ EasyBoard stopped cleanly.")

    # 5. 守护父进程
    try:
        # process.wait()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # 当你在终端按下 Ctrl+C 时，直接触发物理超度
        session_cleanup()
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Start the EasyBoard dashboard.")
    parser.add_argument(
        "--logdir", type=str, required=True, help="Directory containing the logs."
    )
    parser.add_argument(
        "--port", type=int, default=8501, help="Port to run the dashboard on."
    )
    args = parser.parse_args()

    actual_port = find_free_port(args.port)
    log_dir_abs = os.path.abspath(args.logdir)

    print("\n" + "=" * 50)
    print(f"🚀 Starting EasyBoard...")
    print(f"📂 Monitoring log directory: {log_dir_abs}")
    print(f"🌐 Dashboard is running at: http://localhost:{actual_port}")
    print("=" * 50 + "\n")

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.py"),
        "--server.port",
        str(actual_port),
    ]

    # 传递自定义环境变量
    env_vars = {"EASYBOARD_LOGDIR": log_dir_abs}

    # 启动绝杀引擎
    run_with_dogtag_and_kill(cmd, env_vars)


if __name__ == "__main__":
    main()
