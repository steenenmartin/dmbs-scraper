from apscheduler.schedulers.blocking import BlockingScheduler

from src.credit_institute_scraper.scrapers.run_scraper import scrape
from src.credit_institute_scraper.database import postgres_conn
from src.credit_institute_scraper.utils.logging_helper import initiate_logger


def main():
    initiate_logger()
    scheduler = BlockingScheduler(timezone='Europe/Copenhagen')
    # Delay only the opening request to 09:02 while feeds update, then run on
    # five-minute boundaries from 09:05. Wall-clock timezone follows DST.
    scheduler.add_job(scrape, 'cron', args=[postgres_conn], day_of_week='mon-fri',
                      hour=9, minute='2,5-55/5', id='morning',
                      max_instances=1, coalesce=True, misfire_grace_time=60)
    scheduler.add_job(scrape, 'cron', args=[postgres_conn], day_of_week='mon-fri',
                      hour='10-16', minute='*/5', id='intraday',
                      max_instances=1, coalesce=True, misfire_grace_time=60)
    scheduler.add_job(scrape, 'cron', args=[postgres_conn], day_of_week='mon-fri',
                      hour=17, minute=0, id='close',
                      max_instances=1, coalesce=True, misfire_grace_time=60)
    scheduler.start()


if __name__ == '__main__':
    main()
