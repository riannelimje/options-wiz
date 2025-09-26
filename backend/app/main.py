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
async def get_options_chain(symbol: str):
    """Get options chain for a symbol"""
    try:
        ticker = yf.Ticker(symbol)
        
        info = ticker.info
        current_price = info.get("currentPrice", info.get("regularMarketPrice"))
        
        if not current_price:
            raise HTTPException(status_code=404, detail="Stock price not found")
        
        expirations = ticker.options
        if not expirations:
            return {"error": "No options data available for this symbol"}
        
        # Get options for the first available expiration (nearest term)
        exp_date = expirations[0]
        options_chain = ticker.option_chain(exp_date)
        
        # Process calls and puts
        calls = options_chain.calls.to_dict('records') if not options_chain.calls.empty else []
        puts = options_chain.puts.to_dict('records') if not options_chain.puts.empty else []
        
        # Calculate days to expiration
        exp_datetime = pd.to_datetime(exp_date)
        days_to_exp = (exp_datetime - pd.Timestamp.now()).days
        
        # TODO: add a parameter to customer strike range 
        # Get strikes within +/- 10% of current price
        relevant_calls = [
            call for call in calls 
            if current_price * 0.9 <= call['strike'] <= current_price * 1.1
        ][:10]  # limit to 10 results if not will be too huge

        relevant_puts = [
            put for put in puts 
            if current_price * 0.9 <= put['strike'] <= current_price * 1.1
        ][:10]
        
        return {
            "symbol": symbol.upper(),
            "current_price": current_price,
            "expiration_date": exp_date,
            "days_to_expiration": days_to_exp,
            "calls": relevant_calls,  
            "puts": relevant_puts,    
            "available_expirations": list(expirations)[:5]  # show first 5 expiration dates
        }
        
    except Exception as e:
        return {"error": str(e)}
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)