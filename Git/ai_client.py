"""
Reusable AI Communication Model

This module wraps the Anthropics API client in a reusable class,
allowing for standardized and testable communication with the AI.

Usage:
    from ai_client import AIClient
    ai_client = AIClient(model="model-name", max_tokens=1000, temperature=0.2)
    response = ai_client.get_response(system_prompt, user_message)
"""
import os
import dotenv
import anthropic

dotenv.load_dotenv()

class AIClient:
    def __init__(self, model: str = None, max_tokens: int = 1000, temperature: float = 0.2):
        """
        Initialize the AIClient with the given model, max_tokens, and temperature.

        Params:
            model (str): The model to use. If not provided, it defaults to the env variable
                         'CLAUDE_LARGE_MODEL' or a hardcoded default.
            max_tokens (int): Maximum tokens for the response.
            temperature (float): Temperature setting for the AI response.
        """
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Missing Anthropics API key. Please set ANTHROPIC_API_KEY in your .env file.")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        # Use provided model or fallback to env/default
        self.model = model or os.getenv("CLAUDE_LARGE_MODEL", "claude-3-5-sonnet-20240620")
        self.max_tokens = max_tokens
        self.temperature = temperature

    def get_response(self, system_prompt: str, user_message: str) -> str:
        """
        Get a response from the AI based on a system prompt and user message.

        Params:
            system_prompt (str): The system prompt containing instructions for the AI.
            user_message (str): The user message to provide additional context.

        Returns:
            str: The AI's response text.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return response.content[0].text.strip() 