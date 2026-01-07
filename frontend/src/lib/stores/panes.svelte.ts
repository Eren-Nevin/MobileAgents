import { browser } from '$app/environment';
import { fetchPanes, fetchPaneOutput, wsManager } from '$lib/api';
import type { InputRequest, PaneInfo, PaneOutput, PaneStatus, WebSocketEvent } from '$lib/types';

// Per-pane store interface
interface PaneStore {
	info: PaneInfo;
	lines: string[];
	lineOffset: number; // For stable line keys
	inputRequest: InputRequest | undefined;
	cursorX: number;
	cursorY: number;
}

// Reactive state using Svelte 5 runes
let paneStores = $state<Map<string, PaneStore>>(new Map());
let selectedPaneId = $state<string | null>(null);
let isConnected = $state(false);
let isLoading = $state(false);
let error = $state<string | null>(null);

// Version counter to signal when paneStores Map itself changes (add/remove)
let storeVersion = $state(0);
// Version counter for data updates (triggers re-render of watching components)
let dataVersion = $state(0);

// ============================================================================
// Getters - Direct access to state
// ============================================================================

export function getPaneStore(paneId: string): PaneStore | undefined {
	// Only track storeVersion (add/remove), not dataVersion
	// Fine-grained reactivity on store properties handles data updates
	void storeVersion;
	return paneStores.get(paneId);
}

export function getPaneIds(): string[] {
	void storeVersion;
	return Array.from(paneStores.keys());
}

export function getPanes(): PaneInfo[] {
	void storeVersion;
	return Array.from(paneStores.values()).map((s) => s.info);
}

export function getPanesBySession(): Map<string, PaneInfo[]> {
	void storeVersion;
	const grouped = new Map<string, PaneInfo[]>();
	for (const store of paneStores.values()) {
		const key = store.info.session_name;
		const list = grouped.get(key) || [];
		list.push(store.info);
		grouped.set(key, list);
	}
	return grouped;
}

export function getPane(paneId: string): PaneInfo | undefined {
	void storeVersion; // Track Map changes for reactivity
	return paneStores.get(paneId)?.info;
}

export function getPaneOutput(paneId: string): string[] {
	void storeVersion; // Track Map changes for reactivity
	void dataVersion; // Track data updates for reactivity
	return paneStores.get(paneId)?.lines ?? [];
}

export function getPaneLineOffset(paneId: string): number {
	void storeVersion; // Track Map changes for reactivity
	void dataVersion; // Track data updates for reactivity
	return paneStores.get(paneId)?.lineOffset ?? 0;
}

export function getInputRequest(paneId: string): InputRequest | undefined {
	void storeVersion; // Track Map changes for reactivity
	void dataVersion; // Track data updates for reactivity
	return paneStores.get(paneId)?.inputRequest;
}

export function getCursorPosition(paneId: string): { x: number; y: number } {
	void storeVersion; // Track Map changes for reactivity
	void dataVersion; // Track data updates for reactivity
	const store = paneStores.get(paneId);
	return { x: store?.cursorX ?? 0, y: store?.cursorY ?? 0 };
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

// ============================================================================
// Actions
// ============================================================================

export function selectPane(paneId: string | null): void {
	selectedPaneId = paneId;
}

export function setError(msg: string | null): void {
	error = msg;
}

export function clearError(): void {
	error = null;
}

// ============================================================================
// Internal: Comparison functions
// ============================================================================

function paneEquals(a: PaneInfo, b: PaneInfo): boolean {
	return (
		a.pane_id === b.pane_id &&
		a.session_name === b.session_name &&
		a.window_name === b.window_name &&
		a.status === b.status &&
		a.title === b.title
	);
}

function linesEqual(a: string[], b: string[]): boolean {
	if (a.length !== b.length) return false;
	// Compare from end (most likely to differ for streaming output)
	for (let i = a.length - 1; i >= 0; i--) {
		if (a[i] !== b[i]) return false;
	}
	return true;
}

function inputRequestEquals(
	a: InputRequest | undefined,
	b: InputRequest | undefined
): boolean {
	if (a === b) return true;
	if (!a || !b) return false;
	return a.type === b.type && a.prompt === b.prompt;
}

// ============================================================================
// Internal: Store mutations
// ============================================================================

function createPaneStore(info: PaneInfo): PaneStore {
	return {
		info,
		lines: [],
		lineOffset: 0,
		inputRequest: undefined,
		cursorX: 0,
		cursorY: 0
	};
}

function syncPanes(newPanes: PaneInfo[]): void {
	const newIds = new Set(newPanes.map((p) => p.pane_id));
	let changed = false;

	// Remove panes that no longer exist
	for (const id of paneStores.keys()) {
		if (!newIds.has(id)) {
			paneStores.delete(id);
			changed = true;
		}
	}

	// Add/update panes
	for (const pane of newPanes) {
		const existing = paneStores.get(pane.pane_id);
		if (!existing) {
			paneStores.set(pane.pane_id, createPaneStore(pane));
			changed = true;
		} else if (!paneEquals(existing.info, pane)) {
			// Mutate in place - only the info changes
			existing.info = pane;
		}
	}

	// Increment version only if Map structure changed
	if (changed) {
		storeVersion++;
	}

	// Clear selected pane if it was removed
	if (selectedPaneId && !paneStores.has(selectedPaneId)) {
		selectedPaneId = null;
	}
}

function updatePaneInPlace(
	paneId: string,
	status: PaneStatus,
	lines: string[],
	inputRequest: InputRequest | undefined,
	cursorX: number = 0,
	cursorY: number = 0
): void {
	const store = paneStores.get(paneId);
	if (!store) return;

	let changed = false;

	// Only update status if changed
	if (store.info.status !== status) {
		store.info = { ...store.info, status };
		changed = true;
	}

	// Update cursor position
	if (store.cursorX !== cursorX || store.cursorY !== cursorY) {
		store.cursorX = cursorX;
		store.cursorY = cursorY;
		changed = true;
	}

	// Only update lines if changed
	if (!linesEqual(store.lines, lines)) {
		// Check if this is an append operation
		const isAppend =
			lines.length > store.lines.length &&
			linesEqual(store.lines, lines.slice(0, store.lines.length));

		if (!isAppend) {
			// Content replaced, reset lineOffset
			store.lineOffset = 0;
		}
		// Replace array to trigger Svelte reactivity
		store.lines = lines;
		changed = true;
	}

	// Only update input request if changed
	if (!inputRequestEquals(store.inputRequest, inputRequest)) {
		store.inputRequest = inputRequest;
		changed = true;
	}

	// Signal data change for reactivity
	if (changed) {
		dataVersion++;
	}
}

function addPane(pane: PaneInfo): void {
	if (!paneStores.has(pane.pane_id)) {
		paneStores.set(pane.pane_id, createPaneStore(pane));
		storeVersion++;
	} else {
		// Update existing
		const store = paneStores.get(pane.pane_id)!;
		if (!paneEquals(store.info, pane)) {
			store.info = pane;
		}
	}
}

function removePane(paneId: string): void {
	if (paneStores.has(paneId)) {
		paneStores.delete(paneId);
		storeVersion++;

		if (selectedPaneId === paneId) {
			selectedPaneId = null;
		}
	}
}

// ============================================================================
// WebSocket event handler
// ============================================================================

function handleWebSocketEvent(event: WebSocketEvent): void {
	switch (event.event) {
		case 'initial_state':
		case 'state':
			syncPanes(event.panes);
			break;

		case 'pane_discovered':
			addPane(event.pane);
			break;

		case 'pane_removed':
			removePane(event.pane_id);
			break;

		case 'pane_update':
			updatePaneInPlace(
				event.pane_id,
				event.status,
				event.lines,
				event.input_request,
				event.cursor_x,
				event.cursor_y
			);
			break;
	}
}

// ============================================================================
// Initialize store and WebSocket connection
// ============================================================================

export function initializeStore(): () => void {
	if (!browser) {
		return () => {};
	}

	const unsubscribeEvent = wsManager.onEvent(handleWebSocketEvent);
	const unsubscribeConnection = wsManager.onConnection((connected) => {
		isConnected = connected;
	});

	wsManager.connect();

	return () => {
		unsubscribeEvent();
		unsubscribeConnection();
		wsManager.disconnect();
	};
}

// ============================================================================
// API calls
// ============================================================================

export async function loadPanes(): Promise<void> {
	if (!browser) return;

	isLoading = true;
	error = null;

	try {
		const paneList = await fetchPanes();
		syncPanes(paneList);
	} catch (e) {
		error = e instanceof Error ? e.message : 'Failed to load panes';
		console.error('Failed to load panes:', e);
	} finally {
		isLoading = false;
	}
}

export async function loadPaneOutput(
	paneId: string,
	refresh = false
): Promise<PaneOutput | null> {
	if (!browser) return null;

	try {
		const output = await fetchPaneOutput(paneId, { refresh });
		const store = paneStores.get(paneId);
		if (store) {
			let changed = false;
			if (!linesEqual(store.lines, output.lines)) {
				store.lines = output.lines;
				store.lineOffset = 0; // Reset on full refresh
				changed = true;
			}
			if (!inputRequestEquals(store.inputRequest, output.input_request)) {
				store.inputRequest = output.input_request;
				changed = true;
			}
			// Update cursor position
			if (store.cursorX !== output.cursor_x || store.cursorY !== output.cursor_y) {
				store.cursorX = output.cursor_x;
				store.cursorY = output.cursor_y;
				changed = true;
			}
			if (changed) {
				dataVersion++;
			}
		}
		return output;
	} catch (e) {
		console.error(`Failed to load output for pane ${paneId}:`, e);
		return null;
	}
}

// ============================================================================
// Utility getters
// ============================================================================

export function countByStatus(status: PaneStatus): number {
	let count = 0;
	for (const store of paneStores.values()) {
		if (store.info.status === status) count++;
	}
	return count;
}

export function getPanesWaitingInput(): PaneInfo[] {
	return Array.from(paneStores.values())
		.filter((s) => s.info.status === 'waiting_input')
		.map((s) => s.info);
}
