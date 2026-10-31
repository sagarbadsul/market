import os
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import yfinance as yf

def scrape_market_data():
    """Fetches live market data using yfinance for reliable accuracy."""
    results = {
        "dow_val": "N/A",
        "dow_change": "N/A",
        "dow_green": False,
        "nasdaq_val": "N/A",
        "nasdaq_change": "N/A",
        "nasdaq_green": False,
        "india_vix": "13.5",
        "advances": "N/A",
        "declines": "N/A"
    }

    try:
        # Fetch Dow Jones (^DJI) and Nasdaq Composite (^IXIC)
        tickers = {"dow": "^DJI", "nasdaq": "^IXIC"}
        
        for key, symbol in tickers.items():
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                change_pct = ((current_price - prev_price) / prev_price) * 100
                
                price_str = f"{current_price:,.2f}"
                change_str = f"{'+' if change_pct >= 0 else ''}{change_pct:.2f}%"
                
                results[f"{key}_val"] = price_str
                results[f"{key}_change"] = change_str
                results[f"{key}_green"] = change_pct >= 0

        # Fetch India VIX (^INDIAVIX) via Yahoo Finance
        vix_ticker = yf.Ticker("^INDIAVIX")
        vix_hist = vix_ticker.history(period="1d")
        if not vix_hist.empty:
            results["india_vix"] = f"{vix_hist['Close'].iloc[-1]:.2f}"

        # NSE Advances/Declines fallback from Moneycontrol or static estimate if blocked
        headers = {"User-Agent": "Mozilla/5.0"}
        mc_resp = requests.get("https://www.moneycontrol.com/stocks/marketstats/nsemarketstats/nseadvance.php", headers=headers, timeout=5)
        if mc_resp.status_code == 200:
            soup = BeautifulSoup(mc_resp.text, 'html.parser')
            for row in soup.find_all('tr'):
                text = row.text.lower()
                cols = row.find_all('td')
                if 'advances' in text and len(cols) > 1:
                    results["advances"] = cols[1].text.strip()
                elif 'declines' in text and len(cols) > 1:
                    results["declines"] = cols[1].text.strip()

    except Exception as e:
        print(f"Warning during data fetch: {e}")

    return results

    
def process_market_rules(data):
    """Processes scraped data according to algorithmic rules."""
    if not data["dow_green"] and not data["nasdaq_green"]:
        us_trend = "Indian market trend is negative."
    elif data["dow_green"] and data["nasdaq_green"]:
        us_trend = "Indian market trend is positive."
    else:
        us_trend = "Indian market trend is mixed."

    try:
        vix = float(data["india_vix"])
    except:
        vix = 14.0

    if 14 <= vix <= 15:
        vix_note = "Market will have volatile moves."
    elif vix < 14:
        vix_note = "Market will be stable."
    else:
        vix_note = f"Market volatility is elevated (VIX: {vix})."

    try:
        adv = int(data["advances"])
        dec = int(data["declines"])
    except:
        adv, dec = 0, 0

    if adv > dec:
        momentum_note = "Market internal momentum is up."
    else:
        momentum_note = "Market internal momentum is down."

    return f"US Context: {us_trend} VIX Status: {vix_note} Internal Momentum: {momentum_note} (Advances: {adv}, Declines: {dec}, VIX: {vix})"

def generate_ai_summary(rules_text, api_key):
    """Sends calculated rules to Google Gemini API for a concise synthesis under 30 words."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = (
        "Synthesize the following market indicators into a final, cohesive stock market conclusion "
        "strictly under 30 words:\n\n" + rules_text
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        
    return rules_text[:100]

def save_web_page(data, ai_summary, update_time):
    """Saves a rich HTML dashboard displaying actual numbers, conditional colors, and update timestamp."""
    dow_color = "#22c55e" if data["dow_green"] else "#ef4444"
    nasdaq_color = "#22c55e" if data["nasdaq_green"] else "#ef4444"
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Market Analysis Agent</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
        .card {{ background: #1e293b; padding: 2rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); width: 100%; max-width: 450px; border: 1px solid #334155; box-sizing: border-box; }}
        h1 {{ font-size: 1.4rem; margin-bottom: 1.2rem; color: #38bdf8; text-align: center; }}
        .metrics-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; }}
        .metric-box {{ background: #0f172a; padding: 1rem; border-radius: 8px; border: 1px solid #334155; text-align: center; }}
        .metric-title {{ font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.4rem; }}
        .metric-value {{ font-size: 1.1rem; font-weight: bold; }}
        .ai-box {{ background: #0f172a; padding: 1.2rem; border-radius: 8px; border: 1px solid #334155; margin-bottom: 1.2rem; }}
        .ai-title {{ font-size: 0.85rem; color: #38bdf8; margin-bottom: 0.5rem; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }}
        .ai-text {{ font-size: 1rem; line-height: 1.5; color: #cbd5e1; margin: 0; }}
        .footer {{ text-align: center; font-size: 0.75rem; color: #64748b; line-height: 1.4; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>📊 Daily Market Dashboard</h1>
        
        <div class="metrics-grid">
            <div class="metric-box">
                <div class="metric-title">Dow Jones</div>
                <div class="metric-value" style="color: {dow_color};">{data['dow_val']} ({data['dow_change']})</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Nasdaq Composite</div>
                <div class="metric-value" style="color: {nasdaq_color};">{data['nasdaq_val']} ({data['nasdaq_change']})</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">India VIX</div>
                <div class="metric-value" style="color: #facc15;">{data['india_vix']}</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">NSE Adv / Dec</div>
                <div class="metric-value" style="color: #38bdf8;">{data['advances']} / {data['declines']}</div>
            </div>
        </div>

        <div class="ai-box">
            <div class="ai-title">AI Synthesis</div>
            <p class="ai-text">{ai_summary}</p>
        </div>

        <div class="footer">
            Last Updated: {update_time}<br>
            Automated daily via GitHub Actions & Gemini AI
        </div>
    </div>
</body>
</html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Saved index.html with live timestamp.")

if __name__ == "__main__":
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if not gemini_key:
        print("Error: Missing GEMINI_API_KEY environment variable.")
        sys.exit(1)

    print("Scraping market data...")
    raw_data = scrape_market_data()
    
    print("Applying algorithmic rules...")
    rules_summary = process_market_rules(raw_data)
    
    print("Generating AI synthesis...")
    final_conclusion = generate_ai_summary(rules_summary, gemini_key)
    
    # Generate IST timestamp
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    current_time_ist = datetime.now(ist_offset).strftime("%d %b %Y, %I:%M %p IST")
    
    print(f"Saving web page dashboard with timestamp: {current_time_ist}...")
    save_web_page(raw_data, final_conclusion, current_time_ist)
