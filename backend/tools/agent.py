import inspect
import os
import requests
from tqdm import tqdm

# ========== 模型配置 ==========

# client_bailian = OpenAI(
#         api_key="sk-bbea75db34b84de9b78b2b2218db5285",
#         base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
#     )
# client_blt = OpenAI(
#     api_key="sk-2uUpmQtgLvandvyf900dB63a62Ab48E58a7e540f5b4d1456",
#     base_url="https://api.bltcy.ai/v1",
# )
TEMP=0.5
TOP_P=0.85
LLAMA3_CHAT_TEMPLATE = """{% for message in messages %}{% if loop.index0 == 0 %}{{ bos_token }}{% endif %}{{ '<|start_header_id|>' + message['role'] + '<|end_header_id|>\n\n' + message['content'] | trim + '<|eot_id|>' }}{% endfor %}{% if add_generation_prompt %}{{ '<|start_header_id|>assistant<|end_header_id|>\n\n' }}{% endif %}"""
SUPPORTED_AGENTS = {
    # === 多模态模型（支持图像）===
    "local-gemma3-27b": {"type": "ollama", "model": "gemma3:27b", "multimodal": True},
    "local-qwen2.5vl-7b": {"type": "ollama", "model": "qwen2.5vl:7b", "multimodal": True},
    "local-qwen2.5vl-32b": {"type": "ollama", "model": "qwen2.5vl:32b", "multimodal": True},
    "local-qwen3.5-35b": {"type": "ollama", "model": "qwen3.5:35b", "multimodal": True},
    "local-qwen3:32b": {"type": "ollama", "model": "qwen3:32b", "multimodal": False},
    "qwen3-vl-flash": {
        "type": "openai", "model": "qwen3-vl-flash",
        "api_key": "sk-bbea75db34b84de9b78b2b2218db5285",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "multimodal": True
    },
    "bailian-qwen3.5-plus": {
        "type": "openai", "model": "qwen3.5-plus",
        "api_key": "sk-bbea75db34b84de9b78b2b2218db5285",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "multimodal": True
    },
    "bailian-qwen3.5-flash": {
        "type": "openai", "model": "qwen3.5-flash",
        "api_key": "sk-bbea75db34b84de9b78b2b2218db5285",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "multimodal": True
    },
    "lightai-gpt-4o": {
        "type": "openai", "model": "gpt-4o",
        "api_key": "sk-7DWq2LTpnov3eLnJR7V38iITck5QAo4d66qieRiTITyT7rrF",
        "base_url": "https://api.lightai.io/v1",
        "multimodal": True
    },
    "lightai-gpt-5": {
        "type": "openai", "model": "gpt-5-chat-latest",
        "api_key": "sk-7DWq2LTpnov3eLnJR7V38iITck5QAo4d66qieRiTITyT7rrF",
        "base_url": "https://api.lightai.io/v1",
        "multimodal": True
    },
    "glm-4v": {
        "type": "zhipu", "model": "glm-4v",
        "api_key": "cff8bdd3deccdb90bc17646f817b6dde.K9XJ7rCYzfAbkNYu",
        "multimodal": True
    },

    # === 纯文本模型 ===
    "glm-4": {
        "type": "zhipu", "model": "glm-4",
        "api_key": "cff8bdd3deccdb90bc17646f817b6dde.K9XJ7rCYzfAbkNYu",
        "multimodal": False
    },
    "gpt-4o-mini": {
        "type": "openai", "model": "gpt-4o-mini",
        "api_key": "sk-7DWq2LTpnov3eLnJR7V38iITck5QAo4d66qieRiTITyT7rrF",
        "base_url": "https://api.lightai.io/v1",
        "multimodal": False
    },
    "local-llama3.1-8b": {
        "type": "ollama", "model": "llama3.1:8b",
        "multimodal": False
    },
    "local-qwen8b": {
        "type": "ollama", "model": "qwen3-vl:8b",
        "multimodal": False
    },
    "local-llama3": {
        "type": "ollama", "model": "llama3:latest",
        "multimodal": False
    },
    "vllm-qwen3.5-4b": {
        "type": "openai",
        "model": "qwen35-4b",
        "model_env": "VLLM_MODEL",
        "api_key": "EMPTY",
        "api_key_env": "VLLM_API_KEY",
        "base_url": "http://127.0.0.1:8000/v1",
        "base_url_env": "VLLM_BASE_URL",
        "multimodal": False,
    },
    "vllm-qwen3.5-9b": {
        "type": "openai",
        "model": "qwen35-9b",
        "model_env": "VLLM_MODEL",
        "api_key": "EMPTY",
        "api_key_env": "VLLM_API_KEY",
        "base_url": "http://127.0.0.1:8001/v1",
        "base_url_env": "VLLM_BASE_URL",
        "multimodal": False,
    },
    "vllm-deepseek-r1-14b": {
        "type": "openai",
        "model": "deepseek-r1-14b",
        "model_env": "VLLM_MODEL",
        "api_key": "EMPTY",
        "api_key_env": "VLLM_API_KEY",
        "base_url": "http://127.0.0.1:8000/v1",
        "base_url_env": "VLLM_BASE_URL",
        "multimodal": False,
    },
    "vllm-llama3.1-8b": {
        "type": "openai",
        "model": "llama-3.1-8b",
        "model_env": "VLLM_MODEL",
        "api_key": "EMPTY",
        "api_key_env": "VLLM_API_KEY",
        "base_url": "http://127.0.0.1:8000/v1",
        "base_url_env": "VLLM_BASE_URL",
        "multimodal": False,
    },
        "vllm-qwen3.6-27b": {
        "type": "openai",
        "model": "qwen36-27b",
        "model_env": "VLLM_MODEL",
        "api_key": "EMPTY",
        "api_key_env": "VLLM_API_KEY",
        "base_url": "http://127.0.0.1:8000/v1",
        "base_url_env": "VLLM_BASE_URL",
        "multimodal": True,
    },
    "vllm-qwen2.5-3b": {
        "type": "openai",
        "model": "qwen25-3b-instruct",
        "model_env": "VLLM_MODEL",
        "api_key": "EMPTY",
        "api_key_env": "VLLM_API_KEY",
        "base_url": "http://127.0.0.1:8000/v1",
        "base_url_env": "VLLM_BASE_URL",
        "multimodal": False,
    },
    "vllm-qwen2.5-7b-awq": {
        "type": "openai",
        "model": "qwen25-7b-instruct-awq",
        "model_env": "VLLM_MODEL",
        "api_key": "EMPTY",
        "api_key_env": "VLLM_API_KEY",
        "base_url": "http://127.0.0.1:8000/v1",
        "base_url_env": "VLLM_BASE_URL",
        "multimodal": False,
    },
}

# ========== 统一客户端管理 ==========

clients = {}  # 缓存已初始化的客户端


def _cfg_value(cfg: dict, key: str):
    env_key = cfg.get(f"{key}_env")
    if env_key:
        return os.environ.get(env_key, cfg.get(key))
    return cfg.get(key)


def resolved_agent_config(agent: str) -> dict:
    if agent not in SUPPORTED_AGENTS:
        raise ValueError(f"Unsupported agent: {agent}")
    cfg = dict(SUPPORTED_AGENTS[agent])
    for key in ("model", "api_key", "base_url"):
        cfg[key] = _cfg_value(cfg, key)
    return cfg


class OllamaHTTPClient:
    def __init__(self, host: str):
        self.host = host.rstrip("/")

    def chat(self, model: str, messages: list, options: dict | None = None, timeout: int | None = None):
        response = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "options": options or {},
                "stream": False,
            },
            timeout=max(60, int(timeout or 300)),
        )
        response.raise_for_status()
        return response.json()


def _ollama_chat(client, *, model: str, messages: list, options: dict | None = None, timeout: int | None = None):
    kwargs = {
        "model": model,
        "messages": messages,
        "options": options or {},
    }
    try:
        signature = inspect.signature(client.chat)
    except (TypeError, ValueError):
        signature = None
    if signature is None or "timeout" in signature.parameters:
        kwargs["timeout"] = timeout
    return client.chat(**kwargs)


def get_client(agent: str):
    """统一懒加载客户端，按需初始化，安全导入"""
    global clients
    if agent in clients:
        return clients[agent]

    cfg = SUPPORTED_AGENTS[agent]
    client_type = cfg["type"]

    try:
        if client_type == "ollama":
            host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
            try:
                from ollama import Client
                client = Client(host=host)
            except ImportError:
                client = OllamaHTTPClient(host=host)
            clients[agent] = client
            return client

        elif client_type == "openai":
            from openai import OpenAI
            import httpx
            api_key = _cfg_value(cfg, "api_key")
            api_key_env = cfg.get("api_key_env")
            base_url = _cfg_value(cfg, "base_url")
            if not api_key:
                hint = f"（可通过环境变量 {api_key_env} 提供）" if api_key_env else ""
                raise RuntimeError(f"缺少 {agent} 的 API key{hint}")
            client = OpenAI(api_key=api_key, base_url=base_url, http_client=httpx.Client(trust_env=False))
            clients[agent] = client
            return client

        elif client_type == "zhipu":
            from zhipuai import ZhipuAI
            client = ZhipuAI(api_key=cfg["api_key"])
            clients[agent] = client
            return client

        else:
            raise ValueError(f"Unsupported client type: {client_type}")

    except ImportError as e:
        pkg = {
            "ollama": "ollama",
            "openai": "openai",
            "zhipu": "zhipuai"
        }.get(client_type, client_type)
        raise ImportError(f"请安装依赖包: pip install {pkg}") from e
    except Exception as e:
        raise RuntimeError(f"初始化 {agent} 客户端失败: {str(e)}") from e


# ========== 核心接口 ==========

def llm_query(system_prompt: str, user_query: str, agent: str = "glm-4", timeout: int = 30, enable_search: bool = False) -> str:
    """纯文本 LLM 调用接口 (带开箱即用的联网搜索)"""
    if agent not in SUPPORTED_AGENTS:
        raise ValueError(f"Unsupported agent: {agent}")
    if SUPPORTED_AGENTS[agent].get("multimodal", False):
        tqdm.write(f"⚠️  Warning: {agent} 是多模态模型，但当前调用为纯文本模式，仍可运行。")

    cfg = SUPPORTED_AGENTS[agent]
    client = get_client(agent)

    tqdm.write(f"[SYSTEM]: {system_prompt}")
    tqdm.write(f"[QUERY]: {user_query}")

    try:
        if cfg["type"] == "ollama":
            # Ollama 本地模型不支持自带联网
            if enable_search:
                tqdm.write("⚠️ Warning: Ollama 本地模型不支持开箱即用的联网搜索，已忽略该参数。")
            
            response = _ollama_chat(
                client,
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                options={"temperature": TEMP, "top_p": TOP_P},
                timeout=timeout,
            )
            answer = response["message"]["content"]

        elif cfg["type"] == "openai":
            # ✨ 针对兼容 OpenAI 格式的第三方接口 (如阿里云 DashScope)
            # 通过 extra_body 传入特定平台支持的参数
            extra_args = {}
            extra_body = {}
            if enable_search:
                # 注意：这行代码对阿里云 Qwen 模型生效，但如果传给纯正的 OpenAI 可能会被忽略
                extra_body["enable_search"] = True
            if agent.startswith("vllm-qwen3"):
                extra_body["chat_template_kwargs"] = {"enable_thinking": False}
            if agent.startswith("vllm-deepseek"):
                extra_args["response_format"] = {"type": "json_object"}
            if agent.startswith("vllm-llama"):
                extra_args["response_format"] = {"type": "json_object"}
            if extra_body:
                extra_args["extra_body"] = extra_body
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ]

            response = client.chat.completions.create(
                model=_cfg_value(cfg, "model"),
                messages=messages,
                temperature=TEMP,
                top_p=TOP_P,
                max_tokens=128,
                timeout=timeout,
                **extra_args  # 将扩展参数解包传入
            )
            answer = response.choices[0].message.content

        elif cfg["type"] == "zhipu":
            # ✨ 针对智谱，直接通过内置 tools 开启
            tools = [{"type": "web_search", "web_search": {"enable": True}}] if enable_search else None
            
            response = client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                tools=tools,
                timeout=timeout
            )
            answer = response.choices[0].message.content

        else:
            raise NotImplementedError(f"Agent type '{cfg['type']}' not implemented for text.")

        tqdm.write(f"[ANSWER]: {answer}")
        return answer

    except Exception as e:
        tqdm.write(f"[ERROR] {str(e)}")
        raise

__all__ = ["llm_query", "resolved_agent_config"]
