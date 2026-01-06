<script lang="ts">
	import { getPanesBySession, getPanes, getIsLoading, getError } from '$lib/stores/panes.svelte';
	import { browser } from '$app/environment';
	import PaneCard from './PaneCard.svelte';
	import type { PaneInfo } from '$lib/types';

	// Filter options
	type FilterOption = 'claude' | 'codex' | 'all';
	const filterOptions: { value: FilterOption; label: string }[] = [
		{ value: 'claude', label: 'Claude' },
		{ value: 'codex', label: 'Codex' },
		{ value: 'all', label: 'All Panes' }
	];

	// Filter state - load from localStorage, default to 'claude'
	let filter = $state<FilterOption>(
		browser ? (localStorage.getItem('paneFilter') as FilterOption) || 'claude' : 'claude'
	);

	// View mode: 'sessions' (grouped) or 'grid' (flat)
	let viewMode = $state<'sessions' | 'grid'>(
		browser ? (localStorage.getItem('paneViewMode') as 'sessions' | 'grid') || 'sessions' : 'sessions'
	);

	// Save to localStorage when changed
	$effect(() => {
		if (browser) {
			localStorage.setItem('paneFilter', filter);
		}
	});

	$effect(() => {
		if (browser) {
			localStorage.setItem('paneViewMode', viewMode);
		}
	});

	const panesBySession = $derived(getPanesBySession());
	const allPanes = $derived(getPanes());
	const isLoading = $derived(getIsLoading());
	const error = $derived(getError());

	// Check if a pane matches the filter
	function matchesFilter(pane: PaneInfo, filterType: FilterOption): boolean {
		if (filterType === 'all') return true;

		const windowName = pane.window_name.toLowerCase();
		const title = pane.title.toLowerCase();

		if (filterType === 'claude') {
			return windowName.includes('claude') || title.includes('claude');
		}
		if (filterType === 'codex') {
			return windowName.includes('codex') || title.includes('codex');
		}
		return true;
	}

	// Filter panes grouped by session
	const filteredPanesBySession = $derived(() => {
		if (filter === 'all') return panesBySession;

		const filtered = new Map<string, PaneInfo[]>();
		for (const [sessionName, panes] of panesBySession.entries()) {
			const matchingPanes = panes.filter((p) => matchesFilter(p, filter));
			if (matchingPanes.length > 0) {
				filtered.set(sessionName, matchingPanes);
			}
		}
		return filtered;
	});

	// Filter panes as flat list
	const filteredPanes = $derived(() => {
		if (filter === 'all') return allPanes;
		return allPanes.filter((p) => matchesFilter(p, filter));
	});

	const displayPanesBySession = $derived(filteredPanesBySession());
	const displayPanesFlat = $derived(filteredPanes());
	const isEmpty = $derived(
		viewMode === 'sessions' ? displayPanesBySession.size === 0 : displayPanesFlat.length === 0
	);

	const filterLabel = $derived(filterOptions.find((o) => o.value === filter)?.label || 'All');
</script>

<div class="p-4 max-w-4xl mx-auto">
	<!-- Header with filter selector and view toggle -->
	<div class="flex items-center justify-between mb-4 gap-3">
		<h1 class="text-lg font-semibold text-white">Panes</h1>

		<div class="flex items-center gap-2">
			<!-- Filter selector -->
			<div class="relative">
				<select
					bind:value={filter}
					class="appearance-none bg-gray-700 text-white text-sm font-medium px-3 py-1.5 pr-8 rounded-lg border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
				>
					{#each filterOptions as option}
						<option value={option.value}>{option.label}</option>
					{/each}
				</select>
				<svg
					class="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
			</div>

			<!-- View mode toggle -->
			<button
				onclick={() => (viewMode = viewMode === 'sessions' ? 'grid' : 'sessions')}
				class="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
				title={viewMode === 'sessions' ? 'Switch to grid view' : 'Switch to session view'}
			>
				{#if viewMode === 'sessions'}
					<!-- Grid icon -->
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
						/>
					</svg>
				{:else}
					<!-- List/sessions icon -->
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 6h16M4 10h16M4 14h16M4 18h16"
						/>
					</svg>
				{/if}
			</button>
		</div>
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
				No {filter === 'all' ? '' : filterLabel} panes found
			</div>
			<p class="text-sm text-gray-600">
				{#if filter === 'all'}
					Start a tmux session to see panes here
				{:else}
					No panes with "{filter}" in the name or title
				{/if}
			</p>
		</div>
	{:else if viewMode === 'sessions'}
		<!-- Session-grouped view -->
		<div class="space-y-6">
			{#each [...displayPanesBySession.entries()] as [sessionName, panes]}
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
	{:else}
		<!-- Grid view (flat) -->
		<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
			{#each displayPanesFlat as pane (pane.pane_id)}
				<PaneCard {pane} />
			{/each}
		</div>
	{/if}
</div>
