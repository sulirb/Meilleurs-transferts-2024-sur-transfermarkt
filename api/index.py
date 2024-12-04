import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from flask import Flask, jsonify, render_template_string, request
import concurrent.futures
import os
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

def fetch_transfer_data(url):
    driver = None
    try:
        logger.info("Initialisation du driver Firefox")
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        logger.info(f"Accès à l'URL: {url}")
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
            complete_transfer.append(f'<div class="transfer"><div class="player"><a href="{link}" target="_blank">{player}</a></div> <div class="position">({position})</div> <div class="transfer-details">{club_1} <span class="ci--arrow-right-lg"></span> {club_2} (prix: {montant})</div></div>\n')
            
        return complete_transfer
        logger.info("Scraping terminé avec succès")
    except Exception as e:
        print(f"Erreur lors du scraping : {str(e)}")

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
        <h1>Meilleurs transferts</h1>
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
        <h1>Meilleurs transferts</h1>
            <div class="home-container">
            <h2>Recherche rapide : </h2>
            <ul>
                <li><a class="poste" href="/goalkeepers">Gardiens</a></li>
                <li><a class="poste" href="/defenders">Défenseurs</a></li>
                <li><a class="poste" href="/midfielders">Milieux</a></li>
                <li><a class="poste" href="/forwards">Attaquants</a></li>
            </ul>
            </div>
            <div class="home-container">
               <form action="/per_position" method="get">
                <label for="position">Recherchez un poste en particulier :</label>
                <select id="position" name="spielerposition_id">
                <option value="1">Gardien de but</option>
                <option value="2">Libéro</option>
                <option value="3">Défenseur central</option>
                <option value="4">Arrière gauche</option>
                <option value="5">Arrière droit</option>
                <option value="6">Milieu défensif</option>
                <option value="7">Milieu central</option>
                <option value="8">Milieu droit</option>
                <option value="9">Milieu gauche</option>
                <option value="10">Milieu offensif</option>
                <option value="11">Ailier gauche</option>
                <option value="12">Ailier droit</option>
                <option value="13">Deuxième attaquant</option>
                <option value="14">Avant-centre</option>
        </select>
        <button type="submit">Valider</button>
    </form>
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

@app.route('/per_position', methods=['GET'])
def transferts_par_poste():
    position_id = request.args.get('spielerposition_id', default='', type=str)
    base_url = f"https://www.transfermarkt.fr/transfers/saisontransfers/statistik/top/plus/1/galerie/0?saison_id=2024&transferfenster=alle&land_id=&ausrichtung=&spielerposition_id={position_id}&altersklasse=&leihe=&transferfenster=&saison-id=0&plus=1&page="
    return run_script(base_url)

if __name__ == '__main__':
    app.run(debug=True)
