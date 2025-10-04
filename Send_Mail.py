# 3_send_emails.py
import csv, smtplib, time
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "ton.adresse@gmail.com"
SMTP_PASS = "ton_mot_de_passe_ou_mdp_app"

FROM_NAME = "Dr Prénom Nom"
FROM_EMAIL = SMTP_USER
REPLY_TO = "ton.adresse@gmail.com"

SUBJECT = "Candidature – Médecin généraliste (mobilité France entière)"
BODY = """Bonjour,

Je me permets de vous adresser ma candidature spontanée au poste de médecin généraliste.
• Expérience : X ans en médecine générale
• Compétences : soins non programmés, consultations polyvalentes, coordination ville-hôpital
• Mobilité : France entière, prise de poste rapide

CV en pièce jointe (PDF). Références disponibles sur demande.

Cordialement,
Dr Prénom Nom
Tél : 06 00 00 00 00
LinkedIn : https://www.linkedin.com/in/xxxxx

--- Informations RGPD ---
Vous recevez cet e-mail car votre établissement figure dans l’annuaire public des hôpitaux. 
Si vous ne souhaitez plus recevoir de candidatures de ma part, répondez “STOP” à ce message et j’effacerai vos données de contact.
"""

ATTACH_PATH = "CV_Dr_Nom.pdf"  # place le PDF à côté du script

def send_one(to_addr):
    msg = EmailMessage()
    msg["Subject"] = SUBJECT
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = to_addr
    msg["Reply-To"] = REPLY_TO
    msg.set_content(BODY)

    # Pièce jointe
    with open(ATTACH_PATH, "rb") as f:
        data = f.read()
    msg.add_attachment(data, maintype="application", subtype="pdf", filename=ATTACH_PATH)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

if __name__ == "__main__":
    sent = 0
    with open("emails_fhf.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            to_addr = row["email"]
            try:
                send_one(to_addr)
                sent += 1
                print("OK:", to_addr)
            except Exception as e:
                print("ERR:", to_addr, e)
            time.sleep(6)  # ~10 e-mails/min, reste poli avec les serveurs et ton SMTP
    print("Total envoyés:", sent)
