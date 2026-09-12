from apscheduler.schedulers.blocking import BlockingScheduler

from src.credit_institute_scraper.scrapers.run_scraper import scrape
from src.credit_institute_scraper.database import postgres_conn
from src.credit_institute_scraper.utils.logging_helper import initiate_logger


def main():
    initiate_logger()
    scheduler = BlockingScheduler(timezone='Europe/Copenhagen')
    # The first request runs at 09:02 to allow feeds to update. Wall-clock timezone
    # follows DST; stable five-minute database keys are calculated by scrape().
    scheduler.add_job(scrape, 'cron', args=[postgres_conn], day_of_week='mon-fri',
                      hour='9-16', minute='2-57/5', id='intraday',
                      max_instances=1, coalesce=True, misfire_grace_time=60)
    scheduler.add_job(scrape, 'cron', args=[postgres_conn], day_of_week='mon-fri',
                      hour=17, minute=0, id='close',
                      max_instances=1, coalesce=True, misfire_grace_time=60)
    scheduler.start()


if __name__ == '__main__':
    main()
