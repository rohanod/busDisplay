#!/bin/bash
cd "${HOME}/busdisplay"
git fetch --quiet
git reset --hard origin/main --quiet
chown -R "$(whoami):$(whoami)" .
exit 0