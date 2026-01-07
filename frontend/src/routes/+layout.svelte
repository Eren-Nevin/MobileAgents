<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { Header, ReloadPrompt } from '$lib/components';
	import { initializeStore, loadPanes } from '$lib/stores/panes.svelte';

	let { children } = $props();

	// Hide global header on pane detail pages (they have their own integrated header)
	const showHeader = $derived(!$page.url.pathname.startsWith('/pane/'));

	onMount(() => {
		// Initialize WebSocket and store
		const cleanup = initializeStore();

		// Load initial panes
		loadPanes();

		return cleanup;
	});
</script>

<div class="min-h-screen bg-gray-900 text-gray-100 flex flex-col">
	{#if showHeader}
		<Header />
	{/if}

	<main class="flex-1 flex flex-col">
		{@render children()}
	</main>

	{#if browser}
		<ReloadPrompt />
	{/if}
</div>
