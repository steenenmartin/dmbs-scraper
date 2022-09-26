# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "18rem",
    "z-index": 1,
    "overflow-x": "hidden",
    "transition": "all 0.5s",
    "padding": "0.5rem 1rem",
    "background-color": "#454545",
}

SIDEBAR_HIDDEN = {
    **SIDEBAR_STYLE,
    "left": "-18rem",
    "padding": "0rem 0rem",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "transition": "margin-left 0.5s",
    "margin-left": "18rem",
    "padding": "2rem 1rem"
}

CONTENT_STYLE1 = {
    **CONTENT_STYLE,
    "margin-left": "0rem",
}

ROW_STYLE = {
    "align": "center",
    "style": {"margin-left": "4px",
              "margin-right": "4px"}
}

DROPDOWN_STYLE = {
    "style": {"border": "none"}
}

app_color = {"graph_bg": "#f2f2f2", "graph_line": "#FFFFFF"}


def __graph_style(x_axis_title):
    return dict(
        plot_bgcolor=app_color["graph_bg"],
        paper_bgcolor="#FFFFFF",
        font={"color": "#000000"},
        # height="100%",
        xaxis={
            "title": x_axis_title,
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


DAILY_GRAPH_STYLE = __graph_style(x_axis_title="Time (UTC)")
HISTORICAL_GRAPH_STYLE = __graph_style(x_axis_title="Date")
