import sqlite3
import pandas
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "portugal_squad.db"
print(DB_PATH)
def init_db():
    conn = sqlite3.connect(DB_PATH)

    # add table for static data
    conn.execute('''CREATE TABLE IF NOT EXISTS players 
                 (player_id TEXT PRIMARY KEY,
                 name TEXT,
                 position TEXT,
                 strong_foot TEXT,
                 height_cm REAL,
                 weight_kg REAL,
                 birth_date TEXT ,
                 birth_place TEXT,
                 club TEXT,
                 wage_weekly INTEGER,
                 currency TEXT
                 ) ''')
    # conn.execute("DROP TABLE IF EXISTS player_stats")
    conn.execute('''CREATE TABLE IF NOT EXISTS player_stats
                 (player_id TEXT,
                 season_name TEXT,
                 tab_name TEXT,
                 stat_name TEXT,
                 per_90 REAL,
                 percentile REAL,
                 PRIMARY KEY (player_id, season_name, tab_name, stat_name)
                 )''')

    conn.commit()
    conn.close()

def insert_player_data(data_dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sql = '''INSERT OR REPLACE INTO players
    (player_id,name,position,strong_foot,height_cm,weight_kg,birth_date,birth_place,club,wage_weekly,currency) VALUES
    (?,?,?,?,?,?,?,?,?,?,?)'''

    values = (data_dict['player_id'],data_dict['name'],data_dict['position'],data_dict['strong_foot'],
              data_dict['height_cm'],data_dict['weight_kg'],data_dict['birth_date'],data_dict['birth_place'],data_dict['club'],
              data_dict['wage_weekly'],data_dict['currency'])
    cursor.execute(sql,values)
    conn.commit()
    conn.close()

def insert_player_stat(player_stat_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sql_ = '''INSERT OR REPLACE INTO player_stats
            (player_id,season_name,tab_name,stat_name,per_90,percentile) VALUES
            (?,?,?,?,?,?)'''
    
    # values = (data_dict['player_id'],data_dict['season_name'],data_dict['tab_name'],data_dict['stat_name'],
    #           data_dict['per_90'],data_dict['percentile'])
    cursor.executemany(sql_,player_stat_list)
    conn.commit()
    conn.close()
