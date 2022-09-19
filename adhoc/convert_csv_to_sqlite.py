import os
import pandas as pd
import datetime as dt
from src.database.sqlite_conn import client_factory

df_lst = []
main_dir = '../kurser'
for date_name in os.listdir(main_dir):
    date_dir = os.path.join(main_dir, date_name)
    for data_file in os.listdir(date_dir):
        data_path = os.path.join(date_dir, data_file)
        if not data_path.endswith('csv'):
            continue

        tmp_df = pd.read_csv(data_path)
        tmp_df.rename(columns={'loebetid': 'years_to_maturity',
                               'aktuel_kurs': 'spot_price',
                               'max_antal_afdragsfrie_aar': 'max_interest_only_period',
                               'kuponrente': 'coupon_rate',
                               'isin': 'isin',
                               'institut': 'institute'
                               },
                      inplace=True)
        if 'institute' not in tmp_df.columns:
            tmp_df['institute'] = 'Jyske'
        tmp_df['timestamp'] = dt.datetime.strptime(data_file.strip('.csv'), '%Y%m%d%H%M%S')
        tmp_df = tmp_df[['timestamp', 'institute', 'isin', 'years_to_maturity', 'max_interest_only_period', 'coupon_rate', 'spot_price']]
        df_lst.append(tmp_df)
df = pd.concat(df_lst)

with client_factory() as conn:
    df.to_sql(name='prices', con=conn, if_exists='append', index=False)