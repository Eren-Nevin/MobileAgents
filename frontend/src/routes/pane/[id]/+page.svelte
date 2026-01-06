<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { PaneDetail } from '$lib/components';
	import { getPane } from '$lib/stores/panes.svelte';

	const paneId = $derived(`%${$page.params.id}`);
	const pane = $derived(getPane(paneId));

	$effect(() => {
		// Redirect to home if pane doesn't exist
		if (paneId && !pane) {
			// Give some time for panes to load
			const timeout = setTimeout(() => {
				if (!getPane(paneId)) {
					goto('/');
				}
			}, 2000);

			return () => clearTimeout(timeout);
		}
	});
</script>

<svelte:head>
	<title>{pane?.title || pane?.pane_id || 'Pane'} - Mate</title>
</svelte:head>

{#if pane}
	<PaneDetail {pane} />
{:else}
	<div class="flex-1 flex items-center justify-center">
		<div class="text-center">
			<div class="animate-spin w-8 h-8 border-2 border-gray-600 border-t-blue-500 rounded-full mx-auto mb-4">
			</div>
			<p class="text-gray-400">Loading pane...</p>
		</div>
	</div>
{/if}
