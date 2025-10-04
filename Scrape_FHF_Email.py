# 2_scrape_fhf_emails.py
import time, csv, sys, re
import requests
from bs4 import BeautifulSoup

BASE = "https://etablissements.fhf.fr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AhmedBot/1.0; +contact)",
    "Accept-Language": "fr-FR,fr;q=0.9"
}

def get(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r

def extract_emails(text):
    # Simple regex email
    return set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or ""))

def list_structure_links_by_dept(dept_code):
    # Le site a plusieurs modes de recherche ; ici on exploite la recherche par mots-clés avec le code postal/dept.
    # On fait plusieurs pages (paginations ?page=2,3...) tant qu'on trouve des résultats.
    links = []
    page = 1
    while True:
        url = f"{BASE}/annuaire?keywords=&departement%5B%5D={dept_code}&page={page}"
        html = get(url).text
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("a[href*='/annuaire/structure']")
        if not cards:
            break
        for a in cards:
            href = a.get("href")
            if href and "/annuaire/structure" in href:
                links.append(BASE + href)
        page += 1
        time.sleep(1.5)
    return list(dict.fromkeys(links))  # dedupe, conserve l'ordre

def scrape_emails_from_structure(url):
    html = get(url).text
    emails = set(extract_emails(html))
    # parfois, l'email est derrière un bouton "Voir la fiche" ou en clair dans une section contact
    return emails

if __name__ == "__main__":
    # Ex : python 2_scrape_fhf_emails.py 75 92 93 94 95 77 78 91
    dept_codes = sys.argv[1:] or ["75","69","13","31"]  # Paris, Lyon, Marseille, Toulouse par défaut
    out = open("emails_fhf.csv","w", newline="", encoding="utf-8")
    writer = csv.writer(out)
    writer.writerow(["structure_url","email"])

    total_links = 0
    total_emails = set()

    for d in dept_codes:
        print(f"[{d}] recherche de structures…")
        links = list_structure_links_by_dept(d)
        total_links += len(links)
        print(f"  -> {len(links)} fiches")
        for link in links:
            mails = scrape_emails_from_structure(link)
            for m in mails:
                writer.writerow([link, m])
                total_emails.add(m)
            time.sleep(1.2)  # douceur serveur

    out.close()
    print(f"Fiches visitées: {total_links} | Emails uniques: {len(total_emails)} | Fichier: emails_fhf.csv")
