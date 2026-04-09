#!/Users/sophiafeldman/Documents/Old_school_work/FALLSeniorYear/449/AI_RAG/ISATRecruiter/bin/python
import sys
print("DEBUG: Python executable:", sys.executable)
print("DEBUG: Python path:", sys.path[0])
import os
from openai import OpenAI
try:
    from dotenv import load_dotenv
except ImportError as e:
    print(f"ERROR: Failed to import dotenv: {e}")
    print("Make sure python-dotenv is installed: pip install python-dotenv")
    sys.exit(1)

# Get project root (parent directory of tests/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')

# Check if .env file exists
if not os.path.exists(env_path):
    print(f"Error: .env file not found at {env_path}")
    print(f"Please create a .env file in the project root with: OPENAI_API_KEY=sk-your-key-here")
    sys.exit(1)

# Load .env from project root
load_dotenv(env_path)

openai_key = os.getenv("OPENAI_API_KEY")

def if_error(openai_key: str) -> bool:
    """Check if API key exists in environment."""
    if openai_key is None:
        print("Error: openai key not found in .env file")
        return False
    else:
        return True

def test_api_key(openai_key: str) -> bool:
    """Test if the API key is valid by making a simple API call."""
    try:
        client = OpenAI(api_key=openai_key)
        
        # Test with a simple models list call
        print("Testing API key validity...")
        client.models.list()
        print("✓ API key is valid and working!")
        
        # Optional: Test with a simple completion
        print("Testing completion endpoint...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'test successful'"}],
            max_tokens=10
        )
        print(f"✓ Completion test successful: {response.choices[0].message.content}")
        
        return True
    except Exception as e:
        print(f"✗ API key test failed: {str(e)}")
        if "Invalid API key" in str(e) or "401" in str(e):
            print("  → Your API key appears to be invalid or expired.")
        elif "Rate limit" in str(e):
            print("  → Rate limit reached, but key is valid.")
        return False

if __name__ == "__main__":
    if if_error(openai_key):
        print("OpenAI key found in .env file")
        print(f"Key preview: {openai_key[:7]}...{openai_key[-4:]}\n")
        test_api_key(openai_key)
    else:   
        print("OpenAI key not found in .env file")