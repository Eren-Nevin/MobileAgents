import { browser } from '$app/environment';
import { fetchPanes, fetchPaneOutput, wsManager } from '$lib/api';
import type { InputRequest, PaneInfo, PaneOutput, PaneStatus, WebSocketEvent } from '$lib/types';

// Reactive state using Svelte 5 runes
let panes = $state<Map<string, PaneInfo>>(new Map());
let outputs = $state<Map<string, string[]>>(new Map());
let inputRequests = $state<Map<string, InputRequest | undefined>>(new Map());
let selectedPaneId = $state<string | null>(null);
let isConnected = $state(false);
let isLoading = $state(false);
let error = $state<string | null>(null);

// Derived state
export function getPanes(): PaneInfo[] {
	return Array.from(panes.values());
}

export function getPanesBySession(): Map<string, PaneInfo[]> {
	const grouped = new Map<string, PaneInfo[]>();
	for (const pane of panes.values()) {
		const key = pane.session_name;
		const list = grouped.get(key) || [];
		list.push(pane);
		grouped.set(key, list);
	}
	return grouped;
}

export function getPane(paneId: string): PaneInfo | undefined {
	return panes.get(paneId);
}

export function getPaneOutput(paneId: string): string[] {
	return outputs.get(paneId) || [];
}

export function getInputRequest(paneId: string): InputRequest | undefined {
	return inputRequests.get(paneId);
}

export function getSelectedPaneId(): string | null {
	return selectedPaneId;
}

export function getIsConnected(): boolean {
	return isConnected;
}

export function getIsLoading(): boolean {
	return isLoading;
}

export function getError(): string | null {
	return error;
}

// Actions
export function selectPane(paneId: string | null): void {
	selectedPaneId = paneId;
}

export function setError(msg: string | null): void {
	error = msg;
}

export function clearError(): void {
	error = null;
}

function updatePane(pane: PaneInfo): void {
	panes.set(pane.pane_id, pane);
	// Trigger reactivity by reassigning
	panes = new Map(panes);
}

function removePane(paneId: string): void {
	panes.delete(paneId);
	outputs.delete(paneId);
	inputRequests.delete(paneId);
	panes = new Map(panes);
	outputs = new Map(outputs);
	inputRequests = new Map(inputRequests);

	if (selectedPaneId === paneId) {
		selectedPaneId = null;
	}
}

function updateOutput(paneId: string, lines: string[]): void {
	outputs.set(paneId, lines);
	outputs = new Map(outputs);
}

function updateInputRequest(paneId: string, request: InputRequest | undefined): void {
	inputRequests.set(paneId, request);
	inputRequests = new Map(inputRequests);
}

function setPanes(paneList: PaneInfo[]): void {
	panes = new Map(paneList.map((p) => [p.pane_id, p]));
}

// WebSocket event handler
function handleWebSocketEvent(event: WebSocketEvent): void {
	switch (event.event) {
		case 'initial_state':
		case 'state':
			setPanes(event.panes);
			break;

		case 'pane_discovered':
			updatePane(event.pane);
			break;

		case 'pane_removed':
			removePane(event.pane_id);
			break;

		case 'pane_update': {
			const existingPane = panes.get(event.pane_id);
			if (existingPane) {
				updatePane({
					...existingPane,
					status: event.status,
					last_updated: new Date().toISOString()
				});
			}
			updateOutput(event.pane_id, event.lines);
			updateInputRequest(event.pane_id, event.input_request);
			break;
		}
	}
}

// Initialize store and WebSocket connection
export function initializeStore(): () => void {
	if (!browser) {
		return () => {}; // No-op cleanup for SSR
	}

	// Set up WebSocket handlers
	const unsubscribeEvent = wsManager.onEvent(handleWebSocketEvent);
	const unsubscribeConnection = wsManager.onConnection((connected) => {
		isConnected = connected;
	});

	// Connect WebSocket
	wsManager.connect();

	// Return cleanup function
	return () => {
		unsubscribeEvent();
		unsubscribeConnection();
		wsManager.disconnect();
	};
}

// Fetch panes from API (fallback/initial load)
export async function loadPanes(): Promise<void> {
	if (!browser) return;

	isLoading = true;
	error = null;

	try {
		const paneList = await fetchPanes();
		setPanes(paneList);
	} catch (e) {
		error = e instanceof Error ? e.message : 'Failed to load panes';
		console.error('Failed to load panes:', e);
	} finally {
		isLoading = false;
	}
}

// Fetch output for a specific pane
export async function loadPaneOutput(paneId: string, refresh = false): Promise<PaneOutput | null> {
	if (!browser) return null;

	try {
		const output = await fetchPaneOutput(paneId, { refresh });
		updateOutput(paneId, output.lines);
		if (output.input_request) {
			updateInputRequest(paneId, output.input_request);
		}
		return output;
	} catch (e) {
		console.error(`Failed to load output for pane ${paneId}:`, e);
		return null;
	}
}

// Count panes by status
export function countByStatus(status: PaneStatus): number {
	let count = 0;
	for (const pane of panes.values()) {
		if (pane.status === status) count++;
	}
	return count;
}

// Get panes waiting for input
export function getPanesWaitingInput(): PaneInfo[] {
	return Array.from(panes.values()).filter((p) => p.status === 'waiting_input');
}
