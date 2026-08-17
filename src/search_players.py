from unidecode import unidecode 
from rapidfuzz import process, fuzz

import re



def normalize(name):
    name = unidecode(name)          # "Kylián" -> "Kylian"
    name = name.lower()
    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = " ".join(name.split())
    return name

# names = player_df["normalized_name"].tolist()

# result = process.extractOne(
#     normalize(locked_name),
#     names,
#     scorer=fuzz.WRatio
# )

# def find_player(player_name,player_df):
#     query = normalize(player_name)
#     player_df['Normalized_names'] = player_df['Name'].apply(normalize)

#     matches = player_df[player_df["Normalized_names"].str.contains(query, na=False)]['Name']
#     name = [name.split() for name in matches]
#     # print('in finding player ' , name,query)

#     for name in matches:
#         normalized = normalize(name)
#         # print("normalized: ",normalized)

#         for word in normalized.split():
#             # print(word)
#             for w in query.split():
#                 if w == word:
#                     # print('matched name:', name)
#                     return [name]
    # name = [name for name in matches if any(normalize(name).split()) == any(query.split())]
   


    # player_df['Normalized_names'] = player_df['Name'].apply(normalize)

    # print(player_df['Normalized_names'].head().tolist())

    # results = process.extract(normalize(player_name),player_df['Normalized_names'].tolist(),scorer=fuzz.WRatio,score_cutoff=90,limit=5)
    # return results
def find_player(player_name, player_df):
    query = normalize(player_name)
    query_words = query.split()
    player_df['Normalized_names'] = player_df['Name'].apply(normalize)

    matched_names = []
    for name in player_df['Name']:
        normalized = normalize(name)
        name_words = normalized.split()

        if any(qw == nw for qw in query_words for nw in name_words):
            matched_names.append(name)

    return matched_names