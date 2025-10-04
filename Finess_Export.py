import csv

IN_FILE = "finess.csv"
OUT_FILE = "etabs_hopitaux_france.csv"

KEEP = {
    "Centre Hospitalier (C.H.)",
    "Centre Hospitalier Régional (C.H.R.)",
    "Centre hospitalier, ex Hôpital local",
    "Hôpital des armées",
    "Centre Hospitalier Spécialisé lutte Maladies Mentales",
    "Autre Etablissement Loi Hospitalière",
    "Hospitalisation à Domicile",
    "Maisons d'accueil hospitalières (M.A.H.)",
    "Syndicat Inter Hospitalier (S.I.H.)",
}

with open(IN_FILE, encoding="utf-8", newline="") as fin, open(OUT_FILE, "w", encoding="utf-8", newline="") as fout:
    rdr = csv.reader(fin, delimiter=";")
    next(rdr, None)  # ignore la 1ère ligne "meta"
    w = csv.writer(fout)
    w.writerow([
        "nofinesset","nofinessej","rs_courte","rs_longue","telephone",
        "departement_code","departement_nom","ville_cp",
        "categorie_libelle","categorie_groupe_libelle","statut_juridique_lib","siret"
    ])
    kept = 0
    for row in rdr:
        if not row or len(row) < 32: 
            continue
        cat = row[19].strip()
        if cat not in KEEP:
            continue
        w.writerow([
            row[1].strip(),  # nofinesset
            row[2].strip(),  # nofinessej
            row[3].strip(),  # rs courte
            row[4].strip(),  # rs longue
            row[16].strip(), # téléphone
            row[13].strip(), # dept code
            row[14].strip(), # dept nom
            row[15].strip(), # ville+CP
            row[19].strip(), # catégorie libellé
            row[21].strip(), # catégorie groupe libellé
            row[27].strip(), # statut juridique libellé
            row[22].strip(), # SIRET
        ])
        kept += 1

print("OK, lignes exportées:", kept)
