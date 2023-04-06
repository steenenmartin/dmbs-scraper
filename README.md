# DMBS Scraper

DMBS (Danish Mortgage Backed Securities) Scraper is a web-scraper and an application to extract and display price data for all currently active DMBS ISINs. 

* `scraper.py` collects data periodically every 5 minutes from the 4 main mortgage institutes in Denmark - Nordea Kredit, TotalKredit, Realkredit Danmark and Jyske Realkredit. DLR kredit unfortunately does not display intra-day offer prices, and as such they are not included.
* `app.py` is a dash application enabling the data to be displayed in your browser

## Reporting issues
Use the Github [issue tracker](https://github.com/steenenmartin/dmbs-scraper/issues) to file issues. Pull requests are very welcome

## Running DMBS scraper locally
To set up the repository locally, clone the repository and create a virtual environment with the packages specified in `requirements.txt`. The repository should work with both python 3.9 and 3.10.

Unfortunately, we cannot grant unrestricted access to the underlying PostgreSQL we use to store the data, but you can change the functions in the repository to use a local SQLite database with a few modifications:
Change the line `from ...database.postgres_conn import query_db` to `from ...database.sqlite_conn import query_db` in the following files
* `src/credit_institute_scraper_database/dashapp/callbacks/main_app.py`
* `src/credit_institute_scraper_database/dashapp/callbacks/ohlc_page.py`
* `src/credit_institute_scraper_database/dashapp/pages/ohlc_plots.py`

To run the server locally, execute `src/credit_institute_scraper/dashapp/local_server.py`

To run the scraper locally, execute `src/credit_institute_scraper/local_scraper.py`
