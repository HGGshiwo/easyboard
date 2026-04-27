import glob
import json
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# === Page Configuration ===
st.set_page_config(layout="wide", page_title="EasyBoard Analytics")

# --- Session State Initialization for Dynamic Groups ---
if "group_counter" not in st.session_state:
    st.session_state.group_counter = 1
if "custom_groups_state" not in st.session_state:
    # Initialize with one empty group
    st.session_state.custom_groups_state = [{"id": 0}]


def hex_to_rgba(hex_color, opacity=0.2):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {opacity})"
    return hex_color


@st.cache_data(ttl=2)
def load_data(base_dir):
    files = glob.glob(os.path.join(base_dir, "**", "metrics_*.csv"), recursive=True)
    if not files:
        return pd.DataFrame(), pd.DataFrame(), [], {}

    runs_data = []
    configs_data = []
    all_tags = set()
    run_dict = {}

    dir_to_files = {}
    for f in files:
        d = os.path.dirname(f)
        dir_to_files.setdefault(d, []).append(f)

    for d, fs in dir_to_files.items():
        meta_path = os.path.join(d, "run_meta.json")
        run_tags = []
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as m:
                    meta = json.load(m)
                    run_tags = meta.get("tags", [])
            except Exception:
                pass

        for t in run_tags:
            all_tags.add(t)

        run_dict[d] = run_tags

        df_list = []
        for f in fs:
            try:
                temp_df = pd.read_csv(f)
                if "tag" in temp_df.columns:
                    temp_df.rename(columns={"tag": "metric_name"}, inplace=True)
                df_list.append(temp_df)
            except Exception:
                pass

        if df_list:
            run_df = pd.concat(df_list, ignore_index=True)
            run_df["log_dir"] = d
            run_df["run_tags"] = [tuple(run_tags)] * len(run_df)
            runs_data.append(run_df)

        config_path = os.path.join(d, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as c:
                    cfg = json.load(c)
                    cfg["log_dir"] = d
                    cfg["run_tags"] = ", ".join(run_tags)
                    configs_data.append(cfg)
            except Exception:
                pass

    if not runs_data:
        return pd.DataFrame(), pd.DataFrame(), [], {}

    df = pd.concat(runs_data, ignore_index=True)
    df_configs = pd.DataFrame(configs_data) if configs_data else pd.DataFrame()
    return df, df_configs, sorted(list(all_tags)), run_dict


base_dir = os.environ.get("EASYBOARD_LOGDIR", "logs")
df, df_configs, all_tags, run_dict = load_data(base_dir)

# ================= Top Bar: Title & Refresh Button =================
col_title, col_btn = st.columns([0.88, 0.12])
with col_title:
    st.title("EasyBoard Analytics")
with col_btn:
    # Adding margin to vertically align the button with the title
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if df.empty:
    st.warning("No data found. Please run your experiments first.")
    st.stop()


# ================= Sidebar: Controls & Logic =================

# --- 1. Grouping Engine ---
st.sidebar.subheader("1. Grouping Configuration")
group_mode = st.sidebar.radio(
    "Grouping Mode",
    ["Custom Groups", "Auto Group by Tags"],
    label_visibility="collapsed",
)

groupby_tags = []
custom_groups = []

if group_mode == "Auto Group by Tags":
    st.sidebar.caption("Exact tag matches will be grouped automatically.")
    groupby_tags = st.sidebar.multiselect("Select Tags for Auto Group", all_tags)
else:
    st.sidebar.caption("Define group name (left) and required tags (center).")

    # Iterate over dynamic state to render rows
    for i, grp in enumerate(st.session_state.custom_groups_state):
        gid = grp["id"]
        c1, c2, c3 = st.sidebar.columns([3, 5, 1.5])

        with c1:
            g_name = st.text_input(
                "Name",
                f"Group_{i+1}",
                key=f"g_name_{gid}",
                label_visibility="collapsed",
            )
        with c2:
            g_tags = st.multiselect(
                "Tags", all_tags, key=f"g_tags_{gid}", label_visibility="collapsed"
            )
        with c3:
            # Delete button
            if st.button("Del", key=f"del_{gid}", use_container_width=True):
                # Remove the item from session state and rerun
                st.session_state.custom_groups_state = [
                    g for g in st.session_state.custom_groups_state if g["id"] != gid
                ]
                st.rerun()

        custom_groups.append({"name": g_name, "tags": set(g_tags)})

    # Add Group Button
    if st.sidebar.button("+ Add Group", use_container_width=True):
        st.session_state.group_counter += 1
        st.session_state.custom_groups_state.append(
            {"id": st.session_state.group_counter}
        )
        st.rerun()

show_ungrouped = st.sidebar.checkbox("Show Ungrouped Runs", value=True)

st.sidebar.markdown("---")

# --- 2. Filtering Engine ---
st.sidebar.subheader("2. Data Filtering")
st.sidebar.caption("Runs containing these tags will be selected by default.")
global_filter_tags = st.sidebar.multiselect("Filter by Tags (AND Logic):", all_tags)

st.sidebar.markdown("---")

# --- 3. Experiment List Selection ---
st.sidebar.subheader("3. Experiments")
st.sidebar.caption("Manually include or exclude specific runs.")

selected_runs = []
for log_dir, tags in run_dict.items():
    matches_filter = (
        set(global_filter_tags).issubset(set(tags)) if global_filter_tags else True
    )
    display_name = f"{os.path.basename(log_dir)} {tags}"

    if st.sidebar.checkbox(display_name, value=matches_filter, key=f"chk_{log_dir}"):
        selected_runs.append(log_dir)

if not selected_runs:
    st.info("No runs selected. Please select runs from the sidebar.")
    st.stop()


# ================= Data Processing =================
df_filtered = df[df["log_dir"].isin(selected_runs)].copy()


def get_groups(run_tags_tuple):
    run_tags = set(run_tags_tuple)
    if group_mode == "Auto Group by Tags":
        if not groupby_tags:
            return ["All Runs"]
        overlap = sorted(list(run_tags.intersection(set(groupby_tags))))
        return ["_".join(overlap)] if overlap else ["Ungrouped"]
    else:
        assigned = []
        for g in custom_groups:
            if not g["tags"]:
                continue
            if g["tags"].issubset(run_tags):
                assigned.append(g["name"])
        return assigned if assigned else ["Ungrouped"]


df_filtered["group_name"] = df_filtered["run_tags"].apply(get_groups)

# Explode expands lists into multiple rows for overlapping groups
df_filtered = df_filtered.explode("group_name")

if not show_ungrouped:
    df_filtered = df_filtered[df_filtered["group_name"] != "Ungrouped"]

if df_filtered.empty:
    st.info("No data available after grouping logic.")
    st.stop()

colors = px.colors.qualitative.Plotly


# ================= Main View Rendering =================

# --- Module 1: Configurations ---
st.header("Configurations")
if not df_configs.empty:
    df_cfg_filtered = df_configs[df_configs["log_dir"].isin(selected_runs)].copy()
    if not df_cfg_filtered.empty:
        cols = ["log_dir", "run_tags"] + [
            c for c in df_cfg_filtered.columns if c not in ["log_dir", "run_tags"]
        ]
        st.dataframe(df_cfg_filtered[cols], use_container_width=True, hide_index=True)
else:
    st.info("No configurations logged.")

st.markdown("---")

# --- Module 2: Time-Series Metrics ---
st.header("Time-Series Metrics")
df_scalar = df_filtered[df_filtered["type"] == "scalar"]

if not df_scalar.empty:
    metric_names = df_scalar["metric_name"].unique()
    cols = st.columns(2)

    for i, metric in enumerate(metric_names):
        with cols[i % 2]:
            fig = go.Figure()
            metric_data = df_scalar[df_scalar["metric_name"] == metric]

            agg_data = (
                metric_data.groupby(["group_name", "step"])["value"]
                .agg(["mean", "std"])
                .reset_index()
            )
            agg_data["std"] = agg_data["std"].fillna(0)

            unique_groups = sorted(agg_data["group_name"].unique())
            for j, grp in enumerate(unique_groups):
                grp_data = agg_data[agg_data["group_name"] == grp].sort_values("step")

                x = grp_data["step"]
                y_mean = grp_data["mean"]
                y_std = grp_data["std"]

                base_color = colors[j % len(colors)]

                if y_std.max() > 0:
                    fill_color = hex_to_rgba(base_color, 0.2)
                    y_upper = y_mean + y_std
                    y_lower = y_mean - y_std
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

                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=y_mean,
                        mode="lines",
                        name=grp,
                        line=dict(color=base_color, width=2),
                        hovertemplate=(
                            f"<b>{grp}</b><br>Step: %{{x}}<br>Mean: %{{y:.4f}}<br>Std: ±%{{customdata:.4f}}<extra></extra>"
                        ),
                        customdata=y_std,
                    )
                )

            fig.update_layout(
                title=dict(text=metric, font=dict(size=16)),
                hovermode="x unified",
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
            )
            st.plotly_chart(fig, use_container_width=True)

# --- Module 3: Summary Metrics ---
st.markdown("---")
st.header("Summary Metrics")
df_summary = df_filtered[df_filtered["type"] == "summary"]

if not df_summary.empty:
    summary_metrics = df_summary["metric_name"].unique()
    cols2 = st.columns(len(summary_metrics) if len(summary_metrics) > 0 else 1)

    for i, metric in enumerate(summary_metrics):
        with cols2[i % len(cols2)]:
            metric_data = df_summary[df_summary["metric_name"] == metric]
            agg_data = (
                metric_data.groupby("group_name")["value"]
                .agg(["mean", "std"])
                .reset_index()
            )
            agg_data["std"] = agg_data["std"].fillna(0)

            fig = px.bar(
                agg_data,
                x="group_name",
                y="mean",
                color="group_name",
                error_y="std",
                color_discrete_sequence=colors,
            )
            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>Mean: %{y:.4f}<br>Std: ±%{customdata[0]:.4f}<extra></extra>",
                customdata=agg_data[["std"]],
            )
            fig.update_layout(
                title=dict(text=metric, font=dict(size=16)),
                showlegend=False,
                xaxis_title="",
                yaxis_title="Value",
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
