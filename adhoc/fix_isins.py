import logging
from src.credit_institute_scraper.database import postgres_conn

isin_dict = {
    'DK0009539116': 'DK0005391165',
    'DK0009537417': 'DK0005374179',
    'DK0009537094': 'DK0005370946',
    'DK0009535478': 'DK0005354783',
    'DK0009535122': 'DK0005351227',
    'DK0009528507': 'DK0005285078',
    'DK0009527616': 'DK0005276168',
    'DK0009527293': 'DK0005272936',
    'DK0009530248': 'DK0005302485',
    'DK0009539389': 'DK0005393898',
    'DK0009537680': 'DK0005376802',
    'DK0009536955': 'DK0005369559',
    'DK0009535395': 'DK0005353959',
    'DK0009534901': 'DK0005349015',
    'DK0009528697': 'DK0005286977',
    'DK0009528424': 'DK0005284246',
    'DK0009527376': 'DK0005273769',
    'DK0009530917': 'DK0005309175',
    'DK0009539462': 'DK0005394623',
    'DK0009536872': 'DK0005368726',
    'DK0009535205': 'DK0005352050',
    'DK0009534828': 'DK0005348280',
    'DK0009532889': 'DK0005328894',
    'DK0009532020': 'DK0005320206',
    'DK0009531055': 'DK0005310553',
    'DK0009539546': 'DK0005395463',
    'DK0009537177': 'DK0005371779',
    'DK0009535551': 'DK0005355517',
    'DK0009534232': 'DK0005342325',
    'DK0009529315': 'DK0005293155',
    'DK0009527103': 'DK0005271037',
    'DK0009539629': 'DK0005396297',
    'DK0009537250': 'DK0005372504',
    'DK0009535718': 'DK0005357182',
    'DK0009529661': 'DK0005296612',
    'DK0009530594': 'DK0005305942',
}

old_isins = "', '".join(list(isin_dict.keys()))
sql = f"select * from ohlc_prices where isin in ('{old_isins}')"
df_old = postgres_conn.query_db(sql)


new_isins = "', '".join(list(isin_dict.values()))
sql = f"select * from ohlc_prices where isin in ('{old_isins}')"
df_new = postgres_conn.query_db(sql)


inp = input('Do you wish to continue with the update? Write "y" for yes')
if inp == 'y':
    for table in ['prices', 'ohlc_prices']:
        statements = [f"update {table} set isin = '{v}' where isin = '{k}'" for k, v in isin_dict.items()]
        postgres_conn.execute_statements(statements)
        logging.info(f'Updated isins for table: {table}')

