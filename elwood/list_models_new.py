import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("No GEMINI_API_KEY found.")
    exit(1)

api_key = api_key.strip()
print(f"Key used: {api_key[:5]}...{api_key[-5:]}")

try:
    client = genai.Client(api_key=api_key)
    print("Available Models (New SDK):")
    for m in client.models.list():
        print(f"- {m.name}")
    
    # Simple test generation
    print("\nTesting Model Generation...")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents="Hello! Say 'Ready to assist' if you are working."
    )
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error with New SDK: {str(e)}")
    import traceback
    traceback.print_exc()
