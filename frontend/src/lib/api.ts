const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getSignals() {
  return fetchAPI("/api/signals");
}

export async function generateTheses(query?: string) {
  return fetchAPI("/api/theses/generate", {
    method: "POST",
    body: JSON.stringify({ query: query || null }),
  });
}

export async function getTheses() {
  return fetchAPI("/api/theses");
}

export async function getGraph() {
  return fetchAPI("/api/graph");
}

export async function getGraphTrends() {
  return fetchAPI("/api/graph/trends");
}

export async function getFilings() {
  return fetchAPI("/api/filings");
}

export async function getScorecard() {
  return fetchAPI("/api/scorecard");
}

export async function getPredictions() {
  return fetchAPI("/api/predictions");
}

export async function sendChatMessage(message: string) {
  return fetchAPI("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export async function getChatHistory() {
  return fetchAPI("/api/chat/history");
}

export async function getProfile() {
  return fetchAPI("/api/profile");
}

export async function updateProfile(data: Record<string, unknown>) {
  return fetchAPI("/api/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
