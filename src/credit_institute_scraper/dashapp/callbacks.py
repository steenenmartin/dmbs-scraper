from credit_institute_scraper.dashapp.app import dash_app as app
from .pages import page_not_found, home, plots
from dash import Output, Input


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname == "/":
        return home.home_page()
    elif pathname == "/Plots":
        return plots.plot_page()
    # If the user tries to reach a different page, return a 404 message
    return page_not_found.page_not_found(pathname)
