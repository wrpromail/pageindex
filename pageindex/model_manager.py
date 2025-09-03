import asyncio
import json
import logging
import os
import re
import time
from typing import Optional, Dict, Any, Tuple, Union, List, Set
from dataclasses import dataclass
from pathlib import Path

import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment variables for model configuration
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
MODEL_API_KEY = os.getenv("MODEL_API_KEY")

# Environment variables for rate limiting and concurrency
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.1"))
BATCH_REQUEST_DELAY = float(os.getenv("BATCH_REQUEST_DELAY", "0.5"))


@dataclass
class ModelConfig:
    """Model configuration class"""
    model: Optional[str] = None  # Must be provided via environment or runtime
    temperature: float = 0.0
    max_retries: int = 10
    retry_delay: float = 1.0
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    # Rate limiting and concurrency control
    max_concurrent_requests: int = 5
    request_delay: float = 0.1
    batch_request_delay: float = 0.5


class ModelManager:
    """
    Unified model manager for handling OpenAI API calls.
    Supports both synchronous and asynchronous operations with retry logic.
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        """
        Initialize the model manager.

        Args:
            config: Model configuration, uses defaults if None
        """
        # Load configuration from environment variables if not provided
        if config is None:
            config = ModelConfig()

        # Override with environment variables if available
        if MODEL_NAME:
            config.model = MODEL_NAME
        if MODEL_API_KEY:
            config.api_key = MODEL_API_KEY
        if MODEL_BASE_URL:
            config.base_url = MODEL_BASE_URL

        # Override rate limiting parameters from environment
        config.max_concurrent_requests = MAX_CONCURRENT_REQUESTS
        config.request_delay = REQUEST_DELAY
        config.batch_request_delay = BATCH_REQUEST_DELAY

        # Fallback to legacy environment variables
        if not config.api_key:
            config.api_key = CHATGPT_API_KEY

        self.config = config

        # Validate required configurations
        if not self.config.model:
            raise ValueError("Model name must be provided via MODEL_NAME environment variable or config")
        if not self.config.api_key:
            raise ValueError("API key must be provided either in config, MODEL_API_KEY, or CHATGPT_API_KEY environment variable")

        # Initialize clients
        self._sync_client = None
        self._async_client = None

        # Initialize concurrency control
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        self._last_request_time = 0.0
        self._request_lock = asyncio.Lock()

    @property
    def sync_client(self):
        """Get or create synchronous OpenAI client"""
        if self._sync_client is None:
            client_kwargs = {"api_key": self.config.api_key}
            if self.config.base_url:
                client_kwargs["base_url"] = self.config.base_url
            self._sync_client = openai.OpenAI(**client_kwargs)
        return self._sync_client

    @property
    def async_client(self):
        """Get or create asynchronous OpenAI client"""
        if self._async_client is None:
            client_kwargs = {"api_key": self.config.api_key}
            if self.config.base_url:
                client_kwargs["base_url"] = self.config.base_url
            self._async_client = openai.AsyncOpenAI(**client_kwargs)
        return self._async_client

    def _prepare_messages(self, prompt: str, chat_history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """
        Prepare messages for API call.

        Args:
            prompt: The prompt to send
            chat_history: Optional chat history

        Returns:
            List of message dictionaries
        """
        if chat_history:
            messages = chat_history.copy()
            messages.append({"role": "user", "content": prompt})
        else:
            messages = [{"role": "user", "content": prompt}]

        return messages

    async def _rate_limit_control(self) -> None:
        """
        Control request rate to comply with API limits.
        """
        async with self._request_lock:
            current_time = time.time()
            time_since_last_request = current_time - self._last_request_time

            if time_since_last_request < self.config.request_delay:
                sleep_time = self.config.request_delay - time_since_last_request
                await asyncio.sleep(sleep_time)

            self._last_request_time = time.time()

    async def _execute_with_rate_limit(self, coro):
        """
        Execute a coroutine with rate limiting and concurrency control.

        Args:
            coro: The coroutine to execute

        Returns:
            Result of the coroutine
        """
        async with self._semaphore:
            await self._rate_limit_control()
            return await coro

    def _clean_response(self, response: str, remove_thinking: bool = True, remove_tags: Optional[Set[str]] = None) -> str:
        """
        Clean the model response by removing thinking tags and other specified tags.

        Args:
            response: Raw response from the model
            remove_thinking: Whether to remove <think></think> tags
            remove_tags: Set of tag names to remove (without angle brackets)

        Returns:
            Cleaned response string
        """
        if not response or response == "Error":
            return response

        cleaned = response

        # Remove thinking tags by default
        if remove_thinking:
            # Remove <think>content</think> patterns
            cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        # Remove other specified tags
        if remove_tags:
            for tag in remove_tags:
                # Remove opening and closing tags
                cleaned = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
                # Remove self-closing tags
                cleaned = re.sub(rf'<{tag}[^>]*\s*/?>', '', cleaned, flags=re.IGNORECASE)

        # Strip whitespace
        return cleaned.strip()

    def clean_response(self, response: str, remove_thinking: bool = True, remove_tags: Optional[Set[str]] = None) -> str:
        """
        Public method to clean model responses by removing specified tags.

        Args:
            response: Raw response string to clean
            remove_thinking: Whether to remove <think></think> tags (default: True)
            remove_tags: Set of tag names to remove (without angle brackets)

        Returns:
            Cleaned response string
        """
        return self._clean_response(response, remove_thinking, remove_tags)

    def call_sync(self, prompt: str, chat_history: Optional[List[Dict[str, str]]] = None,
                  remove_thinking: bool = True, remove_tags: Optional[Set[str]] = None) -> str:
        """
        Synchronous API call with retry logic.

        Args:
            prompt: The prompt to send to the model
            chat_history: Optional chat history
            remove_thinking: Whether to remove <think></think> tags (default: True)
            remove_tags: Set of tag names to remove (without angle brackets)

        Returns:
            Model response as string
        """
        messages = self._prepare_messages(prompt, chat_history)

        for attempt in range(self.config.max_retries):
            try:
                response = self.sync_client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                )

                raw_content = response.choices[0].message.content
                return self._clean_response(raw_content, remove_thinking, remove_tags)

            except Exception as e:
                print(f'************* Retrying (attempt {attempt + 1}/{self.config.max_retries}) *************')
                logging.error(f"Error in sync call: {e}")

                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    logging.error(f'Max retries reached for prompt: {prompt[:100]}...')
                    return "Error"

    def call_sync_with_finish_reason(self, prompt: str, chat_history: Optional[List[Dict[str, str]]] = None,
                                      remove_thinking: bool = True, remove_tags: Optional[Set[str]] = None) -> Tuple[str, str]:
        """
        Synchronous API call that returns both content and finish reason.

        Args:
            prompt: The prompt to send to the model
            chat_history: Optional chat history
            remove_thinking: Whether to remove <think></think> tags (default: True)
            remove_tags: Set of tag names to remove (without angle brackets)

        Returns:
            Tuple of (response_content, finish_reason)
        """
        messages = self._prepare_messages(prompt, chat_history)

        for attempt in range(self.config.max_retries):
            try:
                response = self.sync_client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                )

                raw_content = response.choices[0].message.content
                cleaned_content = self._clean_response(raw_content, remove_thinking, remove_tags)
                finish_reason = response.choices[0].finish_reason

                if finish_reason == "length":
                    return cleaned_content, "max_output_reached"
                else:
                    return cleaned_content, "finished"

            except Exception as e:
                print(f'************* Retrying (attempt {attempt + 1}/{self.config.max_retries}) *************')
                logging.error(f"Error in sync call with finish reason: {e}")

                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    logging.error(f'Max retries reached for prompt: {prompt[:100]}...')
                    return "Error", "error"

    async def call_async(self, prompt: str, chat_history: Optional[List[Dict[str, str]]] = None,
                         remove_thinking: bool = True, remove_tags: Optional[Set[str]] = None) -> str:
        """
        Asynchronous API call with retry logic and rate limiting.

        Args:
            prompt: The prompt to send to the model
            chat_history: Optional chat history
            remove_thinking: Whether to remove <think></think> tags (default: True)
            remove_tags: Set of tag names to remove (without angle brackets)

        Returns:
            Model response as string
        """
        messages = self._prepare_messages(prompt, chat_history)

        for attempt in range(self.config.max_retries):
            try:
                # Use rate limiting wrapper for the API call
                async def make_request():
                    async with self.async_client:
                        response = await self.async_client.chat.completions.create(
                            model=self.config.model,
                            messages=messages,
                            temperature=self.config.temperature,
                        )
                    return response

                response = await self._execute_with_rate_limit(make_request())

                raw_content = response.choices[0].message.content
                return self._clean_response(raw_content, remove_thinking, remove_tags)

            except Exception as e:
                print(f'************* Retrying (attempt {attempt + 1}/{self.config.max_retries}) *************')
                logging.error(f"Error in async call: {e}")

                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    logging.error(f'Max retries reached for prompt: {prompt[:100]}...')
                    return "Error"

    async def call_batch_async(self, prompts: List[str], chat_histories: Optional[List[Optional[List[Dict[str, str]]]]] = None,
                               remove_thinking: bool = True, remove_tags: Optional[Set[str]] = None) -> List[str]:
        """
        Batch asynchronous API calls with concurrency control and rate limiting.

        Args:
            prompts: List of prompts to send to the model
            chat_histories: Optional list of chat histories for each prompt
            remove_thinking: Whether to remove <think></think> tags (default: True)
            remove_tags: Set of tag names to remove (without angle brackets)

        Returns:
            List of model responses
        """
        if chat_histories is None:
            chat_histories = [None] * len(prompts)

        if len(prompts) != len(chat_histories):
            raise ValueError("prompts and chat_histories must have the same length")

        # Create tasks for batch processing
        tasks = []
        for prompt, chat_history in zip(prompts, chat_histories):
            task = self.call_async(prompt, chat_history, remove_thinking, remove_tags)
            tasks.append(task)

        # Execute with batch delay between groups
        results = []
        batch_size = self.config.max_concurrent_requests

        for i in range(0, len(tasks), batch_size):
            batch_tasks = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    results.append("Error")
                    logging.error(f"Batch request failed: {result}")
                else:
                    results.append(result)

            # Add delay between batches
            if i + batch_size < len(tasks):
                await asyncio.sleep(self.config.batch_request_delay)

        return results

    def extract_json(self, content: str) -> Dict[str, Any]:
        """
        Extract JSON from model response.

        Args:
            content: Raw response content

        Returns:
            Parsed JSON dictionary
        """
        try:
            # First, try to extract JSON enclosed within ```json and ```
            start_idx = content.find("```json")
            if start_idx != -1:
                start_idx += 7  # Adjust index to start after the delimiter
                end_idx = content.rfind("```")
                json_content = content[start_idx:end_idx].strip()
            else:
                # If no delimiters, assume entire content could be JSON
                json_content = content.strip()

            # Clean up common issues that might cause parsing errors
            json_content = json_content.replace('None', 'null')  # Replace Python None with JSON null
            json_content = json_content.replace('\n', ' ').replace('\r', ' ')  # Remove newlines
            json_content = ' '.join(json_content.split())  # Normalize whitespace

            # Attempt to parse and return the JSON object
            return json.loads(json_content)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to extract JSON: {e}")
            # Try to clean up the content further if initial parsing fails
            try:
                # Remove any trailing commas before closing brackets/braces
                json_content = json_content.replace(',]', ']').replace(',}', '}')
                return json.loads(json_content)
            except:
                logging.error("Failed to parse JSON even after cleanup")
                return {}
        except Exception as e:
            logging.error(f"Unexpected error while extracting JSON: {e}")
            return {}


# Global instance for backward compatibility
_default_manager = None

def get_default_manager() -> ModelManager:
    """Get the default model manager instance"""
    global _default_manager
    if _default_manager is None:
        _default_manager = ModelManager()
    return _default_manager

# Backward compatibility functions
def ChatGPT_API(model: str, prompt: str, api_key: Optional[str] = None, chat_history: Optional[List[Dict[str, str]]] = None,
                remove_thinking: bool = True, remove_tags: Optional[Set[str]] = None) -> str:
    """Backward compatibility function for synchronous API calls"""
    config = ModelConfig(model=model, api_key=api_key)
    manager = ModelManager(config)
    return manager.call_sync(prompt, chat_history, remove_thinking, remove_tags)

def ChatGPT_API_with_finish_reason(model: str, prompt: str, api_key: Optional[str] = None, chat_history: Optional[List[Dict[str, str]]] = None,
                                   remove_thinking: bool = True, remove_tags: Optional[Set[str]] = None) -> Tuple[str, str]:
    """Backward compatibility function for synchronous API calls with finish reason"""
    config = ModelConfig(model=model, api_key=api_key)
    manager = ModelManager(config)
    return manager.call_sync_with_finish_reason(prompt, chat_history, remove_thinking, remove_tags)

async def ChatGPT_API_async(model: str, prompt: str, api_key: Optional[str] = None,
                            remove_thinking: bool = True, remove_tags: Optional[Set[str]] = None) -> str:
    """Backward compatibility function for asynchronous API calls with rate limiting"""
    config = ModelConfig(model=model, api_key=api_key)
    manager = ModelManager(config)
    return await manager.call_async(prompt, remove_thinking=remove_thinking, remove_tags=remove_tags)

def extract_json(content: str) -> Dict[str, Any]:
    """Backward compatibility function for JSON extraction"""
    manager = get_default_manager()
    return manager.extract_json(content)
