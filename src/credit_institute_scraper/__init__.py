import pandas as pd
from .utils.logging_helper import initiate_logger as __initiate_logger
__initiate_logger()


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
pd.set_option('display.float_format', lambda x: '%.2f' % x)
