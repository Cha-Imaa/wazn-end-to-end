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

async function fetchBackendJson(path, errorMessage) {
  const response = await fetch(buildApiUrl(path), {
    method: "GET",
  });

  const payload = await parseJsonResponse(response);

  if (!response.ok) {
    throw new LearningApiError(errorMessage, {
      reason: "http_error",
      status: response.status,
      statusText: response.statusText,
      payload,
    });
  }

  return payload;
}

export async function fetchLearningResultFromBackend(query) {
  const encodedWord = encodeURIComponent(query);

  return fetchBackendJson(
    `/api/analyze?word=${encodedWord}`,
    "Failed to fetch learning result."
  );
}

export async function fetchSentenceFromBackend(query) {
  const encodedWord = encodeURIComponent(query);

  return fetchBackendJson(
    `/api/sentence?word=${encodedWord}`,
    "Failed to fetch the example sentence."
  );
}

export async function fetchInsightsFromBackend(query) {
  const encodedWord = encodeURIComponent(query);

  return fetchBackendJson(
    `/api/insights?word=${encodedWord}`,
    "Failed to fetch insights."
  );
}