import subprocess
import os
import re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--version', default='')
args = parser.parse_args()

# Get version from git
if args.version.strip():
    version = args.version.strip()
else:
    try:
        version = subprocess.check_output(['git', 'describe', '--tags', '--abbrev=0']).decode('utf-8').strip()
        if version.startswith('v'):
            version = version[1:]
    except Exception as e:
        print(f"Could not get version from git: {e}")
        # Fallback to a predefined version or exit
        version = "1.9.4" # Fallback

# Read installer.py
with open('installer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace version
content = re.sub(r'PLUGIN_VERSION = ".*"', f'PLUGIN_VERSION = "{version}"', content)

# Write to a new file
with open('installer_preped.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("installer_preped.py created with version " + version)
