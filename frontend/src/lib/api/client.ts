import { browser } from '$app/environment';

// In development with Vite proxy, use relative path
// In production or if proxy fails, could use direct URL
const API_BASE = '/api';

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
	const url = `${API_BASE}${endpoint}`;

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
