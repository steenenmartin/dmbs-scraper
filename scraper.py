from src.credit_institute_scraper.scrapers.run_scraper import scrape
from src.credit_institute_scraper.database import postgres_conn
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler()


@sched.scheduled_job('cron', day_of_week='mon-fri', hour="7-16", minute="*/5")
def scheduled_job():
    scrape(postgres_conn)


sched.start()
