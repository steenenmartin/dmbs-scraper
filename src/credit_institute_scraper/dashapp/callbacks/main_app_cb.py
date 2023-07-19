import logging
import urllib.parse
from dash import Output, Input, State, ctx, html
from .utils import make_indicator
from .. import styles
from ..dash_app import dash_app as app
from ..pages import page_not_found, home_page, spot_prices_page, ohlc_page, spread_page
from ...database.postgres_conn import query_db
from ...utils.date_helper import get_active_time_range


@app.callback(Output("page-content", "children"), Input("url", "href"))
def render_page_content(href):
    o = list(urllib.parse.urlparse(href))
    q = dict(urllib.parse.parse_qsl(o[4]))
    pathname = o[2]

    if pathname == "/":
        return home_page.home_page()
    elif pathname == "/prices":
        return spot_prices_page.spot_prices_plot_page(dropdown_args=q)
    elif pathname == "/ohlc":
        return ohlc_page.ohlc_plot_page(dropdown_args=q)
    elif pathname == "/spreads":
        return spread_page.spread_plot_page(dropdown_args=q)

    # If the user tries to reach a different page, return a 404 message
    return page_not_found.page_not_found(href)


@app.callback(Output('url', 'search'), Input('dummy1', 'value'), Input('dummy2', 'value'), Input('dummy3', 'value'))
def update_search_bar(search_spot_prices, search_ohlc, search_spreads):
    if ctx.triggered_id == 'dummy1':
        return search_spot_prices
    elif ctx.triggered_id == 'dummy2':
        return search_ohlc
    else:
        return search_spreads


@app.callback(Output("sidebar", "style"),
              Output("page-content", "style"),
              Output("side_click", "data"),
              Output("btn_sidebar", "style"),
              Output("btn_sidebar", "children"),
              Input("btn_sidebar", "n_clicks"),
              State("side_click", "data"))
def toggle_sidebar(n, nclick):
    if n and nclick:
        sidebar_style = styles.SIDEBAR_HIDDEN
        content_style = styles.CONTENT_STYLE_NO_SIDEBAR
        cur_nclick = 0
        btn_txt = html.Img(src='assets/arrow-right.png', style={'max-width': '100%', 'max-height': '100%'})
        btn_style = {'margin-left': '0rem', "transition": "all 0.5s"}
    else:
        sidebar_style = styles.SIDEBAR_STYLE
        content_style = styles.CONTENT_STYLE
        cur_nclick = 1
        btn_txt = html.Img(src='assets/arrow-left.png', style={'max-width': '100%', 'max-height': '100%'})
        btn_style = {'margin-left': '14.45rem', "transition": "all 0.5s"}

    return sidebar_style, content_style, cur_nclick, btn_style, btn_txt


@app.callback(Output('spot_prices_store', 'data'),
              Output('master_data', 'data'),
              Output('date_range_div', 'children'),
              Output("loading-spinner-output1", "children"),
              Output('uptime_status', 'children'),
              Input('interval-component', 'n_intervals'),
              Input('url', 'pathname'),
              State('spot_prices_store', 'data'),
              State('master_data', 'data'))
def periodic_updater(n, pathname, spot_prices, master_data):
    start_time, end_time = get_active_time_range(force_9_17=True)

    logging.info(f'Updated data by "{ctx.triggered_id}" at interval {n}. '
                 f'Start time ({start_time.tzname()}): {start_time.strftime("%Y-%m-%d %H:%M")}, '
                 f'end time ({end_time.tzname()}): {end_time.strftime("%Y-%m-%d %H:%M")}')

    # Only update data if we are on spot prices page and interval-component is changed or if data hasn't been populated
    if (ctx.triggered_id == 'interval-component' and pathname == '/prices') or spot_prices is None or master_data is None:
        logging.info('Updated spot prices data store and master data store')
        spot_prices = query_db(sql="select * from spot_prices where timestamp between :start_time and :end_time",
                               params={'start_time': start_time, 'end_time': end_time}).to_dict("records")
        master_data = query_db(sql="select * from master_data").to_dict("records")

    status = query_db("select * from status")

    return spot_prices, master_data, (start_time, end_time), '', make_indicator(status)
