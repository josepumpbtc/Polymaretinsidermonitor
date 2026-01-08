🐳 Polymarket Whale Tracker Bot
An automated Looping Agent that monitors Polymarket for high-value trades ("Whale" activity). It filters transactions, resolves wallet addresses to Polymarket usernames, and delivers a daily summary report directly to a Telegram channel.

🚀 Key Features
Threshold Filtering: Automatically captures single trades exceeding $3,000 USD.

Username Resolution: Integrates with the Polymarket Gamma API to convert 0x-addresses into human-readable display names.

Automated Delivery: Generates a clean .csv report and broadcasts it to the @polyinsidermonitor Telegram channel.

Serverless Operation: Configured to run for free via GitHub Actions (no VPS required).

Real-time Data: Queries the official Goldsky Subgraph for the most accurate on-chain transaction data.


🛠️ Tech Stack
Language: Python 3.9+

Data Processing: Pandas

Data Source: Goldsky GraphQL (Polymarket Activity Subgraph)

User Info: Polymarket Gamma API

Automation: GitHub Actions 

Communication: Telegram Bot API


Column,Description
bet_size,The total amount of the trade in USDC/USD.
username,The user's Polymarket display name (falls back to 0x-address if not set).
token_id,The unique identifier for the specific outcome token.
token_outcome_name,"The specific result predicted (e.g., ""Yes"", ""No"", ""Donald Trump"")."
market,The question/market the user is betting on.
time_utc,Timestamp of the transaction in UTC.


⚙️ Setup & Installation
1. Telegram Configuration
Invite your bot (@polyinsidertstbot) to your channel (@polyinsidermonitor).

Promote the bot to Administrator with permission to Post Messages.

2. GitHub Secrets Setup
To keep your credentials secure, do not hardcode them. Add them to your GitHub Repository:

Go to Settings > Secrets and variables > Actions.

Click New repository secret and add:

TELEGRAM_TOKEN: 8289795345:AAGwY_sVtvsZBC2VEazZG3Wl1hh9ltAEqo4

3. Deployment
Push the polymarket_agent.py script to your main branch.

Create a file at .github/workflows/daily_report.yml using the configuration provided.

The bot will now run automatically every day at 00:00 UTC.


🖥️ Local Usage
If you wish to run the agent manually on your local machine:

Bash

# Install dependencies
pip install requests pandas

# Set your token as an environment variable
export TELEGRAM_TOKEN="your_token_here"

# Run the script
python polymarket_agent.py
