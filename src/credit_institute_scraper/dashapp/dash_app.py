import dash
import dash_bootstrap_components as dbc
from dash import Input, Output
from ..utils.server_helper import is_heroku_server

dash_app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=0.6"}],
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# dash_app.title = 'Bond stats'


# dash_app.clientside_callback(
#     """
#     function(url) {
#         function getQueryVariable(variable) {
#             var query = window.location.search.substring(1);
#             var vars = query.split('&');
#             for (var i = 0; i < vars.length; i++) {
#                 var pair = vars[i].split('=');
#                 if (decodeURIComponent(pair[0]) == variable) {
#                     return decodeURIComponent(pair[1]);
#                 }
#             }
#             console.log('Query variable %s not found', variable);
#         }
#             document.title = 'test'
#     }
#     """,
#     Output('page-title-output', 'children'),
#     Input('url', 'search')
# )

dash_app.clientside_callback(
    """
    function(tab_value) {
        let str = tab_value.substring(1);
        if (str.length === 0) {
            document.title = 'Bond stats'
        }
        else {
            document.title = str[0].toUpperCase() + str.substring(1) + ' | Bond stats'
        }
    }
    """,
    Output('page-title-output', 'children'),
    Input('url', 'pathname')
)

if is_heroku_server():
    dash_app.index_string = """
    <!DOCTYPE html>
    <html>
        <head>
            <!-- Google tag (gtag.js) -->
            <script async src="https://www.googletagmanager.com/gtag/js?id=G-V3RXS9EHBM"></script>
            <script>
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              gtag('js', new Date());
            
              gtag('config', 'G-V3RXS9EHBM');
            </script>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    """
