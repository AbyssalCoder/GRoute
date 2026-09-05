const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';
export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(options?.headers ?? {}) } });
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  return response.json();
}
export { API };
