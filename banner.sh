#!/bin/bash

echo -ne "\\033[2J\033[3;1f"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cat "$SCRIPT_DIR/assets/banner.txt"
printf "\n"
