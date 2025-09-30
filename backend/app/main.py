from fastapi import FastAPI, HTTPException
import yfinance as yf
import pandas as pd

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Welcome to OptionsWiz"}

@app.get("/stock/{symbol}")
async def get_stock_price(symbol: str):
    try: 
        ticker = yf.Ticker(symbol)
        info = ticker.info
        current_price = info.get("currentPrice", info.get("regularMarketPrice"))

        return {
            "ticker": symbol.upper(),
            "current_price": current_price,
            "company_name": info.get("shortName", "N/A"),
            "currency": info.get("currency", "N/A")
        }
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/options/{symbol}")
async def get_options_chain(symbol: str, expiration: str = None):
    """Get options chain for a symbol with optional expiration date"""
    try:
        print(f"Fetching options for symbol: {symbol}")
        ticker = yf.Ticker(symbol)
        
        print("Getting ticker info...")
        info = ticker.info
        current_price = info.get("currentPrice", info.get("regularMarketPrice"))
        print(f"Current price: {current_price}")
        
        if not current_price:
            raise HTTPException(status_code=404, detail="Stock price not found")
        
        print("Getting available expirations...")
        expirations = ticker.options
        print(f"Available expirations: {expirations}")
        
        if not expirations:
            return {"error": "No options data available for this symbol"}
        
        # Determine which expiration date to use
        if expiration:
            # User specified an expiration date
            if expiration in expirations:
                exp_date = expiration
                print(f"Using user-specified expiration: {exp_date}")
            else:
                return {"error": f"Expiration date {expiration} not available for {symbol}"}
        else:
            # Find the first non-expired expiration date
            exp_date = None
            today = pd.Timestamp.now().date()
            print(f"Today's date: {today}")
            
            for exp in expirations:
                exp_datetime = pd.to_datetime(exp).date()
                print(f"Checking expiration: {exp} -> {exp_datetime}")
                if exp_datetime > today:  
                    exp_date = exp
                    print(f"Selected expiration: {exp_date}")
                    break
            
            if not exp_date:
                return {"error": "No active (non-expired) options available for this symbol"}
        
        print(f"Getting options chain for {exp_date}...")
        options_chain = ticker.option_chain(exp_date)
        
        # Process calls and puts
        print("Processing calls and puts...")
        calls = options_chain.calls.to_dict('records') if not options_chain.calls.empty else []
        puts = options_chain.puts.to_dict('records') if not options_chain.puts.empty else []
        
        print(f"Found {len(calls)} calls and {len(puts)} puts")
        
        # Clean data - replace NaN, inf, -inf with None for JSON compatibility
        def clean_float_values(data_list):
            """Clean float values that can't be JSON serialized"""
            import math
            cleaned_data = []
            for item in data_list:
                cleaned_item = {}
                for key, value in item.items():
                    if isinstance(value, float):
                        if math.isnan(value) or math.isinf(value):
                            cleaned_item[key] = None
                        else:
                            cleaned_item[key] = value
                    else:
                        cleaned_item[key] = value
                cleaned_data.append(cleaned_item)
            return cleaned_data
        
        print("Cleaning data for JSON compatibility...")
        calls = clean_float_values(calls)
        puts = clean_float_values(puts)
        
        # Calculate days to expiration
        exp_datetime = pd.to_datetime(exp_date)
        days_to_exp = (exp_datetime - pd.Timestamp.now()).days
        
        # TODO: add a parameter to customer strike range 
        # Get strikes within +/- 10% of current price
        print("Filtering relevant options...")
        relevant_calls = [
            call for call in calls 
            if current_price * 0.9 <= call['strike'] <= current_price * 1.1
        ][:10]  # limit to 10 results if not will be too huge

        relevant_puts = [
            put for put in puts 
            if current_price * 0.9 <= put['strike'] <= current_price * 1.1
        ][:10]
        
        print(f"Returning {len(relevant_calls)} relevant calls and {len(relevant_puts)} relevant puts")
        
        # Smart expiration filtering with metadata
        def categorize_expiration(days_until_exp):
            """Categorize expiration by time frame"""
            if days_until_exp <= 7:
                return "weekly"
            elif days_until_exp <= 30:
                return "short-term"
            elif days_until_exp <= 90:
                return "monthly"
            elif days_until_exp <= 180:
                return "quarterly"
            else:
                return "long-term"
        
        print("Creating smart expiration list with metadata...")
        smart_expirations = []
        today = pd.Timestamp.now().date()
        
        for exp in expirations:
            exp_date_obj = pd.to_datetime(exp).date()
            days_until_exp = (exp_date_obj - today).days
            
            # Include expirations within next 6 months (180 days)
            # This covers weeklies, monthlies, and some quarterlies
            if 0 < days_until_exp <= 180:
                exp_category = categorize_expiration(days_until_exp)
                smart_expirations.append({
                    "date": exp,
                    "days_until_expiration": days_until_exp,
                    "category": exp_category,
                    "is_current": exp == exp_date,
                    "formatted_date": exp_date_obj.strftime("%b %d, %Y"),
                    "trading_days_approx": int(days_until_exp * 5/7)  # Rough estimate excluding weekends
                })
        
        # Sort by days until expiration and limit to 12 most relevant
        smart_expirations = sorted(smart_expirations, key=lambda x: x["days_until_expiration"])[:12]
        
        print(f"Smart filtering returned {len(smart_expirations)} relevant expirations")
        
        return {
            "symbol": symbol.upper(),
            "current_price": current_price,
            "expiration_date": exp_date,
            "days_to_expiration": days_to_exp,
            "calls": relevant_calls,  
            "puts": relevant_puts,    
            "available_expirations": smart_expirations  # Enhanced with metadata!
        }
        
    except Exception as e:
        print(f"ERROR in get_options_chain: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Internal error: {str(e)}"}
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)