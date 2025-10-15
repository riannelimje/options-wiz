from fastapi import FastAPI, HTTPException
import yfinance as yf
import pandas as pd
import numpy as np
import math
from calculations.greeks import OptionsGreeks
from calculations.black_scholes import BlackScholesModel, days_to_years, get_risk_free_rate

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

@app.get("/option-pnl/{symbol}")
async def calculate_option_pnl(
    symbol: str,
    option_type: str,  # "call" or "put"
    strike: float,
    premium: float,
    expiration_days: int = 30
):
    """
    Calculate profit/loss for a single option at various stock prices at expiration.
    
    Parameters:
    - symbol: Stock symbol (e.g., AAPL)
    - option_type: "call" or "put"
    - strike: Strike price of the option
    - premium: Premium paid for the option
    - expiration_days: Days to expiration (for reference, doesn't affect P&L at expiration)
    """
    try:
        print(f"Calculating P&L for {symbol} {option_type} option: Strike=${strike}, Premium=${premium}")
        
        # Get current stock price for reference
        ticker = yf.Ticker(symbol)
        info = ticker.info
        current_price = info.get("currentPrice", info.get("regularMarketPrice"))
        
        if not current_price:
            raise HTTPException(status_code=404, detail="Stock price not found")
        
        print(f"Current stock price: ${current_price}")
        
        # Generate stock price range for P&L calculation (±50% from current price)
        min_price = current_price * 0.5
        max_price = current_price * 1.5
        price_step = (max_price - min_price) / 100  # 100 data points for smooth curve
        
        stock_prices = []
        pnl_values = []
        option_values = []
        
        print(f"Generating P&L curve from ${min_price:.2f} to ${max_price:.2f}")
        
        for i in range(101):  # 101 points for 100 intervals
            stock_price = min_price + (i * price_step)
            stock_prices.append(round(stock_price, 2))
            
            # Calculate option value at expiration (intrinsic value only)
            if option_type.lower() == "call":
                option_value = max(0, stock_price - strike)
            elif option_type.lower() == "put":
                option_value = max(0, strike - stock_price)
            else:
                raise HTTPException(status_code=400, detail="option_type must be 'call' or 'put'")
            
            option_values.append(round(option_value, 2))
            
            # P&L = Option Value at Expiration - Premium Paid
            pnl = option_value - premium
            pnl_values.append(round(pnl, 2))
        
        # Calculate key metrics
        max_profit = max(pnl_values)
        max_loss = min(pnl_values)
        
        # Find breakeven point(s)
        breakeven_points = []
        for i, pnl in enumerate(pnl_values):
            if abs(pnl) < 0.01:  # Within 1 cent of breakeven
                breakeven_points.append(stock_prices[i])
        
        # Remove duplicates and keep only unique breakeven points
        breakeven_points = list(set(breakeven_points))
        breakeven_points.sort()
        
        # Calculate probability metrics (simplified)
        current_price_index = min(range(len(stock_prices)), 
                                key=lambda i: abs(stock_prices[i] - current_price))
        
        # Count profitable scenarios
        profitable_scenarios = sum(1 for pnl in pnl_values if pnl > 0)
        probability_of_profit = (profitable_scenarios / len(pnl_values)) * 100
        
        print(f"P&L calculation complete: Max Profit=${max_profit:.2f}, Max Loss=${max_loss:.2f}")
        print(f"Breakeven points: {breakeven_points}")
        
        return {
            "symbol": symbol.upper(),
            "option_type": option_type.lower(),
            "strike": strike,
            "premium": premium,
            "current_price": current_price,
            "expiration_days": expiration_days,
            
            # P&L Data for Charting
            "stock_prices": stock_prices,
            "pnl_values": pnl_values,
            "option_values": option_values,
            
            # Key Metrics
            "max_profit": max_profit if max_profit != float('inf') else None,
            "max_loss": max_loss,
            "breakeven_points": breakeven_points,
            "probability_of_profit": round(probability_of_profit, 1),
            
            # Additional Info
            "price_range": {
                "min": min_price,
                "max": max_price,
                "current_index": current_price_index
            },
            "analysis": {
                "in_the_money": (
                    current_price > strike if option_type.lower() == "call" 
                    else current_price < strike
                ),
                "intrinsic_value": max(0, 
                    current_price - strike if option_type.lower() == "call"
                    else strike - current_price
                ),
                "time_value": premium - max(0, 
                    current_price - strike if option_type.lower() == "call"
                    else strike - current_price
                )
            }
        }
        
    except Exception as e:
        print(f"ERROR in calculate_option_pnl: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Internal error: {str(e)}"}

@app.get("/option-greeks/{symbol}")
async def calculate_option_greeks(
    symbol: str,
    option_type: str,  # "call" or "put"
    strike: float,
    expiration_days: int,
    volatility: float = None  # Optional: will estimate from market data if not provided
):
    """
    Calculate Option Greeks (Delta, Gamma, Theta, Vega, Rho) for a given option.
    
    Parameters:
    - symbol: Stock symbol (e.g., AAPL)
    - option_type: "call" or "put"
    - strike: Strike price of the option
    - expiration_days: Days to expiration
    - volatility: Implied volatility (optional, will estimate if not provided)
    """
    try:
        print(f"Calculating Greeks for {symbol} {option_type} option: Strike=${strike}, Days={expiration_days}")
        
        # Get current stock price
        ticker = yf.Ticker(symbol)
        info = ticker.info
        current_price = info.get("currentPrice", info.get("regularMarketPrice"))
        
        if not current_price:
            raise HTTPException(status_code=404, detail="Stock price not found")
        
        print(f"Current stock price: ${current_price}")
        
        # Convert days to years
        time_to_expiration = days_to_years(expiration_days)
        
        # Get risk-free rate
        risk_free_rate = get_risk_free_rate()
        
        # Estimate volatility if not provided
        if volatility is None:
            print("Estimating volatility from historical data...")
            try:
                # Get 30 days of historical data to estimate volatility
                hist = ticker.history(period="1mo")
                if len(hist) > 5:
                    # Calculate daily returns
                    returns = hist['Close'].pct_change().dropna()
                    # Annualized volatility
                    volatility = returns.std() * math.sqrt(252)  # 252 trading days per year
                    print(f"Estimated volatility: {volatility:.4f} ({volatility*100:.2f}%)")
                else:
                    volatility = 0.25  # Default 25% if can't calculate
                    print("Using default volatility: 25%")
            except Exception as e:
                print(f"Error estimating volatility: {e}, using default 25%")
                volatility = 0.25
        else:
            print(f"Using provided volatility: {volatility:.4f} ({volatility*100:.2f}%)")
        
        # Calculate all Greeks
        greeks = OptionsGreeks.calculate_greeks(
            option_type=option_type.lower(),
            S=current_price,
            K=strike,
            T=time_to_expiration,
            r=risk_free_rate,
            sigma=volatility
        )
        
        # Get interpretations
        interpretations = OptionsGreeks.interpret_greeks(greeks, option_type.lower())
        
        # Calculate theoretical option price using Black-Scholes
        theoretical_price = BlackScholesModel.option_price(
            option_type=option_type.lower(),
            S=current_price,
            K=strike,
            T=time_to_expiration,
            r=risk_free_rate,
            sigma=volatility
        )
        
        # Calculate intrinsic value
        if option_type.lower() == "call":
            intrinsic_value = max(0, current_price - strike)
        else:  # put
            intrinsic_value = max(0, strike - current_price)
        
        # Time value is the difference
        time_value = max(0, theoretical_price - intrinsic_value)
        
        print(f"Greeks calculation complete: Delta={greeks['delta']:.4f}, Theta=${greeks['theta']:.4f}")
        
        return {
            "symbol": symbol.upper(),
            "option_type": option_type.lower(),
            "strike": strike,
            "current_price": current_price,
            "expiration_days": expiration_days,
            "time_to_expiration_years": round(time_to_expiration, 4),
            
            # Market Parameters
            "market_params": {
                "volatility": round(volatility, 4),
                "volatility_percent": round(volatility * 100, 2),
                "risk_free_rate": round(risk_free_rate, 4),
                "risk_free_rate_percent": round(risk_free_rate * 100, 2)
            },
            
            # Option Pricing
            "pricing": {
                "theoretical_price": round(theoretical_price, 2),
                "intrinsic_value": round(intrinsic_value, 2),
                "time_value": round(time_value, 2),
                "moneyness": "ITM" if intrinsic_value > 0 else "ATM" if abs(current_price - strike) < 1 else "OTM"
            },
            
            # Greeks
            "greeks": {
                "delta": round(greeks["delta"], 4),
                "gamma": round(greeks["gamma"], 4),
                "theta": round(greeks["theta"], 4),
                "vega": round(greeks["vega"], 4),
                "rho": round(greeks["rho"], 4)
            },
            
            # Human-readable interpretations
            "interpretations": interpretations,
            
            # Additional Analysis
            "analysis": {
                "delta_dollar_equivalent": round(greeks["delta"] * 100, 2),  # Per 100 shares
                "gamma_acceleration": "High" if greeks["gamma"] > 0.1 else "Moderate" if greeks["gamma"] > 0.05 else "Low",
                "theta_daily_decay": round(greeks["theta"], 2),
                "vega_iv_sensitivity": round(greeks["vega"] * 100, 2),  # For 100% IV change
                "rho_rate_sensitivity": round(greeks["rho"] * 100, 2),  # For 100bp rate change
                
                # Risk metrics
                "time_decay_risk": "High" if abs(greeks["theta"]) > 0.5 else "Moderate" if abs(greeks["theta"]) > 0.1 else "Low",
                "volatility_risk": "High" if greeks["vega"] > 0.2 else "Moderate" if greeks["vega"] > 0.1 else "Low"
            }
        }
        
    except Exception as e:
        print(f"ERROR in calculate_option_greeks: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Internal error: {str(e)}"}
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)