# ROS SDK 客户端

基于 OpenAPI 3.1 规范生成的 ROS 系统客户端 SDK。

## 快速开始

### 生成客户端

```bash
# Python SDK
pip install openapi-python-client
openapi-python-client generate --path ../docs/openapi.yaml --output ros-client-py

# TypeScript SDK
npm install -g openapi-typescript-codegen
openapi --input ../docs/openapi.yaml --output ros-client-ts --client axios
```

### Python 使用示例

```python
from ros_client import Client
from ros_client.api.auth import login

client = Client(base_url="http://139.196.15.52")
token = login.sync(client=client, json={"username": "admin", "password": "***"})
client = Client(base_url="http://139.196.15.52", token=token)
```

### TypeScript 使用示例

```typescript
import { RosClient } from './ros-client-ts'
const client = new RosClient({ BASE: 'http://139.196.15.52' })
const plans = await client.productPlans.listPlans()
```

## API 文档

- Swagger UI: `http://139.196.15.52/api/v2/docs`
- ReDoc: `http://139.196.15.52/api/v2/redoc`
- OpenAPI JSON: `http://139.196.15.52/api/v2/openapi.json`
