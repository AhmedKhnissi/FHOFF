# 1_finess_export.py
import csv, re

IN_FILE = "finess.csv"
OUT_FILE = "etabs_hopitaux_france.csv"

def is_hospital(libcat: str) -> bool:
    libcat = (libcat or "").upper()
    # On garde large : CHU / CENTRE HOSPITALIER / HOPITAL / CLINIQUE (tu peux resserrer si tu veux public only)
    patterns = ["CHU", "CENTRE HOSPITALIER", "HÔPITAL", "HOPITAL", "CLINIQUE"]
    return any(p in libcat for p in patterns)

with open(IN_FILE, newline="", encoding="utf-8") as f_in, open(OUT_FILE, "w", newline="", encoding="utf-8") as f_out:
    reader = csv.DictReader(f_in, delimiter=",")  # data.gouv publie en csv ; séparateur virgule
    fields = ["nofinesset","rs","libcategetab","libdepartement","ligneacheminement","telephone"]
    writer = csv.DictWriter(f_out, fieldnames=fields)
    writer.writeheader()
    kept = 0
    for row in reader:
        if is_hospital(row.get("libcategetab","")):
            writer.writerow({k: row.get(k,"") for k in fields})
            kept += 1

print(f"Établissements exportés: {kept}. Fichier: {OUT_FILE}")
