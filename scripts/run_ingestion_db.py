from src.scrape_data import get_available_scout_urls, get_player_url, get_per_scout_report,get_static_meta
from src.database import init_db, insert_player_data, insert_player_stat
from typing import Dict,List
import pandas as pd
import time 


def run_ingestion(player_name:str)-> None:

    # extracting and populating the metadata of a player
    meta_data = get_static_meta(player_name=player_name)
    insert_player_data(meta_data)

    id = meta_data['player_id']
    # extract the scout reports first and then populate the table one by one
    available_scout_reports = get_available_scout_urls(player_name=player_name)
    # iterate through the scout reports
    
    for report_name,report_url in available_scout_reports.items():
        tab_name , df = get_per_scout_report(report_url)
        df.columns = [col[1] if isinstance(col, tuple) else col for col in df.columns]
        stats_to_save = []

        for index, row in df.iterrows():
            if pd.isna(row['Statistic']) or row['Statistic'] == 'Statistic':
                continue      
            # Build a tuple for each row
            stats_to_save.append((
                id, 
                report_name, 
                tab_name, 
                row['Statistic'], 
                row['Per 90'], 
                row['Percentile']
            ))
        insert_player_stat(stats_to_save)
        time.sleep(5)

    return



if __name__ == '__main__':
    init_db()
    players_to_search = ['Renato De Palma Veiga','cristiano Ronaldo',"Matheus Luiz Nunes","Vitor Machado Ferreira","João Maria Lobo Alves Palhinha Gonçalves",
    "Rúben Diogo da Silva Neves","Bernardo Mota Veiga de Carvalho e Silva","António João Pereira Albuquerque Tavares Silva",
        "Gonçalo Bernardo Inácio","Diogo Dalot","Nélson Cabral Semedo", "José Pedro Malheiro de Sá","Rui Tiago Dantas da Silva","Bruno Miguel Borges Fernandes", "Rúben dos Santos Gato Alves Dias", 
        "Rafael Leao","João Pedro Gonçalves Neves","Carlos Roberto Forbs Borges","João Félix","Gonçalo Matias Ramos",
        "Francisco Conceição"]
    
    for idx, name in enumerate(players_to_search[3:]):
        run_ingestion(name)
        perc = (idx+1)*100/len(players_to_search)
        print(f"\rProgress: [{perc:5.1f}%] | Current Player: {name[:25]:<25}", end="", flush=True)
        time.sleep(5)
