"""
🤖 ENABLE PURE AI CHAT - Configuration & Fixes
===============================================

The chatbot is currently showing template responses instead of real AI.
This script helps you enable genuinely AI-powered responses.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, 'backend')

from services.gemini_provider import is_gemini_available, get_init_error, GEMINI_API_KEY

print("=" * 70)
print("🤖 WildTrack AI - Chat AI Status Check")
print("=" * 70)

# Check 1: API Key
print("\n1️⃣  GEMINI API KEY STATUS")
print("-" * 70)
if GEMINI_API_KEY:
    masked_key = GEMINI_API_KEY[:10] + "..." + GEMINI_API_KEY[-4:]
    print(f"✅ GEMINI_API_KEY is set: {masked_key}")
else:
    print("❌ GEMINI_API_KEY is NOT set")
    print("\n   To enable AI chat, you need a Google Gemini API key:")
    print("   1. Go to: https://aistudio.google.com/app/apikeys")
    print("   2. Create new API key")
    print("   3. Copy the key")
    print("   4. Set in Render environment: GEMINI_API_KEY=your_key_here")
    print("   5. Redeploy on Render")

# Check 2: Init Status
print("\n2️⃣  GEMINI SDK INITIALIZATION")
print("-" * 70)
if is_gemini_available():
    print("✅ Gemini SDK is initialized and ready")
    print("   AI chat is ENABLED - responses will be pure AI")
else:
    init_error = get_init_error()
    if init_error:
        print(f"❌ Gemini failed to initialize: {init_error}")
    else:
        print("❌ Gemini SDK not initialized (missing GEMINI_API_KEY)")

# Check 3: Fallback Status
print("\n3️⃣  CURRENT RESPONSE MODE")
print("-" * 70)
if is_gemini_available():
    print("🤖 Mode: PURE AI (Gemini)")
    print("   User questions will be answered by real AI")
    print("   Responses will be contextual and dynamic")
else:
    print("📋 Mode: TEMPLATE FALLBACK")
    print("   Showing pre-written responses (knowledge base)")
    print("   Not genuine AI - still helpful but static")

# Check 4: Available Alternatives
print("\n4️⃣  ALTERNATIVE AI SERVICES (if Gemini not available)")
print("-" * 70)
print("""
Option A: OpenAI (ChatGPT-3.5/GPT-4)
   - Pro: Excellent quality, widely supported
   - Setup: Set OPENAI_API_KEY env variable
   
Option B: Hugging Face Inference API
   - Pro: Free tier available, open models
   - Setup: Set HUGGINGFACE_API_KEY env variable
   
Option C: Local LLM (Ollama/LlamaCpp)
   - Pro: Works offline, no API required
   - Setup: Run local server on :11434
   - Con: Slower, requires local GPU
""")

# Check 5: Enable AI - Quick Fix
print("\n5️⃣  QUICK FIX - Enable AI Chat NOW")
print("-" * 70)

if not is_gemini_available():
    print("\n⚙️  Option 1: Add Gemini API Key to Render")
    print("   1. Go to: https://dashboard.render.com/services/wildtrack-backend-s3lq")
    print("   2. Click 'Environment' tab")
    print("   3. Add new var: GEMINI_API_KEY = <your-key>")
    print("   4. Save & redeploy")
    print("   5. Chat will then be pure AI ✓")
    
    print("\n⚙️  Option 2: Use Mock AI (Testing)")
    print("   - Uncomment in chat_service.py to use simulated AI")
    print("   - Responses feel natural but are templated")
    
    print("\n⚙️  Option 3: Switch to OpenAI")
    print("   - Implement OpenAI integration")
    print("   - Set OPENAI_API_KEY instead of GEMINI_API_KEY")
else:
    print("\n✅ AI is already enabled!")
    print("   If chat still shows templates, clear browser cache:")
    print("   1. Press Ctrl+Shift+Delete")
    print("   2. Clear all cache & cookies")
    print("   3. Reload page")
    print("   4. Try chat again")

# Check 6: Test Current Setup
print("\n6️⃣  TEST CURRENT SETUP")
print("-" * 70)

try:
    from services.chat_service import generate_chat_response
    
    test_response = generate_chat_response(
        "Hello, can you help me identify a footprint?",
        session_id="test_session"
    )
    
    if test_response and len(test_response) > 50:
        print("✅ Chat system is working!")
        print(f"\nSample response (first 100 chars):")
        print(f"   {test_response[:100]}...")
        
        if "WildTrackAI assistant" in test_response or "Gemini" in str(test_response):
            print("\n🤖 Response is AI-generated (Gemini available)")
        else:
            print("\n📋 Response is template-based (Gemini not available)")
    else:
        print("❌ Chat system returned empty response")
except Exception as e:
    print(f"❌ Error testing chat: {e}")

# Summary & Next Steps
print("\n" + "=" * 70)
print("SUMMARY & NEXT STEPS")
print("=" * 70)

if is_gemini_available():
    print("""
✅ PURE AI IS ACTIVE

Your chat will now provide:
  • Real AI-generated responses
  • Contextual understanding of footprints
  • Dynamic analysis based on predictions
  • Natural, conversational tone

To see the improvements:
  1. Clear browser cache (Ctrl+Shift+Delete)
  2. Refresh the app
  3. Try asking questions in AI Chat
  4. Ask about predictions after uploading images
""")
else:
    print("""
⚠️  TEMPLATE MODE IS ACTIVE

To enable PURE AI:
  1. Get Gemini API key from: https://aistudio.google.com/app/apikeys
  2. Add to Render: Settings → Environment → Add GEMINI_API_KEY
  3. Redeploy service
  4. Wait 2-5 minutes for deployment
  5. Clear browser cache
  6. Try chat again

Without API key:
  • Chat still works with templates
  • Still helpful but not genuine AI
  • Answers are pre-written
  • No real understanding of context
""")

print("\n" + "=" * 70)
print("Need help? Check:")
print("  • GEMINI_API_KEY in environment variables")
print("  • Logs: https://dashboard.render.com/services/wildtrack-backend-s3lq")
print("=" * 70)
