#!/Users/sophiafeldman/Documents/Old_school_work/FALLSeniorYear/449/AI_RAG/ISATRecruiter/bin/python
from openai import OpenAI

api_key = input("Enter your OpenAI API key: ")

try:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hello how are you"}]
    )
    print("Key successful")
except Exception as e:
    print(f"Error: {e}")
