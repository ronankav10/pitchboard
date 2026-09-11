#!/bin/zsh
cd "$HOME/pitchboard" || { echo "Could not find ~/pitchboard — is this file in the right place?"; read -r "?Press Enter to close..."; exit 1; }

echo "Starting Pitchboard..."
echo "A browser tab should open automatically in a few seconds."
echo "Leave this window open while you're using the app — closing it stops the app."
echo ""

python3 -m streamlit run app.py

echo ""
read -r "?App stopped. Press Enter to close this window..."
