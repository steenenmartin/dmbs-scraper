import logging
import urllib.parse
import os
from dash import Output, Input, State, ctx, html
from .utils import make_indicator
from .. import styles
from ..dash_app import dash_app as app
from ..pages import page_not_found, home_page, daily_page, historical_page, about_page
from ...database.postgres_conn import query_db
from ...utils.date_helper import get_active_time_range


@app.callback(Output("page-content", "children"), Input("url", "href"))
def render_page_content(href):
    o = list(urllib.parse.urlparse(href))
    q = dict(urllib.parse.parse_qsl(o[4]))
    pathname = o[2]

    if pathname == "/":
        return home_page.home_page()
    elif pathname == "/daily":
        return daily_page.daily_plot_page(dropdown_args=q)
    elif pathname == "/historical":
        return historical_page.historical_plot_page(dropdown_args=q)
    elif pathname == "/about":
        return about_page.about_page()

    # If the user tries to reach a different page, return a 404 message
    return page_not_found.page_not_found(pathname)


@app.callback(Output('url', 'search'), Input('dummy1', 'value'), Input('dummy2', 'value'))
def update_search_bar(search_daily, search_historic):
    if ctx.triggered_id == 'dummy1':
        return search_daily
    else:
        return search_historic


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


@app.callback(Output('daily_store', 'data'),
              Output('master_data', 'data'),
              Output('date_range_div', 'children'),
              Output("loading-spinner-output1", "children"),
              Output('uptime_status', 'children'),
              Input('interval-component', 'n_intervals'),
              Input('url', 'pathname'),
              State('daily_store', 'data'),
              State('master_data', 'data'))
def periodic_updater(n, pathname, df, master_data):
    start_time, end_time = get_active_time_range(force_7_15=True)

    logging.info(f'Updated data by "{ctx.triggered_id}" at interval {n}. '
                 f'Start time: {start_time.isoformat()}, '
                 f'end time: {end_time.isoformat()}')

    # Only update data if we are on the daily page and interval-component is changed or if data hasn't been populated
    if (ctx.triggered_id == 'interval-component' and pathname == '/daily') or df is None or master_data is None:
        logging.info('Updated daily data store and master data store')
        df = query_db(sql="select * from spot_prices where timestamp between :start_time and :end_time",
                      params={'start_time': start_time, 'end_time': end_time}).to_dict("records")
        master_data = query_db(sql="select * from master_data").to_dict("records")

    status = query_db("select * from status")

    return df, master_data, (start_time, end_time), '', make_indicator(status)
