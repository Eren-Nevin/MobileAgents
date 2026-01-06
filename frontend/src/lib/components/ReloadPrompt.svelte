<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';

	let needRefresh = $state(false);
	let offlineReady = $state(false);
	let updateServiceWorker: ((reloadPage?: boolean) => Promise<void>) | undefined;

	onMount(async () => {
		if (!browser) return;

		const { useRegisterSW } = await import('virtual:pwa-register/svelte');
		const { needRefresh: nr, offlineReady: or, updateServiceWorker: usw } = useRegisterSW({
			onRegistered(r) {
				console.log('SW Registered:', r);
			},
			onRegisterError(error) {
				console.log('SW registration error', error);
			}
		});

		// Subscribe to the stores
		nr.subscribe((value) => (needRefresh = value));
		or.subscribe((value) => (offlineReady = value));
		updateServiceWorker = usw;
	});

	function close() {
		offlineReady = false;
		needRefresh = false;
	}

	async function updateSW() {
		if (updateServiceWorker) {
			await updateServiceWorker(true);
		}
	}
</script>

{#if offlineReady || needRefresh}
	<div
		class="fixed bottom-4 right-4 z-50 p-4 bg-gray-800 border border-gray-600 rounded-lg shadow-lg max-w-sm"
		role="alert"
	>
		<div class="flex items-start gap-3">
			<div class="flex-1">
				{#if offlineReady}
					<p class="text-sm text-gray-200">App ready to work offline</p>
				{:else}
					<p class="text-sm text-gray-200">New version available</p>
				{/if}
			</div>
			<div class="flex gap-2">
				{#if needRefresh}
					<button
						onclick={updateSW}
						class="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors"
					>
						Update
					</button>
				{/if}
				<button
					onclick={close}
					class="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
				>
					Close
				</button>
			</div>
		</div>
	</div>
{/if}
