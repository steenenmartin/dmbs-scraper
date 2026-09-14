"""Optional SQLite worker. Existing tables and master-data keys are required."""
import argparse
from apscheduler.schedulers.blocking import BlockingScheduler

from credit_institute_scraper.scrapers.run_scraper import scrape
from credit_institute_scraper.database import sqlite_conn
from credit_institute_scraper.utils.logging_helper import initiate_logger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--debug', action='store_true', help='Allow scraping outside the normal collection window')
    args = parser.parse_args()
    initiate_logger()
    scheduler = BlockingScheduler(timezone='Europe/Copenhagen')
    scheduler.add_job(scrape, 'interval', minutes=5, args=[sqlite_conn], kwargs={'debug': args.debug},
                      max_instances=1, coalesce=True, misfire_grace_time=60)
    scheduler.start()


if __name__ == '__main__':
    main()
