#!/bin/bash
git -C "${HOME}/busdisplay" pull --rebase --quiet || true
exit 0