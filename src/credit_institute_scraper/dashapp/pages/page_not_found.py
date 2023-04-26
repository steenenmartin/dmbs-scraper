import dash_bootstrap_components as dbc
from dash import html


def page_not_found(href: str):
    show_help = "daily" in href or "historical" in href
    updated_href = href.replace('daily', 'prices').replace('historical', 'ohlc')#.replace('http', 'https') <- Does not work on local server. Comment in before deploy!
    return dbc.Container(
        [
            html.H2("404: Not found", className="text-danger"),
            html.Hr(),
            html.H5("Bondstats was recently updated, please use" if show_help else f'The url "{href}" was not recognised...'),
            html.A(
                href=updated_href,
                children=html.Big(updated_href) if show_help else None
            ),
        ]
    )
