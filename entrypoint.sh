#!/bin/bash

echo "===================="

git config --global user.name "${INPUT_NAME}"
git config --global user.email "${INPUT_EMAIL}"
git config --global --add safe.directory /github/workspace

# Run scanner with action inputs
python3 /usr/bin/scanner.py \
    --mode "${INPUT_SCAN_MODE:-auto}" \
    --output-dir "${INPUT_OUTPUT_DIR:-./reports}"

echo "===================="
