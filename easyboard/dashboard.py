import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import glob
import json

# === 页面配置 ===
st.set_page_config(layout="wide", page_title="EasyBoard Analytics")

def hex_to_rgba(hex_color, opacity=0.2):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'rgba({r}, {g}, {b}, {opacity})'
    return hex_color

@st.cache_data(ttl=2)
def load_data(base_dir):
    files = glob.glob(os.path.join(base_dir, "**", "metrics.csv"), recursive=True)
    if not files: return None
    
    df_list = []
    for f in files:
        dir_path = os.path.dirname(f)
        # 获取相对路径，并统一替换为正斜杠 '/'，例如 "PPO/Warehouse/lr_0.01/seed_1"
        rel_path = os.path.relpath(dir_path, base_dir).replace('\\', '/')
        if rel_path == '.': rel_path = 'Root'
        
        df = pd.read_csv(f)
        df['rel_path'] = rel_path
        
        # 为了方便左侧树状菜单展示，拆分出“父目录”和“最终运行名(如seed)”
        df['parent_path'] = os.path.dirname(rel_path) if '/' in rel_path else 'Root'
        df['run_name'] = os.path.basename(rel_path)
        
        df_list.append(df)
    return pd.concat(df_list, ignore_index=True)

@st.cache_data(ttl=2)
def load_configs(base_dir):
    files = glob.glob(os.path.join(base_dir, "**", "config.json"), recursive=True)
    if not files: return pd.DataFrame()
    data = []
    for f in files:
        dir_path = os.path.dirname(f)
        rel_path = os.path.relpath(dir_path, base_dir).replace('\\', '/')
        if rel_path == '.': rel_path = 'Root'
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                cfg = json.load(fp)
                cfg['rel_path'] = rel_path
                data.append(cfg)
        except: pass
    return pd.DataFrame(data)

base_dir = os.environ.get('EASYBOARD_LOGDIR', 'logs')
df = load_data(base_dir)
df_configs = load_configs(base_dir)

st.title("📊 EasyBoard Analytics")

if df is None or df.empty:
    st.warning("📭 No data found. Please run your experiments first.")
    st.stop()

# ================= 侧边栏：全局控制台 =================
st.sidebar.header("Global Controls")
if st.sidebar.button("🔄 Force Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# --- 核心魔法 1：动态聚合层级控制器 ---
st.sidebar.subheader("1. Aggregation Level")
# st.sidebar.caption("选择在目录的哪一层计算均值和方差")

# 计算所有路径中的最大深度 (根据 '/' 的数量)
max_depth = int(df['rel_path'].apply(lambda x: len(x.split('/'))).max())

# 动态生成聚合选项
agg_options = {}
sample_path = df['rel_path'].iloc[0].split('/')
for depth in range(1, max_depth):
    example = "/".join(sample_path[:depth])
    agg_options[depth] = f"Level {depth} (e.g., {example})"
agg_options[max_depth] = f"Level {max_depth} (No Aggregation)"

# 全局聚合深度选择器
selected_depth = st.sidebar.radio(
    "Group by directory depth:",
    options=list(agg_options.keys()),
    format_func=lambda x: agg_options[x],
    index=max_depth - 2 if max_depth > 1 else 0 # 默认聚合倒数第二层 (通常是相同参数的不同seed)
)

st.sidebar.markdown("---")

# --- 核心魔法 2：树状剔除菜单 (只做筛选，不干预聚合) ---
st.sidebar.subheader("2. Run Filters")
# st.sidebar.caption("取消勾选以剔除异常数据")

selected_runs_paths = []
# 按父目录归类来生成折叠菜单
all_parents = sorted(df['parent_path'].unique().tolist())

for parent in all_parents:
    with st.sidebar.expander(f"📁 {parent}", expanded=True):
        runs = sorted(df[df['parent_path'] == parent]['run_name'].unique().tolist())
        for r in runs:
            # Checkbox的默认状态为 True
            if st.checkbox(f"📄 {r}", value=True, key=f"chk_{parent}_{r}"):
                # 如果选中，则将该运行的完整相对路径加入白名单
                full_path = f"{parent}/{r}" if parent != 'Root' else r
                selected_runs_paths.append(full_path)

if not selected_runs_paths:
    st.info("Please select at least one run from the sidebar.")
    st.stop()

# 1. 物理剔除未选中的数据
df_filtered = df[df['rel_path'].isin(selected_runs_paths)].copy()

# 2. 核心魔法 3：根据选择的 depth，动态截取路径作为画图的 Label (Group By 的 Key)
def generate_plot_label(path, depth):
    parts = path.split('/')
    if depth >= len(parts): return path
    return "/".join(parts[:depth])

df_filtered['plot_label'] = df_filtered['rel_path'].apply(lambda x: generate_plot_label(x, selected_depth))

colors = px.colors.qualitative.Plotly

# ================= 主界面：图表渲染 =================

# --- 模块 1：Config 参数表 ---
st.header("📝 Configurations")
if not df_configs.empty:
    df_cfg_filtered = df_configs[df_configs['rel_path'].isin(selected_runs_paths)].copy()
    if not df_cfg_filtered.empty:
        # 为了方便看，加上当前聚合的标签
        df_cfg_filtered['Belongs_to_Group'] = df_cfg_filtered['rel_path'].apply(lambda x: generate_plot_label(x, selected_depth))
        cols = ['Belongs_to_Group', 'rel_path'] + [c for c in df_cfg_filtered.columns if c not in ['Belongs_to_Group', 'rel_path']]
        st.dataframe(df_cfg_filtered[cols], use_container_width=True, hide_index=True)
else:
    st.info("No configurations logged.")

st.markdown("---")

# --- 模块 2：时间序列 (动态均值与方差阴影) ---
st.header("📈 Time-Series Metrics")
df_scalar = df_filtered[df_filtered['type'] == 'scalar']

if not df_scalar.empty:
    scalar_tags = df_scalar['tag'].unique()
    cols = st.columns(2)
    
    for i, tag in enumerate(scalar_tags):
        with cols[i % 2]:
            fig = go.Figure()
            tag_data = df_scalar[df_scalar['tag'] == tag]
            
            # 使用我们刚刚动态生成的 plot_label 进行统计聚合
            agg_data = tag_data.groupby(['plot_label', 'step'])['value'].agg(['mean', 'std']).reset_index()
            agg_data['std'] = agg_data['std'].fillna(0)
            
            unique_labels = sorted(agg_data['plot_label'].unique())
            for j, label in enumerate(unique_labels):
                lbl_data = agg_data[agg_data['plot_label'] == label]
                
                x = lbl_data['step']
                y_mean = lbl_data['mean']
                y_std = lbl_data['std']
                
                base_color = colors[j % len(colors)]
                
                # 如果方差 > 0 (说明这条线融合了多个数据源)，则画半透明阴影
                if y_std.max() > 0:
                    fill_color = hex_to_rgba(base_color, 0.2)
                    y_upper = y_mean + y_std
                    y_lower = y_mean - y_std
                    fig.add_trace(go.Scatter(
                        x=pd.concat([x, x[::-1]]), y=pd.concat([y_upper, y_lower[::-1]]),
                        fill='toself', fillcolor=fill_color, line=dict(color='rgba(255,255,255,0)'),
                        hoverinfo="skip", showlegend=False
                    ))
                
                # 画主线
                fig.add_trace(go.Scatter(
                    x=x, y=y_mean, mode='lines', name=label, line=dict(color=base_color, width=2),
                    hovertemplate=(f"<b>{label}</b><br>Step: %{{x}}<br>Mean: %{{y:.4f}}<br>Std: ±%{{customdata:.4f}}<extra></extra>"),
                    customdata=y_std
                ))
                
            fig.update_layout(
                title=dict(text=tag, font=dict(size=16)), hovermode="x unified",
                margin=dict(l=20, r=20, t=40, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

# --- 模块 3：非时间柱状图 (动态误差棒) ---
st.markdown("---")
st.header("🏆 Summary Metrics")
df_summary = df_filtered[df_filtered['type'] == 'summary']

if not df_summary.empty:
    summary_tags = df_summary['tag'].unique()
    cols2 = st.columns(len(summary_tags) if len(summary_tags) > 0 else 1)
    
    for i, tag in enumerate(summary_tags):
        with cols2[i]:
            tag_data = df_summary[df_summary['tag'] == tag]
            agg_data = tag_data.groupby('plot_label')['value'].agg(['mean', 'std']).reset_index()
            agg_data['std'] = agg_data['std'].fillna(0)
            
            fig = px.bar(
                agg_data, x='plot_label', y='mean', color='plot_label', error_y='std',
                color_discrete_sequence=colors
            )
            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>Mean: %{y:.4f}<br>Std: ±%{customdata[0]:.4f}<extra></extra>",
                customdata=agg_data[['std']]
            )
            fig.update_layout(
                title=dict(text=tag, font=dict(size=16)), showlegend=False, 
                xaxis_title="", yaxis_title="Value", margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)