# 前端 API Client 约定

前端建议把所有后端请求集中在一个 API 层，避免组件里直接写 `fetch`。

建议目录：

```text
frontend/src/api/
  http.ts
  ingest.ts
  knowledge.ts
  search.ts
  chat.ts
  generate.ts
  tasks.ts
  harness.ts
```

基础地址：

```ts
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";
```

## HTTP 封装

```ts
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }

  return res.json() as Promise<T>;
}
```

文件上传不要手动设置 `Content-Type`，让浏览器自动设置 multipart boundary。

## 会话状态建议

可以用 Pinia 或 composable 维护问答状态：

```ts
type ChatState = {
  activeSessionId: string | null;
  messages: Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    citations?: Citation[];
    pending?: boolean;
  }>;
};
```

发送问题的推荐流程：

```ts
async function sendKnowledgeQuestion(message: string) {
  if (!activeSessionId) {
    const session = await createChatSession({ title: "New chat", scope: {} });
    activeSessionId = session.id;
  }

  messages.push({ id: crypto.randomUUID(), role: "user", content: message });
  messages.push({ id: "pending", role: "assistant", content: "", pending: true });

  await sendChatMessageStream(activeSessionId, {
    message,
    retrieval_mode: "hybrid",
    reasoning_mode: "normal",
    top_k: 8,
  }, {
    onStatus(status) {
      updatePendingMessage({ status: status.message });
    },
    onDelta(delta) {
      appendPendingMessage(delta);
    },
    onFinal(answer) {
      replacePendingMessage({
        id: answer.message_id,
        role: "assistant",
        content: answer.answer,
        citations: answer.citations,
        trace: answer.trace,
      });
    },
  });
}
```

## 推荐 API 方法

### 信息输入

```ts
export function ingestContent(payload: IngestRequest) {
  return apiFetch<IngestResponse>("/ingest", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
```

```ts
export async function ingestFile(file: File, contentType?: string, source?: string) {
  const form = new FormData();
  form.append("file", file);
  if (contentType) form.append("content_type", contentType);
  if (source) form.append("source", source);

  const res = await fetch(`${API_BASE}/ingest/files`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<IngestResponse>;
}
```

### 搜索

```ts
export function searchKnowledge(payload: SearchRequest) {
  return apiFetch<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
```

### 问答

```ts
export function createChatSession(payload: ChatSessionCreate) {
  return apiFetch<ChatSessionRead>("/chat/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function sendChatMessage(sessionId: string, payload: ChatMessageRequest) {
  return apiFetch<ChatMessageResponse>(`/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function sendChatMessageStream(
  sessionId: string,
  payload: ChatMessageRequest,
  handlers: {
    onStatus?: (status: ChatStreamStatus) => void;
    onDelta?: (delta: string) => void;
    onFinal?: (response: ChatMessageResponse) => void;
  },
) {
  // Use fetch + ReadableStream for POST SSE. EventSource cannot send JSON body.
  // Parse event: status / delta / final / error blocks from text/event-stream.
}
```

交互式问答优先使用 `sendChatMessageStream`；`sendChatMessage` 保留给脚本、测试和不需要流式体验的调用。

### 内容生成

```ts
export function previewGeneration(payload: GenerationRequest) {
  return apiFetch<GenerationPreviewResponse>("/generate/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createGenerationTask(payload: GenerationRequest) {
  return apiFetch<GenerationTaskResponse>("/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
```

### 任务

```ts
export function getTask(taskId: string) {
  return apiFetch<TaskRead>(`/tasks/${taskId}`);
}
```

### Nanobot Harness

```ts
export function createHarnessJob(payload: HarnessJobRequest) {
  return apiFetch<HarnessJobResponse>("/harness/jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
```

## 任务轮询约定

异步任务包括：

- 文档入库。
- 图片 OCR 后的多模态理解。
- PPTX 生成。
- 生图。
- 图示生成。
- nanobot 网络检索。
- nanobot 跨文档推理。

推荐轮询：

```ts
async function pollTask(taskId: string, onUpdate: (task: TaskRead) => void) {
  while (true) {
    const task = await getTask(taskId);
    onUpdate(task);
    if (["succeeded", "failed", "cancelled"].includes(task.status)) return task;
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}
```

## 类型来源

后端 OpenAPI 是类型的唯一事实来源：

```text
http://127.0.0.1:8000/api/openapi.json
```

后续可以使用 `openapi-typescript` 自动生成前端类型。
