<script lang="ts">
	import type { PaneInfo } from '$lib/types';
	import { getPaneOutput, getInputRequest, loadPaneOutput } from '$lib/stores/panes.svelte';
	import { sendKeys } from '$lib/api';
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

	let inputValue = $state('');
	let isSending = $state(false);
	let inputError = $state<string | null>(null);

	async function handleSendKeys() {
		if (!inputValue.trim() || isSending) return;

		isSending = true;
		inputError = null;

		try {
			await sendKeys(pane.pane_id, inputValue);
			inputValue = '';
			// Refresh output after sending
			setTimeout(() => loadPaneOutput(pane.pane_id, true), 100);
		} catch (e) {
			inputError = e instanceof Error ? e.message : 'Failed to send';
		} finally {
			isSending = false;
		}
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSendKeys();
		}
	}

	onMount(() => {
		// Load initial output
		loadPaneOutput(pane.pane_id, true);
	});
</script>

<div class="flex flex-col h-full">
	<!-- Header (sticky) -->
	<div class="sticky top-0 z-10 flex items-center justify-between p-4 bg-gray-800 border-b border-gray-700">
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
	<div class="flex-1 relative overflow-hidden">
		<PaneOutput lines={output} />
	</div>

	<!-- Special input area for detected prompts -->
	{#if hasInput && inputRequest}
		<InputArea paneId={pane.pane_id} {inputRequest} />
	{/if}

	<!-- Always-visible input -->
	<div class="p-3 bg-gray-800 border-t border-gray-700">
		{#if inputError}
			<div class="mb-2 p-2 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
				{inputError}
			</div>
		{/if}

		<div class="flex gap-2">
			<input
				type="text"
				bind:value={inputValue}
				onkeydown={handleKeyDown}
				disabled={isSending}
				placeholder="Send text to pane..."
				class="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50 font-mono text-sm"
			/>
			<button
				onclick={handleSendKeys}
				disabled={isSending || !inputValue.trim()}
				class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors"
			>
				{isSending ? '...' : 'Send'}
			</button>
		</div>
	</div>
</div>
