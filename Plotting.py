import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import warnings

from datetime import datetime
from matplotlib.ticker import (AutoMinorLocator, MultipleLocator)

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)


def create_single_day_plot_per_institute(date):
    kurs_dfs = None
    day_path = f"./Kurser/{date.strftime('%Y%m%d')}"

    if len(os.listdir(day_path)) == 1:
        return

    for file in sorted(os.listdir(day_path)):
        if file.endswith(".csv"):
            time_string = file.split(".")[0]
            time = datetime(int(time_string[0:4]), int(time_string[4:6]), int(time_string[6:8]), int(time_string[8:10]), int(time_string[10:12]))
            kurs_df = pd.read_csv(f"{day_path}/{file}")
            kurs_df["time"] = time
            kurs_df.set_index(["institute", "years_to_maturity", "maximum_years_without_repayment", "coupon_rate"], inplace=True)
            if kurs_dfs is None:
                kurs_dfs = kurs_df
            else:
                kurs_dfs = pd.concat([kurs_dfs, kurs_df])

    for institute in kurs_dfs.index.levels[0].values:
        indices = [i for i in set(kurs_dfs.index.values) if i[0] == institute and i[1] == 30 and i[2] == 0]
        with sns.color_palette("RdYlGn", n_colors=len(indices)):
            plt.figure(figsize=(20, 15))

            for index in reversed(sorted(indices)):
                group_df = kurs_dfs.loc[index]
                plt.step(group_df["time"], group_df["spot_price"], where='post', label=f"{index[2]} %")
                plt.title(f"{index[0]}: Løbetid {index[1]} år, {index[2]} års afdragsfrihed ({date.strftime('%Y/%m/%d')})")

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
    kurs_dfs = None
    kurser_folder = f"./Kurser"
    for root, subdirectories, files in os.walk(kurser_folder):
        for subdirectory in sorted(subdirectories):
            for file in reversed(sorted(os.listdir(kurser_folder + "/" + subdirectory))):
                if file.endswith(".csv"):
                    time_string = file.split(".")[0]
                    time = datetime(int(time_string[0:4]), int(time_string[4:6]), int(time_string[6:8]))
                    kurs_df = pd.read_csv(kurser_folder + "/" + subdirectory + "/" + file)
                    kurs_df["time"] = time
                    kurs_df.set_index(["years_to_maturity", "maximum_years_without_repayment", "coupon_rate"], inplace=True)
                    if kurs_dfs is None:
                        kurs_dfs = kurs_df
                    else:
                        kurs_dfs = pd.concat([kurs_dfs, kurs_df])
                    break

    kurs_dfs.sort_values("time")
    indices = [i for i in set(kurs_dfs.index.values) if i[0] == 30 and i[1] == 0]
    with sns.color_palette("RdYlGn", n_colors=len(indices)):
        plt.figure(figsize=(20, 15))

        for index in reversed(sorted(indices)):
            group_df = kurs_dfs.loc[index]
            plt.plot(group_df["time"], group_df["aktuel_kurs"], label=f"{index[2]} %")
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

        plt.savefig(f"{kurser_folder}/ClosingPrices")
        plt.close('all')
