"""
CrystaLyse.AI Configuration Module

Centralized configuration for API keys, model settings, and high-performance parameters.
Ensures all agents use the MDG API key for higher rate limits.
"""

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Default model configuration optimized for high-performance operations
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.7

# Rate limits for different models
RATE_LIMITS = {
    "gpt-4o": {
        "tokens_per_minute": 2_000_000,      # 2M TPM
        "requests_per_minute": 10_000,       # 10K RPM  
        "tokens_per_day": 200_000_000,       # 200M TPD
    },
    "o4-mini": {
        "tokens_per_minute": 10_000_000,     # 10M TPM (!)
        "requests_per_minute": 10_000,       # 10K RPM
        "tokens_per_day": 1_000_000_000,     # 1B TPD (!!)
    }
}

# For backward compatibility
MDG_RATE_LIMITS = RATE_LIMITS["gpt-4o"]

def configure_openai_client():
    """
    Configure OpenAI client with MDG API key for high rate limits.
    
    Returns:
        bool: True if MDG API key is configured, False otherwise
    """
    try:
        import openai
        
        # Use only MDG API key for high rate limits
        mdg_api_key = os.getenv("OPENAI_MDG_API_KEY")
        if mdg_api_key:
            # Set for both old and new OpenAI client versions
            openai.api_key = mdg_api_key
            
            # CRITICAL: Force agents package to use MDG key by setting OPENAI_API_KEY to MDG key
            os.environ["OPENAI_API_KEY"] = mdg_api_key
            
            logger.info("✅ Using OPENAI_MDG_API_KEY - High rate limits enabled")
            logger.info(f"📊 Rate limits: {MDG_RATE_LIMITS['tokens_per_minute']:,} TPM, {MDG_RATE_LIMITS['requests_per_minute']:,} RPM")
            logger.info("🔄 Set OPENAI_API_KEY to MDG key for agents package compatibility")
            return True
        
        logger.error("❌ OPENAI_MDG_API_KEY not found. Please set this environment variable.")
        return False
        
    except ImportError:
        logger.error("❌ OpenAI package not installed")
        return False

def get_agent_config(model: Optional[str] = None, temperature: Optional[float] = None) -> dict:
    """
    Get standardized agent configuration with optimized settings.
    
    Args:
        model: Override default model
        temperature: Override default temperature
        
    Returns:
        dict: Agent configuration optimized for high-performance operation
    """
    selected_model = model or DEFAULT_MODEL
    
    # Configure API and display appropriate rate limits
    api_configured = configure_openai_client()
    
    # Display model-specific rate limits
    if selected_model in RATE_LIMITS:
        limits = RATE_LIMITS[selected_model]
        logger.info(f"🚀 Model: {selected_model}")
        logger.info(f"📊 Rate limits: {limits['tokens_per_minute']:,} TPM, {limits['requests_per_minute']:,} RPM, {limits['tokens_per_day']:,} TPD")
    
    return {
        "model": selected_model,
        "temperature": temperature or DEFAULT_TEMPERATURE,
        "max_tokens": 4096,  # Optimized for detailed materials analysis
        "api_configured": api_configured
    }

def verify_rate_limits():
    """
    Verify that MDG API key is configured for high rate limits.
    
    Returns:
        dict: Rate limit status and configuration
    """
    mdg_configured = os.getenv("OPENAI_MDG_API_KEY") is not None
    
    return {
        "mdg_api_configured": mdg_configured,
        "expected_rate_limits": MDG_RATE_LIMITS if mdg_configured else "API key required",
        "recommended_batch_size": 50 if mdg_configured else 1,
        "recommended_parallel_requests": 100 if mdg_configured else 1,
        "status": "optimal" if mdg_configured else "missing_api_key"
    }

# Auto-configure on import
_api_configured = configure_openai_client()

# Export configuration status
API_CONFIGURED = _api_configured
USING_MDG_KEY = os.getenv("OPENAI_MDG_API_KEY") is not None

if USING_MDG_KEY:
    print("🚀 CrystaLyse.AI: High-performance mode enabled with MDG API key")
    print(f"📊 Rate limits: {MDG_RATE_LIMITS['tokens_per_minute']:,} TPM, {MDG_RATE_LIMITS['requests_per_minute']:,} RPM")
    print("🔄 OPENAI_API_KEY set to MDG key for agents package")
else:
    print("❌ CrystaLyse.AI: OPENAI_MDG_API_KEY required - please set this environment variable")