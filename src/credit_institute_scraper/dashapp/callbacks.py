from .dash_app import dash_app as app
from .pages import page_not_found, home, daily_plots
from .styles import app_color
from dash import Output, Input
from ..database.sqlite_conn import query_db
import plotly.graph_objects as go
import pandas as pd
import datetime as dt
import inspect
from colour import Color

date = dt.date(2022, 9, 21)
df = query_db("select * from prices where date(timestamp) = :date", params={'date': date})


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname == "/":
        return home.home_page()
    elif pathname == "/Daily":
        return daily_plots.daily_plot_page()
    # If the user tries to reach a different page, return a 404 message
    return page_not_found.page_not_found(pathname)


@app.callback(Output("daily_plot", "figure"), [Input("select_institute_daily_plot", "value"),
                                               Input("select_coupon_daily_plot", "value"),
                                               Input("select_ytm_daily_plot", "value"),
                                               Input("select_max_io_daily_plot", "value")])
def update_daily_plot(institute, coupon_rate, years_to_maturity, max_interest_only_period):
    global df

    argspec = inspect.getargvalues(inspect.currentframe())
    sql = "select * from prices where date(timestamp) = :date"

    filters = []
    for arg in argspec.args:
        if argspec.locals[arg] is not None:
            sql += f" and {arg} = :{arg}"
        else:
            filters.append(arg)

    df = query_db(sql, params={**locals(), 'date': date})
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    scatters = []
    groups = df.groupby(filters) if filters else [('', df)]
    colors = list(Color("Blue").range_to(Color("green"), len(groups)))
    for i, grp in enumerate(sorted(groups, key=lambda x: x[1]['spot_price'].mean(), reverse=True)):
        g, tmp_df = grp
        g = g if isinstance(g, (list, tuple)) else [g]
        full_idx = pd.date_range(dt.datetime.combine(date, dt.time(7)), dt.datetime.combine(date, dt.time(15)), freq='5T')
        tmp_df = tmp_df.set_index('timestamp').reindex(full_idx, fill_value=float('nan'))
        scatters.append(go.Scatter(x=tmp_df.index,
                                   y=tmp_df['spot_price'],
                                   line=dict(width=3),
                                   name='<br>'.join(
                                       f'{f.capitalize().replace("_", " ")}: {v}' for f, v in zip(filters, g)),
                                   line_shape='hv',
                                   showlegend=True,
                                   marker={'color': colors[i].get_hex()}
                                   ))
    fig = go.Figure(scatters)
    fig.update_layout(
        plot_bgcolor=app_color["graph_bg"],
        paper_bgcolor=app_color["graph_bg"],
        font={"color": "#fff"},
        height=1000,
        xaxis={
            "showline": True,
            "zeroline": False,
            "fixedrange": True,
            "range": [dt.datetime(date.year, date.month, date.day, 7, 0, 0), dt.datetime(date.year, date.month, date.day, 15, 0, 0)],
            "showgrid": True,
            "gridcolor": "#676565",
            "griddash": 'dash',
            "minor_griddash": "dot"
        },
        yaxis={
            "showgrid": True,
            "showline": True,
            # "fixedrange": True,
            "zeroline": False,
            "gridcolor":"#676565",
        },
        legend={
            "font": {"size": 10}
        })
    return fig


@app.callback([Output('select_institute_daily_plot', 'options'),
               Output('select_coupon_daily_plot', 'options'),
               Output('select_ytm_daily_plot', 'options'),
               Output('select_max_io_daily_plot', 'options')],
              Input('daily_plot', 'figure')
              )
def update_dropdowns(_):
    inst = [{'label': opt, 'value': opt} for opt in sorted(df['institute'].unique())]
    coup = [{'label': opt, 'value': opt} for opt in sorted(df['coupon_rate'].unique())]
    ytm = [{'label': opt, 'value': opt} for opt in sorted(df['years_to_maturity'].unique())]
    maxio = [{'label': opt, 'value': opt} for opt in sorted(df['max_interest_only_period'].unique())]
    return inst, coup, ytm, maxio
