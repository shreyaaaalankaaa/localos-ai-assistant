const API = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export type Mode = 'fast' | 'normal' | 'reasoning' | 'coding';
export type Section = 'home' | 'chat' | 'reasoning' | 'coding' | 'apps' | 'files' | 'settings';
export type Message = { role: 'user' | 'assistant'; content: string; model?: string };
export type LiveStatus = {
  backend_online: boolean;
  ollama_online: boolean;
  models_ready: boolean;
  model_count: number;
  memory_active: boolean;
  system_nominal: boolean;
  platform: string;
};
export type Metrics = {
  cpu: number; ram: number; gpu: number | null;
  ram_used_gb: number; ram_total_gb: number;
  disk: number; uptime_seconds: number; platform: string; hostname: string;
};
export type Models = { online: boolean; installed: string[]; defaults: Record<Mode, string> };
export type FileEntry = { name: string; type: 'folder' | 'file'; path: string; size_bytes?: number; extension?: string };
export type FolderResponse = { folder: string; folders: FileEntry[]; files: FileEntry[]; status: string };
export type ToolResult = { status: string; message?: string; [key: string]: unknown };
export type Profile = { preferred_name?: string; tone?: string; style?: string; [key: string]: unknown };

declare global {
  interface Window { jarvis?: { token?: string } }
}

// Electron's preload provides the token; in browser dev mode the Vite dev server
// puts it in a <meta> tag. The backend rejects any request without it.
export function sessionToken(): string {
  return window.jarvis?.token
    || document.querySelector<HTMLMetaElement>('meta[name="jarvis-token"]')?.content
    || '';
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), path === '/chat' ? 100000 : 7500);
  try {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', 'X-Jarvis-Token': sessionToken(), ...(options.headers || {}) },
      signal: options.signal || controller.signal,
    });
    if (!response.ok) {
      let text = response.status === 401
        ? 'The backend rejected this session. Start the backend, then reload JARVIS.'
        : `Request failed (${response.status})`;
      try {
        const error = await response.json();
        text = error.detail || error.message || text;
      } catch { /* keep HTTP error */ }
      throw new Error(text);
    }
    return (await response.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export const json = (method: 'POST' | 'PATCH' | 'DELETE', body?: unknown): RequestInit => ({
  method,
  ...(body === undefined ? {} : { body: JSON.stringify(body) }),
});
