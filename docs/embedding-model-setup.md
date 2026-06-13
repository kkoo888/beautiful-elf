# Embedding 模型替换操作手册

> 目标：将意图路由 + 记忆管理器的 Embedding 从 Ollama (Qwen3-0.6B, 52s) 替换为本地 ONNX (bge-large-zh-v1.5, ~50ms)

---

## 一、环境准备

```bash
# 确认 Python 版本（需要 3.9+）
python --version

# 安装依赖
pip install huggingface_hub optimum onnx onnxruntime
```

---

## 二、下载模型

### 方案 A：HuggingFace 直连（国外网络）

```bash
# 创建模型目录
mkdir -p models/embedding

# 下载 bge-large-zh-v1.5
huggingface-cli download BAAI/bge-large-zh-v1.5 \
  --local-dir models/embedding/bge-large-zh-v1.5
```

### 方案 B：国内镜像（推荐，速度快）

```bash
# 设置镜像源
export HF_ENDPOINT=https://hf-mirror.com

# 下载
huggingface-cli download BAAI/bge-large-zh-v1.5 \
  --local-dir models/embedding/bge-large-zh-v1.5
```

### 方案 C：Git 克隆（备用）

```bash
# HuggingFace
git clone https://huggingface.co/BAAI/bge-large-zh-v1.5 models/embedding/bge-large-zh-v1.5

# 或 GitCode 镜像
git clone https://gitcode.com/hf_mirrors/ai-gitcode/bge-large-zh-v1.5 models/embedding/bge-large-zh-v1.5
```

---

## 三、转换为 ONNX 格式

```bash
# 转换（约 2-5 分钟）
optimum-cli export onnx \
  --model models/embedding/bge-large-zh-v1.5 \
  --task feature-extraction \
  models/embedding/bge-large-zh-v1.5-onnx/

# 验证输出目录
ls -lh models/embedding/bge-large-zh-v1.5-onnx/
# 应该看到：
#   model.onnx          ← ONNX 模型（约 1.2GB）
#   config.json
#   tokenizer.json
#   tokenizer_config.json
#   vocab.txt
#   special_tokens_map.json
```

---

## 四、（可选）INT8 量化 — 压缩模型体积

```bash
# 安装量化工具
pip install onnxruntime-tools

# 量化（约 5-10 分钟，模型从 1.2GB 压缩到约 300MB）
python -m onnxruntime.quantization.quantize \
  --input models/embedding/bge-large-zh-v1.5-onnx/model.onnx \
  --output models/embedding/bge-large-zh-v1.5-onnx/model_quant.onnx \
  --quantize_mode dynamic

# 替换原文件（备份后替换）
mv models/embedding/bge-large-zh-v1.5-onnx/model.onnx \
   models/embedding/bge-large-zh-v1.5-onnx/model.onnx.bak
mv models/embedding/bge-large-zh-v1.5-onnx/model_quant.onnx \
   models/embedding/bge-large-zh-v1.5-onnx/model.onnx
```

---

## 五、复制到项目

```bash
# 复制 ONNX 模型到项目路由目录
cp -r models/embedding/bge-large-zh-v1.5-onnx/ \
  backend/app/router/models/bge-large-zh-onnx/

# 确认文件就位
ls -lh backend/app/router/models/bge-large-zh-onnx/
```

---

## 六、安装 Python 依赖

```bash
cd backend

# 激活虚拟环境（如果有的话）
source venv/bin/activate    # Linux/Mac
# 或
venv\Scripts\activate       # Windows

# 安装 ONNX Runtime
pip install onnxruntime

# 验证安装
python -c "import onnxruntime; print(onnxruntime.__version__)"
```

---

## 七、验证模型可用

```bash
cd backend

python -c "
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

# 加载
tokenizer = AutoTokenizer.from_pretrained('app/router/models/bge-large-zh-onnx/')
session = ort.InferenceSession('app/router/models/bge-large-zh-onnx/model.onnx')

# 测试推理
text = '你好，今天天气怎么样？'
inputs = tokenizer(text, return_tensors='np', padding=True, truncation=True, max_length=512)
outputs = session.run(None, {
    'input_ids': inputs['input_ids'],
    'attention_mask': inputs['attention_mask'],
})

# 取 [CLS] token 作为句向量
embedding = outputs[0][0][0]
print(f'向量维度: {embedding.shape}')       # 应该是 (1024,)
print(f'前 5 个值: {embedding[:5]}')
print('✅ ONNX 推理成功')
"
```

---

## 八、修改项目代码

> 这步小茜会帮你做，以下是改动说明供参考

需要改动的文件：

1. **`backend/main.py`** — 修改 `_init_intent()` 和 `_init_memory()` 中的 embedding 初始化
2. **`backend/app/router/models/v4.2_phase3_inference/router.runtime.yaml`** — 更新 bge 配置

### 8.1 main.py 改动（意图路由）

```python
# 之前（Ollama）
from llama_index.embeddings.ollama import OllamaEmbedding
embedding_model = OllamaEmbedding(
    model_name="dengcao/Qwen3-Embedding-0.6B:Q8_0",
    base_url=settings.OLLAMA_HOST,
)

# 之后（ONNX）
import onnxruntime as ort
from transformers import AutoTokenizer

class ONNXEmbedding:
    """本地 ONNX Embedding 推理"""
    def __init__(self, model_dir: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.session = ort.InferenceSession(
            f"{model_dir}/model.onnx",
            providers=['CPUExecutionProvider']
        )

    async def aget_text_embedding(self, text: str) -> list:
        import numpy as np
        inputs = self.tokenizer(
            text, return_tensors='np',
            padding=True, truncation=True, max_length=512
        )
        outputs = self.session.run(None, {
            'input_ids': inputs['input_ids'],
            'attention_mask': inputs['attention_mask'],
        })
        # [CLS] token 的向量作为句向量
        return outputs[0][0][0].tolist()

embedding_model = ONNXEmbedding("app/router/models/bge-large-zh-onnx/")
```

---

## 九、重建 Qdrant 集合（如果维度变了）

> bge-large-zh-v1.5 是 1024 维，和当前一致，**不需要重建**。
> 如果换成 768/512 维的模型才需要执行这步。

```bash
# 进入 Qdrant 管理界面或用 API 删除旧集合
curl -X DELETE http://localhost:6333/collections/intent_vectors
curl -X DELETE http://localhost:6333/collections/semantic_cache
curl -X DELETE http://localhost:6333/collections/memory_vectors

# 重启后端会自动重建集合（vector_size 按新维度配置）
```

---

## 十、重启验证

```bash
# 重启后端
cd backend
python main.py

# 观察日志，应该看到：
# [intent_router] 意图路由就绪        ← ONNX 加载成功
# [memory_manager] 记忆管理器就绪     ← ONNX 加载成功

# 测试对话，观察 intent_router 耗时
# 之前: ~52 秒 → 之后: ~50-200ms
```

---

## 速度对比参考

| 方案 | 模型 | 推理耗时 | 模型大小 |
|------|------|---------|---------|
| 之前 | Qwen3-Embedding-0.6B (Ollama CPU) | ~52 秒 | ~600M 参数 |
| 之后 | bge-large-zh-v1.5 (ONNX) | ~50-200ms | ~1.2GB (FP32) |
| 之后(量化) | bge-large-zh-v1.5 (ONNX INT8) | ~30-100ms | ~300MB |

---

## 常见问题

### Q: 下载很慢怎么办？
用方案 B（hf-mirror.com 镜像），或用 GitCode 镜像。

### Q: 转换 ONNX 报错？
```bash
# 确认 optimum 版本 >= 1.14
pip install --upgrade optimum onnx onnxruntime
```

### Q: ONNX 推理报维度不匹配？
确认 Qdrant 集合的 vector_size 和模型输出维度一致：
- bge-large-zh-v1.5 → 1024 维
- bge-base-zh-v1.5 → 768 维
- bge-small-zh-v1.5 → 512 维

### Q: 内存不够用？
用 INT8 量化（第四步），模型从 1.2GB 压到 ~300MB。
或换 `bge-base-zh-v1.5`（~400MB FP32 / ~100MB INT8）。
