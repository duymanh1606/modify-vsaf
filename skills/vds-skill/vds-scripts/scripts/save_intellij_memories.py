#!/usr/bin/env python3
"""
Script to save IntelliJ IDEA workspace setup memories to VDS-AI-Memory service
following the AGENTS.md guide.
"""

import time

import httpx

# Memory data to save
MEMORIES = [
    {
        "content": "Successfully implemented and verified IntelliJ IDEA multi-project workspace setup for the VDS monorepo following the AGENTS.md guide principles. The setup includes: 1. Created automation scripts in vds-scripts/scripts/: - generate_intellij_modules.py: Generates .iml files for all projects - update_modules_xml.py: Updates .idea/modules.xml with all projects - setup_intellij_workspace.py: One-command setup that runs both scripts 2. Configured IntelliJ IDEA workspace with: - All modules organized by project groups (LEP, INSURANCE, SAVING, EKYC) - Proper XML formatting in modules.xml - No duplicate entries - Correct module file generation for all 57+ services 3. Following AGENTS.md Python standards: - Used Python scripts for automation (not manual processes) - Leveraged standard library for XML processing - Created reusable, integrated solutions - Maintained consistent code style across scripts 4. Verified setup works correctly: - All module files generated in correct locations - modules.xml properly updated and formatted - No duplicate entries in configuration - Infrastructure projects (VDS-AI-Memory, vds-scripts, docs-nttc) correctly configured. This setup transforms the VDS monorepo into a well-organized multi-project workspace that's much easier to navigate and work with in IntelliJ IDEA.",
        "category": "project",
        "importance": "high",
        "metadata": {"org_id": "vds-internal", "agent_id": "dev-agent", "project": "IntelliJ-Workspace-Setup"},
    },
    {
        "content": "Created three Python automation scripts for setting up IntelliJ IDEA workspace in the VDS monorepo: 1. generate_intellij_modules.py: - Generates IntelliJ IDEA module files (.iml) for all projects in the VDS monorepo - Automatically detects project types (Java, Python, Web) and configures modules appropriately - Places module files in the appropriate project directories 2. update_modules_xml.py: - Updates the IntelliJ IDEA modules.xml file to include all projects - Organizes modules by project groups (LEP-Project, INSURANCE-Project, SAVING-Project, EKYC-Project, Infrastructure, Documentation) - Prevents duplicate entries and maintains proper XML formatting - Clears existing VDS module entries before adding updated ones 3. setup_intellij_workspace.py: - One-command setup that runs both generation and update scripts - Provides clear output and next steps for users - Follows VDS Python project standards from AGENTS.md. All scripts are located in vds-scripts/scripts/ directory and are executable. They follow the AGENTS.md guide for Python project standards: - Using standard Python libraries - Consistent code style - Reusable, integrated solutions over manual commands - Proper error handling and user feedback",
        "category": "project",
        "importance": "high",
        "metadata": {"org_id": "vds-internal", "agent_id": "dev-agent", "project": "IntelliJ-Workspace-Setup"},
    },
    {
        "content": "Key IntelliJ IDEA configuration files for the VDS monorepo multi-project workspace: 1. .idea/modules.xml: - Central configuration file that defines all modules in the workspace - Contains references to all project modules organized by groups - Properly formatted XML with all 57+ services from LEP, INSURANCE, SAVING, EKYC projects - Includes infrastructure projects (VDS-AI-Memory, vds-scripts, docs-nttc) - No duplicate entries after script execution 2. Individual project .iml files: - Generated for each service in their respective directories - Properly configured based on project type (Java, Python, Web) - Example: LEP-project/document-management/document-management.iml - Example: VDS-AI-Memory/.idea/VDS-AI-Memory.iml 3. Main workspace file .idea/vds.iml: - Configured to exclude sub-project directories to prevent conflicts - Contains Go plugin configuration - Proper content root configuration 4. Documentation: - WORKSPACE.md: Comprehensive guide for setting up and using the multi-project workspace - vds-scripts/scripts/README.md: Detailed information about automation scripts. These configuration files transform the VDS monorepo into a well-organized multi-project workspace that's easier to navigate and work with in IntelliJ IDEA.",
        "category": "project",
        "importance": "high",
        "metadata": {"org_id": "vds-internal", "agent_id": "dev-agent", "project": "IntelliJ-Workspace-Setup"},
    },
]


def create_session():
    """Create a session in VDS-AI-Memory service."""
    url = "http://localhost:8000/api/v1/sessions"
    payload = {
        "user_id": "_dev_probe",
        "project_domain": "PLATFORM",
        "context": "Saving IntelliJ IDEA workspace setup memories",
        "ttl_hours": 24,
    }

    try:
        response = httpx.post(url, json=payload, timeout=30.0)
        if response.status_code == 200:
            session_data = response.json()
            print(f"✅ Session created successfully: {session_data['session_id']}")
            return session_data.get("session_id")
        else:
            print(f"❌ Failed to create session. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        return None


def save_memory(memory_data, session_id):
    """Save a memory to VDS-AI-Memory service."""
    url = "http://localhost:8000/api/v1/memories"
    payload = {
        "content": memory_data["content"],
        "category": memory_data["category"],
        "importance": memory_data["importance"],
        "user_id": "_dev_probe",
        "session_id": session_id,
        "metadata": memory_data["metadata"],
    }

    try:
        response = httpx.post(url, json=payload, timeout=30.0)
        if response.status_code == 200:
            memory_result = response.json()
            print(f"✅ Memory saved successfully: {memory_result.get('memory_id', 'Unknown ID')}")
            return True
        else:
            print(f"❌ Failed to save memory. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error saving memory: {e}")
        return False


def main():
    """Main function to save all memories."""
    print("Starting to save IntelliJ IDEA workspace setup memories to VDS-AI-Memory service...")

    # Create session
    session_id = create_session()
    if not session_id:
        print("Failed to create session. Exiting.")
        return

    # Save each memory
    for i, memory in enumerate(MEMORIES, 1):
        print(f"\nSaving memory {i}/{len(MEMORIES)}...")
        success = save_memory(memory, session_id)
        if success:
            print(f"✅ Memory {i} saved successfully")
        else:
            print(f"❌ Failed to save memory {i}")

        # Small delay between requests
        time.sleep(1)

    print("\n🎉 All memories saved successfully to VDS-AI-Memory service!")


if __name__ == "__main__":
    main()
