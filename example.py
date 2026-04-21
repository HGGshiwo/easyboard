import time
import random
import math
from easyboard import SummaryWriter

print("🚀 初始化实验中...")

# 统一的日志存放顶层目录
LOG_DIR = "example_logs"

# 保存我们创建的全部 writers 以便在循环里调用
writers = []

# ==========================================
# 1. 初始化两组实验，每组 3 个 Seed
# ==========================================
algorithms = ["PPO", "SAC"]
seeds = [1, 2, 3]

for algo in algorithms:
    for seed in seeds:
        # 自由嵌套目录！例如：RoboNav_Task/PPO/seed_1
        run_path = f"RoboNav_Task/{algo}/seed_{seed}"
        writer = SummaryWriter(log_dir=LOG_DIR, run_path=run_path)
        
        # 记录实验参数（自动汇集成表格）
        lr = 0.01 if algo == "PPO" else 0.005
        writer.add_config({
            "Algorithm": algo,
            "Learning_Rate": lr,
            "Batch_Size": 64 if algo == "PPO" else 128,
            "Environment": "Warehouse_v2"
        })
        
        # 将 writer 和对应的算法名存起来
        writers.append((algo, writer))

# ==========================================
# 2. 模拟训练主循环 (时间序列数据)
# ==========================================
print("🏃 开始模拟训练，请打开 easyboard 网页查看实时曲线！")
total_steps = 100

for step in range(total_steps):
    for algo, writer in writers:
        # 制造一些逼真的带噪声的假数据
        noise = random.uniform(-0.1, 0.1)
        
        if algo == "PPO":
            # PPO 收敛慢一点，方差大一点
            loss = 5.0 * math.exp(-step / 20.0) + random.uniform(0, 0.5)
            reward = step * 0.1 + noise * 5
        else:
            # SAC 收敛快一点，方差小一点
            loss = 3.0 * math.exp(-step / 10.0) + random.uniform(0, 0.2)
            reward = step * 0.15 + noise * 2

        # 高频记录！后台会自动缓冲合并，不会卡顿
        writer.add_scalar("Training/Loss", loss, step)
        writer.add_scalar("Training/Reward", reward, step)
        
    # 稍微睡一下，模拟真实训练耗时
    # 这时你可以去网页点左侧的 "Force Refresh Data" 看实时的曲线生长！
    time.sleep(0.05) 

# ==========================================
# 3. 模拟训练结束 (记录最终非时间结果)
# ==========================================
print("🏆 训练结束，记录最终结果...")
for algo, writer in writers:
    # 假设 SAC 的成功率稍高一些
    base_success = 0.7 if algo == "PPO" else 0.9
    final_success_rate = base_success + random.uniform(-0.1, 0.1)
    
    # 记录单个数值，生成带误差棒的柱状图
    writer.add_summary("Metrics/Final_Success_Rate", final_success_rate)
    
    # 安全关闭，确保所有数据刷入硬盘
    writer.close()

print("✅ 全部完成！")
print("请在终端运行： easyboard --logdir=example_logs")