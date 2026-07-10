# 工作流模块重构操作手册

> **目标**：借鉴 Coze 前端 + Dify 后端，统一为 beautiful-elf 自己的 API 格式
> **技术栈**：FastAPI + React + TypeScript + React Flow
> **可断点续写**：每个步骤独立，完成后可暂停，下次从下一步继续

---

## 📋 目录

- [阶段 0：准备工作](#阶段-0准备工作)
- [阶段 1：定义统一 API 契约](#阶段-1定义统一-api-契约)
- [阶段 2：后端执行引擎（参考 Dify）](#阶段-2后端执行引擎参考-dify)
- [阶段 3：前端编辑器（参考 Coze）](#阶段-3前端编辑器参考-coze)
- [阶段 4：前后端联调](#阶段-4前后端联调)
- [阶段 5：测试验证](#阶段-5测试验证)

---

## 阶段 0：准备工作

### 0.1 克隆参考项目（只读参考）

```bash
# 克隆到临时目录（不提交到我们的仓库）
cd /tmp
git clone --depth 1 https://github.com/coze-dev/coze-studio.git
git clone --depth 1 https://github.com/langgenius/dify.git
```

### 0.2 关键参考文件索引

#### Coze 前端（UI 交互参考）

| 文件 | 说明 |
|------|------|
| `coze-studio/frontend/packages/workflow/` | 🎯 **核心：工作流编辑器** |
| `coze-studio/frontend/packages/agent-ide/workflow/` | Agent 工作流模式 |
| `coze-studio/frontend/packages/workflow/src/` | 节点组件、画布、配置面板 |

#### Dify 后端（执行引擎参考）

| 文件 | 说明 |
|------|------|
| `dify/api/core/workflow/workflow_entry.py` | 🎯 **核心：工作流入口** |
| `dify/api/core/workflow/node_factory.py` | 节点工厂（注册/创建节点） |
| `dify/api/core/workflow/node_runtime.py` | 节点运行时 |
| `dify/api/core/workflow/graph_topology.py` | 🎯 **核心：DAG 拓扑排序** |
| `dify/api/core/workflow/nodes/` | 所有节点实现 |
| `dify/api/core/workflow/nodes/llm/` | LLM 节点 |
| `dify/api/core/workflow/nodes/code/` | 代码执行节点 |
| `dify/api/core/workflow/nodes/if_else/` | 条件分支节点 |
| `dify/api/core/workflow/nodes/iteration/` | 迭代/循环节点 |
| `dify/api/core/workflow/nodes/http_request/` | HTTP 请求节点 |
| `dify/api/core/workflow/nodes/agent/` | Agent 节点 |
| `dify/api/core/workflow/variable_pool_initializer.py` | 变量池 |
| `dify/api/core/workflow/template_rendering.py` | 模板渲染（变量替换） |

#### beautiful-elf（我们的代码）

| 文件 | 说明 |
|------|------|
| `backend/app/agent/workflow_engine.py` | 当前引擎（空壳） |
| `backend/app/api/v1/workflow.py` | 当前 API |
| `backend/app/models/workflow.py` | 数据模型 |
| `backend/app/services/workflow_service.py` | 业务服务 |
| `web/src/renderer/modules/workflow/` | 前端模块 |
| `web/src/renderer/modules/workflow/components/workflow-editor.tsx` | DAG 编辑器 |

### ✅ 阶段 0 完成标志

- [ ] 参考项目已克隆
- [ ] 关键文件已浏览
- [ ] 理解 Coze 前端结构
- [ ] 理解 Dify 后端结构

**断点**：完成后可暂停，下次从阶段 1 开始。

---

## 阶段 1：定义统一 API 契约

> **原则**：不兼容 Coze 也不兼容 Dify，全部统一成我们自己的格式

### 1.1 DAG 数据格式

```json
{
  "nodes": {
    "start_1": {
      "type": "start",
      "label": "开始",
      "position": {"x": 100, "y": 200},
      "config": {
        "variables": [
          {"name": "topic", "type": "string", "required": true}
        ]
      }
    },
    "llm_1": {
      "type": "llm",
      "label": "分析主题",
      "position": {"x": 300, "y": 200},
      "config": {
        "prompt": "请分析以下主题：{{start_1.topic}}",
        "model": "auto",
        "temperature": 0.7
      }
    },
    "condition_1": {
      "type": "condition",
      "label": "判断结果",
      "position": {"x": 500, "y": 200},
      "config": {
        "field": "llm_1.result",
        "operator": "contains",
        "value": "重要"
      }
    },
    "end_1": {
      "type": "end",
      "label": "结束",
      "position": {"x": 700, "y": 200},
      "config": {}
    }
  },
  "edges": [
    {"from": "start_1", "to": "llm_1"},
    {"from": "llm_1", "to": "condition_1"},
    {"from": "condition_1", "to": "end_1", "label": "是"},
    {"from": "condition_1", "to": "llm_1", "label": "否"}
  ]
}
```

### 1.2 节点类型清单

| 类型 | 说明 | config 字段 |
|------|------|------------|
| `start` | 开始节点 | `variables`: 输入变量列表 |
| `end` | 结束节点 | `output_keys`: 输出字段 |
| `llm` | LLM 调用 | `prompt`, `model`, `temperature`, `max_tokens` |
| `tool` | 工具调用 | `tool_name`, `args` |
| `condition` | 条件分支 | `field`, `operator`, `value` |
| `code` | 代码执行 | `language`, `code` |
| `http` | HTTP 请求 | `method`, `url`, `headers`, `body` |
| `iteration` | 循环遍历 | `input_key`, `output_key`, `sub_dag` |
| `parallel` | 并行执行 | `branches`: 子 DAG 列表 |
| `variable` | 变量操作 | `operation`, `key`, `value` |

### 1.3 API 端点定义

```
# 工作流 CRUD
GET    /api/v1/workflows                    # 列表
POST   /api/v1/workflows                    # 创建
GET    /api/v1/workflows/{id}               # 详情
PUT    /api/v1/workflows/{id}               # 更新
DELETE /api/v1/workflows/{id}               # 删除
PATCH  /api/v1/workflows/{id}/enable        # 启用
PATCH  /api/v1/workflows/{id}/disable       # 禁用

# 执行
POST   /api/v1/workflows/{id}/execute       # 执行工作流
GET    /api/v1/workflows/{id}/runs           # 运行记录
GET    /api/v1/workflows/{id}/runs/{run_id}  # 运行详情

# 实时通信
WS     /ws/workflow/{run_id}                 # WebSocket 实时状态
```

### 1.4 响应格式

```json
// 成功
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {...}
}

// 分页
{
  "code": "SUCCESS",
  "data": [...],
  "total": 100,
  "page": 1,
  "pageSize": 20
}

// 错误
{
  "code": "WORKFLOW_VALIDATION",
  "message": "DAG 存在循环依赖",
  "userTip": "请检查节点连接"
}
```

### ✅ 阶段 1 完成标志

- [ ] DAG JSON 格式已定义
- [ ] 节点类型清单已确认
- [ ] API 端点已定义
- [ ] 响应格式已确认

**断点**：完成后可暂停，下次从阶段 2 开始。

---

## 阶段 2：后端执行引擎（参考 Dify）

### 2.1 重构 workflow_engine.py

**参考文件**：`dify/api/core/workflow/graph_topology.py` + `dify/api/core/workflow/node_factory.py`

**改动要点**：
1. 实现真正的节点执行器（不是空壳）
2. 支持条件分支路由
3. 支持变量替换
4. 支持循环/迭代

```python
# 新文件结构
backend/app/agent/workflow/
├── __init__.py
├── engine.py              # 主引擎（重构自 workflow_engine.py）
├── graph_topology.py      # DAG 拓扑排序（参考 Dify）
├── node_factory.py        # 节点工厂（注册/创建）
├── node_runtime.py        # 节点运行时
├── variable_pool.py       # 变量池
├── nodes/
│   ├── __init__.py
│   ├── base.py            # 节点基类
│   ├── start_node.py      # 开始节点
│   ├── end_node.py        # 结束节点
│   ├── llm_node.py        # LLM 节点（真正调用 LLM）
│   ├── tool_node.py       # 工具节点（真正执行工具）
│   ├── condition_node.py  # 条件分支节点
│   ├── code_node.py       # 代码执行节点
│   ├── http_node.py       # HTTP 请求节点
│   └── iteration_node.py  # 循环节点
```

### 2.2 实现步骤

#### Step 1：节点基类

```python
# backend/app/agent/workflow/nodes/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseNode(ABC):
    """节点基类"""
    
    @abstractmethod
    async def execute(self, config: dict, context: dict) -> dict:
        """
        执行节点
        
        Args:
            config: 节点配置
            context: 上下文变量池
            
        Returns:
            节点输出（会合并到 context）
        """
        pass
    
    def resolve_variables(self, template: str, context: dict) -> str:
        """替换模板中的变量 {{node_id.field}}"""
        import re
        def replace(match):
            key = match.group(1)
            return str(context.get(key, match.group(0)))
        return re.sub(r'\{\{(.+?)\}\}', replace, template)
```

#### Step 2：LLM 节点（参考 Dify LLMNode）

```python
# backend/app/agent/workflow/nodes/llm_node.py
from .base import BaseNode
from app.utils.llm_client import LLMClient

class LLMNode(BaseNode):
    """LLM 调用节点"""
    
    async def execute(self, config: dict, context: dict) -> dict:
        prompt = self.resolve_variables(config.get("prompt", ""), context)
        model = config.get("model", "auto")
        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens", 2048)
        
        client = LLMClient()
        response = await client.achat(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return {"result": response}
```

#### Step 3：条件节点（参考 Dify IfElseNode）

```python
# backend/app/agent/workflow/nodes/condition_node.py
from .base import BaseNode

class ConditionNode(BaseNode):
    """条件分支节点"""
    
    OPERATORS = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        "contains": lambda a, b: b in str(a),
        "not_contains": lambda a, b: b not in str(a),
        ">": lambda a, b: float(a) > float(b),
        "<": lambda a, b: float(a) < float(b),
        "exists": lambda a, b: a is not None,
    }
    
    async def execute(self, config: dict, context: dict) -> dict:
        field = config.get("field", "")
        operator = config.get("operator", "==")
        expected = config.get("value", "")
        
        actual = context.get(field)
        op_func = self.OPERATORS.get(operator, lambda a, b: False)
        result = op_func(actual, expected)
        
        return {"result": result, "branch": "true" if result else "false"}
```

#### Step 4：节点工厂

```python
# backend/app/agent/workflow/node_factory.py
from typing import Dict, Type
from .nodes.base import BaseNode
from .nodes.start_node import StartNode
from .nodes.end_node import EndNode
from .nodes.llm_node import LLMNode
from .nodes.tool_node import ToolNode
from .nodes.condition_node import ConditionNode
from .nodes.code_node import CodeNode
from .nodes.http_node import HTTPNode
from .nodes.iteration_node import IterationNode

class NodeFactory:
    """节点工厂"""
    
    _registry: Dict[str, Type[BaseNode]] = {
        "start": StartNode,
        "end": EndNode,
        "llm": LLMNode,
        "tool": ToolNode,
        "condition": ConditionNode,
        "code": CodeNode,
        "http": HTTPNode,
        "iteration": IterationNode,
    }
    
    @classmethod
    def create(cls, node_type: str) -> BaseNode:
        node_class = cls._registry.get(node_type)
        if not node_class:
            raise ValueError(f"未注册的节点类型: {node_type}")
        return node_class()
    
    @classmethod
    def register(cls, node_type: str, node_class: Type[BaseNode]):
        cls._registry[node_type] = node_class
```

#### Step 5：变量池

```python
# backend/app/agent/workflow/variable_pool.py
from typing import Any, Dict

class VariablePool:
    """变量池 — 节点间数据传递"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
    
    def set(self, key: str, value: Any):
        self._data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def resolve(self, template: str) -> str:
        """替换模板中的 {{key}}"""
        import re
        def replace(match):
            k = match.group(1)
            return str(self._data.get(k, match.group(0)))
        return re.sub(r'\{\{(.+?)\}\}', replace, template)
    
    def to_dict(self) -> dict:
        return dict(self._data)
```

#### Step 6：主引擎（重构）

```python
# backend/app/agent/workflow/engine.py
from typing import Dict, Any, List
from .graph_topology import topological_sort
from .node_factory import NodeFactory
from .variable_pool import VariablePool

class WorkflowEngine:
    """工作流执行引擎"""
    
    async def execute(self, db, workflow_id: int, input_data: dict = None) -> dict:
        # 1. 加载工作流定义
        workflow = await self._load_workflow(db, workflow_id)
        dag = workflow.dag_json
        nodes = dag.get("nodes", {})
        edges = dag.get("edges", [])
        
        # 2. 拓扑排序
        order = topological_sort(nodes, edges)
        
        # 3. 初始化变量池
        pool = VariablePool()
        if input_data:
            for k, v in input_data.items():
                pool.set(k, v)
        
        # 4. 逐步执行
        for node_name in order:
            node_def = nodes[node_name]
            node_type = node_def.get("type", "default")
            node_config = node_def.get("config", {})
            
            # 创建节点执行器
            executor = NodeFactory.create(node_type)
            
            # 执行节点
            result = await executor.execute(node_config, pool.to_dict())
            
            # 结果写入变量池
            for k, v in result.items():
                pool.set(f"{node_name}.{k}", v)
            
            # 条件分支：根据结果决定下一步
            if node_type == "condition":
                branch = result.get("branch", "true")
                # 过滤 edges，只走匹配的分支
                edges = self._filter_edges(edges, node_name, branch)
                order = topological_sort(nodes, edges)
        
        return pool.to_dict()
    
    def _filter_edges(self, edges, from_node, branch):
        """根据条件分支过滤边"""
        filtered = []
        for edge in edges:
            if edge.get("from") == from_node:
                if edge.get("label", "是") == branch or edge.get("label") == "":
                    filtered.append(edge)
            else:
                filtered.append(edge)
        return filtered
```

### ✅ 阶段 2 完成标志

- [ ] 节点基类已实现
- [ ] LLM 节点已实现（真正调用 LLM）
- [ ] 工具节点已实现（真正执行工具）
- [ ] 条件节点已实现（支持分支路由）
- [ ] 代码节点已实现
- [ ] HTTP 节点已实现
- [ ] 迭代节点已实现
- [ ] 节点工厂已实现
- [ ] 变量池已实现
- [ ] 主引擎已重构
- [ ] 单元测试通过

**断点**：完成后可暂停，下次从阶段 3 开始。

---

## 阶段 3：前端编辑器（参考 Coze）

### 3.1 参考 Coze 的 UI 交互

**核心参考**：`coze-studio/frontend/packages/workflow/`

**借鉴要点**：
1. 节点拖拽交互
2. 节点配置面板
3. 调试面板
4. 变量连线

### 3.2 实现步骤

#### Step 1：节点类型注册

```typescript
// web/src/renderer/modules/workflow/components/nodes/index.ts
import { StartNode } from './start-node'
import { EndNode } from './end-node'
import { TaskNode } from './task-node'
import { LLMNode } from './llm-node'
import { ConditionNode } from './condition-node'
import { CodeNode } from './code-node'
import { HTTPNode } from './http-node'
import { IterationNode } from './iteration-node'

export const nodeTypes = {
  start: StartNode,
  end: EndNode,
  task: TaskNode,
  llm: LLMNode,
  condition: ConditionNode,
  code: CodeNode,
  http: HTTPNode,
  iteration: IterationNode,
}
```

#### Step 2：LLM 节点组件

```typescript
// web/src/renderer/modules/workflow/components/nodes/llm-node.tsx
import { memo } from 'react'
import { Handle, Position } from 'reactflow'

export const LLMNode = memo(({ data }) => {
  return (
    <div className="workflow-node llm-node">
      <Handle type="target" position={Position.Top} />
      <div className="node-header">
        <span className="node-icon">🤖</span>
        <span className="node-label">{data.label || 'LLM'}</span>
      </div>
      <div className="node-body">
        <div className="node-preview">
          {data.prompt?.substring(0, 50) || '未配置 Prompt'}...
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
})
```

#### Step 3：节点配置面板

```typescript
// web/src/renderer/modules/workflow/components/node-config-drawer.tsx
import { Drawer, Form, Input, Select, Slider } from 'antd'

export const NodeConfigDrawer = ({ node, onClose, onSave }) => {
  const [form] = Form.useForm()
  
  return (
    <Drawer title="节点配置" onClose={onClose} open={!!node}>
      <Form form={form} initialValues={node?.config} onFinish={onSave}>
        {node?.type === 'llm' && (
          <>
            <Form.Item name="prompt" label="Prompt">
              <Input.TextArea rows={6} />
            </Form.Item>
            <Form.Item name="model" label="模型">
              <Select options={[{value: 'auto', label: '自动'}]} />
            </Form.Item>
            <Form.Item name="temperature" label="温度">
              <Slider min={0} max={1} step={0.1} />
            </Form.Item>
          </>
        )}
        {/* 其他节点类型的配置... */}
      </Form>
    </Drawer>
  )
}
```

### ✅ 阶段 3 完成标志

- [ ] 节点类型已注册
- [ ] LLM 节点组件已实现
- [ ] 条件节点组件已实现
- [ ] 代码节点组件已实现
- [ ] HTTP 节点组件已实现
- [ ] 迭代节点组件已实现
- [ ] 节点配置面板已实现
- [ ] 变量连线已实现

**断点**：完成后可暂停，下次从阶段 4 开始。

---

## 阶段 4：前后端联调

### 4.1 API 对接

```typescript
// web/src/renderer/modules/workflow/services/workflow-api.ts
import { apiClient, extractData } from '@/services/api-client'

export const workflowApi = {
  list: (params) => apiClient.get('/workflows', { params }),
  get: (id) => apiClient.get(`/workflows/${id}`),
  create: (data) => apiClient.post('/workflows', data),
  update: (id, data) => apiClient.put(`/workflows/${id}`, data),
  delete: (id) => apiClient.delete(`/workflows/${id}`),
  execute: (id, input) => apiClient.post(`/workflows/${id}/execute`, input),
  getRuns: (id, params) => apiClient.get(`/workflows/${id}/runs`, { params }),
}
```

### 4.2 WebSocket 实时状态

```typescript
// web/src/renderer/modules/workflow/services/workflow-ws.ts
export const connectWorkflowWS = (runId: string, onEvent: (event) => void) => {
  const ws = new WebSocket(`ws://${location.host}/ws/workflow/${runId}`)
  ws.onmessage = (e) => onEvent(JSON.parse(e.data))
  return ws
}
```

### ✅ 阶段 4 完成标志

- [ ] API 对接完成
- [ ] WebSocket 实时状态完成
- [ ] 前端可以创建/编辑工作流
- [ ] 前端可以执行工作流
- [ ] 前端可以查看运行记录

**断点**：完成后可暂停，下次从阶段 5 开始。

---

## 阶段 5：测试验证

### 5.1 测试用例

```bash
# 创建工作流
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试工作流",
    "description": "简单测试",
    "dag_json": {
      "nodes": {
        "start_1": {"type": "start", "label": "开始", "position": {"x": 100, "y": 200}, "config": {"variables": [{"name": "topic", "type": "string"}]}},
        "llm_1": {"type": "llm", "label": "分析", "position": {"x": 300, "y": 200}, "config": {"prompt": "分析：{{start_1.topic}}", "model": "auto"}},
        "end_1": {"type": "end", "label": "结束", "position": {"x": 500, "y": 200}, "config": {}}
      },
      "edges": [
        {"from": "start_1", "to": "llm_1"},
        {"from": "llm_1", "to": "end_1"}
      ]
    }
  }'

# 执行工作流
curl -X POST http://localhost:8000/api/v1/workflows/1/execute \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI 发展趋势"}'
```

### ✅ 阶段 5 完成标志

- [ ] 创建工作流 API 测试通过
- [ ] 执行工作流 API 测试通过
- [ ] 条件分支测试通过
- [ ] 循环测试通过
- [ ] 前端编辑器测试通过
- [ ] 实时状态推送测试通过

---

## 📊 进度跟踪

| 阶段 | 状态 | 完成时间 | 备注 |
|------|------|---------|------|
| 0. 准备工作 | ⬜ 未开始 | | |
| 1. API 契约 | ⬜ 未开始 | | |
| 2. 后端引擎 | ⬜ 未开始 | | |
| 3. 前端编辑器 | ⬜ 未开始 | | |
| 4. 前后端联调 | ⬜ 未开始 | | |
| 5. 测试验证 | ⬜ 未开始 | | |

---

## 🔧 快速恢复指南

如果中断后需要继续：

1. **查看当前进度**：检查上面的进度跟踪表
2. **确认环境**：确保 MySQL、Redis、后端都在运行
3. **从断点继续**：找到对应阶段的 ✅ 标志，从下一个未完成的开始
4. **验证前序**：每个阶段开始前，先验证上一个阶段的产出
