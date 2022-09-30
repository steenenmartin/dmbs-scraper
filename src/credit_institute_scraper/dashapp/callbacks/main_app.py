from .. import styles
from ..dash_app import dash_app as app
from ..pages import page_not_found, home, daily_plots, historical_plots, about
from dash import Output, Input, State, ctx
import urllib.parse


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
        return historical_plots.historical_plot_page(dropdown_args=q)
    elif pathname == "/about":
        return about.about_page()

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
    if n:
        if nclick == "SHOW":
            sidebar_style = styles.SIDEBAR_HIDDEN
            content_style = styles.CONTENT_STYLE1
            cur_nclick = "HIDDEN"
            btn_txt = "SHOW"
            btn_style = {'margin-left': '0rem', "transition": "all 0.5s", }
        else:
            sidebar_style = styles.SIDEBAR_STYLE
            content_style = styles.CONTENT_STYLE
            cur_nclick = "SHOW"
            btn_txt = "HIDE"
            btn_style = {'margin-left': '13.5rem', "transition": "all 0.5s", }
    else:
        sidebar_style = styles.SIDEBAR_STYLE
        content_style = styles.CONTENT_STYLE
        cur_nclick = 'SHOW'
        btn_txt = "HIDE"
        btn_style = {'margin-left': '13.5rem', "transition": "all 0.5s", }

    return sidebar_style, content_style, cur_nclick, btn_style, btn_txt


