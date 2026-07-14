const API_BASE_URL =
  import.meta.env.VITE_WAZN_API_BASE_URL || "http://127.0.0.1:8000";

export class LearningApiError extends Error {
  constructor(message, details = {}) {
    super(message);
    this.name = "LearningApiError";
    this.details = details;
  }
}

function buildApiUrl(path) {
  if (!API_BASE_URL) {
    throw new LearningApiError("WAZN API base URL is not configured.", {
      reason: "missing_api_base_url",
    });
  }

  return `${API_BASE_URL.replace(/\/$/, "")}${path}`;
}

async function parseJsonResponse(response) {
  try {
    return await response.json();
  } catch {
    throw new LearningApiError("Backend returned invalid JSON.", {
      reason: "invalid_json",
      status: response.status,
    });
  }
}

export async function fetchLearningResultFromBackend(query) {
  const encodedWord = encodeURIComponent(query);

  const response = await fetch(buildApiUrl(`/api/analyze?word=${encodedWord}`), {
    method: "GET",
  });

  const payload = await parseJsonResponse(response);

  if (!response.ok) {
    throw new LearningApiError("Failed to fetch learning result.", {
      reason: "http_error",
      status: response.status,
      statusText: response.statusText,
      payload,
    });
  }

  return payload;
}