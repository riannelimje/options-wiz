"""
Black-Scholes Model Implementation

This module implements the Black-Scholes model for option pricing and Greeks calculation.
The Black-Scholes model is the foundation for modern options pricing theory.
"""

import math
from typing import Dict, Optional
from scipy.stats import norm
import numpy as np


class BlackScholesModel:
    """
    Black-Scholes option pricing model implementation.
    
    This class provides methods to calculate option prices and Greeks using the
    classic Black-Scholes formula.
    """
    
    @staticmethod
    def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate d1 parameter for Black-Scholes formula.
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility (annualized)
            
        Returns:
            d1 value
        """
        if T <= 0 or sigma <= 0:
            return 0
        
        return (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    
    @staticmethod
    def _d2(d1: float, sigma: float, T: float) -> float:
        """
        Calculate d2 parameter for Black-Scholes formula.
        
        Args:
            d1: d1 parameter from _d1()
            sigma: Volatility (annualized)
            T: Time to expiration (in years)
            
        Returns:
            d2 value
        """
        if T <= 0:
            return d1
        
        return d1 - sigma * math.sqrt(T)
    
    @classmethod
    def call_price(cls, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate European call option price using Black-Scholes formula.
        
        Formula: C = S * N(d1) - K * e^(-r*T) * N(d2)
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate (as decimal, e.g., 0.05 for 5%)
            sigma: Volatility (as decimal, e.g., 0.20 for 20%)
            
        Returns:
            Call option price
        """
        if T <= 0:
            return max(0, S - K)  # Intrinsic value only
        
        if sigma <= 0:
            return max(0, S - K)  # No volatility, intrinsic value only
        
        try:
            d1 = cls._d1(S, K, T, r, sigma)
            d2 = cls._d2(d1, sigma, T)
            
            call_price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
            return max(0, call_price)  # Option price can't be negative
            
        except (ValueError, ZeroDivisionError, OverflowError):
            return max(0, S - K)  # Fallback to intrinsic value
    
    @classmethod
    def put_price(cls, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate European put option price using Black-Scholes formula.
        
        Formula: P = K * e^(-r*T) * N(-d2) - S * N(-d1)
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate (as decimal)
            sigma: Volatility (as decimal)
            
        Returns:
            Put option price
        """
        if T <= 0:
            return max(0, K - S)  # Intrinsic value only
        
        if sigma <= 0:
            return max(0, K - S)  # No volatility, intrinsic value only
        
        try:
            d1 = cls._d1(S, K, T, r, sigma)
            d2 = cls._d2(d1, sigma, T)
            
            put_price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            return max(0, put_price)  # Option price can't be negative
            
        except (ValueError, ZeroDivisionError, OverflowError):
            return max(0, K - S)  # Fallback to intrinsic value
    
    @classmethod
    def option_price(cls, option_type: str, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate option price for either call or put.
        
        Args:
            option_type: "call" or "put"
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility
            
        Returns:
            Option price
        """
        if option_type.lower() == "call":
            return cls.call_price(S, K, T, r, sigma)
        elif option_type.lower() == "put":
            return cls.put_price(S, K, T, r, sigma)
        else:
            raise ValueError("option_type must be 'call' or 'put'")
    
    @classmethod
    def implied_volatility(cls, market_price: float, option_type: str, S: float, K: float, 
                          T: float, r: float, initial_guess: float = 0.25) -> Optional[float]:
        """
        Calculate implied volatility using Newton-Raphson method.
        
        Args:
            market_price: Current market price of the option
            option_type: "call" or "put"
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            initial_guess: Starting volatility guess
            
        Returns:
            Implied volatility or None if calculation fails
        """
        if T <= 0 or market_price <= 0:
            return None
        
        sigma = initial_guess
        max_iterations = 100
        tolerance = 1e-6
        
        for _ in range(max_iterations):
            try:
                # Calculate option price with current sigma
                theoretical_price = cls.option_price(option_type, S, K, T, r, sigma)
                
                # Calculate vega (sensitivity to volatility) for Newton-Raphson
                if T <= 0 or sigma <= 0 or S <= 0:
                    vega = 0
                else:
                    d1 = cls._d1(S, K, T, r, sigma)
                    vega = S * norm.pdf(d1) * math.sqrt(T) / 100.0
                
                if abs(vega) < 1e-10:  # Avoid division by zero
                    break
                
                # Newton-Raphson iteration
                price_diff = theoretical_price - market_price
                if abs(price_diff) < tolerance:
                    return sigma
                
                sigma = sigma - price_diff / vega
                
                # Keep sigma within reasonable bounds
                sigma = max(0.001, min(5.0, sigma))
                
            except (ValueError, ZeroDivisionError, OverflowError):
                break
        
        return sigma if 0.001 <= sigma <= 5.0 else None


def days_to_years(days: int) -> float:
    """
    Convert days to years for Black-Scholes calculations.
    
    Args:
        days: Number of days
        
    Returns:
        Time in years (assumes 365 days per year)
    """
    return days / 365.0


def get_risk_free_rate() -> float:
    """
    Get current risk-free rate. 
    
    In a production system, this would fetch from an API.
    For now, returns a reasonable estimate.
    
    Returns:
        Risk-free rate as decimal (e.g., 0.05 for 5%)
    """
    return 0.045  # 4.5% - reasonable estimate for 2025