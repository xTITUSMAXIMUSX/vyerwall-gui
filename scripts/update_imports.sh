#!/bin/bash

# Update all imports from old structure to new structure

find /home/ubuntu/vyerwall-gui/app/modules -type f -name "*.py" -exec sed -i 's/from auth_utils import/from app.auth import/g' {} \;
find /home/ubuntu/vyerwall-gui/app/modules -type f -name "*.py" -exec sed -i 's/from config_manager import/from app.core import/g' {} \;

echo "Import updates complete"
