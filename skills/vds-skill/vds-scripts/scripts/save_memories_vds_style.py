#!/usr/bin/env python3
"""
Script to save IntelliJ IDEA workspace setup memories to VDS-AI-Memory service
following the exact format specified in AGENTS.md guide.
"""

import time

import httpx

# Memory data to save - following AGENTS.md format exactly
MEMORIES = [
    {
        "content": "Successfully implemented and verified IntelliJ IDEA multi-project workspace setup for the VDS monorepo following the AGENTS.md guide principles. The setup includes automation scripts for generating module files and updating modules.xml. This transforms the VDS monorepo into a well-organized multi-project workspace that's much easier to navigate and work with in IntelliJ IDEA.",
        "category": "project",
        "importance": "high",
        "force_mem0": True,
        "metadata": {
            "org_id": "vds-internal",
            "agent_id": "dev-agent",
            "project": "IntelliJ-Workspace-Setup",
            "decision_type": "implementation",
        },
    },
    {
        "content": "Created three Python automation scripts for IntelliJ IDEA workspace: generate_intellij_modules.py, update_modules_xml.py, and setup_intellij_workspace.py. These scripts follow VDS Python project standards using standard libraries and consistent code style.",
        "category": "business-logic",
        "importance": "critical",
        "force_mem0": True,
        "metadata": {
            "org_id": "vds-internal",
            "agent_id": "dev-agent",
            "project": "IntelliJ-Workspace-Setup",
            "decision_type": "automation",
        },
    },
    {
        "content": "Key IntelliJ IDEA configuration files for VDS monorepo: .idea/modules.xml organizes all modules by project groups. Individual project .iml files are generated for each service. Main workspace file .idea/vds.iml excludes sub-project directories to prevent conflicts.",
        "category": "project",
        "importance": "high",
        "metadata": {
            "org_id": "vds-internal",
            "agent_id": "dev-agent",
            "project": "IntelliJ-Workspace-Setup",
            "decision_type": "configuration",
        },
    },
]


def create_session():
    """Create a session following AGENTS.md guide."""
    url = "http://localhost:8000/api/v1/sessions"
    payload = {
        "user_id": "_dev_probe",
        "project_domain": "PLATFORM",
        "context": "IntelliJ IDEA workspace setup for VDS monorepo",
        "ttl_hours": 24,
    }

    try:
        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
        session_data = response.json()
        print(f"✅ Session created: {session_data['session_id']}")
        return session_data["session_id"]
    except Exception as e:
        print(f"❌ Failed to create session: {e}")
        return None


def save_memory(memory_data, session_id):
    """Save a memory following AGENTS.md guide."""
    url = "http://localhost:8000/api/v1/memories"
    payload = {
        "content": memory_data["content"],
        "category": memory_data["category"],
        "importance": memory_data["importance"],
        "user_id": "_dev_probe",
        "session_id": session_id,
        "metadata": memory_data["metadata"],
    }

    # Add force_mem0 if specified
    if memory_data.get("force_mem0"):
        payload["force_mem0"] = True

    try:
        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        print(f"✅ Memory saved: {result.get('memory_id', 'Unknown')}")
        return True
    except Exception as e:
        print(f"❌ Failed to save memory: {e}")
        print(f"   Response: {response.text if 'response' in locals() else 'No response'}")
        return False


def main():
    """Main function following AGENTS.md workflow."""
    print("🚀 Saving IntelliJ IDEA workspace setup memories to VDS-AI-Memory service")
    print("=" * 70)

    # Step 1: Create session (as specified in AGENTS.md)
    print("\n1️⃣  Creating VDS-AI-Memory session...")
    session_id = create_session()
    if not session_id:
        print("❌ Failed to create session. Exiting.")
        return

    # Step 2: Save memories (as specified in AGENTS.md)
    print(f"\n2️⃣  Saving {len(MEMORIES)} memories...")
    success_count = 0

    for i, memory in enumerate(MEMORIES, 1):
        print(f"\n   Saving memory {i}/{len(MEMORIES)}...")
        if save_memory(memory, session_id):
            success_count += 1
        time.sleep(1)  # Brief pause between requests

    # Step 3: Summary
    print("\n3️⃣  Summary")
    print(f"   Successfully saved {success_count}/{len(MEMORIES)} memories")

    if success_count == len(MEMORIES):
        print("🎉 All memories saved successfully to VDS-AI-Memory service!")
    else:
        print("⚠️  Some memories failed to save. Check output above for details.")


if __name__ == "__main__":
    main()
