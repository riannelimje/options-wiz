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

def get_options_data(symbol, expiration=None):
    """Fetch options chain data from backend"""
    try:
        url = f"{API_BASE_URL}/options/{symbol}"
        if expiration:
            url += f"?expiration={expiration}"
        
        response = requests.get(url)
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
            # Smart Expiration Date Selector
            available_exps = options_data.get('available_expirations', [])
            current_exp_date = options_data.get('expiration_date', 'N/A')
            
            if len(available_exps) > 1:
                st.subheader("📅 Select Expiration Date")
                
                # Create enhanced selector options with metadata
                exp_options = {}
                exp_labels = []
                
                for exp_info in available_exps:
                    date = exp_info['date']
                    days = exp_info['days_until_expiration']
                    category = exp_info['category']
                    formatted_date = exp_info['formatted_date']
                    is_current = exp_info.get('is_current', False)
                    
                    # Create rich label with category emoji
                    category_emoji = {
                        'weekly': '⚡', 
                        'short-term': '📅', 
                        'monthly': '🗓️', 
                        'quarterly': '📆'
                    }
                    emoji = category_emoji.get(category, '📅')
                    
                    # Format: "⚡ Oct 03, 2025 (3 days) - Weekly [CURRENT]"
                    label = f"{emoji} {formatted_date} ({days} days) - {category.title()}"
                    if is_current:
                        label += " [CURRENT]"
                    
                    exp_options[label] = date
                    exp_labels.append(label)
                
                # Find current selection index
                current_index = 0
                for i, (label, date) in enumerate(exp_options.items()):
                    if date == current_exp_date:
                        current_index = i
                        break
                
                selected_exp_label = st.selectbox(
                    "Choose expiration date:",
                    options=exp_labels,
                    index=current_index,
                    help="📊 Categories: ⚡Weekly (≤7 days), 📅Short-term (8-30 days), 🗓️Monthly (31-90 days), 📆Quarterly (91-180 days)"
                )
                
                selected_exp_date = exp_options[selected_exp_label]
                
                # If user selected a different expiration, fetch that data
                if selected_exp_date != current_exp_date:
                    with st.spinner(f"🔄 Loading options for {selected_exp_date}..."):
                        options_data = get_options_data(symbol, selected_exp_date)
                    
                    if "error" in options_data:
                        st.error(f"Error loading {selected_exp_date}: {options_data['error']}")
                        # Fallback to original data
                        options_data = get_options_data(symbol)
                    else:
                        st.success(f"✅ Loaded options for {selected_exp_date}")
                        # Update current expiration info for display
                        current_exp_date = selected_exp_date
            
            # Current Selection Info
            st.subheader("📊 Current Options Chain")
            
            # Enhanced metrics display
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Expiration Date", options_data.get('expiration_date', 'N/A'))
            with col2:
                days_to_exp = options_data.get('days_to_expiration', 0)
                st.metric("Days to Expiration", f"{days_to_exp} days")
            with col3:
                # Find current expiration category from the updated data
                current_exp_from_data = options_data.get('expiration_date', 'N/A')
                current_category = "Unknown"
                for exp_info in options_data.get('available_expirations', []):
                    if exp_info['date'] == current_exp_from_data:
                        current_category = exp_info['category'].title()
                        break
                st.metric("Category", current_category)
            with col4:
                st.metric("Total Expirations", len(options_data.get('available_expirations', [])))
            
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
            
            # Options Summary & Tips
            if len(available_exps) > 1:
                st.subheader("💡 Options Trading Tips")
                
                # Categorize available expirations for display
                categories = {}
                for exp_info in available_exps:
                    category = exp_info['category']
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(exp_info)
                
                # Display category summary
                cols = st.columns(len(categories))
                for i, (category, exps) in enumerate(categories.items()):
                    with cols[i]:
                        emoji_map = {'weekly': '⚡', 'short-term': '📅', 'monthly': '🗓️', 'quarterly': '📆'}
                        emoji = emoji_map.get(category, '📅')
                        st.metric(f"{emoji} {category.title()}", f"{len(exps)} options")
                
                # Trading insights based on current selection
                days_to_exp = options_data.get('days_to_expiration', 0)
                if days_to_exp <= 7:
                    st.info("⚡ **Weekly Options**: High gamma, time decay accelerates rapidly. Great for short-term directional plays.")
                elif days_to_exp <= 30:
                    st.info("📅 **Short-term Options**: Balanced risk/reward. Popular for earnings plays and swing trading.")
                elif days_to_exp <= 90:
                    st.info("🗓️ **Monthly Options**: Good for strategies, moderate time decay. Suitable for covered calls and protective puts.")
                else:
                    st.info("📆 **Quarterly Options**: Lower time decay, higher premium. Good for long-term strategies and LEAPS.")
            
            # Debug section for options data
            with st.expander("Debug: Raw Options API Response"):
                st.json(options_data)