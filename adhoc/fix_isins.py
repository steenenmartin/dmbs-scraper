import logging
from src.credit_institute_scraper.database import postgres_conn

isin_dict = {
    'DKK000953911': 'DK0009539116',
    'DKK000953741': 'DK0009537417',
    'DKK000953709': 'DK0009537094',
    'DKK000953547': 'DK0009535478',
    'DKK000953512': 'DK0009535122',
    'DKK000952850': 'DK0009528507',
    'DKK000952761': 'DK0009527616',
    'DKK000952729': 'DK0009527293',
    'DKK000953024': 'DK0009530248',
    'DKK000953938': 'DK0009539389',
    'DKK000953768': 'DK0009537680',
    'DKK000953695': 'DK0009536955',
    'DKK000953539': 'DK0009535395',
    'DKK000953490': 'DK0009534901',
    'DKK000952869': 'DK0009528697',
    'DKK000952842': 'DK0009528424',
    'DKK000952737': 'DK0009527376',
    'DKK000953091': 'DK0009530917',
    'DKK000953946': 'DK0009539462',
    'DKK000953687': 'DK0009536872',
    'DKK000953520': 'DK0009535205',
    'DKK000953482': 'DK0009534828',
    'DKK000953288': 'DK0009532889',
    'DKK000953202': 'DK0009532020',
    'DKK000953105': 'DK0009531055',
    'DKK000953954': 'DK0009539546',
    'DKK000953717': 'DK0009537177',
    'DKK000953555': 'DK0009535551',
    'DKK000953423': 'DK0009534232',
    'DKK000952931': 'DK0009529315',
    'DKK000952710': 'DK0009527103',
    'DKK000953962': 'DK0009539629',
    'DKK000953725': 'DK0009537250',
    'DKK000953571': 'DK0009535718',
    'DKK000952966': 'DK0009529661',
    'DKK000953059': 'DK0009530594',
}

old_isins = "', '".join(list(isin_dict.keys()))
sql_old = f"select * from ohlc_prices where isin in ('{old_isins}')"
new_isins = "', '".join(list(isin_dict.values()))
sql_new = f"select * from ohlc_prices where isin in ('{old_isins}')"

df_old = postgres_conn.query_db(sql_old)
logging.info(f'len of old before update {len(df_old)}')
df_new = postgres_conn.query_db(sql_new)
logging.info(f'len of new before update {len(df_new)}')

inp = input('Do you wish to continue with the update? Write "y" for yes')
if inp == 'y':
    for table in ['prices', 'ohlc_prices']:
        statements = [f"update {table} set isin = '{v}' where isin = '{k}'" for k, v in isin_dict.items()]
        postgres_conn.execute_statements(statements)
        logging.info(f'Updated isins for table: {table}')

df_old = postgres_conn.query_db(sql_old)
logging.info(f'len of old after update {len(df_old)}')
df_new = postgres_conn.query_db(sql_new)
logging.info(f'len of new after update {len(df_new)}')
