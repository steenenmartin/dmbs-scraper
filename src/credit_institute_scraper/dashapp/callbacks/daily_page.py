import logging
import pandas as pd
from colour import Color
from dash import Output, Input, State
from plotly import graph_objects as go
from ..dash_app import dash_app as app
from .. import styles
from .utils import update_search_bar_template, update_dropdowns
from ...utils.object_helper import listify


@app.callback([Output("daily_plot", "figure"),
               Output("loading-spinner-output2", "children")],
              [Input("select_institute_daily_plot", "value"),
               Input("select_coupon_daily_plot", "value"),
               Input("select_ytm_daily_plot", "value"),
               Input("select_max_io_daily_plot", "value"),
               Input("select_isin_daily_plot", "value"),
               Input("daily_store", "data")],
              State("date_range_div", "children")
              )
def update_daily_plot(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, df, date_range):
    groupers, filters = [], []
    args = [('institute', institute), ('coupon_rate', coupon_rate), ('years_to_maturity', years_to_maturity),
            ('max_interest_only_period', max_interest_only_period), ('isin', isin)]
    for k, v in args:
        if v:
            v_str = f'"{v}"' if isinstance(v, str) else v
            filters.append(f"{k} == {v_str}")
        if not v or len(v) > 1:
            groupers.append(k)

    df = pd.DataFrame(df)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    full_idx = pd.date_range(date_range[0], date_range[1], freq='5T')
    if filters:
        df = df.query(' and '.join(filters))

    lines = []
    groups = sorted(df.groupby(groupers), key=lambda x: x[1]['spot_price'].mean(), reverse=True) if groupers else [
        ('', df)]
    colors = Color("darkblue").range_to(Color("#34a1fa"), len(groups))
    for grp, c in zip(groups, colors):
        g, tmp_df = grp
        g = listify(g)

        tmp_df = tmp_df.set_index('timestamp').reindex(full_idx, fill_value=float('nan'))
        # tmp_df.index = [x.strftime('%H:%M') for x in tmp_df.index]
        lgnd = '<br>'.join(f'{f.capitalize().replace("_", " ")}: {v}' for f, v in zip(groupers, g))
        hover = 'Time: %{x}<br>Price: %{y:.2f}'
        lines.append(go.Scatter(
            x=tmp_df.index,
            y=tmp_df['spot_price'],
            line=dict(width=3, shape='hv'),
            name=lgnd,
            hovertemplate=hover,
            showlegend=False,
            marker={'color': c.get_hex()},
        ))
    fig = go.Figure(lines)
    fig.update_layout(**styles.DAILY_GRAPH_STYLE)
    logging.info(f'Updated daily plot figure with args {", ".join(f"{k}={v}" for k, v in args)}')
    return fig, ''


@app.callback(
    Output('dummy1', 'value'),
    Input('select_institute_daily_plot', 'value'),
    Input('select_coupon_daily_plot', 'value'),
    Input("select_ytm_daily_plot", "value"),
    Input("select_max_io_daily_plot", "value"),
    Input("select_isin_daily_plot", "value"),
    State('url', 'search'))
def update_search_bar_daily(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, search):
    return update_search_bar_template(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, search)


@app.callback([
    Output('select_institute_daily_plot', 'options'),
    Output('select_coupon_daily_plot', 'options'),
    Output('select_ytm_daily_plot', 'options'),
    Output('select_max_io_daily_plot', 'options'),
    Output('select_isin_daily_plot', 'options')
], Input('daily_store', 'data'))
def update_dropdowns_daily_plot(df):
    return update_dropdowns(df=df, log_text='Updated dropdown labels for daily plot')
