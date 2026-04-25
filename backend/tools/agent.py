import base64
import inspect
import os
from PIL import Image, ImageOps
import io
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
        "api_key": "EMPTY",
        "base_url": "http://127.0.0.1:8000/v1",
        "multimodal": False,
    },
    "vllm-qwen3.5-9b": {
        "type": "openai",
        "model": "qwen35-9b",
        "api_key": "EMPTY",
        "base_url": "http://127.0.0.1:8001/v1",
        "multimodal": False,
    },
    "vllm-qwen2.5-3b": {
        "type": "openai",
        "model": "qwen25-3b-instruct",
        "api_key": "EMPTY",
        "base_url": "http://127.0.0.1:8000/v1",
        "multimodal": False,
    },
    "vllm-qwen2.5-7b-awq": {
        "type": "openai",
        "model": "qwen25-7b-instruct-awq",
        "api_key": "EMPTY",
        "base_url": "http://127.0.0.1:8000/v1",
        "multimodal": False,
    },
}

# ========== 统一客户端管理 ==========

clients = {}  # 缓存已初始化的客户端


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
            api_key = cfg.get("api_key")
            api_key_env = cfg.get("api_key_env")
            base_url = cfg.get("base_url")
            base_url_env = cfg.get("base_url_env")
            if api_key_env:
                api_key = os.environ.get(api_key_env, api_key)
            if base_url_env:
                base_url = os.environ.get(base_url_env, base_url)
            if not api_key:
                hint = f"（可通过环境变量 {api_key_env} 提供）" if api_key_env else ""
                raise RuntimeError(f"缺少 {agent} 的 API key{hint}")
            client = OpenAI(api_key=api_key, base_url=base_url)
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


# ========== 工具函数 ==========

def encode_image(image_path: str, resize: bool = False, target_size: int = 512) -> str:
    """将图像编码为 Base64 字符串（仅用于 VLM）"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    with Image.open(image_path) as img:
        img = ImageOps.exif_transpose(img)
        if resize:
            w, h = img.size
            if w > h:
                new_w, new_h = target_size, int(h * target_size / w)
            else:
                new_h, new_w = target_size, int(w * target_size / h)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        if img.mode != "RGB":
            img = img.convert("RGB")

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


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
            if extra_body:
                extra_args["extra_body"] = extra_body

            response = client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
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

def vlm_query(system_prompt: str, image_path: str, user_query: str, agent: str = "local-qwen2.5vl-7b", resize: bool = True, target_size: int = 512, enable_search: bool = False) -> str:
    """视觉语言模型调用接口（图文 + 可选联网搜索）"""
    if agent not in SUPPORTED_AGENTS:
        raise ValueError(f"Unsupported agent: {agent}")
    if not SUPPORTED_AGENTS[agent].get("multimodal", False):
        raise ValueError(f"Agent '{agent}' 不支持多模态输入，请使用纯文本接口 llm_query()")

    cfg = SUPPORTED_AGENTS[agent]
    base64_image = encode_image(image_path, resize=resize, target_size=target_size)
    tqdm.write(f"[SYSTEM]: {system_prompt}")
    tqdm.write(f"[QUERY]: {user_query}")

    try:
        client = get_client(agent)

        if cfg["type"] == "ollama":
            if enable_search:
                tqdm.write("⚠️ Warning: Ollama 本地模型不支持开箱即用的联网搜索，已忽略该参数。")
                
            response = _ollama_chat(
                client,
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query, "images": [base64_image]}
                ],
                options={"temperature": TEMP, "top_p": TOP_P},
                timeout=25,
            )
            answer = response["message"]["content"]

        elif cfg["type"] == "openai":
            image_url = f"data:image/jpeg;base64,{base64_image}"
            
            # ✨ 针对兼容 OpenAI 格式的接口，处理联网参数
            extra_args = {}
            if enable_search:
                extra_args["extra_body"] = {"enable_search": True}
                
            response = client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_query},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                timeout=25,
                **extra_args  # 将扩展参数解包传入
            )
            answer = response.choices[0].message.content

        elif cfg["type"] == "zhipu":
            # ✨ 针对智谱 GLM-4V，通过内置 tools 开启联网
            tools = [{"type": "web_search", "web_search": {"enable": True}}] if enable_search else None
            
            # 保持你调通的原有 messages 结构（图像和文本分两条）
            response = client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    },
                    {"role": "user", "content": user_query}
                ],
                tools=tools, # 传入联网工具
                timeout=60
            )
            answer = response.choices[0].message.content

        else:
            raise NotImplementedError(f"Agent type '{cfg['type']}' not implemented for VLM.")

        tqdm.write(f"[ANSWER]: {answer}")
        return answer

    except Exception as e:
        tqdm.write(f"[ERROR] {str(e)}")
        raise


def vlm_query_multi_base64(
    system_prompt: str,
    images_base64: list,
    user_query: str,
    agent: str = "local-qwen2.5vl-7b",
    enable_search: bool = False,
    timeout: int = 25,
) -> str:
    """多图版 VLM 接口（输入为 base64 列表），统一适配 ollama/openai/zhipu。"""
    if agent not in SUPPORTED_AGENTS:
        raise ValueError(f"Unsupported agent: {agent}")
    if not SUPPORTED_AGENTS[agent].get("multimodal", False):
        raise ValueError(f"Agent '{agent}' 不支持多模态输入，请使用纯文本接口 llm_query()")
    if not images_base64:
        raise ValueError("images_base64 is empty")

    cfg = SUPPORTED_AGENTS[agent]
    tqdm.write(f"[SYSTEM]: {system_prompt}")
    tqdm.write(f"[QUERY]: {user_query}")

    try:
        client = get_client(agent)

        if cfg["type"] == "ollama":
            if enable_search:
                tqdm.write("⚠️ Warning: Ollama 本地模型不支持开箱即用的联网搜索，已忽略该参数。")
            response = _ollama_chat(
                client,
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query, "images": images_base64},
                ],
                options={"temperature": TEMP, "top_p": TOP_P},
                timeout=timeout,
            )
            answer = response["message"]["content"]

        elif cfg["type"] == "openai":
            content = [{"type": "text", "text": user_query}]
            for base64_image in images_base64:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    }
                )
            extra_args = {}
            if enable_search:
                extra_args["extra_body"] = {"enable_search": True}
            response = client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                timeout=timeout,
                **extra_args,
            )
            answer = response.choices[0].message.content

        elif cfg["type"] == "zhipu":
            tools = [{"type": "web_search", "web_search": {"enable": True}}] if enable_search else None
            content = []
            for base64_image in images_base64:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"image/jpeg;base64,{base64_image}"},
                    }
                )
            content.append({"type": "text", "text": user_query})
            response = client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                tools=tools,
                timeout=max(60, timeout),
            )
            answer = response.choices[0].message.content

        else:
            raise NotImplementedError(f"Agent type '{cfg['type']}' not implemented for VLM.")

        tqdm.write(f"[ANSWER]: {answer}")
        return answer

    except Exception as e:
        tqdm.write(f"[ERROR] {str(e)}")
        raise

# ========== 测试入口 ==========

if __name__ == "__main__":
    # === 测试纯文本 ===
    print("\n" + "="*50)
    print("🔍 测试纯文本 LLM：local-qwen2.5vl-32b")
    text_result = llm_query(
        system_prompt="You are a rigorous assistant, please answer in one sentence.",
        user_query="Is the earth round?",
        agent="bailian-qwen3.5-plus"
    )
    print("✅ 纯文本回答:", text_result)

    # === 测试多模态（如配置了图像路径）===
    image_path = "/opt/data/private/zijian/CSG_new/data/hm3d/17DRP5sb8fy/matterport_color_images/0e92a69a50414253a23043758f111cec_i0_1.jpg"
    if os.path.exists(image_path):
        print("\n" + "="*50)
        print("🖼️  测试多模态 VLM：local-qwen2.5vl-7b")
        vlm_result = vlm_query(
            system_prompt="You are a visual assistant. Please describe the image content.",
            image_path=image_path,
            user_query="What objects are in the picture?",
            agent="bailian-qwen3.5-plus"
        )
        print("✅ VLM 回答:", vlm_result)
    else:
        print(f"⚠️  图像路径不存在，跳过多模态测试: {image_path}")
    
    
    # === 测试 LLM 联网搜索功能 ===
    print("\n" + "="*50)
    print("🌐 测试纯文本 LLM 联网搜索：glm-4")
    
    # 测试用例：问一个高度时效性的问题
    # 比如现在是 2026 年 3 月，我们可以问最近的体育赛事、科技新闻或当天的热点
    search_query = "请帮我查一下，2026年最近这几天，科技圈或者人工智能领域有什么最新的大新闻？请带上具体的日期。"
    
    try:
        search_result = llm_query(
            system_prompt="你是一个实时新闻播报员。请务必结合联网搜索的结果回答问题，并尽量给出信息的来源或时间。",
            user_query=search_query,
            agent="bailian-qwen3.5-plus", # 智谱的接口对联网支持得最原汁原味
            enable_search=True # ✨ 开启联网魔法！
        )
        print("\n✅ 联网搜索回答:\n", search_result)
    except Exception as e:
        print("\n❌ 联网测试失败:", str(e))



    image_path = "/opt/data/private/zijian/CSG_new/data/matterport3d/eval/zsNo4HB9uLZ/images/frame_id_0006.jpg" # 比如找一张不常见的新型机器人的照片
    if os.path.exists(image_path):
        print("\n" + "="*50)
        print("🖼️  测试多模态 VLM (带联网)：glm-4v")
        vlm_result = vlm_query(
            system_prompt="你是一个现场工程师助理。请识别图片中的物体，并结合网络搜索给出最新的相关信息。",
            image_path=image_path,
            user_query="帮我查一下图片里这个设备的最新使用手册或者近期新闻。",
            agent="bailian-qwen3.5-plus", 
            enable_search=True  # ✨ 开启联网
        )
        print("✅ 带联网的 VLM 回答:", vlm_result)
