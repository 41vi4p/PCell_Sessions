

import json
import os

# Your provided Mock Database
USERS_DB = {
    "10981": {"password": "54027", "email": "10981.crce@edu.in", "name": "Student One"},
    "10982": {"password": "32043", "email": "10982@crce.edu.in", "name": "Student Two"},
    "10983": {"password": "10234", "email": "10983@crce.edu.in", "name": "Student Three"}
}

def get_student_emails(roll_no: str):
    file_path = os.path.join("data", "emails.json")
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r") as f:
        data = json.load(f)
    return data.get(roll_no, [])


def get_user(roll_no: str):
    """Return user dict for roll_no or None if not found."""
    return USERS_DB.get(roll_no)

