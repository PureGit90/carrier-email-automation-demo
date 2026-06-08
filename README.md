# Formspree → Claude API → Two-Path Email Automation

Demo for Houston auto-transport broker. Streamlit app that matches carriers to a shipment route using Claude API and generates email previews for two branches: carrier RFQ or customer notification.

## What It Does

1. Customer submits a Formspree booking form (pickup ZIP, delivery ZIP, vehicle type)
2. Claude API reads the carrier list CSV and identifies the best matching carriers
3. System routes to one of two email branches:
   - **Carrier RFQ**: emails matched carriers requesting rate quotes
   - **Customer Notification**: emails the customer with their carrier options

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# Run the app
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude |

You can also set this in `.streamlit/secrets.toml`:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

## Project Structure

```
.
├── app.py                    # Streamlit app (main entry point)
├── carrier_agent.py          # Claude API carrier-matching logic
├── requirements.txt          # Python dependencies
├── workflow.md               # Mermaid architecture diagram
├── sample_data/
│   └── carriers.csv          # 30-carrier mock dataset
└── README.md
```

## Model

Uses `claude-haiku-4-5-20251001` — fast and cost-efficient for structured extraction tasks. In production, the same model handles the full 800+ carrier list.

## Production Architecture

```
Formspree → n8n webhook → Claude API (carrier match) → SendGrid (email send) → Airtable (CRM log)
```

The Streamlit demo simulates the Claude matching step and email generation. No emails are actually sent in the demo.
