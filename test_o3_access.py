#!/usr/bin/env python3
"""
Simple test to check if MDG API key can access o3 model
"""

import asyncio
import os
from openai import AsyncOpenAI

async def test_o3_access():
    """Test if we can access o3 model with MDG API key"""
    
    mdg_api_key = os.getenv("OPENAI_MDG_API_KEY")
    if not mdg_api_key:
        print("❌ OPENAI_MDG_API_KEY not found!")
        return False
    
    print(f"🔑 Using MDG API key: {mdg_api_key[:20]}...")
    
    client = AsyncOpenAI(api_key=mdg_api_key)
    
    try:
        print("🧪 Testing o3 model access...")
        
        response = await client.chat.completions.create(
            model="o3",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, can you access computational tools?"}
            ],
            max_completion_tokens=100
        )
        
        print("✅ o3 model accessible!")
        print(f"📝 Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ o3 model access failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_o3_access())
    if success:
        print("🎉 o3 model is accessible with MDG API key!")
    else:
        print("🚨 o3 model is not accessible")