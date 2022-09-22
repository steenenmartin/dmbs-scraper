from src.credit_institute_scraper.run_scraper import scrape
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler()


@sched.scheduled_job('cron', day_of_week='mon-fri', hour="7-18", minute="*/1")
def scheduled_job():
    scrape()


sched.start()
