#!/usr/bin/env bash
# Render build script — runs during the build phase

set -e

# WeasyPrint requires Pango/HarfBuzz system libraries
apt-get update -qq
apt-get install -y -qq \
  libpango-1.0-0 \
  libpangoft2-1.0-0 \
  libharfbuzz0b \
  libffi-dev \
  libjpeg-dev \
  libopenjp2-7

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
