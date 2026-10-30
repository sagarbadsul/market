import os
import sys
import requests
from bs4 import BeautifulSoup
import urllib.parse

def scrape_market_data():
    """Scrapes market performance and statistics using standard browser headers."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    results = {
        "dow_green": False,
        "nasdaq_green": False,
        "india_vix": 13.5,  # Default fallback
        "advances": 0,
        "declines": 0
    }

    try:
        # 1. Scraping US Indices & India VIX from Investing.com
        # Dow Jones Industrial Average
        dow_resp = requests.get("https://www.investing.com/indices/us-30", headers=headers, timeout=10)
        if dow_resp.status_code == 200:
            soup = BeautifulSoup(dow_resp.text, 'html.parser')
            change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'}) or soup.find('span', class_='key-info_italic-decrement__DJe_X')
            if change_elem and '-' not in change_elem.text:
                results["dow_green"] = True

        # Nasdaq Composite
        nasdaq_resp = requests.get("https://www.investing.com/indices/nasdaq-composite", headers=headers, timeout=10)
        if nasdaq_resp.status_code == 200:
            soup = BeautifulSoup(nasdaq_resp.text, 'html.parser')
            change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'})
            if change_elem and '-' not in change_elem.text:
                results["nasdaq_green"] = True

        # India VIX
        vix_resp = requests.get("https://www.investing.com/indices/india-vix", headers=headers, timeout=10)
        if vix_resp.status_code == 200:
            soup = BeautifulSoup(vix_resp.text, 'html.parser')
            price_elem = soup.find('div', {'data-test': 'instrument-price-last'}) or soup.find('span', class_='text-2xl')
            if price_elem:
                results["india_vix"] = float(price_elem.text.replace(',', '').strip())

        # 2. Scraping NSE Advances/Declines from Moneycontrol Market Statistics alternative
        mc_resp = requests.get("https://www.moneycontrol.com/stocks/marketstats/nsemarketstats/nseadvance.php", headers=headers, timeout=10)
        if mc_resp.status_code == 200:
            soup = BeautifulSoup(mc_resp.text, 'html.parser')
            # Look for Advance and Decline count tables/elements
            adv_elem = soup.find('td', text=lambda t: t and 'Advances' in t)
            # Fallback robust parsing for market stats tables
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
    """Processes scraped data according to exact algorithmic rules."""
    # US Markets Rule
    if not data["dow_green"] and not data["nasdaq_green"]:
        us_trend = "Indian market trend is negative."
    elif data["dow_green"] and data["nasdaq_green"]:
        us_trend = "Indian market trend is positive."
    else:
        us_trend = "Indian market trend is mixed."

    # India VIX Rule
    vix = data["india_vix"]
    if 14 <= vix <= 15:
        vix_note = "Market will have volatile moves."
    elif vix < 14:
        vix_note = "Market will be stable."
    else:
        vix_note = f"Market volatility is elevated (VIX: {vix})."

    # NSE Advances/Declines Rule
    if data["advances"] > data["declines"]:
        momentum_note = "Market internal momentum is up."
    else:
        momentum_note = "Market internal momentum is down."

    return f"US Context: {us_trend} VIX Status: {vix_note} Internal Momentum: {momentum_note} (Advances: {data['advances']}, Declines: {data['declines']}, VIX: {vix})"

def generate_ai_summary(rules_text, api_key):
    """Sends calculated rules to Google Gemini API for a concise synthesis under 30 words."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
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

def send_telegram_message(message, token, chat_id):
    """Sends the formatted message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram alert sent successfully.")
        else:
            print(f"Failed to send Telegram alert. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

if __name__ == "__main__":
    gemini_key = os.environ.get("GEMINI_API_KEY")
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not all([gemini_key, telegram_token, telegram_chat_id]):
        print("Error: Missing required environment variables.")
        sys.exit(1)

    print("Scraping market data...")
    raw_data = scrape_market_data()
    
    print("Applying algorithmic rules...")
    rules_summary = process_market_rules(raw_data)
    
    print("Generating AI synthesis...")
    final_conclusion = generate_ai_summary(rules_summary, gemini_key)
    
    print(f"Final Output: {final_conclusion}")
    
    print("Sending Telegram alert...")
    send_telegram_message(final_conclusion, telegram_token, telegram_chat_id)
