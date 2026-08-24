from unidecode import unidecode 
from rapidfuzz import process, fuzz

import re
import pandas as pd 
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]




def load_players():
    player_data_file = BASE_DIR / "data" / "final_squad_cleaned.json"
    return pd.read_json(player_data_file, orient='records')

def normalize(name):
    name = unidecode(name)          # "Kylián" -> "Kylian"
    name = name.lower()
    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = " ".join(name.split())
    return name


# def find_player(player_name, player_df):
#     query = normalize(player_name)
#     query_words = ''.join(query.split())
#     player_df['Normalized_names'] = player_df['Name'].apply(normalize).str.split()

#     matched_names = []
#     # print(query_words)
#     # print(player_df['Normalized_names'])
   

#     for name in player_df['Name']:
#         normalized = normalize(name)
#         name_words = normalized.split()

#         a = [qw == nw for qw in query_words for nw in name_words]
#         print(a)
        
#         if all(qw == nw for qw in query_words for nw in name_words):
#             matched_names.append(name)

#     return matched_names

def find_player(query, player_df):
    query_words = set(normalize(query).split())  # {"messi"}

    matched = []
    for name in player_df["Name"]:
        target_words = set(normalize(name).split())  # {"junior", "messias"} OR {"l", "messi"}

        # Check if ALL query words exist as full words in target name
        if query_words.issubset(target_words):
            matched.append(name)

    return matched

if __name__ == '__main__':

    players_data = load_players()

    name = 'neymar'

    found = find_player(name,players_data)

    print(found)