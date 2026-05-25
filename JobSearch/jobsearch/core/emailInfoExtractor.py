import imaplib
import email
from email.header import decode_header
import re
import pandas as pd
from datetime import datetime

# ---------------------------
# CONFIGURATION
# ---------------------------
IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = "neerajaasi@aaratechinc.com"
APP_PASSWORD = "N0tall0wed*23"

FROM_DATE = "01-Jan-2026"
TO_DATE   = "28-Feb-2026"

SUBJECT_KEYWORD = "Interview"

# ---------------------------
# CONNECT TO GMAIL
# ---------------------------
mail = imaplib.IMAP4_SSL(IMAP_SERVER)
mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
mail.select("inbox")

search_criteria = f'(SUBJECT "{SUBJECT_KEYWORD}" SINCE "{FROM_DATE}" BEFORE "{TO_DATE}")'
status, messages = mail.search(None, search_criteria)
email_ids = messages[0].split()

print(f"Found {len(email_ids)} Interview emails")

data_rows = []
serial_no = 1

# ---------------------------
# EMAIL REGEX
# ---------------------------
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

# ---------------------------
# PROCESS EMAILS
# ---------------------------
for email_id in email_ids:
    status, msg_data = mail.fetch(email_id, "(RFC822)")
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    # Decode Subject
    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8")

    # Extract body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    body = body.replace("\r", "").replace("\n", "\n")

    # ---------------------------
    # Extract Vendor Name
    # ---------------------------
    vendor_match = re.search(r"Vendor\s*:\s*(.+)", body, re.IGNORECASE)
    vendor_name = vendor_match.group(1).strip() if vendor_match else "Not Found"

    # ---------------------------
    # Extract Client Name
    # ---------------------------
    client_match = re.search(r"Client\s*:\s*(.+)", body, re.IGNORECASE)
    client_name = client_match.group(1).strip() if client_match else "Not Found"

    # ---------------------------
    # Extract Vendor Emails (if mentioned)
    # ---------------------------
    vendor_email_match = re.search(r"Vendor Email\s*:\s*(.+)", body, re.IGNORECASE)
    if vendor_email_match:
        vendor_emails_list = re.findall(EMAIL_REGEX, vendor_email_match.group(1))
    else:
        vendor_emails_list = []

    # ---------------------------
    # Extract Client Emails (if mentioned)
    # ---------------------------
    client_email_match = re.search(r"Client Email\s*:\s*(.+)", body, re.IGNORECASE)
    if client_email_match:
        client_emails_list = re.findall(EMAIL_REGEX, client_email_match.group(1))
    else:
        client_emails_list = []

    vendor_emails = ", ".join(set(vendor_emails_list)) if vendor_emails_list else "Not Found"
    client_emails = ", ".join(set(client_emails_list)) if client_emails_list else "Not Found"

    # ---------------------------
    # Append to Data
    # ---------------------------
    data_rows.append([
        serial_no,
        vendor_name,
        vendor_emails,
        client_name,
        client_emails,
        subject
    ])

    serial_no += 1

mail.logout()

# ---------------------------
# CREATE EXCEL FILE
# ---------------------------
df = pd.DataFrame(data_rows, columns=[
    "S.No",
    "Vendor Name",
    "Vendor Emails",
    "Client Name",
    "Client Emails",
    "Email Subject"
])

file_name = f"Interview_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
df.to_excel(file_name, index=False)

print(f"\nExcel file created successfully: {file_name}")