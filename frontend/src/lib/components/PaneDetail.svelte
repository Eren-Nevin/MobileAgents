<script lang="ts">
	import type { PaneInfo } from '$lib/types';
	import { getPaneOutput, getInputRequest, loadPaneOutput } from '$lib/stores/panes.svelte';
	import { sendKeys, sendSpecialKey } from '$lib/api';
	import { onMount } from 'svelte';
	import StatusBadge from './StatusBadge.svelte';
	import PaneOutput from './PaneOutput.svelte';
	import InputArea from './InputArea.svelte';

	interface Props {
		pane: PaneInfo;
	}

	let { pane }: Props = $props();

	const output = $derived(getPaneOutput(pane.pane_id));
	const inputRequest = $derived(getInputRequest(pane.pane_id));
	const hasInput = $derived(pane.status === 'waiting_input' && inputRequest);

	let inputError = $state<string | null>(null);

	async function handleInput(e: Event) {
		const input = e.target as HTMLInputElement;
		const char = input.value;
		if (!char) return;

		// Clear input immediately
		input.value = '';

		try {
			// Send character without Enter
			await sendKeys(pane.pane_id, char, false);
			setTimeout(() => loadPaneOutput(pane.pane_id, true), 50);
		} catch (e) {
			inputError = e instanceof Error ? e.message : 'Failed to send';
		}
	}

	async function handleEnter() {
		try {
			await sendSpecialKey(pane.pane_id, 'Enter');
			setTimeout(() => loadPaneOutput(pane.pane_id, true), 100);
		} catch (e) {
			inputError = e instanceof Error ? e.message : 'Failed to send';
		}
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			handleEnter();
		}
	}

	async function handleSpecialKey(key: 'Up' | 'Down' | 'Tab' | 'Escape') {
		try {
			await sendSpecialKey(pane.pane_id, key);
			setTimeout(() => loadPaneOutput(pane.pane_id, true), 100);
		} catch (e) {
			console.error('Failed to send special key:', e);
		}
	}

	onMount(() => {
		// Load initial output
		loadPaneOutput(pane.pane_id, true);
	});
</script>

<div class="flex flex-col h-[100dvh]">
	<!-- Header (sticky) -->
	<div class="shrink-0 sticky top-0 z-10 flex items-center justify-between p-4 bg-gray-800 border-b border-gray-700">
		<div class="flex items-center gap-3">
			<a
				href="/"
				class="p-2 -ml-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
				aria-label="Back to list"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M15 19l-7-7 7-7"
					/>
				</svg>
			</a>

			<div>
				<div class="flex items-center gap-2">
					<span class="text-sm text-gray-400">
						{pane.session_name}:{pane.window_name}
					</span>
					<StatusBadge status={pane.status} size="sm" />
				</div>
				{#if pane.title}
					<h1 class="text-white font-medium">{pane.title}</h1>
				{/if}
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
	<div class="flex-1 min-h-0 overflow-hidden">
		<PaneOutput lines={output} />
	</div>

	<!-- Bottom input area (sticky) -->
	<div class="shrink-0 sticky bottom-0 z-10 bg-gray-800 border-t border-gray-700">
		<!-- Special input area for detected prompts -->
		{#if hasInput && inputRequest}
			<div class="border-b border-gray-700">
				<InputArea paneId={pane.pane_id} {inputRequest} />
			</div>
		{/if}

		<!-- Always-visible input -->
		<div class="p-3">
			{#if inputError}
				<div class="mb-2 p-2 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
					{inputError}
				</div>
			{/if}

			<div class="flex gap-2 items-center">
				<!-- Esc and Tab keys -->
				<button
					onclick={() => handleSpecialKey('Escape')}
					class="w-9 h-9 bg-gray-700 hover:bg-gray-600 text-white text-xs font-medium rounded transition-colors"
					aria-label="Escape"
				>
					ESC
				</button>
				<button
					onclick={() => handleSpecialKey('Tab')}
					class="px-3 h-9 bg-gray-700 hover:bg-gray-600 text-white text-xs font-medium rounded transition-colors"
					aria-label="Tab"
				>
					TAB
				</button>
				<input
					type="text"
					oninput={handleInput}
					onkeydown={handleKeyDown}
					placeholder="Type to send..."
					class="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 font-mono text-sm"
				/>
				<!-- Arrow keys -->
				<div class="flex flex-col gap-0.5">
					<button
						onclick={() => handleSpecialKey('Up')}
						class="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
						aria-label="Arrow Up"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
						</svg>
					</button>
					<button
						onclick={() => handleSpecialKey('Down')}
						class="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
						aria-label="Arrow Down"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
						</svg>
					</button>
				</div>
				<button
					onclick={handleEnter}
					class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors"
				>
					Enter
				</button>
			</div>
		</div>
	</div>
</div>
