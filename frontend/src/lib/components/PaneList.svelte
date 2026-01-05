<script lang="ts">
	import { getPanesBySession, getIsLoading, getError } from '$lib/stores/panes.svelte';
	import { browser } from '$app/environment';
	import PaneCard from './PaneCard.svelte';

	// Filter state - show only Claude panes when true
	// Load from localStorage on init
	let claudeOnly = $state(browser ? localStorage.getItem('claudeOnly') === 'true' : false);

	// Save to localStorage when changed
	$effect(() => {
		if (browser) {
			localStorage.setItem('claudeOnly', String(claudeOnly));
		}
	});

	const panesBySession = $derived(getPanesBySession());
	const isLoading = $derived(getIsLoading());
	const error = $derived(getError());

	// Filter panes by Claude when toggle is active
	const filteredPanesBySession = $derived(() => {
		if (!claudeOnly) return panesBySession;

		const filtered = new Map<string, typeof panesBySession extends Map<string, infer V> ? V : never>();
		for (const [sessionName, panes] of panesBySession.entries()) {
			const claudePanes = panes.filter(
				(p) => p.window_name.toLowerCase().includes('claude') || p.title.toLowerCase().includes('claude')
			);
			if (claudePanes.length > 0) {
				filtered.set(sessionName, claudePanes);
			}
		}
		return filtered;
	});

	const displayPanes = $derived(filteredPanesBySession());
	const isEmpty = $derived(displayPanes.size === 0);
</script>

<div class="p-4 max-w-4xl mx-auto">
	<!-- Header with filter toggle -->
	<div class="flex items-center justify-between mb-4">
		<h1 class="text-lg font-semibold text-white">Panes</h1>
		<button
			onclick={() => claudeOnly = !claudeOnly}
			class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
				{claudeOnly ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}"
			aria-pressed={claudeOnly}
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
			</svg>
			Claude Only
		</button>
	</div>

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
			<div class="text-gray-500 mb-2">
				{claudeOnly ? 'No Claude panes found' : 'No panes found'}
			</div>
			<p class="text-sm text-gray-600">
				{claudeOnly ? 'No panes with "claude" in the name' : 'Start a tmux session to see panes here'}
			</p>
		</div>
	{:else}
		<div class="space-y-6">
			{#each [...displayPanes.entries()] as [sessionName, panes]}
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
