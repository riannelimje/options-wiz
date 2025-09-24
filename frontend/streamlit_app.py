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
        
        # TODO: options data analysis
        st.subheader("Options Analysis")
        st.info("Options pricing coming soon!")
        
        # TODO: Replace with real options chain data - create in backend 
        st.write("**Sample Options Chain Preview:**")
        sample_data = pd.DataFrame({
            'Strike': [140, 145, 150, 155, 160],
            'Call Price': [12.50, 8.25, 4.75, 2.10, 0.85],
            'Put Price': [0.95, 2.30, 4.85, 8.90, 14.25],
            'Call Volume': [245, 189, 456, 123, 67],
            'Put Volume': [89, 145, 234, 189, 156]
        })
        st.dataframe(sample_data, width='stretch')