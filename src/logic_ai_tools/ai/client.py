"""
AI Client Interface
-----------------
Standardized interface for AI model interactions.

Features:
- Configurable model selection
- Consistent error handling
- Response formatting
- Token management
- OpenAI fallback support
"""

import os
import sys
import anthropic
import openai
from typing import Optional, Dict, Any
from ..utils.interrupt_handler import handle_interrupt

class AIClient:
    """Client for interacting with AI models."""
    
    def __init__(
        self,
        model: str = "claude-3-haiku-20240307",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ):
        """Initialize AI client with configuration."""
        self.anthropic_client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Get OpenAI model names from env or use defaults
        self.openai_models = {
            "small": os.getenv("OPENAI_SMALL_MODEL", "gpt-4o-mini"),
            "medium": os.getenv("OPENAI_MEDIUM_MODEL", "gpt-4o-mini"),
            "large": os.getenv("OPENAI_LARGE_MODEL", "gpt-4o-mini")
        }
        
        # Initialize OpenAI client as None - will be created only when needed
        self.openai_client = None

    def get_openai_model(self) -> str:
        """Get equivalent OpenAI model based on current Anthropic model."""
        if "haiku" in self.model:
            return self.openai_models["small"]
        elif "sonnet" in self.model:
            return self.openai_models["medium"]
        else:
            return self.openai_models["large"]

    def initialize_openai_client(self):
        """Initialize OpenAI client if not already initialized."""
        if self.openai_client is None:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("❌ OpenAI API key not found. Please set the OPENAI_API_KEY environment variable to use OpenAI as a fallback.")
            self.openai_client = openai.OpenAI(api_key=openai_api_key)

    def get_response(self, system_prompt: str, user_message: str) -> str:
        """
        Get a response from the AI based on a system prompt and user message.
        Falls back to OpenAI if Anthropic fails and user approves.

        Params:
            system_prompt (str): The system prompt containing instructions for the AI.
            user_message (str): The user message to provide additional context.

        Returns:
            str: The AI's response text.
        """
        try:
            try:
                response = self.anthropic_client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}]
                )
                return response.content[0].text.strip()
            except KeyboardInterrupt:
                handle_interrupt()
            except Exception as e:
                print(f"\n⚠️ Anthropic API Error: {str(e)}")
                try:
                    retry = input("\nWould you like to retry with OpenAI? (y/n): ").lower().strip()
                except KeyboardInterrupt:
                    handle_interrupt()
                
                if retry == 'y':
                    try:
                        # Initialize OpenAI client only when needed
                        self.initialize_openai_client()
                        openai_model = self.get_openai_model()
                        print(f"\nUsing OpenAI model: {openai_model}")
                        
                        response = self.openai_client.chat.completions.create(
                            model=openai_model,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_message}
                            ]
                        )
                        return response.choices[0].message.content.strip()
                    except KeyboardInterrupt:
                        handle_interrupt()
                    except ValueError as ve:
                        # Handle missing API key error
                        print(f"\n{str(ve)}")
                        raise
                    except Exception as openai_error:
                        print(f"\n❌ OpenAI API Error: {str(openai_error)}")
                        raise
                else:
                    raise
        except KeyboardInterrupt:
            handle_interrupt() 