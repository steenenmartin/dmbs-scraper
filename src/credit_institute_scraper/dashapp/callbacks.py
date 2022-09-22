from .dash_app import dash_app as app
from .pages import page_not_found, home, daily_plots
from .styles import app_color
from dash import Output, Input, State
import plotly.graph_objects as go
import pandas as pd
import datetime as dt
import logging
from colour import Color

date = dt.date(2022, 9, 21)


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname == "/":
        return home.home_page()
    elif pathname == "/Daily":
        return daily_plots.daily_plot_page(date=date)
    # If the user tries to reach a different page, return a 404 message
    return page_not_found.page_not_found(pathname)


@app.callback(Output("daily_plot", "figure"),
              [Input("select_institute_daily_plot", "value"),
               Input("select_coupon_daily_plot", "value"),
               Input("select_ytm_daily_plot", "value"),
               Input("select_max_io_daily_plot", "value")],
              State("daily_store", "data")
              )
def update_daily_plot(institute, coupon_rate, years_to_maturity, max_interest_only_period, df):
    legends, filters = [], []
    args = [('institute', institute), ('coupon_rate', coupon_rate), ('years_to_maturity', years_to_maturity),
            ('max_interest_only_period', max_interest_only_period)]
    for k, v in args:
        if v is None:
            legends.append(k)
        else:
            v_str = f'"{v}"' if isinstance(v, str) else v
            filters.append(f"{k} == {v_str}")

    df = pd.DataFrame(df)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    if filters:
        df = df.query(' and '.join(filters))

    scatters = []
    groups = df.groupby(legends) if legends else [('', df)]
    full_idx = pd.date_range(dt.datetime.combine(date, dt.time(7)), dt.datetime.combine(date, dt.time(15)), freq='5T')
    colors = list(Color("Blue").range_to(Color("green"), len(groups))) if groups else []
    for i, grp in enumerate(sorted(groups, key=lambda x: x[1]['spot_price'].mean(), reverse=True)):
        g, tmp_df = grp
        g = g if isinstance(g, (list, tuple)) else [g]

        tmp_df = tmp_df.set_index('timestamp').reindex(full_idx, fill_value=float('nan'))
        scatters.append(go.Scatter(x=tmp_df.index,
                                   y=tmp_df['spot_price'],
                                   line=dict(width=3),
                                   name='<br>'.join(
                                       f'{f.capitalize().replace("_", " ")}: {v}' for f, v in zip(legends, g)),
                                   line_shape='hv',
                                   showlegend=True,
                                   marker={'color': colors[i].get_hex()}
                                   ))
    fig = go.Figure(scatters)
    fig.update_layout(
        title='Daily change in spot prices',
        plot_bgcolor=app_color["graph_bg"],
        paper_bgcolor=app_color["graph_bg"],
        font={"color": "#fff"},
        height=870,
        xaxis={
            "showline": True,
            "zeroline": False,
            "fixedrange": True,
            "range": [dt.datetime.combine(date, dt.time(7)), dt.datetime.combine(date, dt.time(15))],
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
            "gridcolor": "#676565",
        },
        legend={
            "font": {"size": 10}
        })
    logging.info(f'Updated daily plot figure with args {", ".join(f"{k}={v}" for k, v in args)}')
    return fig


@app.callback([Output('select_institute_daily_plot', 'options'),
               Output('select_coupon_daily_plot', 'options'),
               Output('select_ytm_daily_plot', 'options'),
               Output('select_max_io_daily_plot', 'options')],
              Input('daily_plot', 'value'),
              State('daily_store', 'data')
              )
def update_dropdowns(_, df):
    df = pd.DataFrame(df)
    inst = [{'label': opt, 'value': opt} for opt in sorted(df['institute'].unique())]
    coup = [{'label': opt, 'value': opt} for opt in sorted(df['coupon_rate'].unique())]
    ytm = [{'label': opt, 'value': opt} for opt in sorted(df['years_to_maturity'].unique())]
    maxio = [{'label': opt, 'value': opt} for opt in sorted(df['max_interest_only_period'].unique())]
    logging.info('Updated dropdown labels for daily plot')
    return inst, coup, ytm, maxio
