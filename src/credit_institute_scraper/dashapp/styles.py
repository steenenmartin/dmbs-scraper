# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "17rem",
    "padding": "2rem 1rem",
    "background-color": "#031333",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "margin-left": "14rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

LIST_STYLE = {
    "labelStyle": {"display": "block"},
    "style": {"margin-left": "4px",
              "font-size": "14px"}
}

LEFT_COL_STYLE = {
    "style": {"margin-left": "5px"}
}

RIGHT_COL_STYLE = {
    "md": 10
}

ROW_STYLE = {
    "align": "center",
    "style": {"background-color": "#082255"}
}

DROPDOWN_STYLE = {
    "style": {"border": "none"}
}

app_color = {"graph_bg": "#082255", "graph_line": "#007ACE"}

GRAPH_STYLE = dict(
    plot_bgcolor=app_color["graph_bg"],
    paper_bgcolor=app_color["graph_bg"],
    font={"color": "#fff"},
    height=870,
    xaxis={
        "showline": True,
        "zeroline": False,
        "fixedrange": True,
        "showgrid": True,
        "gridcolor": "#676565",
        "minor_griddash": "dot",
        "nticks": 8,
        # "showspikes": True
    },
    yaxis={
        "showgrid": True,
        "showline": True,
        # "fixedrange": True,
        "zeroline": False,
        "gridcolor": "#676565",
        "minor_griddash": "dot"
    },
    legend={
        "font": {"size": 10}
    }
)