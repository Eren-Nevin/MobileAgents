<script lang="ts">
	interface Props {
		options: string[];
		onSubmit: (value: string) => void;
		disabled?: boolean;
	}

	let { options, onSubmit, disabled = false }: Props = $props();
</script>

<div class="space-y-2">
	<p class="text-sm text-gray-400">Select an option:</p>

	<div class="flex flex-wrap gap-2">
		{#each options as option, index}
			<button
				onclick={() => onSubmit(String(index + 1))}
				{disabled}
				class="px-4 py-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 border border-gray-700 hover:border-gray-600 text-white rounded-lg transition-colors active:scale-95"
			>
				<span class="text-gray-500 mr-1">{index + 1})</span>
				{option}
			</button>
		{/each}
	</div>
</div>
