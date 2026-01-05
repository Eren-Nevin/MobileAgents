<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { Header } from '$lib/components';
	import { initializeStore, loadPanes } from '$lib/stores/panes.svelte';

	let { children } = $props();

	onMount(() => {
		// Initialize WebSocket and store
		const cleanup = initializeStore();

		// Load initial panes
		loadPanes();

		return cleanup;
	});
</script>

<div class="min-h-screen bg-gray-900 text-gray-100 flex flex-col">
	<Header />

	<main class="flex-1 flex flex-col">
		{@render children()}
	</main>
</div>
