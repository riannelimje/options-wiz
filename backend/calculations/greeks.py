"""
Options Greeks Calculation Module

This module implements the calculation of option Greeks (Delta, Gamma, Theta, Vega, Rho).
Greeks measure the sensitivity of option prices to various factors.
"""

import math
from typing import Dict, Optional, Tuple
from scipy.stats import norm
import numpy as np


class OptionsGreeks:
    """
    Options Greeks calculator using Black-Scholes model.
    
    Greeks are partial derivatives of the option price with respect to various parameters:
    - Delta: Sensitivity to underlying price changes
    - Gamma: Rate of change of delta
    - Theta: Time decay
    - Vega: Sensitivity to volatility changes
    - Rho: Sensitivity to interest rate changes
    """
    
    @staticmethod
    def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d1 parameter for Black-Scholes formula."""
        if T <= 0 or sigma <= 0:
            return 0
        
        return (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    
    @staticmethod
    def _d2(d1: float, sigma: float, T: float) -> float:
        """Calculate d2 parameter for Black-Scholes formula."""
        if T <= 0:
            return d1
        
        return d1 - sigma * math.sqrt(T)
    
    @classmethod
    def delta(cls, option_type: str, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Delta: The rate of change of option price with respect to underlying price.
        
        Delta ranges from 0 to 1 for calls, -1 to 0 for puts.
        - Call Delta = N(d1)
        - Put Delta = N(d1) - 1
        
        Args:
            option_type: "call" or "put"
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility
            
        Returns:
            Delta value
        """
        if T <= 0:
            # At expiration, delta is 1 if ITM, 0 if OTM
            if option_type.lower() == "call":
                return 1.0 if S > K else 0.0
            else:  # put
                return -1.0 if S < K else 0.0
        
        if sigma <= 0:
            # No volatility, binary outcome
            if option_type.lower() == "call":
                return 1.0 if S > K else 0.0
            else:
                return -1.0 if S < K else 0.0
        
        try:
            d1 = cls._d1(S, K, T, r, sigma)
            
            if option_type.lower() == "call":
                return norm.cdf(d1)
            elif option_type.lower() == "put":
                return norm.cdf(d1) - 1.0
            else:
                raise ValueError("option_type must be 'call' or 'put'")
                
        except (ValueError, ZeroDivisionError, OverflowError):
            return 0.0
    
    @classmethod
    def gamma(cls, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Gamma: The rate of change of delta with respect to underlying price.
        
        Gamma is the same for calls and puts.
        Gamma = φ(d1) / (S * σ * √T)
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility
            
        Returns:
            Gamma value
        """
        if T <= 0 or sigma <= 0 or S <= 0:
            return 0.0
        
        try:
            d1 = cls._d1(S, K, T, r, sigma)
            return norm.pdf(d1) / (S * sigma * math.sqrt(T))
            
        except (ValueError, ZeroDivisionError, OverflowError):
            return 0.0
    
    @classmethod
    def theta(cls, option_type: str, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Theta: The rate of change of option price with respect to time.
        
        Theta represents time decay (usually negative for long positions).
        Expressed as change per day (divide by 365 from annual rate).
        
        Args:
            option_type: "call" or "put"
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility
            
        Returns:
            Theta value (per day)
        """
        if T <= 0:
            return 0.0
        
        if sigma <= 0:
            return 0.0
        
        try:
            d1 = cls._d1(S, K, T, r, sigma)
            d2 = cls._d2(d1, sigma, T)
            
            # Common terms
            sqrt_T = math.sqrt(T)
            exp_neg_rT = math.exp(-r * T)
            pdf_d1 = norm.pdf(d1)
            
            if option_type.lower() == "call":
                theta = ((-S * pdf_d1 * sigma) / (2 * sqrt_T) - 
                        r * K * exp_neg_rT * norm.cdf(d2))
            elif option_type.lower() == "put":
                theta = ((-S * pdf_d1 * sigma) / (2 * sqrt_T) + 
                        r * K * exp_neg_rT * norm.cdf(-d2))
            else:
                raise ValueError("option_type must be 'call' or 'put'")
            
            # Convert from annual to daily
            return theta / 365.0
            
        except (ValueError, ZeroDivisionError, OverflowError):
            return 0.0
    
    @classmethod
    def vega(cls, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Vega: The rate of change of option price with respect to volatility.
        
        Vega is the same for calls and puts.
        Vega = S * φ(d1) * √T
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility
            
        Returns:
            Vega value (for 1% change in volatility)
        """
        if T <= 0 or sigma <= 0 or S <= 0:
            return 0.0
        
        try:
            d1 = cls._d1(S, K, T, r, sigma)
            # Divide by 100 to express per 1% volatility change
            return S * norm.pdf(d1) * math.sqrt(T) / 100.0
            
        except (ValueError, ZeroDivisionError, OverflowError):
            return 0.0
    
    @classmethod
    def rho(cls, option_type: str, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Rho: The rate of change of option price with respect to interest rate.
        
        Rho measures sensitivity to interest rate changes.
        
        Args:
            option_type: "call" or "put"
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility
            
        Returns:
            Rho value (for 1% change in interest rate)
        """
        if T <= 0:
            return 0.0
        
        if sigma <= 0:
            return 0.0
        
        try:
            d1 = cls._d1(S, K, T, r, sigma)
            d2 = cls._d2(d1, sigma, T)
            
            if option_type.lower() == "call":
                rho = K * T * math.exp(-r * T) * norm.cdf(d2)
            elif option_type.lower() == "put":
                rho = -K * T * math.exp(-r * T) * norm.cdf(-d2)
            else:
                raise ValueError("option_type must be 'call' or 'put'")
            
            # Divide by 100 to express per 1% interest rate change
            return rho / 100.0
            
        except (ValueError, ZeroDivisionError, OverflowError):
            return 0.0
    
    @classmethod
    def calculate_greeks(cls, option_type: str, S: float, K: float, T: float, 
                        r: float, sigma: float) -> Dict[str, float]:
        """
        Calculate all Greeks for an option.
        
        Args:
            option_type: "call" or "put"
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility
            
        Returns:
            Dictionary containing all Greeks
        """
        try:
            return {
                "delta": cls.delta(option_type, S, K, T, r, sigma),
                "gamma": cls.gamma(S, K, T, r, sigma),
                "theta": cls.theta(option_type, S, K, T, r, sigma),
                "vega": cls.vega(S, K, T, r, sigma),
                "rho": cls.rho(option_type, S, K, T, r, sigma)
            }
        except Exception as e:
            # Return zero Greeks if calculation fails
            return {
                "delta": 0.0,
                "gamma": 0.0,
                "theta": 0.0,
                "vega": 0.0,
                "rho": 0.0
            }
    
    @classmethod
    def interpret_greeks(cls, greeks: Dict[str, float], option_type: str) -> Dict[str, str]:
        """
        Provide human-readable interpretations of Greeks values.
        
        Args:
            greeks: Dictionary of Greeks values
            option_type: "call" or "put"
            
        Returns:
            Dictionary of interpretations
        """
        interpretations = {}
        
        # Delta interpretation
        delta = greeks.get("delta", 0)
        if option_type.lower() == "call":
            if delta > 0.8:
                interpretations["delta"] = "Deep ITM - moves almost 1:1 with stock"
            elif delta > 0.6:
                interpretations["delta"] = "ITM - strong positive correlation with stock"
            elif delta > 0.4:
                interpretations["delta"] = "Near ATM - moderate sensitivity to stock moves"
            elif delta > 0.2:
                interpretations["delta"] = "OTM - low sensitivity to stock moves"
            else:
                interpretations["delta"] = "Deep OTM - minimal sensitivity to stock moves"
        else:  # put
            if delta < -0.8:
                interpretations["delta"] = "Deep ITM - moves almost 1:1 inverse to stock"
            elif delta < -0.6:
                interpretations["delta"] = "ITM - strong negative correlation with stock"
            elif delta < -0.4:
                interpretations["delta"] = "Near ATM - moderate inverse sensitivity to stock moves"
            elif delta < -0.2:
                interpretations["delta"] = "OTM - low inverse sensitivity to stock moves"
            else:
                interpretations["delta"] = "Deep OTM - minimal sensitivity to stock moves"
        
        # Gamma interpretation
        gamma = greeks.get("gamma", 0)
        if gamma > 0.1:
            interpretations["gamma"] = "High gamma - delta changes rapidly"
        elif gamma > 0.05:
            interpretations["gamma"] = "Moderate gamma - noticeable delta acceleration"
        else:
            interpretations["gamma"] = "Low gamma - delta changes slowly"
        
        # Theta interpretation
        theta = greeks.get("theta", 0)
        if theta < -0.5:
            interpretations["theta"] = "High time decay - losing significant value daily"
        elif theta < -0.1:
            interpretations["theta"] = "Moderate time decay - steady value erosion"
        else:
            interpretations["theta"] = "Low time decay - minimal daily value loss"
        
        # Vega interpretation
        vega = greeks.get("vega", 0)
        if vega > 0.2:
            interpretations["vega"] = "High volatility sensitivity - significant IV impact"
        elif vega > 0.1:
            interpretations["vega"] = "Moderate volatility sensitivity - noticeable IV impact"
        else:
            interpretations["vega"] = "Low volatility sensitivity - minimal IV impact"
        
        return interpretations