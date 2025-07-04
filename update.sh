#!/bin/bash
cd "${HOME}/busdisplay"
git fetch --quiet
git reset --hard origin/main --quiet
exit 0