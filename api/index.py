from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from flask import Flask, jsonify

app = Flask(__name__)
gecko_driver_path = "C:/Users/sirba/OneDrive/Documents/webdrivers/geckodriver.exe"
options = webdriver.FirefoxOptions()
options.add_argument('--headless')

options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'

@app.route('/', methods=['GET'])

def run_script():
    driver = None
    try:
        driver = webdriver.Firefox(service=Service(gecko_driver_path), options=options)

        base_url = "https://www.transfermarkt.fr/transfers/saisontransfers/statistik?land_id=0&ausrichtung=&spielerposition_id=&altersklasse=&leihe=&transferfenster=&saison-id=0&plus=1&page="
        num_pages = 6

        all_transfers = []

        for page in range(1, num_pages + 1):
            url = f"{base_url}{page}"
            driver.get(url)
    
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, "html.parser")

            transfer_tab = soup.find("table", {"class": "items"})
            if not transfer_tab:
                continue

            player_profiles = transfer_tab.find_all("table", {"class": "inline-table"})
    
            position_list = [
                "Gardien de but", "Libéro", "Défenseur central", "Arrière gauche", "Arrière droit", 
                "Milieu défensif", "Milieu central", "Milieu droit", "Milieu gauche", "Milieu offensif", 
                "Ailier gauche", "Ailier droit", "Deuxième attaquant", "Avant-centre"
            ]

            positions = []
            for player_profile in player_profiles:
                found_position = None
                for position in position_list:
                    position_td = player_profile.find_all("tr")[1].find("td", string=position)
                    if position_td:
                        found_position = position
                        break
                if found_position:
                    positions.append(found_position)

            players = []
            for player in transfer_tab.find_all("img", {"class": "bilderrahmen-fixed"}):
                players.append(player["alt"])

            clubs = []
            for club in transfer_tab.find_all("img", {"class": "tiny_wappen"}):
                clubs.append(club["alt"])

            montants = []
            for montant in transfer_tab.select("td.rechts.hauptlink, td.rechts.hauptlink.bg-gruen_20"):
                montants.append(montant.text)

            def chunked(iterable, n):
                """Yield successive n-sized chunks from iterable."""
                for i in range(0, len(iterable), n):
                    yield iterable[i:i + n]
        
            complete_transfer = []
            for player, montant, club_pair, position in zip(players, montants, chunked(clubs, 2), positions):
                club_1 = club_pair[0]
                club_2 = club_pair[1] if len(club_pair) > 1 else 'N/A'  # Handle case where clubs list is odd
                complete_transfer.append(f'<div class="inline"><div class="player">{player}</div> <div class="position">({position})</div> <div class="transfer">{club_1} ------> {club_2} (prix: {montant})</div></div>\n')
            
            all_transfers.extend(complete_transfer)

        response_html = "\n".join(all_transfers)
        return response_html

    except Exception as e:
        return jsonify(error=str(e))

    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    app.run(debug=True)
