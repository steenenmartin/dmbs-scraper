from .dash_app import dash_app as app
from .pages import page_not_found, home, daily_plots, historical_plots, about
from . import styles
from ..utils.object_helper import listify
from ..utils.date_helper import get_active_time_range
from dash import Output, Input, State
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import pandas as pd
import logging
import urllib.parse
from colour import Color
from ..database.postgres_conn import query_db


@app.callback(Output("page-content", "children"), Input("url", "href"))
def render_page_content(href):
    o = list(urllib.parse.urlparse(href))
    q = dict(urllib.parse.parse_qsl(o[4]))
    pathname = o[2]

    if pathname == "/":
        return home.home_page()
    elif pathname == "/daily":
        return daily_plots.daily_plot_page(dropdown_args=q)
    elif pathname == "/historical":
        return historical_plots.historical_plot_page()

    # If the user tries to reach a different page, return a 404 message
    return page_not_found.page_not_found(pathname)


@app.callback(Output("daily_plot", "figure"),
              [Input("select_institute_daily_plot", "value"),
              Input("select_coupon_daily_plot", "value"),
              Input("select_ytm_daily_plot", "value"),
              Input("select_max_io_daily_plot", "value"),
              Input("select_isin_daily_plot", "value"),
              Input("daily_store", "data")],
              State("date_range_store", "data")
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
    groups = sorted(df.groupby(groupers), key=lambda x: x[1]['spot_price'].mean(), reverse=True) if groupers else [('', df)]
    colors = Color("darkblue").range_to(Color("lightblue"), len(groups))
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
    return fig


@app.callback(
    Output('url', 'search'),
    Input('select_institute_daily_plot', 'value'),
    Input('select_coupon_daily_plot', 'value'),
    Input("select_ytm_daily_plot", "value"),
    Input("select_max_io_daily_plot", "value"),
    Input("select_isin_daily_plot", "value"),
    State('url', 'search'))
def update_search_bar(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, search):
    args = [('institute', institute), ('coupon_rate', coupon_rate), ('years_to_maturity', years_to_maturity),
            ('max_interest_only_period', max_interest_only_period), ('isin', isin)]

    q = dict(urllib.parse.parse_qsl(search[1:]))  # [1:] to remove the leading `?`
    for k, v in args:
        if v:
            q[k] = ','.join(map(str, v))
        else:
            q.pop(k, None)
    query_string = urllib.parse.urlencode(q)
    return '?' + query_string if query_string else ''


def update_dropdowns(df, log_text):
    df = pd.DataFrame(df)
    inst = [{'label': opt, 'value': opt} for opt in sorted(df['institute'].unique())]
    coup = [{'label': opt, 'value': opt} for opt in sorted(df['coupon_rate'].unique())]
    ytm = [{'label': opt, 'value': opt} for opt in sorted(df['years_to_maturity'].unique())]
    maxio = [{'label': opt, 'value': opt} for opt in sorted(df['max_interest_only_period'].unique())]
    isin = [{'label': opt, 'value': opt} for opt in sorted(df['isin'].unique())]
    logging.info(log_text)
    return inst, coup, ytm, maxio, isin


@app.callback([
        Output('select_institute_daily_plot', 'options'),
        Output('select_coupon_daily_plot', 'options'),
        Output('select_ytm_daily_plot', 'options'),
        Output('select_max_io_daily_plot', 'options'),
        Output('select_isin_daily_plot', 'options')
    ],  Input('daily_store', 'data'))
def update_dropdowns_daily_plot(df):
    return update_dropdowns(df=df, log_text='Updated dropdown labels for daily plot')


@app.callback([
        Output('select_institute_historical_plot', 'options'),
        Output('select_coupon_historical_plot', 'options'),
        Output('select_ytm_historical_plot', 'options'),
        Output('select_max_io_historical_plot', 'options'),
        Output('select_isin_historical_plot', 'options')
    ], Input('historical_store', 'data'))
def update_dropdowns_historical_plot(df):
    return update_dropdowns(df=df, log_text='Updated dropdown labels for hitorical plot')


@app.callback(Output('daily_store', 'data'),
              Output('date_range_store', 'data'),
              Input('interval-component', 'n_intervals'))
def periodic_data_update_daily_plot(n):
    start_time, end_time = get_active_time_range()
    logging.info(f'Updated data at interval {n}. Start time: {start_time.isoformat()}, end time: {end_time.isoformat()}')
    df = query_db(sql="select * from prices where timestamp between :start_time and :end_time",
                  params={'start_time': start_time, 'end_time': end_time}).to_dict("records")
    return df, (start_time, end_time)

@app.callback(Output("historical_plot", "figure"),
              [Input("select_institute_historical_plot", "value"),
               Input("select_coupon_historical_plot", "value"),
               Input("select_ytm_historical_plot", "value"),
               Input("select_max_io_historical_plot", "value"),
               Input("select_isin_historical_plot", "value"),
               Input("historical_store", "data")])
def update_historical_plot(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, df):
    filters = []
    args = [('institute', institute), ('coupon_rate', coupon_rate), ('years_to_maturity', years_to_maturity),
            ('max_interest_only_period', max_interest_only_period), ('isin', isin)]
    for k, v in args:
        if v:
            v_str = f'"{v}"' if isinstance(v, str) else v
            filters.append(f"{k} == {v_str}")

    df = pd.DataFrame(df)
    if filters:
        df = df.query(' and '.join(filters))
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    fig_dct = dict()
    for g, dat in df[df['price_type'].isin(['Open', 'Close', 'Low', 'High'])].groupby('price_type'):
        fig_dct[str(g).lower()] = dat['spot_price']
    fig_dct['x'] = dat['timestamp'].dt.date
    fig = go.Figure(data=go.Ohlc(**fig_dct))

    fig.update_layout(**styles.HISTORICAL_GRAPH_STYLE)
    logging.info(f'Updated historical plot figure with args {", ".join(f"{k}={v}" for k, v in args)}')

    return fig


@app.callback(Output("sidebar", "style"),
              Output("page-content", "style"),
              Output("side_click", "data"),
              Output("btn_sidebar", "style"),
              Output("btn_sidebar", "children"),
              Input("btn_sidebar", "n_clicks"),
              State("side_click", "data"))
def toggle_sidebar(n, nclick):
    if n:
        if nclick == "SHOW":
            sidebar_style = styles.SIDEBAR_HIDDEN
            content_style = styles.CONTENT_STYLE1
            cur_nclick = "HIDDEN"
            btn_txt = "SHOW"
            btn_style = {'margin-left': '0rem', "transition": "all 0.5s",}
        else:
            sidebar_style = styles.SIDEBAR_STYLE
            content_style = styles.CONTENT_STYLE
            cur_nclick = "SHOW"
            btn_txt = "HIDE"
            btn_style = {'margin-left': '13.5rem', "transition": "all 0.5s",}
    else:
        sidebar_style = styles.SIDEBAR_STYLE
        content_style = styles.CONTENT_STYLE
        cur_nclick = 'SHOW'
        btn_txt = "HIDE"
        btn_style = {'margin-left': '13.5rem', "transition": "all 0.5s",}

    return sidebar_style, content_style, cur_nclick, btn_style, btn_txt
