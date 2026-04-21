import argparse
import os
import sys
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Start the EasyBoard dashboard.")
    parser.add_argument('--logdir', type=str, required=True, help='Directory containing the logs.')
    parser.add_argument('--port', type=int, default=8501, help='Port to run the dashboard on.')
    args = parser.parse_args()

    # 1. 把 logdir 存入环境变量，让 dashboard.py 能够读到
    os.environ['EASYBOARD_LOGDIR'] = os.path.abspath(args.logdir)

    # 2. 找到 dashboard.py 所在的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_path = os.path.join(current_dir, 'dashboard.py')

    print(f"🚀 Starting EasyBoard at http://localhost:{args.port}")
    print(f"📂 Monitoring log directory: {os.environ['EASYBOARD_LOGDIR']}")

    # 3. 使用当前的 Python 环境强制启动 Streamlit（完美解决你之前的环境冲突问题）
    cmd = [sys.executable, "-m", "streamlit", "run", dashboard_path, "--server.port", str(args.port)]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 EasyBoard stopped.")

if __name__ == "__main__":
    main()