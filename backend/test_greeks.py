"""
Test script for Options Greeks calculations.

This script tests the Greeks calculation module with known values to ensure accuracy.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculations.greeks import OptionsGreeks
from calculations.black_scholes import BlackScholesModel, days_to_years, get_risk_free_rate

def test_greeks_calculation():
    """Test Greeks calculation with known parameters."""
    
    print("Testing Options Greeks Calculations")
    print("=" * 50)
    
    # Test parameters (similar to a real AAPL option)
    S = 180.0      # Current stock price
    K = 175.0      # Strike price
    T = 30         # Days to expiration
    r = 0.045      # Risk-free rate (4.5%)
    sigma = 0.25   # Volatility (25%)
    
    # Convert days to years
    T_years = days_to_years(T)
    
    print(f"Test Parameters:")
    print(f"  Stock Price (S): ${S}")
    print(f"  Strike Price (K): ${K}")
    print(f"  Days to Expiration: {T}")
    print(f"  Time to Expiration (years): {T_years:.4f}")
    print(f"  Risk-free Rate: {r:.3f} ({r*100:.1f}%)")
    print(f"  Volatility: {sigma:.3f} ({sigma*100:.1f}%)")
    print()
    
    # Test Call Option
    print("CALL OPTION GREEKS")
    print("-" * 30)
    
    call_greeks = OptionsGreeks.calculate_greeks("call", S, K, T_years, r, sigma)
    call_price = BlackScholesModel.call_price(S, K, T_years, r, sigma)
    
    print(f"Theoretical Price: ${call_price:.2f}")
    print(f"Delta: {call_greeks['delta']:.4f} (${call_greeks['delta']*100:.0f} per 100 shares)")
    print(f"Gamma: {call_greeks['gamma']:.4f}")
    print(f"Theta: ${call_greeks['theta']:.4f} per day")
    print(f"Vega: {call_greeks['vega']:.4f} per 1% IV change")
    print(f"Rho: {call_greeks['rho']:.4f} per 1% rate change")
    print()
    
    # Test Put Option
    print("PUT OPTION GREEKS")
    print("-" * 30)
    
    put_greeks = OptionsGreeks.calculate_greeks("put", S, K, T_years, r, sigma)
    put_price = BlackScholesModel.put_price(S, K, T_years, r, sigma)
    
    print(f"Theoretical Price: ${put_price:.2f}")
    print(f"Delta: {put_greeks['delta']:.4f} (${put_greeks['delta']*100:.0f} per 100 shares)")
    print(f"Gamma: {put_greeks['gamma']:.4f}")
    print(f"Theta: ${put_greeks['theta']:.4f} per day")
    print(f"Vega: {put_greeks['vega']:.4f} per 1% IV change")
    print(f"Rho: {put_greeks['rho']:.4f} per 1% rate change")
    print()
    
    # Test Interpretations
    print("INTERPRETATIONS")
    print("-" * 30)
    
    call_interpretations = OptionsGreeks.interpret_greeks(call_greeks, "call")
    put_interpretations = OptionsGreeks.interpret_greeks(put_greeks, "put")
    
    print("Call Option:")
    for greek, interpretation in call_interpretations.items():
        print(f"  {greek.title()}: {interpretation}")
    
    print("\nPut Option:")
    for greek, interpretation in put_interpretations.items():
        print(f"  {greek.title()}: {interpretation}")
    
    print()
    
    # Verify some basic properties
    print("VERIFICATION CHECKS")
    print("-" * 30)
    
    checks = []
    
    # Call delta should be positive, put delta negative
    checks.append(("Call delta > 0", call_greeks['delta'] > 0))
    checks.append(("Put delta < 0", put_greeks['delta'] < 0))
    
    # Gamma should be positive for both
    checks.append(("Call gamma > 0", call_greeks['gamma'] > 0))
    checks.append(("Put gamma > 0", put_greeks['gamma'] > 0))
    
    # Gamma should be the same for calls and puts
    checks.append(("Call gamma = Put gamma", abs(call_greeks['gamma'] - put_greeks['gamma']) < 0.0001))
    
    # Theta should be negative for long positions
    checks.append(("Call theta < 0", call_greeks['theta'] < 0))
    checks.append(("Put theta < 0", put_greeks['theta'] < 0))
    
    # Vega should be positive for both
    checks.append(("Call vega > 0", call_greeks['vega'] > 0))
    checks.append(("Put vega > 0", put_greeks['vega'] > 0))
    
    # Vega should be the same for calls and puts
    checks.append(("Call vega = Put vega", abs(call_greeks['vega'] - put_greeks['vega']) < 0.0001))
    
    # Call rho should be positive, put rho negative
    checks.append(("Call rho > 0", call_greeks['rho'] > 0))
    checks.append(("Put rho < 0", put_greeks['rho'] < 0))
    
    # Display results
    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {check_name}: {status}")
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    print()
    print(f"SUMMARY: {passed}/{total} checks passed")
    
    if passed == total:
        print("All tests passed! Greeks calculations are working correctly.")
    else:
        print("Some tests failed. Check the implementation.")

    return passed == total

if __name__ == "__main__":
    test_greeks_calculation()