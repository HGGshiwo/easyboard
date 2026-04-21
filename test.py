import time

from easyboard import SummaryWriter
writer1 = SummaryWriter(log_dir="test_logs", group="test_group")
writer2 = SummaryWriter(log_dir="test_logs", group="test_group2")
writer3 = SummaryWriter(log_dir="test_logs", group="test_group3")

for step in range(1000):
    for i in range(10):
        writer1.add_scalar(f"test_metric{i}", step * 0.1, step)
        writer2.add_scalar(f"test_metric{i}", step * 0.1, step)
        writer3.add_scalar(f"test_metric{i}", step * 0.1, step)
    
    time.sleep(0.5)
    