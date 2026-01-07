export type PaneStatus = 'running' | 'waiting_input' | 'idle' | 'exited';

export type InputType = 'text' | 'choice' | 'confirm';

export interface InputRequest {
	input_type: InputType;
	prompt?: string;
	message?: string;
	options?: string[];
}

export interface PaneInfo {
	pane_id: string;
	session_name: string;
	window_name: string;
	window_index: number;
	pane_index: number;
	title: string;
	status: PaneStatus;
	last_updated: string;
}

export interface PaneOutput {
	pane_id: string;
	lines: string[];
	line_count: number;
	input_request?: InputRequest;
	cursor_x: number;
	cursor_y: number;
}

export interface InputSubmission {
	input_type: InputType;
	value: string;
}
