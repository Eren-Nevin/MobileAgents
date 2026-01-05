<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		message?: string;
		onSubmit: (value: string) => void;
		disabled?: boolean;
	}

	let { message, onSubmit, disabled = false }: Props = $props();

	let selectedOption = $state<'yes' | 'no'>('yes');
	let containerRef: HTMLDivElement;

	function handleKeyDown(e: KeyboardEvent) {
		if (disabled) return;

		switch (e.key) {
			case 'ArrowLeft':
			case 'ArrowUp':
				e.preventDefault();
				selectedOption = 'yes';
				break;
			case 'ArrowRight':
			case 'ArrowDown':
				e.preventDefault();
				selectedOption = 'no';
				break;
			case 'Enter':
			case ' ':
				e.preventDefault();
				onSubmit(selectedOption);
				break;
			case 'y':
			case 'Y':
				e.preventDefault();
				onSubmit('yes');
				break;
			case 'n':
			case 'N':
			case 'Escape':
				e.preventDefault();
				onSubmit('no');
				break;
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
	role="group"
	aria-label="Confirm action"
	class="space-y-3 outline-none"
>
	{#if message}
		<p class="text-white font-medium">{message}</p>
	{/if}

	<div class="flex gap-3">
		<button
			onclick={() => onSubmit('yes')}
			onmouseenter={() => (selectedOption = 'yes')}
			{disabled}
			class="flex-1 px-4 py-2.5 disabled:opacity-50 text-white font-medium rounded-lg transition-all active:scale-95 {selectedOption === 'yes'
				? 'bg-green-500 ring-2 ring-green-300 ring-offset-2 ring-offset-gray-800'
				: 'bg-green-600 hover:bg-green-500'}"
		>
			Approve (Y)
		</button>

		<button
			onclick={() => onSubmit('no')}
			onmouseenter={() => (selectedOption = 'no')}
			{disabled}
			class="flex-1 px-4 py-2.5 disabled:opacity-50 text-white font-medium rounded-lg transition-all active:scale-95 {selectedOption === 'no'
				? 'bg-red-500 ring-2 ring-red-300 ring-offset-2 ring-offset-gray-800'
				: 'bg-red-600 hover:bg-red-500'}"
		>
			Cancel (N)
		</button>
	</div>

	<p class="text-xs text-gray-500">Use arrow keys + Enter, or press Y/N</p>
</div>
