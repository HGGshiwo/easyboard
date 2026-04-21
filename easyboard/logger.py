import os
import csv
import time
import atexit
import json
from datetime import datetime

class SummaryWriter:
    def __init__(
        self,
        log_dir="logs/default_exp",
        tags=None,
        flush_size=1000,
        flush_secs=2.0,
    ):
        """
        Initializes the SummaryWriter.
        
        :param log_dir: Absolute or relative path for storage (e.g., "logs/20231024_PPO").
                        This is only used for physical storage and does not affect grouping.
        :param tags: List of string tags to identify and group the run (e.g., ["PPO", "lr_0.01", "seed_1"]).
        """
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.tags = tags if tags is not None else []
        
        # Generate timestamped metric file for elegant file management
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path = os.path.join(self.log_dir, f"metrics_{timestamp_str}.csv")
        self.config_path = os.path.join(self.log_dir, "config.json")
        self.meta_path = os.path.join(self.log_dir, "run_meta.json")

        self.buffer = []
        self.flush_size = flush_size
        self.flush_secs = flush_secs
        self.last_flush_time = time.time()

        self._save_metadata()
        self._initialize_csv()

        atexit.register(self.flush)

    def _save_metadata(self):
        """Saves run tags to a meta file for the dashboard to read."""
        meta_data = {"tags": self.tags}
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=4, ensure_ascii=False)

    def _initialize_csv(self):
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                # Renamed 'tag' to 'metric_name' to avoid confusion with run tags
                writer.writerow(["timestamp", "type", "metric_name", "step", "value"])

    def add_config(self, config_dict):
        existing_config = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    existing_config = json.load(f)
            except Exception:
                pass
        
        existing_config.update(config_dict)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(existing_config, f, indent=4, ensure_ascii=False)

    def add_scalar(self, metric_name, value, step):
        self.buffer.append([time.time(), "scalar", metric_name, step, float(value)])
        self._check_flush()

    def add_summary(self, metric_name, value):
        self.buffer.append([time.time(), "summary", metric_name, -1, float(value)])
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