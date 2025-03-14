from typing import List, Optional


class LLMConfig:
    def __init__(
        self,
        model: str = "gpt-4o",
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        stop: Optional[List[str]] = None,
        n: Optional[int] = None,    
    ):
        """Configuaration class for LLM model and API token."""
        self.model = model
        self.api_token = api_token
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.stop = stop
        self.n = n

    @staticmethod
    def from_kwargs(kwargs: dict) -> "LLMConfig":
        return LLMConfig(
            model=kwargs.get("model", "gpt-4o"),
            api_token=kwargs.get("api_token"),
            base_url=kwargs.get("base_url"),
            temperature=kwargs.get("temperature"),
            max_tokens=kwargs.get("max_tokens"),
            top_p=kwargs.get("top_p"),
            frequency_penalty=kwargs.get("frequency_penalty"),
            presence_penalty=kwargs.get("presence_penalty"),
            stop=kwargs.get("stop"),
            n=kwargs.get("n")
        )

    def to_dict(self):
        return {
            "model": self.model,
            "api_token": self.api_token,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stop": self.stop,
            "n": self.n,
        }

    def clone(self, **kwargs):
        """Create a copy of this configuration with updated values.

        Args:
            **kwargs: Key-value pairs of configuration options to update

        Returns:
            llm_config: A new instance with the specified updates
        """
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return LLMConfig.from_kwargs(config_dict)


