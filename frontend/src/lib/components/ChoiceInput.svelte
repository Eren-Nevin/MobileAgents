<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		options: string[];
		onSubmit: (value: string) => void;
		disabled?: boolean;
	}

	let { options, onSubmit, disabled = false }: Props = $props();

	let selectedIndex = $state(0);
	let containerRef: HTMLDivElement;

	function handleKeyDown(e: KeyboardEvent) {
		if (disabled) return;

		switch (e.key) {
			case 'ArrowUp':
			case 'ArrowLeft':
				e.preventDefault();
				selectedIndex = selectedIndex > 0 ? selectedIndex - 1 : options.length - 1;
				break;
			case 'ArrowDown':
			case 'ArrowRight':
				e.preventDefault();
				selectedIndex = selectedIndex < options.length - 1 ? selectedIndex + 1 : 0;
				break;
			case 'Enter':
			case ' ':
				e.preventDefault();
				onSubmit(String(selectedIndex + 1));
				break;
			default:
				// Number keys 1-9 for quick selection
				const num = parseInt(e.key);
				if (num >= 1 && num <= options.length) {
					e.preventDefault();
					onSubmit(String(num));
				}
		}
	}

	onMount(() => {
		containerRef?.focus();
	});
</script>

<div
	bind:this={containerRef}
	onkeydown={handleKeyDown}
	tabindex="0"
	role="listbox"
	aria-label="Select an option"
	class="space-y-2 outline-none"
>
	<p class="text-sm text-gray-400">Select an option (use arrow keys + Enter):</p>

	<div class="flex flex-col gap-1">
		{#each options as option, index}
			<button
				onclick={() => onSubmit(String(index + 1))}
				onmouseenter={() => (selectedIndex = index)}
				{disabled}
				role="option"
				aria-selected={selectedIndex === index}
				class="px-4 py-2 text-left disabled:opacity-50 rounded-lg transition-all {selectedIndex === index
					? 'bg-blue-600 text-white border-2 border-blue-400'
					: 'bg-gray-800 hover:bg-gray-700 text-white border border-gray-700'}"
			>
				<span class="inline-block w-6 text-center {selectedIndex === index ? 'text-blue-200' : 'text-gray-500'}">{index + 1})</span>
				{option}
			</button>
		{/each}
	</div>

	<p class="text-xs text-gray-500">Tip: Press 1-{options.length} for quick select</p>
</div>
