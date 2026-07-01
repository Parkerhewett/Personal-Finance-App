"""Reusable Plotly chart builders styled for the dark theme."""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


# -----------------------------------------------------------------------------
# Theme constants — keep all chart styling in one place
# -----------------------------------------------------------------------------
THEME = {
    "bg":          "rgba(0,0,0,0)",
    "font_color":  "#FAFAFA",
    "grid_color":  "#2A3145",
    "accent":      "#FFB81C",
    "income":      "#22C55E",   # green
    "expense":     "#EF4444",   # red
    "savings":     "#3B82F6",   # blue
    "tax":         "#F97316",   # orange
    "neutral":     "#6B7280",   # gray
}

# Color palette for category groups
GROUP_COLORS = {
    "Income":         "#22C55E",
    "Housing":        "#8B5CF6",
    "Food":           "#F59E0B",
    "Transportation": "#06B6D4",
    "Personal":       "#EC4899",
    "Lifestyle":      "#F97316",
    "Health":         "#10B981",
    "Savings":        "#3B82F6",
    "Take-Home":      "#22C55E",
    "Gross Pay":      "#FFB81C",
}


def _apply_theme(fig: go.Figure, height: int = 500) -> go.Figure:
    """Apply consistent dark-theme styling to any figure."""
    fig.update_layout(
        paper_bgcolor=THEME["bg"],
        plot_bgcolor=THEME["bg"],
        font=dict(color=THEME["font_color"], family="sans-serif"),
        height=height,
        margin=dict(l=20, r=20, t=50, b=20),
        hoverlabel=dict(bgcolor="#1A1F2E", font_size=13),
    )
    fig.update_xaxes(gridcolor=THEME["grid_color"], zerolinecolor=THEME["grid_color"])
    fig.update_yaxes(gridcolor=THEME["grid_color"], zerolinecolor=THEME["grid_color"])
    return fig


# -----------------------------------------------------------------------------
# Sankey — the headliner chart
# -----------------------------------------------------------------------------
def sankey_money_flow(flows_df: pd.DataFrame, height: int = 700) -> go.Figure:
    """
    Build a Sankey diagram from gold.sankey_flows.

    Expects columns: source_node, target_node, amount, level, flow_type
    """
    # Build the unique node list and a name→index map
    all_nodes = pd.unique(
        flows_df[["source_node", "target_node"]].values.ravel()
    ).tolist()
    node_idx = {name: i for i, name in enumerate(all_nodes)}

    # Color each node based on what bucket it belongs to
    def node_color(name: str) -> str:
        if name == "Gross Pay":      return THEME["accent"]
        if name == "Take-Home":      return THEME["income"]
        if name in GROUP_COLORS:     return GROUP_COLORS[name]
        # Tax/deduction descriptors
        n = name.lower()
        if any(k in n for k in ["tax", "withholding", "oasdi", "medicare"]):
            return THEME["tax"]
        if any(k in n for k in ["401(k)", "hsa", "roth", "ira"]):
            return THEME["savings"]
        if any(k in n for k in ["dental", "medical", "parking", "life"]):
            return THEME["neutral"]
        return THEME["neutral"]

    # Build link colors (semi-transparent versions of source node color)
    def link_color(source_name: str) -> str:
        c = node_color(source_name)
        # Convert hex to rgba with alpha
        c = c.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return f"rgba({r},{g},{b},0.35)"

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=18,
            thickness=22,
            line=dict(color="rgba(255,255,255,0.2)", width=0.5),
            label=all_nodes,
            color=[node_color(n) for n in all_nodes],
            hovertemplate="<b>%{label}</b><br>Total: $%{value:,.2f}<extra></extra>",
        ),
        link=dict(
            source=[node_idx[s] for s in flows_df["source_node"]],
            target=[node_idx[t] for t in flows_df["target_node"]],
            value=flows_df["amount"].tolist(),
            color=[link_color(s) for s in flows_df["source_node"]],
            hovertemplate="<b>%{source.label}</b> → <b>%{target.label}</b>"
                          "<br>$%{value:,.2f}<extra></extra>",
        ),
    ))

    fig.update_layout(
        title=dict(text="💸 Money Flow — Every Dollar Tracked",
                   font=dict(size=20)),
        font_size=12,
    )
    return _apply_theme(fig, height=height)


# -----------------------------------------------------------------------------
# Waterfall — gross to grocery countdown
# -----------------------------------------------------------------------------
def waterfall_gross_to_net(
    gross: float,
    deductions: list[tuple[str, float]],
    spending: list[tuple[str, float]] | None = None,
    height: int = 600,
) -> go.Figure:
    """
    Build a waterfall chart showing money flowing from gross pay down to
    what's left after deductions and (optionally) spending.

    Args:
        gross: starting gross amount
        deductions: list of (label, amount) tuples — amounts as POSITIVES
        spending: optional list of (label, amount) tuples for spending
                  (also positives — they get subtracted)
    """
    labels = ["Gross Pay"]
    values = [gross]
    measures = ["absolute"]

    for label, amount in deductions:
        labels.append(label)
        values.append(-amount)
        measures.append("relative")

    labels.append("Take-Home")
    values.append(0)
    measures.append("total")

    if spending:
        for label, amount in spending:
            labels.append(label)
            values.append(-amount)
            measures.append("relative")
        labels.append("Remaining")
        values.append(0)
        measures.append("total")

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        textposition="outside",
        text=[f"${abs(v):,.0f}" if v != 0 else "" for v in values],
        connector={"line": {"color": THEME["grid_color"]}},
        increasing={"marker": {"color": THEME["income"]}},
        decreasing={"marker": {"color": THEME["expense"]}},
        totals={"marker": {"color": THEME["accent"]}},
    ))

    fig.update_layout(
        title=dict(text="💧 Gross Pay → Where Every Dollar Goes",
                   font=dict(size=20)),
        showlegend=False,
        xaxis=dict(tickangle=-30),
        yaxis=dict(title="USD"),
    )
    return _apply_theme(fig, height=height)


# -----------------------------------------------------------------------------
# Bar chart for category spending
# -----------------------------------------------------------------------------
def horizontal_bar_categories(df: pd.DataFrame, label_col: str,
                              value_col: str, color_col: str | None = None,
                              title: str = "", height: int = 500) -> go.Figure:
    """Horizontal bar chart, sorted descending."""
    df = df.sort_values(value_col, ascending=True)  # ascending for horizontal display

    color_map = None
    if color_col:
        color_map = {k: GROUP_COLORS.get(k, THEME["neutral"])
                     for k in df[color_col].unique()}

    fig = px.bar(
        df, y=label_col, x=value_col, orientation="h",
        color=color_col, color_discrete_map=color_map,
        text=df[value_col].apply(lambda v: f"${v:,.0f}"),
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(title=title, showlegend=color_col is not None)
    return _apply_theme(fig, height=height)


# -----------------------------------------------------------------------------
# Monthly trend line
# -----------------------------------------------------------------------------
def monthly_trend(df: pd.DataFrame, x: str, y: str, color: str | None = None,
                  title: str = "", height: int = 400) -> go.Figure:
    """Line/bar chart for month-over-month trends."""
    fig = px.line(df, x=x, y=y, color=color, markers=True,
                  color_discrete_map=GROUP_COLORS)
    fig.update_layout(title=title)
    fig.update_traces(line=dict(width=3))
    return _apply_theme(fig, height=height)


# -----------------------------------------------------------------------------
# Donut chart
# -----------------------------------------------------------------------------
def donut_chart(df: pd.DataFrame, labels_col: str, values_col: str,
                title: str = "", height: int = 400) -> go.Figure:
    """Donut chart for category proportions."""
    fig = go.Figure(go.Pie(
        labels=df[labels_col],
        values=df[values_col],
        hole=0.55,
        marker=dict(colors=[GROUP_COLORS.get(l, THEME["neutral"])
                            for l in df[labels_col]]),
        textposition="outside",
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(title=title, showlegend=False)
    return _apply_theme(fig, height=height)
