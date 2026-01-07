<script lang="ts">
	import { getIsConnected, countByStatus } from '$lib/stores/panes.svelte';

	const isConnected = $derived(getIsConnected());
	const waitingCount = $derived(countByStatus('waiting_input'));
</script>

<header class="shrink-0 sticky top-0 z-10 flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700">
	<div class="flex items-center gap-3">
		<h1 class="text-lg font-semibold text-white">Mate</h1>
		{#if waitingCount > 0}
			<span
				class="px-2 py-0.5 text-xs font-medium bg-yellow-500/20 text-yellow-400 rounded-full"
			>
				{waitingCount} waiting
			</span>
		{/if}
	</div>

	<div class="flex items-center gap-2">
		<span
			class="flex items-center gap-1.5 text-sm"
			class:text-green-400={isConnected}
			class:text-red-400={!isConnected}
		>
			<span
				class="w-2 h-2 rounded-full"
				class:bg-green-400={isConnected}
				class:bg-red-400={!isConnected}
			></span>
			{isConnected ? 'Connected' : 'Disconnected'}
		</span>
	</div>
</header>
