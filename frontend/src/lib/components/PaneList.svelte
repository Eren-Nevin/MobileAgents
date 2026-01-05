<script lang="ts">
	import { getPanesBySession, getIsLoading, getError } from '$lib/stores/panes.svelte';
	import PaneCard from './PaneCard.svelte';

	const panesBySession = $derived(getPanesBySession());
	const isLoading = $derived(getIsLoading());
	const error = $derived(getError());
	const isEmpty = $derived(panesBySession.size === 0);
</script>

<div class="p-4 max-w-4xl mx-auto">
	{#if error}
		<div class="p-4 mb-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
			{error}
		</div>
	{/if}

	{#if isLoading}
		<div class="flex items-center justify-center py-12">
			<div class="animate-spin w-8 h-8 border-2 border-gray-600 border-t-blue-500 rounded-full">
			</div>
		</div>
	{:else if isEmpty}
		<div class="text-center py-12">
			<div class="text-gray-500 mb-2">No panes found</div>
			<p class="text-sm text-gray-600">
				Start a tmux session to see panes here
			</p>
		</div>
	{:else}
		<div class="space-y-6">
			{#each [...panesBySession.entries()] as [sessionName, panes]}
				<section>
					<h2 class="text-sm font-medium text-gray-400 mb-3 px-1">
						{sessionName}
						<span class="text-gray-600">({panes.length})</span>
					</h2>

					<div class="space-y-3">
						{#each panes as pane (pane.pane_id)}
							<PaneCard {pane} />
						{/each}
					</div>
				</section>
			{/each}
		</div>
	{/if}
</div>
