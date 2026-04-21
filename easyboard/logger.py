import json
import os
import csv
import time
import atexit

class SummaryWriter:
    def __init__(self, log_dir="logs", group="default", seed="0", flush_size=1000, flush_secs=2.0):
        """
        :param flush_size: 缓冲区大小（条数触发）
        :param flush_secs: 强制刷新时间间隔（时间触发）。默认2秒。
        """
        self.dir = os.path.join(log_dir, str(group), f"seed_{seed}")
        os.makedirs(self.dir, exist_ok=True)
        self.csv_path = os.path.join(self.dir, "metrics.csv")
        self.config_path = os.path.join(self.dir, "config.json")
        
        self.buffer = []
        self.flush_size = flush_size
        self.flush_secs = flush_secs
        self.last_flush_time = time.time()  # 记录上次刷新的时间

        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "type", "tag", "step", "value"])

        atexit.register(self.flush)
    
    def add_config(self, config_dict):
        """
        记录实验超参数或备注信息。支持多次调用，会自动合并更新。
        """
        existing_config = {}
        # 如果之前存过，先读出来
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
            except:
                pass
        
        # 更新并覆盖写入
        existing_config.update(config_dict)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(existing_config, f, indent=4, ensure_ascii=False)
            
    def add_scalar(self, tag, value, step):
        self.buffer.append([time.time(), "scalar", tag, step, float(value)])
        self._check_flush()

    def add_summary(self, tag, value):
        self.buffer.append([time.time(), "summary", tag, -1, float(value)])
        self._check_flush()

    def _check_flush(self):
        """检查是否需要刷新（双重条件）"""
        # 条件1：缓冲区满了
        # 条件2：虽然没满，但距离上次刷新已经超过了设定的秒数 (比如 2 秒)
        if len(self.buffer) >= self.flush_size or (time.time() - self.last_flush_time) >= self.flush_secs:
            self.flush()

    def flush(self):
        if not self.buffer:
            return
            
        with open(self.csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(self.buffer)
            
        self.buffer.clear()
        self.last_flush_time = time.time() # 更新最后一次刷新的时间

    def close(self):
        self.flush()
        atexit.unregister(self.flush)

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()