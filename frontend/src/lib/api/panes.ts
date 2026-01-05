import { get, post } from './client';
import type { InputSubmission, PaneInfo, PaneOutput } from '$lib/types';

export async function fetchPanes(): Promise<PaneInfo[]> {
	return get<PaneInfo[]>('/panes');
}

export async function fetchPane(paneId: string): Promise<PaneInfo> {
	return get<PaneInfo>(`/panes/${encodeURIComponent(paneId)}`);
}

export async function fetchPaneOutput(
	paneId: string,
	options?: { lines?: number; refresh?: boolean }
): Promise<PaneOutput> {
	const params = new URLSearchParams();
	if (options?.lines) params.set('lines', options.lines.toString());
	if (options?.refresh) params.set('refresh', 'true');

	const query = params.toString();
	const endpoint = `/panes/${encodeURIComponent(paneId)}/output${query ? `?${query}` : ''}`;
	return get<PaneOutput>(endpoint);
}

export async function sendInput(
	paneId: string,
	submission: InputSubmission
): Promise<{ status: string; pane_id: string }> {
	return post(`/panes/${encodeURIComponent(paneId)}/input`, submission);
}

export async function sendKeys(
	paneId: string,
	keys: string,
	enter: boolean = true
): Promise<{ status: string; pane_id: string }> {
	return post(`/panes/${encodeURIComponent(paneId)}/keys`, { keys, enter });
}
