from dataclasses import dataclass

@dataclass
class Configuration:
    gpt_api_key: str
    gpt_model: str
    gpt_temperature: float
    gpt_top_p: float
    gpt_max_tokens: int = 300
    