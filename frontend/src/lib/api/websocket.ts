import { browser } from '$app/environment';
import type { WebSocketEvent } from '$lib/types';

type EventHandler = (event: WebSocketEvent) => void;
type ConnectionHandler = (connected: boolean) => void;

export class WebSocketManager {
	private ws: WebSocket | null = null;
	private url: string = '';
	private reconnectAttempts = 0;
	private maxReconnectAttempts = 10;
	private reconnectDelay = 1000;
	private eventHandlers: Set<EventHandler> = new Set();
	private connectionHandlers: Set<ConnectionHandler> = new Set();
	private pingInterval: ReturnType<typeof setInterval> | null = null;

	constructor(url?: string) {
		if (url) {
			this.url = url;
		} else if (browser) {
			// If VITE_API_URL is set, use it
			const apiUrl = import.meta.env.VITE_API_URL;
			if (apiUrl) {
				this.url = apiUrl.replace(/^http/, 'ws') + '/ws';
			} else {
				// Auto-detect: use current hostname with backend port
				const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
				this.url = `${wsProtocol}//${window.location.hostname}:8765/ws`;
			}
		}
	}

	connect(): void {
		if (!browser) return;

		if (this.ws?.readyState === WebSocket.OPEN) {
			return;
		}

		try {
			this.ws = new WebSocket(this.url);

			this.ws.onopen = () => {
				console.log('WebSocket connected');
				this.reconnectAttempts = 0;
				this.notifyConnectionHandlers(true);
				this.startPing();
			};

			this.ws.onclose = () => {
				console.log('WebSocket disconnected');
				this.notifyConnectionHandlers(false);
				this.stopPing();
				this.attemptReconnect();
			};

			this.ws.onerror = (error) => {
				console.error('WebSocket error:', error);
			};

			this.ws.onmessage = (event) => {
				this.handleMessage(event);
			};
		} catch (error) {
			console.error('Failed to create WebSocket:', error);
			this.attemptReconnect();
		}
	}

	disconnect(): void {
		this.stopPing();
		this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
		if (this.ws) {
			this.ws.close();
			this.ws = null;
		}
	}

	onEvent(handler: EventHandler): () => void {
		this.eventHandlers.add(handler);
		return () => {
			this.eventHandlers.delete(handler);
		};
	}

	onConnection(handler: ConnectionHandler): () => void {
		this.connectionHandlers.add(handler);
		return () => {
			this.connectionHandlers.delete(handler);
		};
	}

	requestState(): void {
		if (browser && this.ws?.readyState === WebSocket.OPEN) {
			this.ws.send('get_state');
		}
	}

	get isConnected(): boolean {
		return browser && this.ws?.readyState === WebSocket.OPEN;
	}

	private handleMessage(event: MessageEvent): void {
		try {
			// Handle pong response
			if (event.data === 'pong') {
				return;
			}

			const data = JSON.parse(event.data) as WebSocketEvent;
			this.eventHandlers.forEach((handler) => {
				try {
					handler(data);
				} catch (error) {
					console.error('Error in event handler:', error);
				}
			});
		} catch (error) {
			console.error('Failed to parse WebSocket message:', error);
		}
	}

	private notifyConnectionHandlers(connected: boolean): void {
		this.connectionHandlers.forEach((handler) => {
			try {
				handler(connected);
			} catch (error) {
				console.error('Error in connection handler:', error);
			}
		});
	}

	private attemptReconnect(): void {
		if (this.reconnectAttempts >= this.maxReconnectAttempts) {
			console.log('Max reconnection attempts reached');
			return;
		}

		this.reconnectAttempts++;
		const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
		console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

		setTimeout(() => {
			this.connect();
		}, delay);
	}

	private startPing(): void {
		this.stopPing();
		this.pingInterval = setInterval(() => {
			if (this.ws?.readyState === WebSocket.OPEN) {
				this.ws.send('ping');
			}
		}, 30000); // Ping every 30 seconds
	}

	private stopPing(): void {
		if (this.pingInterval) {
			clearInterval(this.pingInterval);
			this.pingInterval = null;
		}
	}
}

// Lazy singleton instance (only created in browser)
let _wsManager: WebSocketManager | null = null;

export function getWsManager(): WebSocketManager {
	if (!_wsManager) {
		_wsManager = new WebSocketManager();
	}
	return _wsManager;
}

// For backwards compatibility
export const wsManager = {
	connect: () => getWsManager().connect(),
	disconnect: () => getWsManager().disconnect(),
	onEvent: (handler: EventHandler) => getWsManager().onEvent(handler),
	onConnection: (handler: ConnectionHandler) => getWsManager().onConnection(handler),
	requestState: () => getWsManager().requestState(),
	get isConnected() {
		return _wsManager?.isConnected ?? false;
	}
};
