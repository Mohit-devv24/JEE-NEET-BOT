#!/bin/bash
# Start StudyMate Telegram Bot
cd "$(dirname "$0")"
source .venv/bin/activate
python bot.py
