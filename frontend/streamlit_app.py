import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

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

def get_option_pnl(symbol, option_type, strike, premium, expiration_days):
    """Fetch option P&L data from backend"""
    try:
        url = f"{API_BASE_URL}/option-pnl/{symbol}"
        params = {
            'option_type': option_type,
            'strike': strike,
            'premium': premium,
            'expiration_days': expiration_days
        }
        
        response = requests.get(url, params=params)
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
        
        # P&L Analysis Section
        st.subheader("💰 Profit & Loss Analysis")
        st.write("Analyze potential profit and loss for single option positions")
        
        # P&L Configuration
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            pnl_option_type = st.selectbox(
                "Option Type",
                options=["call", "put"],
                index=0,
                help="Select whether to analyze a call or put option"
            )
        
        with col2:
            current_price = stock_data.get('current_price', 100)
            pnl_strike = st.number_input(
                "Strike Price ($)",
                min_value=0.01,
                value=float(current_price) if current_price else 100.0,
                step=1.0,
                help="The strike price of the option contract"
            )
        
        with col3:
            pnl_premium = st.number_input(
                "Premium Paid ($)",
                min_value=0.01,
                value=5.0,
                step=0.25,
                help="The premium you paid for the option"
            )
        
        with col4:
            # Use available expiration data to suggest realistic days
            available_days = []
            if "available_expirations" in options_data:
                available_days = [exp["days_until_expiration"] for exp in options_data["available_expirations"]]
            
            default_days = min(available_days) if available_days else 30
            max_days = max(available_days) if available_days else 180
            
            pnl_expiration_days = st.number_input(
                "Days to Expiration",
                min_value=1,
                max_value=max_days,
                value=default_days,
                step=1,
                help="Number of days until the option expires"
            )
        
        # Generate P&L Analysis Button
        if st.button("🔢 Calculate P&L", type="primary"):
            with st.spinner("Calculating profit and loss scenarios..."):
                pnl_data = get_option_pnl(
                    symbol=symbol,
                    option_type=pnl_option_type,
                    strike=pnl_strike,
                    premium=pnl_premium,
                    expiration_days=pnl_expiration_days
                )
            
            if "error" in pnl_data:
                st.error(f"P&L Analysis Error: {pnl_data['error']}")
            else:
                # Display Key Metrics
                st.subheader("📊 Key Metrics")
                
                # Extract metrics from the response - they're at the top level, not nested in 'metrics'
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    max_profit = pnl_data.get('max_profit')
                    if max_profit is None:
                        st.metric("Max Profit", "N/A")
                    elif max_profit == float('inf'):
                        st.metric("Max Profit", "Unlimited ♾️")
                    else:
                        st.metric("Max Profit", f"${max_profit:.2f}")
                
                with col2:
                    max_loss = pnl_data.get('max_loss')
                    if max_loss is None:
                        st.metric("Max Loss", "N/A")
                    else:
                        st.metric("Max Loss", f"${max_loss:.2f}")
                
                with col3:
                    breakeven_points = pnl_data.get('breakeven_points', [])
                    if breakeven_points:
                        # Show first breakeven point if multiple exist
                        breakeven = breakeven_points[0]
                        st.metric("Breakeven", f"${breakeven:.2f}")
                    else:
                        st.metric("Breakeven", "N/A")
                
                with col4:
                    profit_prob = pnl_data.get('probability_of_profit')
                    if profit_prob is None:
                        st.metric("Profit Probability", "N/A")
                    else:
                        st.metric("Profit Probability", f"{profit_prob:.1f}%")
                
                # Create P&L Chart
                st.subheader("📈 Profit & Loss Chart")
                
                # Extract data for plotting
                stock_prices = pnl_data.get('stock_prices', [])
                pnl_values = pnl_data.get('pnl_values', [])
                option_values = pnl_data.get('option_values', [])
                
                if stock_prices and pnl_values:
                    # Create the P&L chart
                    fig = go.Figure()
                    
                    # Add P&L curve
                    fig.add_trace(go.Scatter(
                        x=stock_prices,
                        y=pnl_values,
                        mode='lines',
                        name='P&L at Expiration',
                        line=dict(color='blue', width=3),
                        hovertemplate='<b>Stock Price:</b> $%{x:.2f}<br>' +
                                    '<b>P&L:</b> $%{y:.2f}<extra></extra>'
                    ))
                    
                    # Add zero line
                    fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                                annotation_text="Breakeven", annotation_position="bottom right")
                    
                    # Add current stock price line
                    current_price = stock_data.get('current_price')
                    if current_price:
                        fig.add_vline(x=current_price, line_dash="dot", line_color="orange",
                                    annotation_text=f"Current: ${current_price:.2f}", 
                                    annotation_position="top")
                    
                    # Add strike price line
                    fig.add_vline(x=pnl_strike, line_dash="dash", line_color="red",
                                annotation_text=f"Strike: ${pnl_strike:.2f}", 
                                annotation_position="bottom")
                    
                    # Highlight profit/loss areas
                    profit_indices = [i for i, pnl in enumerate(pnl_values) if pnl > 0]
                    loss_indices = [i for i, pnl in enumerate(pnl_values) if pnl < 0]
                    
                    if profit_indices:
                        profit_x = [stock_prices[i] for i in profit_indices]
                        profit_y = [pnl_values[i] for i in profit_indices]
                        fig.add_trace(go.Scatter(
                            x=profit_x, y=profit_y,
                            fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.1)',
                            mode='none', name='Profit Zone', showlegend=False
                        ))
                    
                    if loss_indices:
                        loss_x = [stock_prices[i] for i in loss_indices]
                        loss_y = [pnl_values[i] for i in loss_indices]
                        fig.add_trace(go.Scatter(
                            x=loss_x, y=loss_y,
                            fill='tozeroy', fillcolor='rgba(255, 0, 0, 0.1)',
                            mode='none', name='Loss Zone', showlegend=False
                        ))
                    
                    # Update layout
                    fig.update_layout(
                        title=f"{symbol.upper()} {pnl_option_type.title()} Option P&L Analysis",
                        xaxis_title="Stock Price at Expiration ($)",
                        yaxis_title="Profit/Loss ($)",
                        hovermode='x unified',
                        height=500,
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Additional Analysis
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🎯 Probability Analysis")
                        
                        profit_prob = pnl_data.get('probability_of_profit')
                        if profit_prob is not None:
                            st.write(f"**Profit Probability:** {profit_prob:.1f}%")
                        else:
                            st.write(f"**Profit Probability:** N/A")
                        
                        # Distance from strike calculation
                        current_price = pnl_data.get('current_price')
                        strike = pnl_data.get('strike')
                        if current_price and strike:
                            distance_pct = abs(current_price - strike) / strike * 100
                            st.write(f"**Current Distance from Strike:** {distance_pct:.1f}%")
                        
                        # Probability breakdown
                        breakeven_points = pnl_data.get('breakeven_points', [])
                        if breakeven_points and pnl_option_type == 'call':
                            breakeven = breakeven_points[0]
                            st.write(f"Stock needs to rise above ${breakeven:.2f} to be profitable")
                        elif breakeven_points and pnl_option_type == 'put':
                            breakeven = breakeven_points[0]
                            st.write(f"Stock needs to fall below ${breakeven:.2f} to be profitable")
                        else:
                            st.write("Breakeven analysis not available")
                    
                    with col2:
                        st.subheader("📋 Position Summary")
                        st.write(f"**Option Type:** {pnl_option_type.title()}")
                        st.write(f"**Strike Price:** ${pnl_strike:.2f}")
                        st.write(f"**Premium Paid:** ${pnl_premium:.2f}")
                        st.write(f"**Days to Expiration:** {pnl_expiration_days}")
                        if current_price:
                            st.write(f"**Current Stock Price:** ${current_price:.2f}")
                        else:
                            st.write(f"**Current Stock Price:** N/A")
                    
                    # Raw P&L Data Table
                    with st.expander("📊 Detailed P&L Data"):
                        pnl_df = pd.DataFrame({
                            'Stock Price': stock_prices,
                            'Option Value': option_values,
                            'P&L': pnl_values
                        })
                        
                        # Format currency columns
                        pnl_df['Stock Price'] = pnl_df['Stock Price'].apply(lambda x: f"${x:.2f}")
                        pnl_df['Option Value'] = pnl_df['Option Value'].apply(lambda x: f"${x:.2f}")
                        pnl_df['P&L'] = pnl_df['P&L'].apply(lambda x: f"${x:.2f}")
                        
                        st.dataframe(pnl_df, use_container_width=True)
                    
                    # Debug P&L data
                    with st.expander("Debug: Raw P&L API Response"):
                        st.json(pnl_data)
                
                else:
                    st.error("No P&L data available for charting")
        
        else:
            st.info("👆 Configure your option position above and click 'Calculate P&L' to see the analysis")
            
            # Example usage hints
            with st.expander("💡 How to Use P&L Analysis"):
                st.write("""
                **Step 1:** Select whether you want to analyze a call or put option
                
                **Step 2:** Enter the strike price (usually near current stock price)
                
                **Step 3:** Enter the premium you paid (check current market prices in options chain above)
                
                **Step 4:** Select days to expiration (use the expiration dates available above)
                
                **Step 5:** Click 'Calculate P&L' to see your profit/loss scenarios
                
                **Key Concepts:**
                - **Breakeven:** Stock price where you neither profit nor lose money
                - **Max Profit:** Maximum possible profit (unlimited for long calls)
                - **Max Loss:** Maximum possible loss (limited to premium paid)
                - **Probability:** Statistical likelihood of profit based on current volatility
                """)

else:
    st.info("👆 Enter a stock symbol to begin analysis")