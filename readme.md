# EasyBoard 📊

**A lightweight, pure-local, and interactive experiment tracking dashboard with tag-based grouping and automatic variance plotting.**

Designed specifically for researchers in **Robotics (ROS), Reinforcement Learning (RL), and Machine Learning**, where running multiple random seeds and comparing distinct groups locally is a daily routine. 

EasyBoard gives you the simplicity of TensorBoard and the powerful grouping/config-tracking features of WandB, without any cloud dependencies, rigid folder structures, or environment conflicts.

## ✨ Key Features

*   **Powerful Tag-Based Grouping**: Say goodbye to rigid directory parsing. Grouping and filtering are now entirely driven by `tags`. You can automatically group runs by shared tags or explicitly define custom groups on the fly.
*   **Automatic Aggregation**: Easily aggregate multiple seeds. The dashboard automatically plots the **mean curve with a standard deviation shaded area** for overlapping runs.
*   **WandB-like Config Tracking**: Easily log your hyperparameters and notes. The dashboard parses them into an interactive, sortable comparison table mapped to your current groups.
*   **Robust File Management**: Metric files are safely timestamped (`metrics_<timestamp>.csv`). This natively supports resumed runs or overlapping processes without overwriting previous data.
*   **Interactive UI (Plotly)**: Hover over curves to see exact Mean ± Std values across all groups simultaneously. Drag to zoom, click legends to toggle visibility, and export to HD images effortlessly.
*   **High Performance**: Implements a smart I/O buffer (size and time-based flushing) to ensure zero bottlenecks on high-frequency loops (e.g., ROS control nodes).
*   **Pure Local & 0-Risk**: Built entirely on standard Python libraries. No C++ compiling, no cloud sync, safe for legacy environments.

---

## 🛠️ Installation

```bash
pip install git+https://github.com/HGGshiwo/easyboard.git
```

---

## 🚀 Quick Start

### 1. Logging Data in Your Code

`log_dir` is now strictly for physical storage. To identify and group your experiments, use the `tags` list.

```python
from easyboard import SummaryWriter
import random

# 1. Initialize the writer. 
# log_dir is just where files are saved. tags dictate how data is grouped!
writer = SummaryWriter(
    log_dir="my_logs/experiment_1_resumed", 
    tags=["Ours_Improved", "lr_0.001", "seed_1"]
)

# 2. Log Hyperparameters (Configurations)
config = {
    "learning_rate": 0.001,
    "map_name": "warehouse_v2",
    "use_lidar": True,
    "notes": "Added integral term to PID controller"
}
writer.add_config(config)

# 3. Log Time-Series Data (Scalars in loops)
for step in range(100):
    loss = 2.0 / (step + 1) + random.uniform(0, 0.2)

    # Very fast! Data is buffered in memory and flushed asynchronously.
    writer.add_scalar("Train/Loss", loss, step)
    writer.add_scalar("Train/Speed", random.uniform(1.0, 1.5), step)

# 4. Log Episodic/Summary Data (Final results without a step)
success_rate = 0.95
writer.add_summary("Result/Success_Rate", success_rate)
```

### 2. Starting the Dashboard

Open your terminal and run the CLI command:

```bash
easyboard --logdir=my_logs
```

*(Optional: You can specify the port using `--port 8080`)*

The terminal will provide a local URL (e.g., `http://localhost:8501`). Open it in your browser to view the interactive dashboard.

---

## 🖥️ Dashboard Overview

The UI is designed for maximum analytical efficiency:

*   **Top Bar - Quick Refresh**: A dedicated `Refresh Data` button sits right next to the title. Click it to bypass the cache and instantly load the freshest data while experiments are running.
*   **Sidebar 1: Grouping Configuration**: 
    *   *Auto Group by Tags*: Automatically merges runs that share the exact specific tags you select.
    *   *Custom Groups*: Dynamically define multiple groups using the `+ Add Group` and `Del` buttons. Specify required tags for each group. (Note: If a run satisfies multiple groups, it is automatically calculated independently for both!)
*   **Sidebar 2: Data Filtering**: Apply a global AND-logic filter. Only runs containing *all* selected tags will be evaluated.
*   **Sidebar 3: Experiments List**: A comprehensive list of all detected runs and their tags. Selections automatically sync with your Global Filters, but you can manually check/uncheck specific runs to include or exclude them from calculations.
*   **Main View**: 
    *   **Configurations**: An interactive DataFrame matching your active groups.
    *   **Time-Series Metrics**: Auto-aggregated line charts (Mean ± Std shadow) based on your grouping rules.
    *   **Summary Metrics**: Bar charts with error bars for non-sequential data.

---

## ⚙️ Advanced Configuration (High-Frequency Logging)

If you are logging at extreme frequencies (e.g., 500Hz in ROS), you can adjust the flush buffer to minimize disk I/O:

```python
# flush_size: Flush to disk every 5000 items
# flush_secs: Or flush every 5 seconds, whichever comes first
writer = SummaryWriter(
    log_dir="my_logs/fast_run", 
    tags=["Baseline", "500Hz"], 
    flush_size=5000, 
    flush_secs=5.0
)
```
This guarantees that your main control thread will never be blocked by hard drive write speeds.