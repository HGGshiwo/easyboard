import json

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import glob

# === 页面基础配置 ===
st.set_page_config(layout="wide", page_title="Experiment Dashboard")


def hex_to_rgba(hex_color, opacity=0.2):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {opacity})"
    return hex_color


@st.cache_data(ttl=2)
def load_data(base_dir="my_ros_logs"):
    base_dir = os.environ.get("EASYBOARD_LOGDIR", "logs")
    files = glob.glob(os.path.join(base_dir, "*", "*", "metrics.csv"))
    if not files:
        return None
    df_list = []
    for f in files:
        parts = f.split(os.sep)
        df = pd.read_csv(f)
        df["group"] = parts[-3]
        df["seed"] = parts[-2]
        df_list.append(df)
    return pd.concat(df_list, ignore_index=True)


# ================= 新增：解析所有的 config.json =================
@st.cache_data(ttl=2)
def load_configs():
    base_dir = os.environ.get('EASYBOARD_LOGDIR', 'logs')
    files = glob.glob(os.path.join(base_dir, "*", "*", "config.json"))
    if not files: return pd.DataFrame()
    
    data = []
    for f in files:
        parts = f.split(os.sep)
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                cfg = json.load(fp)
                cfg['group'] = parts[-3]
                cfg['seed'] = parts[-2]
                data.append(cfg)
        except:
            pass
    return pd.DataFrame(data)

df = load_data()
df_configs = load_configs() # 读取超参数

# === 顶部标题 ===
st.title("Experiment Analysis Dashboard")

if df is None or df.empty:
    st.warning("No data found in log directory. Please check the data path.")
    st.stop()

# === 侧边栏：直接平铺的复选框列表 ===
st.sidebar.header("Data Filters")
if st.sidebar.button("🔄 Force Refresh"):
    st.cache_data.clear()  # 强行清空 Streamlit 的读取缓存
    st.rerun()  # 强行重新运行整个网页脚本读取最新硬盘数据

st.sidebar.subheader("Select Groups:")

all_groups = df["group"].unique().tolist()
selected_groups = []

# 直接列出所有组，并带有复选框，默认全部勾选
for grp in all_groups:
    if st.sidebar.checkbox(grp, value=True):
        selected_groups.append(grp)

if not selected_groups:
    st.info("Please select at least one group from the sidebar.")
    st.stop()
    
# ================= 新增 UI：参数对比表格 =================
df_filtered = df[df["group"].isin(selected_groups)]
colors = px.colors.qualitative.Plotly

if not df_configs.empty:
    st.header("Experiment Configurations")
    st.markdown("---")
    # 按照左侧边栏选中的组进行过滤
    df_cfg_filtered = df_configs[df_configs['group'].isin(selected_groups)]
    if not df_cfg_filtered.empty:
        # 把 group 和 seed 这两列移动到最前面，方便查看
        cols = ['group', 'seed'] + [c for c in df_cfg_filtered.columns if c not in ['group', 'seed']]
        df_cfg_filtered = df_cfg_filtered[cols]
        
        # 使用 Streamlit 的交互式表格展示（支持点击表头排序、拖拽调整列宽！）
        st.dataframe(df_cfg_filtered, use_container_width=True, hide_index=True)
    
# === 模块 1：时间序列数据 ===
df_scalar = df_filtered[df_filtered["type"] == "scalar"]

if not df_scalar.empty:
    st.header("Time-Series Metrics")
    st.markdown("---")  # 分割线

    scalar_tags = df_scalar["tag"].unique()
    cols = st.columns(2)

    for i, tag in enumerate(scalar_tags):
        with cols[i % 2]:
            fig = go.Figure()
            tag_data = df_scalar[df_scalar["tag"] == tag]

            agg_data = (
                tag_data.groupby(["group", "step"])["value"]
                .agg(["mean", "std"])
                .reset_index()
            )
            agg_data["std"] = agg_data["std"].fillna(0)

            for j, grp in enumerate(selected_groups):
                grp_data = agg_data[agg_data["group"] == grp]
                if grp_data.empty:
                    continue

                x = grp_data["step"]
                y_mean = grp_data["mean"]
                y_std = grp_data["std"]
                y_upper = y_mean + y_std
                y_lower = y_mean - y_std

                base_color = colors[j % len(colors)]
                fill_color = hex_to_rgba(base_color, 0.2)

                # 方差阴影
                fig.add_trace(
                    go.Scatter(
                        x=pd.concat([x, x[::-1]]),
                        y=pd.concat([y_upper, y_lower[::-1]]),
                        fill="toself",
                        fillcolor=fill_color,
                        line=dict(color="rgba(255,255,255,0)"),
                        hoverinfo="skip",
                        showlegend=False,
                    )
                )

                # 均值实线
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=y_mean,
                        mode="lines",
                        name=grp,
                        line=dict(color=base_color, width=2),
                        hovertemplate=(
                            f"<b>{grp}</b><br>"
                            + "Step: %{x}<br>"
                            + "Mean: %{y:.4f}<br>"
                            + "Std: ±%{customdata:.4f}<extra></extra>"
                        ),
                        customdata=y_std,
                    )
                )

            fig.update_layout(
                title=dict(text=tag, font=dict(size=16)),
                hovermode="x unified",
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
            )
            st.plotly_chart(fig, use_container_width=True)

# === 模块 2：非时间总结数据 ===
df_summary = df_filtered[df_filtered["type"] == "summary"]

if not df_summary.empty:
    st.header("Summary Metrics")
    st.markdown("---")
    
    summary_tags = df_summary["tag"].unique()
    cols2 = st.columns(len(summary_tags) if len(summary_tags) > 0 else 1)

    for i, tag in enumerate(summary_tags):
        with cols2[i]:
            tag_data = df_summary[df_summary["tag"] == tag]

            agg_data = (
                tag_data.groupby("group")["value"].agg(["mean", "std"]).reset_index()
            )
            agg_data["std"] = agg_data["std"].fillna(0)

            fig = px.bar(
                agg_data,
                x="group",
                y="mean",
                color="group",
                error_y="std",
                color_discrete_sequence=colors,
            )

            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>Mean: %{y:.4f}<br>Std: ±%{customdata[0]:.4f}<extra></extra>",
                customdata=agg_data[["std"]],
            )
            fig.update_layout(
                title=dict(text=tag, font=dict(size=16)),
                showlegend=False,
                xaxis_title="",
                yaxis_title="",
                margin=dict(l=20, r=20, t=40, b=20),
            )

            st.plotly_chart(fig, use_container_width=True)
