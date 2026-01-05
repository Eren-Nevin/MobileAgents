<script lang="ts">
	import type { PaneInfo } from '$lib/types';
	import StatusBadge from './StatusBadge.svelte';

	interface Props {
		pane: PaneInfo;
	}

	let { pane }: Props = $props();

	const isWaiting = $derived(pane.status === 'waiting_input');
</script>

<a
	href="/pane/{pane.pane_id.replace('%', '')}"
	class="block p-4 bg-gray-800 rounded-lg border transition-all active:scale-[0.98] {isWaiting
		? 'border-yellow-500/50 hover:border-yellow-500'
		: 'border-gray-700 hover:border-gray-600'}"
>
	<div class="flex items-start justify-between gap-3">
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-2 mb-1">
				<span class="text-sm font-medium text-gray-400">
					{pane.session_name}:{pane.window_name}
				</span>
				<span class="text-gray-600">#{pane.pane_index}</span>
			</div>

			{#if pane.title}
				<p class="text-white font-medium truncate">{pane.title}</p>
			{:else}
				<p class="text-gray-500 italic">No title</p>
			{/if}
		</div>

		<StatusBadge status={pane.status} size="sm" />
	</div>

	{#if isWaiting}
		<div class="mt-3 pt-3 border-t border-gray-700">
			<span class="text-sm text-yellow-400">Input required</span>
		</div>
	{/if}
</a>
