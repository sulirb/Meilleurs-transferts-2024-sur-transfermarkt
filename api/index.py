from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from flask import Flask, jsonify, render_template_string
import concurrent.futures
import os
from urllib.parse import urljoin

app = Flask(__name__)
gecko_driver_path = os.path.join(os.path.dirname(__file__), "../webdriver/geckodriver.exe")

options = webdriver.FirefoxOptions()
options.add_argument('--headless')
options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'

def fetch_transfer_data(url):
    driver = None
    try:
        driver = webdriver.Firefox(service=Service(gecko_driver_path), options=options)
        driver.get(url)
    
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, "html.parser")

        transfer_tab = soup.find("table", {"class": "items"})
        if not transfer_tab:
            return []

        player_profiles = transfer_tab.find_all("table", {"class": "inline-table"})

        position_list = [
                "Gardien de but", "Libéro", "Défenseur central", "Arrière gauche", "Arrière droit", 
                "Milieu défensif", "Milieu central", "Milieu droit", "Milieu gauche", "Milieu offensif", 
                "Ailier gauche", "Ailier droit", "Deuxième attaquant", "Avant-centre"
            ]

        positions = []
        players = []
        clubs = []
        montants = []
        anchors = []

        for player_profile in player_profiles:
            found_position = None
            for position in position_list:
                position_td = player_profile.find_all("tr")[1].find("td", string=position)
                if position_td:
                    found_position = position
                    break
            if found_position:
                positions.append(found_position)

        for player in transfer_tab.find_all("img", {"class": "bilderrahmen-fixed"}):
            players.append(player["alt"])
            
        for club in transfer_tab.find_all("img", {"class": "tiny_wappen"}):
            clubs.append(club["alt"])
            
        for montant in transfer_tab.select("td.rechts.hauptlink, td.rechts.hauptlink.bg-gruen_20"):
            montants.append(montant.text)

        for link in transfer_tab.find_all("a", href=True):
            if 'profil/spieler' in link['href']:
                full_url = urljoin(url, link['href'])
                anchors.append(full_url)

        def chunked(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]
        
        complete_transfer = []
        for player, montant, club_pair, position, link in zip(players, montants, chunked(clubs, 2), positions, anchors):
            club_1 = club_pair[0]
            club_2 = club_pair[1] if len(club_pair) > 1 else 'N/A'
            complete_transfer.append(f'<div class="transfer"><div class="player"><a href="{link}" target="_blank">{player}</a></div> <div class="position">({position})</div> <div class="transfer-details">{club_1} ------> {club_2} (prix: {montant})</div></div>\n')
            
        return complete_transfer

    finally:
        if driver:
            driver.quit()

def run_script(base_url, num_pages = 6):
    urls=[f"{base_url}{page}" for page in range(1, num_pages + 1)]
    
    all_transfers = []
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(fetch_transfer_data, urls)
            for result in results:
                all_transfers.extend(result)
    
        template = """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Meilleurs transferts</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
        </head>
        <body>
            <div class="container">
                {{ content|safe }}
            </div>
        </body>
        </html>
        """

        response_html = render_template_string(template, content="\n".join(all_transfers)) 
        return response_html

    except Exception as e:
        return jsonify(error=str(e))

@app.route('/', methods=['GET'])
def home():
    content = """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Meilleurs transferts</title>
            <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
        </head>
        <body>
            <div class="container">
                <a href="/goalkeepers">Goalkeepers</a>
                <a href="/defenders">Defenders</a>
                <a href="/midfielders">Midfielders</a>
                <a href="/forwards">Forwards</a>
            </div>
        </body>
        </html>
        """
    return render_template_string(content)

@app.route('/goalkeepers', methods=['GET'])
def transfertsGardiens():
    base_url = "https://www.transfermarkt.fr/transfers/saisontransfers/statistik?land_id=0&ausrichtung=&spielerposition_id=1&altersklasse=&leihe=&transferfenster=&saison-id=0&plus=1&page="
    return run_script(base_url)

@app.route('/defenders', methods=['GET'])
def transfertsDefenseurs():
    base_url = "https://www.transfermarkt.fr/transfers/saisontransfers/statistik?land_id=0&ausrichtung=Abwehr&spielerposition_id=&altersklasse=&leihe=&transferfenster=&saison-id=0&plus=1&page="
    return run_script(base_url)

@app.route('/midfielders', methods=['GET'])
def transfertsMilieux():
    base_url = "https://www.transfermarkt.fr/transfers/saisontransfers/statistik?land_id=0&ausrichtung=Mittelfeld&spielerposition_id=&altersklasse=&leihe=&transferfenster=&saison-id=0&plus=1&page="
    return run_script(base_url)

@app.route('/forwards', methods=['GET'])
def transfertsAttaquants():
    base_url = "https://www.transfermarkt.fr/transfers/saisontransfers/statistik?land_id=0&ausrichtung=Sturm&spielerposition_id=&altersklasse=&leihe=&transferfenster=&saison-id=0&plus=1&page="
    return run_script(base_url)

if __name__ == '__main__':
    app.run(debug=True)
