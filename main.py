import os
import sys
import requests
from bs4 import BeautifulSoup

def scrape_market_data():
    """Scrapes market performance and statistics using standard browser headers."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    results = {
        "dow_green": False,
        "nasdaq_green": False,
        "india_vix": 13.5,
        "advances": 0,
        "declines": 0
    }

    try:
        # 1. Dow Jones
        dow_resp = requests.get("https://www.investing.com/indices/us-30", headers=headers, timeout=10)
        if dow_resp.status_code == 200:
            soup = BeautifulSoup(dow_resp.text, 'html.parser')
            change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'}) or soup.find('span', class_='key-info_italic-decrement__DJe_X')
            if change_elem and '-' not in change_elem.text:
                results["dow_green"] = True

        # 2. Nasdaq Composite
        nasdaq_resp = requests.get("https://www.investing.com/indices/nasdaq-composite", headers=headers, timeout=10)
        if nasdaq_resp.status_code == 200:
            soup = BeautifulSoup(nasdaq_resp.text, 'html.parser')
            change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'})
            if change_elem and '-' not in change_elem.text:
                results["nasdaq_green"] = True

        # 3. India VIX
        vix_resp = requests.get("https://www.investing.com/indices/india-vix", headers=headers, timeout=10)
        if vix_resp.status_code == 200:
            soup = BeautifulSoup(vix_resp.text, 'html.parser')
            price_elem = soup.find('div', {'data-test': 'instrument-price-last'}) or soup.find('span', class_='text-2xl')
            if price_elem:
                results["india_vix"] = float(price_elem.text.replace(',', '').strip())

        # 4. NSE Advances/Declines
        mc_resp = requests.get("https://www.moneycontrol.com/stocks/marketstats/nsemarketstats/nseadvance.php", headers=headers, timeout=10)
        if mc_resp.status_code == 200:
            soup = BeautifulSoup(mc_resp.text, 'html.parser')
            rows = soup.find_all('tr')
            for row in rows:
                text = row.text.lower()
                if 'advances' in text:
                    cols = row.find_all('td')
                    if len(cols) > 1:
                        nums = [int(s) for s in cols[1].text.split() if s.isdigit()]
                        if nums:
                            results["advances"] = nums[0]
                if 'declines' in text:
                    cols = row.find_all('td')
                    if len(cols) > 1:
                        nums = [int(s) for s in cols[1].text.split() if s.isdigit()]
                        if nums:
                            results["declines"] = nums[0]

    except Exception as e:
        print(f"Warning during web scraping: {e}")

    return results

def process_market_rules(data):
    """Processes scraped data according to algorithmic rules."""
    if not data["dow_green"] and not data["nasdaq_green"]:
        us_trend = "Indian market trend is negative."
    elif data["dow_green"] and data["nasdaq_green"]:
        us_trend = "Indian market trend is positive."
    else:
        us_trend = "Indian market trend is mixed."

    vix = data["india_vix"]
    if 14 <= vix <= 15:
        vix_note = "Market will have volatile moves."
    elif vix < 14:
        vix_note = "Market will be stable."
    else:
        vix_note = f"Market volatility is elevated (VIX: {vix})."

    if data["advances"] > data["declines"]:
        momentum_note = "Market internal momentum is up."
    else:
        momentum_note = "Market internal momentum is down."

    return f"US Context: {us_trend} VIX Status: {vix_note} Internal Momentum: {momentum_note} (Advances: {data['advances']}, Declines: {data['declines']}, VIX: {vix})"

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

def save_web_page(message):
    """Saves the final AI conclusion into an HTML file for GitHub Pages."""
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Market Analysis Agent</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
        .card {{ background: #1e293b; padding: 2rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); max-width: 500px; text-align: center; border: 1px solid #334155; }}
        h1 {{ font-size: 1.5rem; margin-bottom: 1rem; color: #38bdf8; }}
        p {{ font-size: 1.1rem; line-height: 1.6; color: #cbd5e1; }}
        .footer {{ margin-top: 1.5rem; font-size: 0.8rem; color: #64748b; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>📊 Latest Market Summary</h1>
        <p>{message}</p>
        <div class="footer">Automated daily via GitHub Actions & Gemini AI</div>
    </div>
</body>
</html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Saved index.html for GitHub Pages.")

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
    
    print(f"Final Output: {final_conclusion}")
    
    print("Saving web page...")
    save_web_page(final_conclusion)
