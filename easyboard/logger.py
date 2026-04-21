import os
import csv
import time
import atexit
import json


class SummaryWriter:
    def __init__(
        self,
        log_dir="logs",
        run_path="default_exp/seed_0",
        flush_size=1000,
        flush_secs=2.0,
    ):
        """
        :param run_path: 支持任意深度的相对路径！例如 "ResNet/CIFAR/lr_0.01/seed_1"
        """
        # 自动解析层级目录
        self.dir = os.path.join(log_dir, run_path)
        os.makedirs(self.dir, exist_ok=True)
        self.csv_path = os.path.join(self.dir, "metrics.csv")
        self.config_path = os.path.join(self.dir, "config.json")

        self.buffer = []
        self.flush_size = flush_size
        self.flush_secs = flush_secs
        self.last_flush_time = time.time()

        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "type", "tag", "step", "value"])

        atexit.register(self.flush)

    def add_config(self, config_dict):
        existing_config = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    existing_config = json.load(f)
            except:
                pass
        existing_config.update(config_dict)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(existing_config, f, indent=4, ensure_ascii=False)

    def add_scalar(self, tag, value, step):
        self.buffer.append([time.time(), "scalar", tag, step, float(value)])
        self._check_flush()

    def add_summary(self, tag, value):
        self.buffer.append([time.time(), "summary", tag, -1, float(value)])
        self._check_flush()

    def _check_flush(self):
        if (
            len(self.buffer) >= self.flush_size
            or (time.time() - self.last_flush_time) >= self.flush_secs
        ):
            self.flush()

    def flush(self):
        if not self.buffer:
            return
        with open(self.csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(self.buffer)
        self.buffer.clear()
        self.last_flush_time = time.time()

    def close(self):
        self.flush()
        atexit.unregister(self.flush)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
