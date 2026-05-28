"""
Multi-Provider AI Gateway with unified interface to 20+ LLM providers
"""
import httpx
import json
from typing import AsyncGenerator, Dict, Any, Optional, List
from abc import ABC, abstractmethod
from app.config import settings


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or self.get_default_base_url()
    
    @classmethod
    @abstractmethod
    def get_provider_name(cls) -> str:
        pass
    
    @abstractmethod
    def get_default_base_url(self) -> str:
        pass
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        json_mode: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion from the provider."""
        pass
    
    @abstractmethod
    async def embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        """Generate embeddings for texts."""
        pass


class OpenAIProvider(BaseProvider):
    """OpenAI API provider (also compatible with many OpenAI-compatible APIs)."""
    
    @classmethod
    def get_provider_name(cls) -> str:
        return "openai"
    
    def get_default_base_url(self) -> str:
        return "https://api.openai.com/v1"
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        json_mode: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
    
    async def embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json={"model": model, "input": texts},
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider."""
    
    @classmethod
    def get_provider_name(cls) -> str:
        return "anthropic"
    
    def get_default_base_url(self) -> str:
        return "https://api.anthropic.com"
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        json_mode: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Convert OpenAI format to Anthropic format
        system_message = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "user":
                anthropic_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                anthropic_messages.append({"role": "assistant", "content": msg["content"]})
        
        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        if system_message:
            payload["system"] = system_message
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=payload,
                timeout=60.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            if event.get("type") == "content_block_delta":
                                yield {"choices": [{"delta": {"content": event["delta"]["text"]}}]}
                            elif event.get("type") == "message_stop":
                                break
                        except json.JSONDecodeError:
                            continue
    
    async def embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        # Anthropic doesn't have native embeddings - would need to use a different provider
        raise NotImplementedError("Anthropic does not provide embeddings")


class GoogleProvider(BaseProvider):
    """Google Gemini API provider."""
    
    @classmethod
    def get_provider_name(cls) -> str:
        return "google"
    
    def get_default_base_url(self) -> str:
        return "https://generativelanguage.googleapis.com/v1beta"
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        json_mode: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            if msg["role"] in ["user", "assistant"]:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        url = f"{self.base_url}/models/{model}:streamGenerateContent"
        params = {"key": self.api_key, "alt": "sse"}
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        if json_mode:
            payload["generationConfig"]["response_mime_type"] = "application/json"
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                url,
                params=params,
                json=payload,
                timeout=60.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            chunk = json.loads(data)
                            if "candidates" in chunk:
                                text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                                yield {"choices": [{"delta": {"content": text}}]}
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
    
    async def embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        url = f"{self.base_url}/models/{model}:embedContent"
        params = {"key": self.api_key}
        
        embeddings = []
        async with httpx.AsyncClient() as client:
            for text in texts:
                response = await client.post(
                    url,
                    params=params,
                    json={"model": model, "content": {"parts": [{"text": text}]}},
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"]["values"])
        
        return embeddings


class OllamaProvider(BaseProvider):
    """Ollama local model provider."""
    
    @classmethod
    def get_provider_name(cls) -> str:
        return "ollama"
    
    def get_default_base_url(self) -> str:
        return settings.OLLAMA_BASE_URL
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        json_mode: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if json_mode:
            payload["format"] = "json"
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120.0
            ) as response:
                async for line in response.aiter_lines():
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk:
                            yield {"choices": [{"delta": {"content": chunk["message"].get("content", "")}}]}
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    
    async def embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        embeddings = []
        async with httpx.AsyncClient() as client:
            for text in texts:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": model, "prompt": text},
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])
        
        return embeddings


class LLMGateway:
    """Unified gateway for multiple LLM providers with automatic fallback."""
    
    PROVIDERS = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "ollama": OllamaProvider,
        # Add more providers as needed
    }
    
    def __init__(self):
        self._provider_instances: Dict[str, BaseProvider] = {}
    
    def get_provider(
        self,
        provider_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> BaseProvider:
        """Get or create a provider instance."""
        if provider_name not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        cache_key = f"{provider_name}:{api_key or ''}:{base_url or ''}"
        
        if cache_key not in self._provider_instances:
            provider_class = self.PROVIDERS[provider_name]
            self._provider_instances[cache_key] = provider_class(api_key, base_url)
        
        return self._provider_instances[cache_key]
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        provider: str = "openai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        json_mode: bool = False,
        fallback_providers: Optional[List[str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat completion with automatic fallback.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name
            provider: Primary provider name
            api_key: API key (optional, uses env default if not provided)
            base_url: Custom base URL (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream responses
            json_mode: Whether to request JSON output
            fallback_providers: List of fallback providers if primary fails
        """
        if fallback_providers is None:
            fallback_providers = [settings.FALLBACK_PROVIDER]
        
        providers_to_try = [provider] + fallback_providers
        
        for current_provider in providers_to_try:
            try:
                provider_instance = self.get_provider(current_provider, api_key, base_url)
                
                # Get appropriate model for this provider
                provider_model = self._map_model(model, current_provider)
                
                async for chunk in provider_instance.chat_completion(
                    messages=messages,
                    model=provider_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    json_mode=json_mode
                ):
                    yield chunk
                
                return  # Success, don't try fallbacks
                
            except Exception as e:
                print(f"Provider {current_provider} failed: {e}")
                if current_provider == providers_to_try[-1]:
                    raise  # Last provider failed, re-raise exception
                continue
    
    def _map_model(self, model: str, provider: str) -> str:
        """Map model names between providers if needed."""
        # Simple mapping - can be extended
        model_mappings = {
            "gpt-4o": {"anthropic": "claude-3-5-sonnet-20241022", "google": "gemini-1.5-pro"},
            "gpt-4o-mini": {"anthropic": "claude-3-haiku-20240307", "google": "gemini-1.5-flash"},
        }
        
        if provider in model_mappings.get(model, {}):
            return model_mappings[model][provider]
        
        return model
    
    async def embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small",
        provider: str = "openai",
        api_key: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings using specified provider."""
        provider_instance = self.get_provider(provider, api_key)
        return await provider_instance.embeddings(texts, model)


# Global gateway instance
gateway = LLMGateway()
