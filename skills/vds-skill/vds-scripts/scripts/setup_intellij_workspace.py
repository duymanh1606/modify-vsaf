#!/usr/bin/env python3
"""
VDS CLI command to set up IntelliJ IDEA workspace for the VDS monorepo.
"""

import os
import subprocess
import sys


def setup_intellij_workspace():
    """
    Set up IntelliJ IDEA workspace by generating module files and updating modules.xml.
    """
    # Get the VDS root directory
    vds_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    scripts_dir = os.path.join(vds_root, "vds-scripts", "scripts")

    print("Setting up IntelliJ IDEA workspace for VDS monorepo...")
    print(f"VDS Root: {vds_root}")

    # Run the module generation script
    print("\n1. Generating IntelliJ IDEA module files...")
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(scripts_dir, "generate_intellij_modules.py")],
            cwd=scripts_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error generating module files: {result.stderr}")
            return False

        print(result.stdout)
    except Exception as e:
        print(f"Error running module generation script: {e}")
        return False

    # Run the modules.xml update script
    print("\n2. Updating modules.xml file...")
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(scripts_dir, "update_modules_xml.py")],
            cwd=scripts_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error updating modules.xml: {result.stderr}")
            return False

        print(result.stdout)
    except Exception as e:
        print(f"Error running modules.xml update script: {e}")
        return False

    print("\n3. IntelliJ IDEA workspace setup complete!")
    print("\nNext steps:")
    print("1. Refresh your project in IntelliJ IDEA (Ctrl+Alt+Y / Cmd+Alt+Y)")
    print("2. The project should now be organized with all modules grouped by project type")
    print("3. If modules don't appear, go to File → Project Structure → Modules to import them")

    return True


if __name__ == "__main__":
    success = setup_intellij_workspace()
    sys.exit(0 if success else 1)
