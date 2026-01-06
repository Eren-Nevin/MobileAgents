import { browser } from '$app/environment';

// Lazily evaluated API base URL (computed on first use in browser)
let _apiBase: string | null = null;

function getApiBase(): string {
	// Return cached value if available
	if (_apiBase) return _apiBase;

	// SSR fallback
	if (!browser) return '/api';

	// If VITE_API_URL is set, use it (for custom configurations)
	if (import.meta.env.VITE_API_URL) {
		_apiBase = import.meta.env.VITE_API_URL + '/api';
	} else {
		// Auto-detect: use current hostname with backend port
		const { protocol, hostname } = window.location;
		_apiBase = `${protocol}//${hostname}:8765/api`;
	}

	return _apiBase;
}

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}

export async function apiRequest<T>(
	endpoint: string,
	options: RequestInit = {}
): Promise<T> {
	const url = `${getApiBase()}${endpoint}`;

	const response = await fetch(url, {
		...options,
		headers: {
			'Content-Type': 'application/json',
			...options.headers
		}
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: response.statusText }));
		throw new ApiError(response.status, error.detail || 'Request failed');
	}

	return response.json();
}

export async function get<T>(endpoint: string): Promise<T> {
	return apiRequest<T>(endpoint, { method: 'GET' });
}

export async function post<T>(endpoint: string, data: unknown): Promise<T> {
	return apiRequest<T>(endpoint, {
		method: 'POST',
		body: JSON.stringify(data)
	});
}
