#!/usr/bin/env python3
"""
Script to save our IntelliJ IDEA workspace setup memories to the VDS-AI-Memory service.
"""

import os
import sys

from mem0 import MemoryClient


def save_memories_to_vds_ai():
    """
    Save our IntelliJ IDEA workspace setup memories to the VDS-AI-Memory service.
    """
    print("Saving IntelliJ IDEA workspace setup memories to VDS-AI-Memory service...")

    # Get the VDS root directory
    vds_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    print(f"VDS Root: {vds_root}")

    # Initialize the MemoryClient
    try:
        # Connect to the local VDS-AI-Memory service
        memory_client = MemoryClient(host="http://localhost:8000")
        print("Connected to VDS-AI-Memory service")
    except Exception as e:
        print(f"Error connecting to VDS-AI-Memory service: {e}")
        print("Please ensure the VDS-AI-Memory service is running.")
        return False

    # Define the memories to save
    memories = [
        {
            "data": "Successfully implemented and verified IntelliJ IDEA multi-project workspace setup for the VDS monorepo following the AGENTS.md guide principles. The setup includes: 1. Created automation scripts in vds-scripts/scripts/: - generate_intellij_modules.py: Generates .iml files for all projects - update_modules_xml.py: Updates .idea/modules.xml with all projects - setup_intellij_workspace.py: One-command setup that runs both scripts 2. Configured IntelliJ IDEA workspace with: - All modules organized by project groups (LEP, INSURANCE, SAVING, EKYC) - Proper XML formatting in modules.xml - No duplicate entries - Correct module file generation for all 57+ services 3. Following AGENTS.md Python standards: - Used Python scripts for automation (not manual processes) - Leveraged standard library for XML processing - Created reusable, integrated solutions - Maintained consistent code style across scripts 4. Verified setup works correctly: - All module files generated in correct locations - modules.xml properly updated and formatted - No duplicate entries in configuration - Infrastructure projects (VDS-AI-Memory, vds-scripts, docs-nttc) correctly configured. This setup transforms the VDS monorepo into a well-organized multi-project workspace that's much easier to navigate and work with in IntelliJ IDEA.",
            "metadata": {
                "category": "experience_lessons",
                "scope": "workspace",
                "source": "user",
                "keywords": "IntelliJ IDEA, multi-project workspace, VDS monorepo, automation scripts, module configuration",
            },
            "user_id": "intellij-workspace-setup",
        },
        {
            "data": "Created three Python automation scripts for setting up IntelliJ IDEA workspace in the VDS monorepo: 1. generate_intellij_modules.py: - Generates IntelliJ IDEA module files (.iml) for all projects in the VDS monorepo - Automatically detects project types (Java, Python, Web) and configures modules appropriately - Places module files in the appropriate project directories 2. update_modules_xml.py: - Updates the IntelliJ IDEA modules.xml file to include all projects - Organizes modules by project groups (LEP-Project, INSURANCE-Project, SAVING-Project, EKYC-Project, Infrastructure, Documentation) - Prevents duplicate entries and maintains proper XML formatting - Clears existing VDS module entries before adding updated ones 3. setup_intellij_workspace.py: - One-command setup that runs both generation and update scripts - Provides clear output and next steps for users - Follows VDS Python project standards from AGENTS.md. All scripts are located in vds-scripts/scripts/ directory and are executable. They follow the AGENTS.md guide for Python project standards: - Using standard Python libraries - Consistent code style - Reusable, integrated solutions over manual commands - Proper error handling and user feedback",
            "metadata": {
                "category": "project_info",
                "scope": "workspace",
                "source": "user",
                "keywords": "IntelliJ IDEA, workspace automation, Python scripts, VDS monorepo, module configuration",
            },
            "user_id": "intellij-workspace-setup",
        },
        {
            "data": "Key IntelliJ IDEA configuration files for the VDS monorepo multi-project workspace: 1. .idea/modules.xml: - Central configuration file that defines all modules in the workspace - Contains references to all project modules organized by groups - Properly formatted XML with all 57+ services from LEP, INSURANCE, SAVING, EKYC projects - Includes infrastructure projects (VDS-AI-Memory, vds-scripts, docs-nttc) - No duplicate entries after script execution 2. Individual project .iml files: - Generated for each service in their respective directories - Properly configured based on project type (Java, Python, Web) - Example: LEP-project/document-management/document-management.iml - Example: VDS-AI-Memory/.idea/VDS-AI-Memory.iml 3. Main workspace file .idea/vds.iml: - Configured to exclude sub-project directories to prevent conflicts - Contains Go plugin configuration - Proper content root configuration 4. Documentation: - WORKSPACE.md: Comprehensive guide for setting up and using the multi-project workspace - vds-scripts/scripts/README.md: Detailed information about automation scripts. These configuration files transform the VDS monorepo into a well-organized multi-project workspace that's easier to navigate and work with in IntelliJ IDEA.",
            "metadata": {
                "category": "project_info",
                "scope": "workspace",
                "source": "user",
                "keywords": "IntelliJ IDEA, configuration files, modules.xml, .iml files, VDS monorepo",
            },
            "user_id": "intellij-workspace-setup",
        },
    ]

    # Save each memory to the VDS-AI-Memory service
    for i, memory in enumerate(memories, 1):
        try:
            result = memory_client.add(data=memory["data"], metadata=memory["metadata"], user_id=memory["user_id"])
            print(f"Saved memory {i} to VDS-AI-Memory service: {result}")
        except Exception as e:
            print(f"Error saving memory {i} to VDS-AI-Memory service: {e}")
            return False

    print("\nAll memories successfully saved to VDS-AI-Memory service!")
    return True


if __name__ == "__main__":
    success = save_memories_to_vds_ai()
    sys.exit(0 if success else 1)
