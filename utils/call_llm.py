from google import genai
import os

def call_llm(prompt: str) -> str:
    """
    Call Google Gemini LLM with the given prompt.
    
    Args:
        prompt (str): The prompt to send to the LLM
        
    Returns:
        str: The response from the LLM
    """
    api_key = os.getenv("GEMINI_API_KEY", "Your API Key")
    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    
    response = client.models.generate_content(
        model=model, 
        contents=[prompt]
    )
    return response.text

if __name__ == "__main__":
    test_prompt = "Hello, how are you?"
    
    print("Making call...")
    response = call_llm(test_prompt)
    print(f"Response: {response}")