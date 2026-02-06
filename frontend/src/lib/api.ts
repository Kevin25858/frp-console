async function getCsrfToken(): Promise<string> {
  // 每次请求都重新获取 CSRF token，避免 session 过期导致的问题
  const response = await fetch('/api/csrf-token', {
    credentials: 'include'
  });
  if (!response.ok) {
    throw new Error('Failed to fetch CSRF token');
  }

  const data = await response.json();
  const token = data.csrf_token;
  if (!token) {
    throw new Error('CSRF token not found in response');
  }
  return token;
}

export class ApiError extends Error {
  status: number;
  body: any;

  constructor(status: number, body: any, message?: string) {
    super(message || `Request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}


export async function apiFetch(url: string, options: RequestInit = {}): Promise<any> {
  const method = options.method?.toUpperCase() || 'GET';

  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    options.headers = {
      ...options.headers,
      'X-CSRF-Token': await getCsrfToken(),
    };
  }

  options.headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  options.credentials = 'include';

  const response = await fetch(`/api${url}`, options);

  if (!response.ok) {
    let errorBody;
    try {
      errorBody = await response.json();
    } catch (_e) {
      errorBody = { message: 'An unknown error occurred' };
    }
    throw new ApiError(response.status, errorBody, errorBody.error || 'API request failed');
  }

  const contentType = response.headers.get('Content-Type') || response.headers.get('content-type');
  if (contentType?.includes('application/json')) {
    return response.json();
  }

  return response.text();
}
