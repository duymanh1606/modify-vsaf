#!/usr/bin/env python3
"""
Script to generate IntelliJ IDEA module files for all VDS projects.
This script creates .iml files for each project to enable better multi-project workspace support.
"""

import os
import xml.etree.ElementTree as ET

# Define the project structure
PROJECTS = {
    "LEP-project": [
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
    "INSURANCE-project": [
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
    "SAVING-project": [
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
    "EKYC-project": ["ekyc-business", "ekyc-service"],
}


def create_module_xml(project_root, project_name, module_name, module_type="JAVA_MODULE"):
    """
    Create an IntelliJ IDEA module XML file.
    """
    module = ET.Element("module", {"type": module_type, "version": "4"})

    # Add NewModuleRootManager component
    new_module_root_manager = ET.SubElement(
        module, "component", {"name": "NewModuleRootManager", "inherit-compiler-output": "true"}
    )
    ET.SubElement(new_module_root_manager, "exclude-output")

    # Add content
    ET.SubElement(new_module_root_manager, "content", {"url": "file://$MODULE_DIR$"})
    ET.SubElement(new_module_root_manager, "orderEntry", {"type": "inheritedJdk"})
    ET.SubElement(new_module_root_manager, "orderEntry", {"type": "sourceFolder", "forTests": "false"})

    # Handle different module types
    if module_type == "JAVA_MODULE":
        ET.SubElement(module, "component", {"name": "Go", "enabled": "true"})
    elif module_type == "PYTHON_MODULE":
        ET.SubElement(new_module_root_manager, "content", {"url": "file://$MODULE_DIR$/.venv"})

    # Create directory if it doesn't exist
    module_dir = os.path.join(project_root, project_name, module_name)
    os.makedirs(module_dir, exist_ok=True)

    # Write XML to file
    module_file_path = os.path.join(module_dir, f"{module_name}.iml")
    tree = ET.ElementTree(module)
    tree.write(module_file_path, encoding="UTF-8", xml_declaration=True)

    # Format the XML nicely
    with open(module_file_path) as f:
        lines = f.readlines()

    with open(module_file_path, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        for line in lines[1:]:
            f.write(line)

    print(f"Created module file: {module_file_path}")


def main():
    """
    Main function to generate module files for all projects.
    """
    vds_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    print(f"Generating IntelliJ IDEA module files in: {vds_root}")

    # Create module files for each project
    for project_name, modules in PROJECTS.items():
        for module_name in modules:
            # Determine module type based on project characteristics
            module_type = "JAVA_MODULE"  # Default

            # Check if it's a Python project
            module_path = os.path.join(vds_root, project_name, module_name)
            if (
                os.path.exists(os.path.join(module_path, "pyproject.toml"))
                or os.path.exists(os.path.join(module_path, "setup.py"))
                or os.path.exists(os.path.join(module_path, "requirements.txt"))
            ):
                module_type = "PYTHON_MODULE"

            # Check if it's a Node.js project
            elif os.path.exists(os.path.join(module_path, "package.json")):
                module_type = "WEB_MODULE"

            create_module_xml(vds_root, project_name, module_name, module_type)

    print("Module generation complete!")


if __name__ == "__main__":
    main()
