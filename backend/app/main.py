from fastapi import FastAPI
import yfinance as yf

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
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)