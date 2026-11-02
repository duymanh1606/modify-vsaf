#!/usr/bin/env python3
"""
Script to search for IntelliJ IDEA workspace setup memories in VDS-AI-Memory service.
"""

import httpx


def search_memories(query, user_id="_dev_probe"):
    """Search for memories in VDS-AI-Memory service."""
    url = "http://localhost:8000/api/v1/memories/search"
    payload = {"query": query, "user_id": user_id, "limit": 10}

    try:
        response = httpx.post(url, json=payload, timeout=30.0)
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Found {len(results)} memories matching '{query}':")
            for i, memory in enumerate(results, 1):
                print(f"\n--- Memory {i} ---")
                print(f"ID: {memory.get('memory_id', 'Unknown')}")
                print(f"Content: {memory.get('content', 'No content')[:200]}...")
                print(f"Category: {memory.get('category', 'Unknown')}")
                print(f"Importance: {memory.get('importance', 'Unknown')}")
                print(f"Metadata: {memory.get('metadata', {})}")
            return results
        else:
            print(f"❌ Failed to search memories. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error searching memories: {e}")
        return []


def main():
    """Main function to search for memories."""
    print("Searching for IntelliJ IDEA workspace setup memories...")

    # Search for memories related to IntelliJ IDEA workspace
    search_memories("IntelliJ IDEA workspace")

    # Search for memories related to VDS monorepo
    search_memories("VDS monorepo")


if __name__ == "__main__":
    main()
