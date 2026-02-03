from bs4 import BeautifulSoup as bs
import requests
from curl_cffi import requests
import pandas as pd 
import time 
import io
import re

base_search_url = "https://fbref.com/en/search/search.fcgi?search="

def get_player_url(player_name,base_search_url=base_search_url):
    search_query = player_name.replace(" ","+")
    response = requests.get(base_search_url+search_query,impersonate='chrome',allow_redirects=True)
    return response

def get_available_scout_urls(player_name):
    response = get_player_url(player_name)
    # 1. Check if we landed on a profile or a search results page
    player_url = response.url
    if '/players/' in player_url:
        soup = bs(response.text, 'html.parser')
    scout_links = {}
    nav_menu = soup.find('div', id='inner_nav')
    if nav_menu:
        for a in nav_menu.find_all('a', href=True):
            if '/scout/' in a['href']:
                # Example text: "2023-2024 Saudi Pro League" or "Euro 2024"
                report_name = a.text.strip()
                full_url = "https://fbref.com" + a['href']
                scout_links[report_name] = full_url 
    if len(scout_links) == 0:
        print(f"could not find the scout report for {player_name}")
        # print(full_url)
        print(player_url)

        
    return scout_links

def get_per_scout_report(scout_url):
    response = requests.get(scout_url,impersonate='chrome',allow_redirects=True)
    soup = bs(response.content, 'html.parser')
    nav_div = soup.find('div',{'class':'filter switcher'})
    if nav_div:
        selected_column = nav_div.find('div',{'class':'current'})
        if selected_column:
            current_group = selected_column.find('a',{'class':'sr_preset'}).get_text(strip=True)
        else:
            current_group = 'N/A'
    else:
        current_group = 'N/A'         
    df= pd.read_html(io.StringIO(response.text))
    return current_group,df[0]


def get_static_meta(player_name):
    response = get_player_url(player_name) 
    if '/players/' in response.url:
        id = re.search(r'players/([a-z0-9]+)/', response.url).group(1)
        soup = bs(response.text,'html.parser') 
    else:
        id,name,position,footed,height,weight,birth_date,birth_place,club,weekly_wage,currency=None,None,None,None,None,None,None,None,None,None,None
    meta = soup.find('div', id='meta')
    if not meta: return {}
    raw_text = meta.get_text(separator=" ").replace('\xa0', ' ')
    clean_text = " ".join(raw_text.split())
    # Remove the specific 'pt ' artifact that FBRef injects
    clean_text = clean_text.replace(" pt ", " ")
    # 2. Extraction using targeted patterns
    name = soup.find('h1').text.strip()
    # Height/Weight (Digits before cm/kg)
    height = re.search(r'(\d+)cm', clean_text).group(1) if re.search(r'(\d+)cm', clean_text) else "N/A"
    weight = re.search(r'(\d+)kg', clean_text).group(1) if re.search(r'(\d+)kg', clean_text) else "N/A"
    pos_match = re.search(r'Position:\s*(.*?)(?=\s*(?:\d{3}cm|[▪,]|Footed:|Born:|$))', clean_text)
    footed = re.search(r'Footed: (\w+)',clean_text).group(1) if re.search(r'Footed: (\w+)', clean_text) else "N/A"
    # match = re.search(r'Position:\s*(.*?)(?=\s*(?:[▪,]|Footed|Born|$))', clean_text)
    position =  pos_match.group(1).strip().rstrip(',') if pos_match else 'N/A'
    # Birth Date: Look for the pattern 'Month Day, Year'
    # This avoids grabbing the location or the 'pt' artifacts
    birth_date = "N/A"
    date_match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', clean_text)
    if date_match:
        birth_date = date_match.group(1)
    # Birth Place: Find text between the Year and the next major label (National Team/Club)
    birth_place = "N/A"
    if birth_date != "N/A":
        # Capture everything after the date until we hit a known "Stop" word
        place_pattern = re.escape(birth_date) + r'\s+in\s+(.*?)(?=National|Club|Born|$)'
        place_match = re.search(place_pattern, clean_text)
        if place_match:
            birth_place = place_match.group(1).replace("pt", "").strip()
    # Pattern: Look for currency symbol, then digits/commas, then the word "Weekly"
    wage_match = re.search(r'([￡$€])\s*([\d,]+)\s*(Weekly|Monthly|Yearly)', clean_text)    
    if wage_match:
        currency = wage_match.group(1)
        # Remove commas from the amount so it's a clean number for SQL
        amount = int(wage_match.group(2).replace(',', ''))
        frequency = wage_match.group(3)
        # Normalize all to Weekly
        if frequency == 'Monthly':
            weekly_wage = amount // 4
        elif frequency == 'Yearly':
            weekly_wage = amount // 52
        else:
            weekly_wage = amount
    else:
        currency = "N/A"
        weekly_wage = 'N/A'
    # Club: Extract specifically after 'Club:' and stop before Instagram
    club_match = re.search(r'Club:\s*(.*?)(?=\s*(?:Wages|Instagram|Contract|Expires|Born|$))', clean_text)
    if club_match:
        club = club_match.group(1).strip().rstrip(':')
    else:
        club = "N/A"
    return {
        'player_id':id,
        'name': name,
        'position': position,
        'strong_foot':  footed,
        'height_cm': height,
        'weight_kg': weight,
        'birth_date': birth_date,
        'birth_place': birth_place,
        'club': club,
        'wage_weekly': weekly_wage,
        'currency' : currency
    }


