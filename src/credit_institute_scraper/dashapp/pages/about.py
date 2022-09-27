import dash_bootstrap_components as dbc
from dash import dcc, html


def about_page():
    return dbc.Container(
        [
            html.H3("About www.bondstats.dk"),
            dbc.Card(
                [
                    dcc.Markdown(
                        """              
                            Bondstats is visualizing fixed rate Danish Mortgage Backed Securities (DMBS) prices from the 
                            five Danish credit institutes Nordea Kredit, Jyske Realkredit, Realkredit Danmark, 
                            Totalkredit and DLR Kredit.
        
                            The scraping is carried out every 5th minute during the stock exchange opening hours.
        
                            The scraped data is visualized at the "Daily changes" page available in the sidebar to the 
                            left. Use one or more filters to select the bonds of your interest.
                            
                            
                            The website is developed by Oskar August Rosendal and Martin Steen Andersen Ehlers
                            
                            Reach us at <bondstats.dk@gmail.com>
        
                        """, style={'margin-left': '2rem', 'margin-top': '1rem'}
                    )
                ], style={'width': '50%'}
            )
        ]
    )
