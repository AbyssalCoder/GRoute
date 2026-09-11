const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';
export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(options?.headers ?? {}) } });
  } catch {
    throw new Error('Live maritime data is temporarily unavailable. Please try again.');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(response.status === 503 ? 'No live vessel match is available right now. Please choose another vessel.' : 'Live maritime data is temporarily unavailable. Please try again.');
  }
  return response.json();
}
export { API };
