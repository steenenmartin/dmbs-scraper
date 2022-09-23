import dash_bootstrap_components as dbc
from dash import dcc, html


def home_page():

    return dbc.Container(
        [
            dcc.Markdown(
                '''                
                    #### Welcome to bondstats!

                    Bondstats is visualizing fixed rate Danish Mortgage Backed Securities (DMBS) prices from the four Danish credit institutes Nordea Kredit, Jyske Realkredit, Realkredit Danmark and Totalkredit.
                    
                    The scraping is carried out every 5th minute during the stock exchange opening hours.
                    
                    The scraped data is visualized at the "Daily changes" page available in the sidebar to the left. Use one or more filters to select the bonds of your interest.
                    
                '''
            )
        ]
    )