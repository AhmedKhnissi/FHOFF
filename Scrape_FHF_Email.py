import csv, re, time, sys
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

BASE = "https://www.hopital.fr"
LIST_PATH_TMPL = "/annuaire/{code}/"  # ex: /annuaire/75/
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OutreachBot/1.0; +contact)",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Cache-Control": "no-cache",
}

# France entière (01..19, 21..95), Corse 2A/2B, DOM
ALL_DEPTS = (
    [f"{i:02d}" for i in range(1, 20)]
    + ["2A", "2B"]
    + [f"{i:02d}" for i in range(21, 96)]
    + ["971", "972", "973", "974", "976"]
)

OUT_CSV = "emails_hopital_fr.csv"

# Regex email robuste
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

def get(url, expect_html=True, retry=2, sleep=2.0):
    """GET avec headers, retry simple, timeout raisonnable."""
    for attempt in range(retry + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            r.raise_for_status()
            if expect_html and "text/html" not in r.headers.get("Content-Type", ""):
                # Certains retours peuvent être sans content-type explicite : on continue.
                pass
            return r.text
        except Exception:
            if attempt == retry:
                raise
            time.sleep(sleep + attempt * 1.5)

def iter_department_list_pages(dept_code):
    """
    Itère /annuaire/{code}/ puis /annuaire/{code}/page/2/ ...
    S'arrête proprement si 404 ou s'il n'y a plus de pagination.
    """
    page = 1
    while True:
        path = f"/annuaire/{dept_code}/" if page == 1 else f"/annuaire/{dept_code}/page/{page}/"
        url = urljoin(BASE, path)
        try:
            html = get(url)  # peut lever HTTPError (404) si pas de page suivante
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                break
            raise

        soup = BeautifulSoup(html, "lxml")

        # Liens directs vers des fiches établissement
        links = [urljoin(BASE, a["href"]) for a in soup.select("a[href*='/etablissement/']") if a.get("href")]

        # Fallback: certains listings ont un libellé “Plus d'informations sur l'établissement”
        for a in soup.find_all("a", string=re.compile(r"Plus d'informations", re.I)):
            href = a.get("href")
            if href:
                links.append(urljoin(BASE, href))

        # Dédoublonner + filtrer les faux positifs
        links = list(dict.fromkeys(links))

        if not links:
            # pas de liens sur cette page -> fin
            break

        # Renvoyer les liens trouvés
        for u in links:
            yield u

        # Détecter s'il existe une page suivante (sinon on stoppe)
        has_next = bool(
            soup.select("a[rel='next'], nav.pagination a.next, a[href$='/page/{}/']".format(page + 1))
        )
        if not has_next:
            break

        page += 1
        time.sleep(1.0)  # respirer un peu

def extract_emails_from_html(html):
    """Récupère emails via mailto: et texte brut."""
    emails = set()

    # 1) mailto:
    for href in re.findall(r'href=[\'"]mailto:([^\'"?#]+)', html or "", flags=re.I):
        addr = href.split("?")[0].strip()
        if EMAIL_RE.fullmatch(addr):
            emails.add(addr)

    # 2) texte brut
    for m in EMAIL_RE.findall(html or ""):
        if "example." in m or "exemple." in m:
            continue
        emails.add(m)

    return emails

def find_site_internet_url(soup, page_url):
    """
    Sur hopital.fr, la fiche affiche souvent 'Site internet : <a href="...">'.
    On essaie d'abord ce motif, sinon on prend le premier lien externe plausible.
    """
    # Motif explicite 'Site internet'
    label = soup.find(string=re.compile(r"Site\s*internet", re.I))
    if label:
        parent = getattr(label, "parent", None)
        if parent:
            a = parent.find("a", href=True)
            if a and a["href"].startswith("http"):
                return a["href"]

    # Fallback: premier lien externe (hors RS et hors hopital.fr)
    for a in soup.select("a[href^='http']"):
        href = a.get("href") or ""
        if not href:
            continue
        if any(x in href for x in ["facebook.com", "twitter.com", "linkedin.com", "youtube.com", "instagram.com", "hopital.fr"]):
            continue
        return href

    return None

def guess_contact_urls(base_url):
    """Teste des chemins usuels de page contact."""
    base = base_url.rstrip("/")
    cands = ["", "/", "/contact", "/contacts", "/nous-contacter", "/contactez-nous",
             "/contact-us", "/nous_contacter", "/contactez_nous"]
    return [base + path for path in cands]

def try_fetch_emails_from_site(site_url):
    """
    Explore le site de l'établissement : home + pages contact.
    """
    emails = set()

    # 0) home
    try:
        html = get(site_url)
        emails |= extract_emails_from_html(html)
    except Exception:
        pass
    if emails:
        return emails

    # 1) chemins 'contact'
    for url in guess_contact_urls(site_url):
        try:
            html = get(url)
            found = extract_emails_from_html(html)
            emails |= found
            if emails:
                break
        except Exception:
            continue

    # 2) si rien: rechercher un lien 'contact' sur la home et le suivre
    if not emails:
        try:
            home = get(site_url)
            for href in re.findall(r'href=[\'"]([^\'"]+)[\'"]', home or "", flags=re.I):
                if re.search(r"contact", href, re.I):
                    target = href if href.startswith("http") else urljoin(site_url, href)
                    try:
                        html = get(target)
                        emails |= extract_emails_from_html(html)
                        if emails:
                            break
                    except Exception:
                        pass
        except Exception:
            pass

    return emails

def scrape_department(dept_code, seen_urls, seen_emails, writer):
    print(f"[{dept_code}] collecte des fiches…")
    count_links = 0
    try:
        for url in iter_department_list_pages(dept_code):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            count_links += 1

            # Récupère la page de la fiche hopital.fr
            try:
                html = get(url)
            except Exception as e:
                print("  ERR fetch fiche:", url, e)
                continue

            soup = BeautifulSoup(html, "lxml")

            # 1) emails éventuels en clair dans la fiche (rare)
            emails = extract_emails_from_html(html)

            # 2) sinon, suivre 'Site internet' et chercher sur le site
            if not emails:
                site_url = find_site_internet_url(soup, url)
                if site_url:
                    emails = try_fetch_emails_from_site(site_url)

            # Écrire
            for m in emails:
                if m not in seen_emails:
                    writer.writerow([dept_code, url, m])
                    seen_emails.add(m)

            time.sleep(0.6)

    except requests.HTTPError as e:
        # 404 de pagination = normal
        code = getattr(e.response, "status_code", "???")
        print(f"[{dept_code}] HTTP {code} sur une page: on passe au suivant.")

    print(f"  -> {count_links} fiches (visitées)")

def main():
    # départements depuis la ligne de commande, sinon tous
    args = sys.argv[1:]
    dept_codes = args or ALL_DEPTS

    seen_urls = set()
    seen_emails = set()

    # CSV en append (reprise possible)
    try:
        fout = open(OUT_CSV, "x", newline="", encoding="utf-8")
        writer = csv.writer(fout)
        writer.writerow(["departement", "source_url", "email"])
    except FileExistsError:
        fout = open(OUT_CSV, "a", newline="", encoding="utf-8")
        writer = csv.writer(fout)

    with fout:
        for d in dept_codes:
            try:
                scrape_department(d, seen_urls, seen_emails, writer)
            except Exception as e:
                print(f"[{d}] ERREUR département:", e)
            time.sleep(1.0)

    print(f"Terminé. Emails uniques: {len(seen_emails)} | Fichier: {OUT_CSV}")

if __name__ == "__main__":
    main()
