import streamlit as st
import requests
import pandas as pd

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="OptionsWiz",
    page_icon="📈",
    layout="wide" # makes app full browser width
)

st.title("📈 OptionsWiz")
st.subheader("Interactive Options Strategy Analyser")

def get_stock_data(symbol):
    """Fetch stock data from backend"""
    try:
        response = requests.get(f"{API_BASE_URL}/stock/{symbol}")
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API returned status {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. Make sure FastAPI server is running on port 8000"}
    except Exception as e:
        return {"error": str(e)}

def get_options_data(symbol):
    """Fetch options chain data from backend"""
    try:
        response = requests.get(f"{API_BASE_URL}/options/{symbol}")
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API returned status {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. Make sure FastAPI server is running on port 8000"}
    except Exception as e:
        return {"error": str(e)}

# Sidebar for inputs
st.sidebar.header("Stock Information")
symbol = st.sidebar.text_input("Enter Ticker Symbol", value="AAPL")

if symbol:
    st.write(f"Selected Symbol: **{symbol.upper()}**")
    
    # Fetch real data from backend
    with st.spinner("Fetching stock data..."):
        stock_data = get_stock_data(symbol)
    
    if "error" in stock_data:
        st.error(f"{stock_data['error']}")
    else:
        # Display real data
        st.success(f"Found: {stock_data.get('company_name', 'N/A')}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            price = stock_data.get('current_price')
            if price:
                st.metric("Current Price", f"${price:.2f}", delta=None)
            else:
                st.metric("Current Price", "N/A")
        
        with col2:
            st.metric("Currency", stock_data.get('currency', 'N/A'))
        
        with col3:
            st.metric("Symbol", stock_data.get('ticker', symbol.upper()))
        
        # Show raw data for debugging 
        with st.expander("Debug: Raw API Response"):
            st.json(stock_data)
        
        # Options Chain Section
        st.subheader("📊 Options Chain Analysis")
        
        # Fetch options data
        with st.spinner("Fetching options chain data..."):
            options_data = get_options_data(symbol)
        
        if "error" in options_data:
            st.error(f"Options Error: {options_data['error']}")
            st.info("This stock may not have options available.")
        else:
            # Display options chain info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Expiration Date", options_data.get('expiration_date', 'N/A'))
            with col2:
                st.metric("Days to Expiration", f"{options_data.get('days_to_expiration', 0)} days")
            with col3:
                st.metric("Available Expirations", len(options_data.get('available_expirations', [])))
            
            # Create tabs for calls and puts
            call_tab, put_tab = st.tabs(["📈 Calls", "📉 Puts"])
            
            with call_tab:
                calls_data = options_data.get('calls', [])
                if calls_data:
                    # Convert to DataFrame for better display
                    calls_df = pd.DataFrame(calls_data)
                    
                    # Select relevant columns for display
                    display_columns = ['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']
                    available_columns = [col for col in display_columns if col in calls_df.columns]
                    
                    if available_columns:
                        display_df = calls_df[available_columns].copy()
                        
                        # Format columns for better readability
                        if 'lastPrice' in display_df.columns:
                            display_df['lastPrice'] = display_df['lastPrice'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
                        if 'bid' in display_df.columns:
                            display_df['bid'] = display_df['bid'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
                        if 'ask' in display_df.columns:
                            display_df['ask'] = display_df['ask'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
                        if 'impliedVolatility' in display_df.columns:
                            display_df['impliedVolatility'] = display_df['impliedVolatility'].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")
                        
                        # Rename columns for display
                        column_names = {
                            'strike': 'Strike',
                            'lastPrice': 'Last Price',
                            'bid': 'Bid',
                            'ask': 'Ask',
                            'volume': 'Volume',
                            'openInterest': 'Open Interest',
                            'impliedVolatility': 'Implied Vol'
                        }
                        display_df = display_df.rename(columns=column_names)
                        
                        st.dataframe(display_df, use_container_width=True)
                    else:
                        st.write("Call options data available but columns need formatting")
                        st.dataframe(calls_df, use_container_width=True)
                else:
                    st.info("No call options data available for this symbol")
            
            with put_tab:
                puts_data = options_data.get('puts', [])
                if puts_data:
                    # Convert to DataFrame for better display
                    puts_df = pd.DataFrame(puts_data)
                    
                    # Select relevant columns for display
                    display_columns = ['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']
                    available_columns = [col for col in display_columns if col in puts_df.columns]
                    
                    if available_columns:
                        display_df = puts_df[available_columns].copy()
                        
                        # Format columns for better readability
                        if 'lastPrice' in display_df.columns:
                            display_df['lastPrice'] = display_df['lastPrice'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
                        if 'bid' in display_df.columns:
                            display_df['bid'] = display_df['bid'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
                        if 'ask' in display_df.columns:
                            display_df['ask'] = display_df['ask'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
                        if 'impliedVolatility' in display_df.columns:
                            display_df['impliedVolatility'] = display_df['impliedVolatility'].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")
                        
                        # Rename columns for display
                        column_names = {
                            'strike': 'Strike',
                            'lastPrice': 'Last Price',
                            'bid': 'Bid',
                            'ask': 'Ask',
                            'volume': 'Volume',
                            'openInterest': 'Open Interest',
                            'impliedVolatility': 'Implied Vol'
                        }
                        display_df = display_df.rename(columns=column_names)
                        
                        st.dataframe(display_df, use_container_width=True)
                    else:
                        st.write("Put options data available but columns need formatting")
                        st.dataframe(puts_df, use_container_width=True)
                else:
                    st.info("No put options data available for this symbol")
            
            # Show additional expiration dates available
            available_exps = options_data.get('available_expirations', [])
            if len(available_exps) > 1:
                st.info(f"📅 Other available expiration dates: {', '.join(available_exps[1:])}")
            
            # Debug section for options data
            with st.expander("Debug: Raw Options API Response"):
                st.json(options_data)