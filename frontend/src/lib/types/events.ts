import type { InputRequest, PaneInfo, PaneStatus } from './pane';

export interface PaneUpdateEvent {
	event: 'pane_update';
	pane_id: string;
	status: PaneStatus;
	lines: string[];
	input_request?: InputRequest;
	cursor_x: number;
	cursor_y: number;
}

export interface PaneDiscoveryEvent {
	event: 'pane_discovered';
	pane: PaneInfo;
}

export interface PaneRemovedEvent {
	event: 'pane_removed';
	pane_id: string;
}

export interface InitialStateEvent {
	event: 'initial_state';
	panes: PaneInfo[];
}

export interface StateEvent {
	event: 'state';
	panes: PaneInfo[];
}

export type WebSocketEvent =
	| PaneUpdateEvent
	| PaneDiscoveryEvent
	| PaneRemovedEvent
	| InitialStateEvent
	| StateEvent;
