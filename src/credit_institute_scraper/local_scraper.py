from credit_institute_scraper.scrapers.run_scraper import scrape
from credit_institute_scraper.database import sqlite_conn
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler()


@sched.scheduled_job('cron', day_of_week='mon-fri', hour="7-18", minute="*/1")
def scheduled_job():
    scrape(sqlite_conn)


sched.start()
