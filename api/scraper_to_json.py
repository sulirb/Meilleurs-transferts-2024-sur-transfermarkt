from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import json
import os
import concurrent.futures
from urllib.parse import urljoin

# Configuration de Selenium
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

        transfers = []

        for player_profile in player_profiles:
            position = next((p for p in position_list if player_profile.find_all("tr")[1].find("td", string=p)), "Inconnu")
            
            player = player_profile.find_previous("img", {"class": "bilderrahmen-fixed"})
            player_name = player["alt"] if player else "Inconnu"
            
            clubs = [img["alt"] for img in transfer_tab.find_all("img", {"class": "tiny_wappen"})]
            
            montant = transfer_tab.select_one("td.rechts.hauptlink, td.rechts.hauptlink.bg-gruen_20")
            montant_text = montant.text if montant else "N/A"
            
            link = player_profile.find_previous("a", href=True)
            player_url = urljoin(url, link["href"]) if link else ""
            
            transfers.append({
                "joueur": player_name,
                "position": position,
                "club_depart": clubs[0] if len(clubs) > 0 else "N/A",
                "club_arrivee": clubs[1] if len(clubs) > 1 else "N/A",
                "montant": montant_text,
                "lien": player_url
            })
        
        return transfers
    
    finally:
        if driver:
            driver.quit()

def run_script(base_url, start_page=1, end_page=5):
    urls = [f"{base_url}{page}" for page in range(start_page, end_page + 1)]
    all_transfers = []
    
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(fetch_transfer_data, urls)
            for result in results:
                all_transfers.extend(result)
        
        with open("transfers.json", "w", encoding="utf-8") as json_file:
            json.dump(all_transfers, json_file, ensure_ascii=False, indent=4)
        
        print("JSON généré avec succès: transfers.json")
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    BASE_URL = "https://www.transfermarkt.fr/transfers/saisontransfers/statistik?land_id=0&ausrichtung=&spielerposition_id=&altersklasse=&leihe=&saison-id=0&plus=1&page="
    run_script(BASE_URL)
