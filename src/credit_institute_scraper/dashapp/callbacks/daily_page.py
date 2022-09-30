import logging
import pandas as pd
from colour import Color
from dash import Output, Input, State, ctx
from dash.exceptions import PreventUpdate
from plotly import graph_objects as go
from ..dash_app import dash_app as app
from .. import styles
from .utils import update_search_bar_template, update_dropdowns
from ...database.postgres_conn import query_db
from ...utils.date_helper import get_active_time_range
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


@app.callback(Output('daily_store', 'data'),
              Output('date_range_div', 'children'),
              Output("loading-spinner-output1", "children"),
              Input('interval-component', 'n_intervals'),
              Input('url', 'pathname'),
              State('daily_store', 'data'))
def periodic_update_daily_plot(n, pathname, df):
    start_time, end_time = get_active_time_range(force_7_15=True)

    # Avoid periodic updates while on home page
    if pathname == '/' and ctx.triggered_id == 'interval-component' and df is not None:
        raise PreventUpdate

    logging.info(
        f'Updated data by "{ctx.triggered_id}" at interval {n}. Start time: {start_time.isoformat()}, end time: {end_time.isoformat()}')

    # Only update data if interval-component is changed or dataframe hasn't been populated
    if ctx.triggered_id == 'interval-component' or df is None:
        df = query_db(sql="select * from prices where timestamp between :start_time and :end_time",
                      params={'start_time': start_time, 'end_time': end_time}).to_dict("records")

    return df, (start_time, end_time), ''
