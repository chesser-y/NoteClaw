# Frontend API Client Contract

The frontend should centralize backend calls in one API layer, for example:

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

Base URL:

```ts
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";
```

## HTTP Wrapper

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

For file upload, do not set `Content-Type`; let the browser set multipart boundary.

## Suggested Frontend Session Store

Use Pinia or composables to keep:

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

Chat send flow:

```ts
async function sendKnowledgeQuestion(message: string) {
  if (!activeSessionId) {
    const session = await createChatSession({ title: "New chat", scope: {} });
    activeSessionId = session.id;
  }

  messages.push({ id: crypto.randomUUID(), role: "user", content: message });
  messages.push({ id: "pending", role: "assistant", content: "", pending: true });

  const answer = await sendChatMessage(activeSessionId, {
    message,
    retrieval_mode: "hybrid",
    use_nanobot_reasoning: false,
    top_k: 8,
  });

  replacePendingMessage({
    id: answer.message_id,
    role: "assistant",
    content: answer.answer,
    citations: answer.citations,
  });
}
```

## API Functions

```ts
export function ingestContent(payload: IngestRequest) {
  return apiFetch<IngestResponse>("/ingest", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

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

export function searchKnowledge(payload: SearchRequest) {
  return apiFetch<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

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

export function getTask(taskId: string) {
  return apiFetch<TaskRead>(`/tasks/${taskId}`);
}

export function createHarnessJob(payload: HarnessJobRequest) {
  return apiFetch<HarnessJobResponse>("/harness/jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
```

## Polling Convention

For async ingestion, PPTX generation, image generation, vision enrichment, and nanobot jobs:

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

## Type Source

The canonical schema source is backend OpenAPI:

```text
http://127.0.0.1:8000/api/openapi.json
```

The frontend can later generate TypeScript types from this file with `openapi-typescript`.
