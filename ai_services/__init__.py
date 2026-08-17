"""AI Services: Multi-provider AI layer with OpenAI, Anthropic, and local LLM support."""
from __future__ import annotations

import os
import json
import time
import hashlib
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Iterator
from enum import Enum
from datetime import datetime

import requests


class AIProvider(Enum):
    """Provider AI supportati."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LOCAL = "local"


@dataclass
class AIMessage:
    """Messaggio per conversazione AI."""
    role: str  # system, user, assistant
    content: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class AIResponse:
    """Risposta da AI."""
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    duration_ms: int = 0
    cost_usd: float = 0.0
    metadata: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AIConfig:
    """Configurazione provider AI."""
    provider: AIProvider = AIProvider.OPENAI
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 2000
    timeout: int = 30
    system_prompt: Optional[str] = None
    
    # Provider-specific
    anthropic_version: str = "2023-06-01"
    ollama_host: str = "http://localhost:11434"


class AIProviderBase(ABC):
    """Base class per provider AI."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self._lock = threading.Lock()
    
    @abstractmethod
    def chat(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        """Esegue chat completion."""
        pass
    
    @abstractmethod
    def stream_chat(self, messages: List[AIMessage], **kwargs) -> Iterator[str]:
        """Streaming chat completion."""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Lista modelli disponibili."""
        pass
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calcola costo stimato (override per provider)."""
        return 0.0


class OpenAIProvider(AIProviderBase):
    """Provider OpenAI / Azure OpenAI."""
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = config.base_url or "https://api.openai.com/v1"
        self.model = config.model
        
        if not self.api_key:
            raise ValueError("OpenAI API key required")
    
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        start = time.time()
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": False
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        data = response.json()
        
        duration = int((time.time() - start) * 1000)
        
        choice = data["choices"][0]
        usage = data.get("usage", {})
        
        return AIResponse(
            content=choice["message"]["content"],
            provider="openai",
            model=payload["model"],
            tokens_used=usage.get("total_tokens"),
            duration_ms=int((time.time() - start) * 1000),
            cost_usd=self._calculate_cost(
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0)
            ),
            metadata={"usage": usage}
        )
    
    def stream_chat(self, messages: List[AIMessage], **kwargs) -> Iterator[str]:
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=self.config.timeout,
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except:
                        pass
    
    def get_available_models(self) -> List[str]:
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=10
            )
            response.raise_for_status()
            return [m["id"] for m in response.json()["data"]]
        except:
            return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Prezzi approssimativi per 1M tokens (USD)
        pricing = {
            "gpt-4o": (5.00, 15.00),
            "gpt-4o-mini": (0.15, 0.60),
            "gpt-4-turbo": (10.00, 30.00),
            "gpt-3.5-turbo": (0.50, 1.50),
        }
        rates = pricing.get(self.model, (0.15, 0.60))
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1_000_000


class AnthropicProvider(AIProviderBase):
    """Provider Anthropic (Claude)."""
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = config.base_url or "https://api.anthropic.com/v1"
        self.model = config.model
        self.version = config.anthropic_version
        
        if not self.api_key:
            raise ValueError("Anthropic API key required")
    
    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.version,
            "Content-Type": "application/json"
        }
    
    def chat(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        start = time.time()
        
        # Separa system prompt
        system_prompt = ""
        user_messages = []
        for m in messages:
            if m.role == "system":
                system_prompt = m.content
            else:
                user_messages.append({"role": m.role, "content": m.content})
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": user_messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        if system_prompt:
            payload["system"] = system_prompt
        
        response = requests.post(
            f"{self.base_url}/messages",
            headers=self._headers(),
            json=payload,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        data = response.json()
        
        duration = int((time.time() - start) * 1000)
        
        return AIResponse(
            content=data["content"][0]["text"],
            provider="anthropic",
            model=payload["model"],
            tokens_used=data["usage"]["input_tokens"] + data["usage"]["output_tokens"],
            duration_ms=int((time.time() - start) * 1000),
            cost_usd=self._calculate_cost(
                data["usage"]["input_tokens"],
                data["usage"]["output_tokens"]
            ),
            metadata={"usage": data["usage"]}
        )
    
    def stream_chat(self, messages: List[AIMessage], **kwargs) -> Iterator[str]:
        system_prompt = ""
        user_messages = []
        for m in messages:
            if m.role == "system":
                system_prompt = m.content
            else:
                user_messages.append({"role": m.role, "content": m.content})
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": user_messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True
        }
        if system_prompt:
            payload["system"] = system_prompt
        
        response = requests.post(
            f"{self.base_url}/messages",
            headers=self._headers(),
            json=payload,
            timeout=self.config.timeout,
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("type") == "content_block_delta":
                        yield data["delta"].get("text", "")
    
    def get_available_models(self) -> List[str]:
        return ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", 
                "claude-3-opus-20240229", "claude-3-sonnet-20240229"]
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        pricing = {
            "claude-3-5-sonnet-20241022": (3.00, 15.00),
            "claude-3-5-haiku-20241022": (0.80, 4.00),
            "claude-3-opus-20240229": (15.00, 75.00),
        }
        rates = pricing.get(self.model, (3.00, 15.00))
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1_000_000


class OllamaProvider(AIProviderBase):
    """Provider Ollama (local LLM)."""
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
        self.host = config.ollama_host
        self.model = config.model
    
    def chat(self, messages: List[AIMessage], **kwargs) -> AIResponse:
        start = time.time()
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": False,
            "options": {
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
            }
        }
        
        response = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        data = response.json()
        
        return AIResponse(
            content=data["message"]["content"],
            provider="ollama",
            model=payload["model"],
            duration_ms=int((time.time() - start) * 1000),
            cost_usd=0.0,  # Locale = gratuito
            metadata={"provider": "ollama"}
        )
    
    def stream_chat(self, messages: List[AIMessage], **kwargs) -> Iterator[str]:
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
            }
        }
        
        response = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=self.config.timeout,
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                if "message" in data and "content" in data["message"]:
                    yield data["message"]["content"]
                if data.get("done"):
                    break
    
    def get_available_models(self) -> List[str]:
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            response.raise_for_status()
            return [m["name"] for m in response.json().get("models", [])]
        except:
            return ["llama3.2", "mistral", "codellama"]


class AIManager:
    """Gestore centralizzato AI con supporto multi-provider."""
    
    def __init__(self):
        self.providers: Dict[AIProvider, AIProviderBase] = {}
        self.default_provider: Optional[AIProvider] = None
        self.config: Optional[AIConfig] = None
        self._conversation_history: List[AIMessage] = []
        self._max_history = 20
        self._cost_tracker = {
            "total_usd": 0.0,
            "total_tokens": 0,
            "requests": 0
        }
        self._lock = threading.Lock()
    
    def configure(self, provider: AIProvider, config: AIConfig) -> None:
        """Configura un provider."""
        if provider == AIProvider.OPENAI:
            self.providers[AIProvider.OPENAI] = OpenAIProvider(config)
        elif provider == AIProvider.ANTHROPIC:
            self.providers[AIProvider.ANTHROPIC] = AnthropicProvider(config)
        elif provider == AIProvider.OLLAMA:
            self.providers[AIProvider.OLLAMA] = OllamaProvider(config)
        
        self.default_provider = provider
        self.config = config
    
    def add_provider(self, provider: AIProvider, config: AIConfig) -> None:
        """Aggiunge provider senza cambiare default."""
        if provider == AIProvider.OPENAI:
            self.providers[AIProvider.OPENAI] = OpenAIProvider(config)
        elif provider == AIProvider.ANTHROPIC:
            self.providers[AIProvider.ANTHROPIC] = AnthropicProvider(config)
        elif provider == AIProvider.OLLAMA:
            self.providers[AIProvider.OLLAMA] = OllamaProvider(config)
    
    def get_provider(self, provider: Optional[AIProvider] = None) -> AIProviderBase:
        """Ottieni provider (default o specificato)."""
        p = provider or self.default_provider
        if p not in self.providers:
            raise ValueError(f"Provider {p} non configurato")
        return self.providers[p]
    
    def chat(self, messages: List[AIMessage], provider: Optional[AIProvider] = None, **kwargs) -> AIResponse:
        """Esegue chat completion."""
        provider_obj = self.get_provider(provider)
        
        # Aggiungi system prompt se configurato
        messages_with_system = list(messages)
        if self.config and self.config.system_prompt:
            has_system = any(m.role == "system" for m in messages)
            if not has_system:
                messages = [AIMessage(role="system", content=self.config.system_prompt)] + messages
        
        response = self.get_provider(provider).chat(messages, **kwargs)
        
        # Track costs
        with self._lock:
            self._cost_tracker["total_usd"] += response.cost_usd
            self._cost_tracker["total_tokens"] += response.tokens_used or 0
            self._cost_tracker["requests"] += 1
        
        return response
    
    def stream_chat(self, messages: List[AIMessage], provider: Optional[AIProvider] = None, **kwargs) -> Iterator[str]:
        """Streaming chat."""
        return self.get_provider(provider).stream_chat(messages, **kwargs)
    
    def ask(self, prompt: str, system_prompt: Optional[str] = None, 
            provider: Optional[AIProvider] = None, **kwargs) -> str:
        """Query semplice singola."""
        messages = []
        if system_prompt:
            messages.append(AIMessage(role="system", content=system_prompt))
        messages.append(AIMessage(role="user", content=prompt))
        
        response = self.chat(messages, provider, **kwargs)
        return response.content
    
    def ask_stream(self, prompt: str, system_prompt: Optional[str] = None,
                   provider: Optional[AIProvider] = None, **kwargs) -> Iterator[str]:
        """Streaming query singola."""
        messages = []
        if system_prompt:
            messages.append(AIMessage(role="system", content=system_prompt))
        messages.append(AIMessage(role="user", content=prompt))
        return self.stream_chat(messages, provider, **kwargs)
    
    def get_available_models(self, provider: Optional[AIProvider] = None) -> List[str]:
        """Modelli disponibili per provider."""
        return self.get_provider(provider).get_available_models()
    
    def get_cost_summary(self) -> Dict:
        """Riepilogo costi."""
        with self._lock:
            return dict(self._cost_tracker)
    
    def reset_cost_tracker(self) -> None:
        """Reset contatori costi."""
        with self._lock:
            self._cost_tracker = {"total_usd": 0.0, "total_tokens": 0, "requests": 0}
    
    def add_to_history(self, message: AIMessage) -> None:
        """Aggiunge a cronologia conversazione."""
        self._conversation_history.append(message)
        if len(self._conversation_history) > self._max_history:
            self._conversation_history = self._conversation_history[-self._max_history:]
    
    def get_conversation_context(self, max_messages: int = 10) -> List[AIMessage]:
        """Ottieni contesto conversazione recente."""
        return self._conversation_history[-max_messages:]
    
    def clear_history(self) -> None:
        """Pulisce cronologia."""
        self._conversation_history.clear()


# Istanza globale
_ai_manager: Optional[AIManager] = None


def get_ai_manager() -> AIManager:
    """Ottieni istanza AI Manager (singleton)."""
    global _ai_manager
    if _ai_manager is None:
        _ai_manager = AIManager()
    return _ai_manager


def configure_ai(provider: AIProvider, **config_kwargs) -> AIManager:
    """Configura AI Manager con provider."""
    config = AIConfig(provider=provider, **config_kwargs)
    manager = get_ai_manager()
    manager.configure(provider, AIConfig(provider=provider, **config_kwargs))
    return manager