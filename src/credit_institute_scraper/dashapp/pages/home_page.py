import dash_bootstrap_components as dbc
from dash import html


def home_page():
    return dbc.Container(
        [
            html.Div(
            [
                dbc.Row(
                [
                    dbc.Col(
                    [
                        html.H3("Welcome to Bondstats"),
                        html.H4("General information"),
                        html.P("Bondstats is the only page which features intra-day live updated fixed rate Danish Mortgage Backed Securities (DMBS) spot prices."),
                        html.P("Prices are collected every 5 minutes during the exchange opening hours (9-17 Copenhagen time) from each of the four Danish credit institutes Nordea Kredit, Jyske Realkredit, Realkredit Danmark and Totalkredit."),
                        html.P("Prices are featured only for bonds open for loan payment. Closed bonds (e.g. bonds opened more than three years ago) are currently not featured."),
                        html.P("The featured prices are identical to the spot prices ('Aktuel kurs') which can be found for each credit insitute here:"),
                        html.Ul(
                            children=[
                                html.A(
                                    href="https://www.jyskebank.dk/bolig/boliglaan/kurser",
                                    children=html.P(" - Jyske Realkredit")
                                ),
                                html.A(
                                    href="https://www.nordea.dk/privat/produkter/boliglaan/Kurser-realkreditlaan-kredit.html",
                                    children=html.P(" - Nordea Kredit")
                                ),
                                html.A(
                                    href="https://rd.dk/kurser-og-renter",
                                    children=html.P(" - Realkredit Danmark")
                                ),
                                html.A(
                                    href="https://www.totalkredit.dk/boliglan/kurser-og-priser/",
                                    children=html.P(" - Totalkredit")
                                )
                            ]
                        ),
                        html.P("Bondstats is developed by Oskar August Rosendal and Martin Steen Andersen Ehlers"),
                        html.P("Reach us at info@bondstats.dk"),
                        html.Br(),
                        html.H4("User guide"),
                        html.P("Mobile users: Use horizontal orientation mode for best user experience."),
                        # html.Br(),
                        html.H6("Spot prices"),
                        html.P("Click the 'Spot prices' tab in the sidebar and select your bond features in the dropdowns."),
                        html.P("Your choices are stored in the url. Save your favorite choices as bookmarks in your browser. For inspiration, follow the links below:"),
                        html.Ul(
                            children=[
                                html.A(
                                    href="https://www.bondstats.dk/prices?show_historic=False&coupon_rate=3&years_to_maturity=30&max_interest_only_period=0",
                                    children=html.P(" - All 30 year 1% bonds with 0 years interest-only period")
                                ),
                                html.A(
                                    href="https://www.bondstats.dk/prices?show_historic=False&institute=Nordea&years_to_maturity=30&max_interest_only_period=0",
                                    children=html.P(" - All 30 year Nordea bonds with 0 years interest-only period")
                                ),
                                html.A(
                                    href="https://www.bondstats.dk/prices?show_historic=False&coupon_rate=6",
                                    children=html.P(" - All 6 % bonds")
                                ),
                                html.A(
                                    href="https://www.bondstats.dk/prices?show_historic=False&isin=DK0002048628",
                                    children=html.P(" - The bond with ISIN code DK0002048628")
                                ),
                            ]
                        ),
                        html.P("Hover over the graph to see details on time, price, institute and ISIN."),
                        html.P("Historic prices can be enabled by toggling 'Show historic prices' for your given selection of bonds."),
                        # html.Br(),
                        html.H6("OHLC prices"),
                        html.P("OHLC (Open-High-Low-Close) prices are found in the 'OHLC prices' tab in the sidebar."),
                        html.P("To use the OHLC price graph, you must choose one single ISIN."),
                        html.P("By selecting dropdown values, the ISIN selector table will narrow down to the list of bonds fulfilling the dropdown criteria."),
                        html.Br(),
                        html.H4("Disclaimer"),
                        html.P("Bondstats reserves the right for errors and omissions in the information found on this website."),
                        html.P("The information shown on Bondstats is gathered directly from the credit institutes, and we therefore disclaim any responsibility that the information is correct."),
                        html.P("You therefore cannot make a claim for compensation against Bondstats if you suffer a loss as a result of decisions you have made based on the information found on this website.")
                    ])
                ])
            ])
        ])
    # return dbc.Container(
    #     [
    #         html.Div(
    #             [
    #                 dbc.Row(
    #                     [
    #                         dbc.Col(
    #                             [
    #                                 html.H3("Cumulative daily changes", className='header__card'),
    #                                 html.Div(children=[html.Small("To filter numerical columns, prepend with either "),
    #                                                    html.Code('=', className='code-container'),
    #                                                    html.Small(', '),
    #                                                    html.Code('>', className='code-container'),
    #                                                    html.Small(' or '),
    #                                                    html.Code('<', className='code-container'),
    #                                                    html.Small(
    #                                                        " - e.g. you could filter the Coupon column by writing "),
    #                                                    html.Code('>0.5', className='code-container')]),
    #                                 html.Div(id='data_table_div', style={'margin-top': '1rem'})
    #                             ]
    #                         )
    #                     ]
    #                 )
    #             ], style={'width': '60rem'}),
    #     ]
    # )
