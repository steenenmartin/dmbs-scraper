import os
import time as timeit
import requests
import bs4
import json
import pandas as pd
from datetime import datetime, time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import (AutoMinorLocator, MultipleLocator)
import seaborn as sns


class JyskeFastRenteKurs:
    def __init__(self, loebetid, aktuel_kurs, tilbudskurs, max_antal_afdragsfrie_aar, kuponrente, aaben_for_tilbud, isin):
        self.loebetid = loebetid
        self.aktuel_kurs = aktuel_kurs
        self.tilbudskurs = tilbudskurs
        self.max_antal_afdragsfrie_aar = max_antal_afdragsfrie_aar
        self.kuponrente = kuponrente
        self.aaben_for_tilbud = aaben_for_tilbud
        self.isin = isin


def scrape():
    try:
        URL = "https://jyskeberegner-api.jyskebank.dk/api/privat/kursliste"
        page = requests.get(URL)
        soup = bs4.BeautifulSoup(page.content, "html.parser")

        jyske_fastrente_kurser = {}
        json_dict = json.loads(soup.text)
        for produkt in json_dict["fastRenteProdukter"]:
            jyske_fastrente_kurser[produkt["isin"]] = JyskeFastRenteKurs(
                produkt["loebetidAar"],
                produkt["aktuelKurs"],
                produkt["tilbudsKurs"],
                produkt["maxAntalAfdragsfrieAar"],
                produkt["kuponrenteProcent"],
                produkt["aabenForTilbud"],
                produkt["isin"]
            )

        y = pd.DataFrame.from_dict([x.__dict__ for x in jyske_fastrente_kurser.values()])

        day_path = f"./Kurser/{datetime.now().strftime('%Y%m%d')}"
        if not os.path.exists(day_path):
            os.makedirs(day_path)

        y.to_csv(f"{day_path}/{datetime.now().strftime('%Y%m%d%H%M')}.csv", index=False)

    except:
        pass
        # raise e


def create_single_day_plot(date):
    kurs_dfs = None
    day_path = f"./Kurser/{date.strftime('%Y%m%d')}"
    for file in sorted(os.listdir(day_path)):
        if file.endswith(".csv"):
            time_string = file.split(".")[0]
            time = datetime(int(time_string[0:4]), int(time_string[4:6]), int(time_string[6:8]), int(time_string[8:10]), int(time_string[10:12]))
            kurs_df = pd.read_csv(f"{day_path}/{file}")
            kurs_df["time"] = time
            kurs_df.set_index(["loebetid", "max_antal_afdragsfrie_aar", "kuponrente"], inplace=True)
            if kurs_dfs is None:
                kurs_dfs = kurs_df
            else:
                kurs_dfs = pd.concat([kurs_dfs, kurs_df])

    indices = [i for i in set(kurs_dfs.index.values) if i[0] == 30 and i[1] == 0]
    with sns.color_palette("RdYlGn", n_colors=len(indices)):
        plt.figure(figsize=(20, 15))

        for index in reversed(sorted(indices)):
            group_df = kurs_dfs.loc[index]
            plt.step(group_df["time"], group_df["aktuel_kurs"], where='post', label=f"{index[2]} %")
            plt.title(f"Løbetid {index[0]} år, {index[1]} års afdragsfrihed ({date.strftime('%Y/%m/%d')})")

        ax = plt.gca()
        ax.xaxis.set_major_locator(MultipleLocator(3600 / (60 * 60 * 24)))
        ax.xaxis.set_minor_locator(MultipleLocator((3600 / 4) / (60 * 60 * 24)))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.yaxis.set_major_locator(MultipleLocator(1))
        ax.yaxis.set_minor_locator(MultipleLocator(0.5))
        ax.grid(which='major', linestyle='-')
        ax.grid(which='minor', linestyle='dotted')

        plt.legend(loc="upper center", fancybox=True, shadow=True, ncol=len(indices))
        plt.xlabel("Tid")
        plt.ylabel("Kurs")
        plt.savefig(f"{day_path}/{date.strftime('%Y%m%d')}")


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
                    kurs_df.set_index(["loebetid", "max_antal_afdragsfrie_aar", "kuponrente"], inplace=True)
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
        ax.grid(which='major', linestyle='-')
        ax.grid(which='minor', linestyle='dotted')

        plt.legend(loc="upper center", fancybox=True, shadow=True, ncol=len(indices))
        plt.xlabel("Dag")
        plt.ylabel("Kurs")
        plt.savefig(f"{kurser_folder}/ClosingPrices")


while True:
    start_time = timeit.time()
    now = datetime.utcnow()
    if now.minute % 5 == 0:
        if time(7, 0) <= now.time() < time(15, 1) and now.isoweekday() <= 5:
            scrape()

        if now.hour == 15 and now.minute == 5:
            create_multi_day_plot()

    timeit.sleep(max(30 - (timeit.time() - start_time), 0))