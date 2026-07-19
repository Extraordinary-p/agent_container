from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class AgentSettings(BaseSettings):
    PROVIDER: str = "openai"
    
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: Optional[str] = None
    
    DOUBao_API_KEY: str = ""
    DOUBao_MODEL: str = "doubao-pro-32k"
    DOUBao_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    
    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-max"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    ZHIPU_API_KEY: str = ""
    ZHIPU_MODEL: str = "glm-4"
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    
    CUSTOM_API_KEY: str = ""
    CUSTOM_MODEL: str = "custom-model"
    CUSTOM_BASE_URL: str = ""
    
    NETBOX_DOCKER_REPO: str = "https://github.com/netbox-community/netbox-docker.git"
    NETBOX_DOCKER_PATH: str = "./netbox-docker"
    
    LOG_LEVEL: str = "INFO"
    
    MAX_TOOL_CALL_ITERATIONS: int = 5
    AGENT_TIMEOUT: int = 300
    
    ENABLE_AUTO_REMEDIATION: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_provider_config(self):
        provider_map = {
            "openai": {
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_MODEL,
                "base_url": self.OPENAI_BASE_URL
            },
            "doubao": {
                "api_key": self.DOUBao_API_KEY,
                "model": self.DOUBao_MODEL,
                "base_url": self.DOUBao_BASE_URL
            },
            "qwen": {
                "api_key": self.QWEN_API_KEY,
                "model": self.QWEN_MODEL,
                "base_url": self.QWEN_BASE_URL
            },
            "zhipu": {
                "api_key": self.ZHIPU_API_KEY,
                "model": self.ZHIPU_MODEL,
                "base_url": self.ZHIPU_BASE_URL
            },
            "deepseek": {
                "api_key": self.DEEPSEEK_API_KEY,
                "model": self.DEEPSEEK_MODEL,
                "base_url": self.DEEPSEEK_BASE_URL
            },
            "custom": {
                "api_key": self.CUSTOM_API_KEY,
                "model": self.CUSTOM_MODEL,
                "base_url": self.CUSTOM_BASE_URL
            }
        }
        return provider_map.get(self.PROVIDER, provider_map["openai"])

settings = AgentSettings()
