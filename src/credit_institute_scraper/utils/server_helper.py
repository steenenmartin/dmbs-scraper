import os


def is_heroku_server():
    return 'DATABASE_URL' in os.environ or 'HEROKU_POSTGRESQL_BRONZE_URL' in os.environ
