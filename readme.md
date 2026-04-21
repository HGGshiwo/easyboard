# EasyBoard 📊

**A lightweight, pure-local, and interactive experiment tracking dashboard with automatic mean & variance plotting.**

Designed specifically for researchers in **Robotics (ROS), Reinforcement Learning (RL), and Machine Learning**, where running multiple random seeds and comparing groups locally is a daily routine. 

EasyBoard gives you the simplicity of TensorBoard and the powerful grouping/config-tracking features of WandB, without any cloud dependencies or environment conflicts.

## ✨ Key Features

*   **Native Grouping & Seeds**: Built-in support for `group` and `seed`. It automatically aggregates multiple seeds within the same group and plots the **mean curve with a 95% variance/std shaded area**.
*   **WandB-like Config Tracking**: Easily log your hyperparameters and notes. The dashboard automatically parses them into an interactive, sortable comparison table.
*   **Interactive UI (Plotly)**: Hover over curves to see exact mean and std values across all groups simultaneously. Drag to zoom, click legends to toggle visibility, and export to HD images effortlessly.
*   **High Performance**: Implements a smart I/O buffer (size and time-based flushing) to ensure zero bottleneck on high-frequency loops (e.g., ROS control nodes).
*   **Pure Local & 0-Risk**: Built entirely on standard Python libraries. No C++ compiling (like `aimrocks`), no cloud sync, safe for legacy environments like ROS Noetic on Ubuntu 20.04.

---

## 🛠️ Installation

```bash
pip install git+https://github.com/HGGshiwo/easyboard.git
```

---

## 🚀 Quick Start

### 1. Logging Data in Your Code

Using EasyBoard is almost identical to using TensorBoard's API, but with native support for grouping and configs.

```python
from easyboard import SummaryWriter
import random

# 1. Initialize the writer with Group and Seed
writer = SummaryWriter(log_dir="my_logs", group="Ours_Improved", seed=1)

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

Open your terminal and run the CLI command provided by EasyBoard:

```bash
easyboard --logdir=my_logs
```

*(Optional: You can specify the port using `--port 8080`)*

The terminal will provide a local URL (e.g., `http://localhost:8501`). Open it in your browser to view the interactive dashboard.

---

## 🖥️ Dashboard Overview

Once the dashboard is open, you will see:

1.  **Sidebar Filters**: Easily toggle the visibility of different `groups` using checkboxes.
2.  **Configurations Table**: An interactive Pandas dataframe parsing all your `add_config` calls. You can click headers to sort (e.g., sort by learning rate) to quickly find the best parameters.
3.  **Time-Series Metrics**: Line charts powered by Plotly. 
    *   It automatically merges data with the same `tag` and `group` across different `seed`s.
    *   Hovering your mouse displays a unified vertical tooltip showing exact **Mean ± Std** for all active groups.
4.  **Summary Metrics**: Bar charts for non-sequential data (like final accuracy or total distance). Automatically calculates means and draws black error bars for standard deviation.
5.  **Force Refresh**: A dedicated button in the sidebar to bypass cache and instantly load the freshest data from your disk while experiments are still running.

---

## ⚙️ Advanced Configuration (High-Frequency Logging)

If you are logging at extreme frequencies (e.g., 500Hz in ROS), you can adjust the flush buffer to minimize disk I/O:

```python
# flush_size: Flush to disk every 5000 items
# flush_secs: Or flush every 5 seconds, whichever comes first
writer = SummaryWriter(
    log_dir="my_logs", 
    group="Exp_A", 
    seed=1, 
    flush_size=5000, 
    flush_secs=5.0
)
```
This guarantees that your main control thread will never be blocked by hard drive write speeds.