import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import warnings
from src.database.sqlite_conn import query_db
from matplotlib.ticker import AutoMinorLocator, MultipleLocator

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)


def create_single_day_plot_per_institute(date):
    day_path = f"./plots/{date.strftime('%Y%m%d')}"

    kurs_dfs = query_db("select * from prices")
    kurs_dfs.set_index(["institute", "years_to_maturity", "max_interest_only_period", "coupon_rate"],
                       inplace=True)
    kurs_dfs['timestamp'] = pd.to_datetime(kurs_dfs['timestamp'])
    kurs_dfs.sort_values('timestamp')

    for institute in kurs_dfs.index.levels[0].values:
        indices = [i for i in set(kurs_dfs.index.values) if i[0] == institute and i[1] == 30 and i[2] == 0]
        with sns.color_palette("RdYlGn", n_colors=len(indices)):
            plt.figure(figsize=(20, 15))

            for index in sorted(indices, reverse=True):
                group_df = kurs_dfs.loc[index]
                plt.step(group_df['timestamp'], group_df["spot_price"], where='post', label=f"{index[2]} %")
                plt.title(
                    f"{index[0]}: Løbetid {index[1]} år, {index[2]} års afdragsfrihed ({date.strftime('%Y/%m/%d')})")

            ax = plt.gca()
            ax.xaxis.set_major_locator(MultipleLocator(3600 / (60 * 60 * 24)))
            ax.xaxis.set_minor_locator(MultipleLocator((3600 / 4) / (60 * 60 * 24)))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.yaxis.set_major_locator(MultipleLocator(1))
            ax.yaxis.set_minor_locator(MultipleLocator(0.5))
            ax.tick_params(bottom=False, top=False, left=True, right=True)
            ax.grid(which='major', linestyle='-')
            ax.grid(which='minor', linestyle='dotted')

            plt.legend(loc="upper center", fancybox=True, shadow=True, ncol=len(indices))
            plt.xlabel("Tid (UTC)")
            plt.ylabel("Kurs")
            plt.tick_params(axis='y', which='both', labelleft='on', labelright='on')
            plt.savefig(f"{day_path}/{date.strftime('%Y%m%d')}_{institute}")
            plt.close('all')


def create_multi_day_plot():
    kurs_dfs = query_db("select * from prices")
    kurs_dfs.set_index(["years_to_maturity", "max_interest_only_period", "coupon_rate"], inplace=True)
    kurs_dfs['timestamp'] = pd.to_datetime(kurs_dfs['timestamp'])
    kurs_dfs.sort_values('timestamp')
    indices = [i for i in set(kurs_dfs.index.values) if i[0] == 30 and i[1] == 0]
    with sns.color_palette("RdYlGn", n_colors=len(indices)):
        plt.figure(figsize=(20, 15))

        for index in sorted(indices, reverse=True):
            group_df = kurs_dfs.loc[index]
            plt.plot(group_df['timestamp'], group_df["spot_price"], label=f"{index[2]} %")
            plt.title(f"Løbetid {index[0]} år, {index[1]} års afdragsfrihed")

        ax = plt.gca()
        ax.xaxis.set_major_locator(MultipleLocator(5))
        ax.xaxis.set_minor_locator(MultipleLocator(1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax.yaxis.set_major_locator(MultipleLocator(1))
        ax.yaxis.set_minor_locator(MultipleLocator(0.5))
        ax.tick_params(bottom=True, top=False, left=True, right=True)
        ax.grid(which='major', linestyle='-')
        ax.grid(which='minor', linestyle='dotted')

        plt.legend(loc="upper center", fancybox=True, shadow=True, ncol=len(indices))
        plt.xlabel("Dato")
        plt.ylabel("Kurs")

        # plt.show()
        plt.savefig(f".plots/ClosingPrices")
        plt.close('all')


if __name__ == '__main__':
    import datetime as dt

    create_single_day_plot_per_institute(dt.date(2022, 9, 16))
