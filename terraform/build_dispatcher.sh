#!/bin/bash
# Build dispatcher.zip for Terraform deployment
set -e
cd "$(dirname "$0")"
zip -j dispatcher.zip dispatcher.py
echo "dispatcher.zip created"
