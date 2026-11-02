#!/usr/bin/env python3
"""
Script to update the IntelliJ IDEA modules.xml file with all VDS projects.
This makes it easier to work with the monorepo as a multi-project workspace.
"""

import os
import xml.etree.ElementTree as ET

# Define the project structure
PROJECT_GROUPS = {
    "LEP-Project": [
        "document-management",
        "document-mgmt",
        "file-management",
        "lending-application-service",
        "lending-basecode",
        "lending-channel-mgmt",
        "lending-cms-be",
        "lending-cms-fe",
        "lending-customer-screening-service",
        "lending-customer-service",
        "lending-decision-service",
        "lending-ekyc-business",
        "lending-ekyc-service",
        "lending-event-backbone",
        "lending-lender-process",
        "lending-lender-service",
        "lending-limit-mgmt",
        "lending-miniapp-fe",
        "lending-notification-service",
        "lending-payment-service",
        "lending-product-mgmt",
        "lending-reconcile-service",
        "lending-refund-service",
        "lending-reminder-process",
    ],
    "INSURANCE-Project": [
        "insurance-authentication-sync-process",
        "insurance-auto-underwriting-process",
        "insurance-centralized-sync-service",
        "insurance-claim-business",
        "insurance-cms-be",
        "insurance-common",
        "insurance-customer-business",
        "insurance-customer-webview",
        "insurance-insurer-service",
        "insurance-job-scheduler",
        "insurance-notification-spi",
        "insurance-ocr-service",
        "insurance-payment-service",
        "insurance-payment-service-v2",
        "insurance-policy-business",
        "insurance-promotion-business",
        "insurance-proposal-business",
        "insurance-reconcile-process",
        "insurance-renewal-process",
        "insurance-socialized-insurance-service",
        "insurance-timeout-process",
    ],
    "SAVING-Project": [
        "saving-account",
        "saving-business",
        "saving-features-management",
        "saving-job-management",
        "saving-order",
        "saving-promotion",
        "saving-refund-process",
        "saving-spi",
        "saving-timeout-process",
        "saving-transaction",
    ],
    "EKYC-Project": ["ekyc-business", "ekyc-service"],
    "Infrastructure": ["VDS-AI-Memory", "vds-scripts"],
    "Documentation": ["docs-nttc"],
}


def update_modules_xml(vds_root):
    """
    Update the IntelliJ IDEA modules.xml file with all projects.
    """
    # Path to modules.xml
    modules_xml_path = os.path.join(vds_root, ".idea", "modules.xml")

    # Parse existing modules.xml
    try:
        tree = ET.parse(modules_xml_path)
        root = tree.getroot()
    except FileNotFoundError:
        # Create new modules.xml if it doesn't exist
        root = ET.Element("project", {"version": "4"})
        component = ET.SubElement(root, "component", {"name": "ProjectModuleManager"})
        ET.SubElement(component, "modules")
        tree = ET.ElementTree(root)

    # Find the modules element
    modules_element = root.find(".//modules")
    if modules_element is None:
        component = root.find(".//component[@name='ProjectModuleManager']")
        if component is None:
            component = ET.SubElement(root, "component", {"name": "ProjectModuleManager"})
        modules_element = ET.SubElement(component, "modules")

    # Clear existing VDS module entries (but keep the main vds.iml)
    existing_modules = modules_element.findall("module")
    for module in existing_modules:
        file_path = module.get("filepath", "")
        # Remove any existing VDS project module entries to avoid duplicates
        if any(
            project_dir in file_path
            for project_dir in [
                "LEP-project",
                "INSURANCE-project",
                "SAVING-project",
                "EKYC-project",
                "VDS-AI-Memory",
                "vds-scripts",
                "docs-nttc",
            ]
        ):
            modules_element.remove(module)

    # Add modules for each project
    for group_name, projects in PROJECT_GROUPS.items():
        for project in projects:
            # Construct the module file path
            if project in ["VDS-AI-Memory", "vds-scripts", "docs-nttc"]:
                # These are top-level directories
                module_file_path = f"$PROJECT_DIR$/{project}/.idea/{project}.iml"
                module_file_url = f"file://$PROJECT_DIR$/{project}/.idea/{project}.iml"
            else:
                # These are in project directories
                module_file_path = f"$PROJECT_DIR$/{group_name.split('-')[0]}-project/{project}/{project}.iml"
                module_file_url = f"file://$PROJECT_DIR$/{group_name.split('-')[0]}-project/{project}/{project}.iml"

            # Check if module entry already exists
            existing = False
            for module in modules_element.findall("module"):
                if module.get("filepath") == module_file_path:
                    existing = True
                    break

            # Add module entry if it doesn't exist
            if not existing:
                ET.SubElement(
                    modules_element,
                    "module",
                    {"fileurl": module_file_url, "filepath": module_file_path, "group": group_name},
                )

    # Write updated modules.xml with proper formatting
    # Create a temporary file with proper formatting
    temp_file = modules_xml_path + ".tmp"
    tree.write(temp_file, encoding="UTF-8", xml_declaration=True)

    # Read and format the XML properly
    with open(temp_file) as f:
        content = f.read()

    # Parse and reformat with proper indentation
    import xml.dom.minidom

    dom = xml.dom.minidom.parseString(content)
    pretty_xml = dom.toprettyxml(indent="  ")

    # Remove extra blank lines
    lines = [line for line in pretty_xml.split("\n") if line.strip()]
    pretty_xml = "\n".join(lines)

    with open(modules_xml_path, "w") as f:
        f.write(pretty_xml)

    # Remove temporary file
    os.remove(temp_file)

    print(f"Updated modules.xml: {modules_xml_path}")


def main():
    """
    Main function to update modules.xml.
    """
    vds_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    print(f"Updating IntelliJ IDEA modules.xml in: {vds_root}")

    update_modules_xml(vds_root)

    print("modules.xml update complete!")


if __name__ == "__main__":
    main()
