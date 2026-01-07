<script lang="ts">
	import type { PaneInfo } from '$lib/types';
	import { getPaneOutput, getPaneLineOffset, getInputRequest, loadPaneOutput } from '$lib/stores/panes.svelte';
	import { sendKeys, sendSpecialKey } from '$lib/api';
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import StatusBadge from './StatusBadge.svelte';
	import PaneOutput from './PaneOutput.svelte';
	import InputArea from './InputArea.svelte';

	interface Props {
		pane: PaneInfo;
	}

	let { pane }: Props = $props();

	// Use getter functions that track dataVersion for reactivity
	const output = $derived(getPaneOutput(pane.pane_id));
	const lineOffset = $derived(getPaneLineOffset(pane.pane_id));
	const inputRequest = $derived(getInputRequest(pane.pane_id));
	const hasInput = $derived(pane.status === 'waiting_input' && inputRequest);

	let hiddenInput: HTMLInputElement;
	let keyboardBarRef: HTMLDivElement;
	let keyboardOpen = $state(false);

	// Modifier key states (toggle buttons)
	let ctrlActive = $state(false);
	let altActive = $state(false);

	// Buffered key sending - collect keystrokes and send together
	let keyBuffer: string = '';
	let specialKeyQueue: string[] = [];
	let bufferTimeout: ReturnType<typeof setTimeout> | null = null;
	let isSending = false;
	const BUFFER_DELAY_MS = 50; // Collect keys for 50ms before sending

	function flushBuffer() {
		if (bufferTimeout) {
			clearTimeout(bufferTimeout);
			bufferTimeout = null;
		}

		if (isSending) {
			// Re-schedule if currently sending
			bufferTimeout = setTimeout(flushBuffer, BUFFER_DELAY_MS);
			return;
		}

		const regularKeys = keyBuffer;
		const specials = [...specialKeyQueue];
		keyBuffer = '';
		specialKeyQueue = [];

		if (regularKeys || specials.length > 0) {
			sendBuffered(regularKeys, specials);
		}
	}

	async function sendBuffered(regularKeys: string, specials: string[]) {
		isSending = true;
		try {
			// Send regular keys as a batch (single request)
			if (regularKeys) {
				await sendKeys(pane.pane_id, regularKeys, false);
			}
			// Send special keys one by one (they can't be batched)
			for (const special of specials) {
				await sendSpecialKey(pane.pane_id, special);
			}
		} catch (e) {
			console.error('Failed to send keys:', e);
		} finally {
			isSending = false;
			// Check if more keys accumulated while sending
			if (keyBuffer || specialKeyQueue.length > 0) {
				flushBuffer();
			}
		}
	}

	function queueKey(key: string, isSpecial: boolean = false) {
		if (isSpecial) {
			// Flush any pending regular keys first, then queue special
			if (keyBuffer) {
				flushBuffer();
			}
			specialKeyQueue.push(key);
			// Send special keys with minimal delay
			if (bufferTimeout) clearTimeout(bufferTimeout);
			bufferTimeout = setTimeout(flushBuffer, 10);
		} else {
			// Buffer regular characters
			keyBuffer += key;
			// Reset/set the flush timer
			if (bufferTimeout) clearTimeout(bufferTimeout);
			bufferTimeout = setTimeout(flushBuffer, BUFFER_DELAY_MS);
		}
	}

	// Special keys that tmux understands
	const SPECIAL_KEYS: Record<string, string> = {
		'Enter': 'Enter',
		'Backspace': 'BSpace',
		'Tab': 'Tab',
		'Escape': 'Escape',
		'ArrowUp': 'Up',
		'ArrowDown': 'Down',
		'ArrowLeft': 'Left',
		'ArrowRight': 'Right',
		'Delete': 'DC',
		'Home': 'Home',
		'End': 'End',
		'PageUp': 'PPage',
		'PageDown': 'NPage',
	};

	// Queue-based sendKey to ensure ordering
	function sendKey(key: string, isSpecial: boolean = false) {
		// Handle modifiers before queueing
		let finalKey = key;
		let finalIsSpecial = isSpecial;

		if (ctrlActive || altActive) {
			let prefix = '';
			if (ctrlActive) prefix += 'C-';
			if (altActive) prefix += 'M-';

			if (isSpecial) {
				finalKey = prefix + key;
			} else {
				finalKey = prefix + key.toLowerCase();
			}
			finalIsSpecial = true; // modifier combos need tmux interpretation

			// Reset modifiers after use
			ctrlActive = false;
			altActive = false;
		}

		queueKey(finalKey, finalIsSpecial);
	}

	function handleKeyDown(e: KeyboardEvent) {
		// Ignore if typing in another input (like the detected prompt inputs)
		if (e.target !== hiddenInput && e.target !== document.body) return;

		// Check for special keys
		if (SPECIAL_KEYS[e.key]) {
			e.preventDefault();
			sendKey(SPECIAL_KEYS[e.key], true);
			return;
		}

		// Ignore modifier-only keys
		if (['Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) return;

		// Ignore if modifier is held (except shift for capitals)
		if (e.ctrlKey || e.altKey || e.metaKey) return;

		// Send printable character
		if (e.key.length === 1) {
			e.preventDefault();
			sendKey(e.key, false);
		}
	}

	// Handle mobile keyboard input
	function handleMobileInput(e: Event) {
		const input = e.target as HTMLInputElement;
		const char = input.value;
		if (char) {
			sendKey(char, false);
		}
		// Clear immediately
		input.value = '';
	}

	function openKeyboard() {
		hiddenInput?.focus();
		keyboardOpen = true;
	}

	function handleFocus() {
		keyboardOpen = true;
		// Scroll to bottom after keyboard opens (multiple attempts for reliability)
		const scrollToBottom = () => {
			keyboardBarRef?.scrollIntoView({ behavior: 'smooth', block: 'end' });
			window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
		};
		// Try multiple times as keyboard animation may take varying time
		setTimeout(scrollToBottom, 100);
		setTimeout(scrollToBottom, 300);
		setTimeout(scrollToBottom, 500);
	}

	function handleBlur() {
		keyboardOpen = false;
	}

	onMount(() => {
		loadPaneOutput(pane.pane_id, true);

		if (browser) {
			// Add global keydown listener for desktop
			document.addEventListener('keydown', handleKeyDown);
		}
	});

	onDestroy(() => {
		if (browser) {
			document.removeEventListener('keydown', handleKeyDown);
		}
	});
</script>

<div class="flex flex-col h-[100dvh]">
	<!-- Header (sticky) - unified navbar -->
	<div class="shrink-0 sticky top-0 z-10 flex items-center justify-between px-4 h-14 bg-gray-800 border-b border-gray-700">
		<div class="flex items-center gap-3">
			<a
				href="/"
				class="text-lg font-semibold text-white hover:text-gray-300 transition-colors"
			>
				Mate
			</a>

			<span class="text-gray-600">›</span>

			<div class="flex items-center gap-2 min-w-0">
				<span class="text-sm text-gray-400 truncate">
					{pane.session_name}:{pane.window_name}
				</span>
				<StatusBadge status={pane.status} size="sm" />
			</div>
		</div>

		<button
			onclick={() => loadPaneOutput(pane.pane_id, true)}
			class="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
			aria-label="Refresh"
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
				/>
			</svg>
		</button>
	</div>

	<!-- Output area -->
	<div class="flex-1 min-h-0 overflow-hidden relative">
		<PaneOutput lines={output} {lineOffset} />
	</div>

	<!-- Bottom input area (sticky) -->
	<div bind:this={keyboardBarRef} class="shrink-0 sticky bottom-0 z-10 bg-gray-800 border-t border-gray-700">
		<!-- Special input area for detected prompts -->
		{#if hasInput && inputRequest}
			<div class="border-b border-gray-700">
				<InputArea paneId={pane.pane_id} {inputRequest} />
			</div>
		{/if}

		<!-- Keyboard input bar -->
		<div class="p-2">
			<!-- Hidden input for mobile keyboard -->
			<input
				bind:this={hiddenInput}
				type="text"
				oninput={handleMobileInput}
				onfocus={handleFocus}
				onblur={handleBlur}
				autocomplete="off"
				autocorrect="off"
				autocapitalize="off"
				spellcheck="false"
				class="absolute opacity-0 w-0 h-0 pointer-events-none"
			/>

			<div class="flex gap-1.5 items-center justify-center flex-wrap">
				<!-- Keyboard button (mobile) -->
				<button
					onclick={openKeyboard}
					class="h-10 px-3 bg-gray-700 hover:bg-gray-600 text-white text-xs font-medium rounded transition-colors {keyboardOpen ? 'ring-2 ring-blue-500' : ''}"
					aria-label="Open keyboard"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<rect x="2" y="6" width="20" height="12" rx="2" stroke-width="2"/>
						<line x1="6" y1="10" x2="6" y2="10" stroke-width="2" stroke-linecap="round"/>
						<line x1="10" y1="10" x2="10" y2="10" stroke-width="2" stroke-linecap="round"/>
						<line x1="14" y1="10" x2="14" y2="10" stroke-width="2" stroke-linecap="round"/>
						<line x1="18" y1="10" x2="18" y2="10" stroke-width="2" stroke-linecap="round"/>
						<line x1="8" y1="14" x2="16" y2="14" stroke-width="2" stroke-linecap="round"/>
					</svg>
				</button>
				<!-- Ctrl modifier (toggle) -->
				<button
					onclick={() => ctrlActive = !ctrlActive}
					class="h-10 px-2 text-white text-xs font-medium rounded transition-colors
						{ctrlActive ? 'bg-blue-600 ring-2 ring-blue-400' : 'bg-gray-700 hover:bg-gray-600'}"
					aria-label="Ctrl modifier"
					aria-pressed={ctrlActive}
				>
					Ctrl
				</button>
				<!-- Alt modifier (toggle) -->
				<button
					onclick={() => altActive = !altActive}
					class="h-10 px-2 text-white text-xs font-medium rounded transition-colors
						{altActive ? 'bg-blue-600 ring-2 ring-blue-400' : 'bg-gray-700 hover:bg-gray-600'}"
					aria-label="Alt modifier"
					aria-pressed={altActive}
				>
					Alt
				</button>
				<!-- Esc key -->
				<button
					onclick={() => sendKey('Escape', true)}
					class="h-10 w-10 bg-gray-700 hover:bg-gray-600 text-white text-xs font-medium rounded transition-colors"
					aria-label="Escape"
				>
					ESC
				</button>
				<!-- Tab key -->
				<button
					onclick={() => sendKey('Tab', true)}
					class="h-10 px-3 bg-gray-700 hover:bg-gray-600 text-white text-xs font-medium rounded transition-colors"
					aria-label="Tab"
				>
					TAB
				</button>
				<!-- Arrow keys -->
				<button
					onclick={() => sendKey('Left', true)}
					class="h-10 w-10 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
					aria-label="Arrow Left"
				>
					<svg class="w-4 h-4 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
					</svg>
				</button>
				<button
					onclick={() => sendKey('Up', true)}
					class="h-10 w-10 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
					aria-label="Arrow Up"
				>
					<svg class="w-4 h-4 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
					</svg>
				</button>
				<button
					onclick={() => sendKey('Down', true)}
					class="h-10 w-10 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
					aria-label="Arrow Down"
				>
					<svg class="w-4 h-4 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				<button
					onclick={() => sendKey('Right', true)}
					class="h-10 w-10 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
					aria-label="Arrow Right"
				>
					<svg class="w-4 h-4 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</button>
				<!-- Enter key -->
				<button
					onclick={() => sendKey('Enter', true)}
					class="h-10 px-4 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded transition-colors"
					aria-label="Enter"
				>
					Enter
				</button>
			</div>
		</div>
	</div>
</div>
