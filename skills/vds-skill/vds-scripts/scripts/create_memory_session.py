#!/usr/bin/env python3
"""
Script to create a session in VDS-AI-Memory service
"""

import httpx


def create_session():
    url = "http://localhost:8000/api/v1/sessions"
    payload = {
        "user_id": "_dev_probe",
        "project_domain": "PLATFORM",
        "context": "Saving IntelliJ IDEA workspace setup memories",
        "ttl_hours": 24,
    }

    try:
        response = httpx.post(url, json=payload)
        if response.status_code == 200:
            session_data = response.json()
            print(f"Session created successfully: {session_data}")
            return session_data.get("session_id")
        else:
            print(f"Failed to create session. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error creating session: {e}")
        return None


if __name__ == "__main__":
    session_id = create_session()
    if session_id:
        print(f"SESSION_ID={session_id}")
