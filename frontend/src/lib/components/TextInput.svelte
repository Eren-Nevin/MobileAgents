<script lang="ts">
	interface Props {
		prompt?: string;
		onSubmit: (value: string) => void;
		disabled?: boolean;
	}

	let { prompt, onSubmit, disabled = false }: Props = $props();

	let value = $state('');

	function handleSubmit(e: Event) {
		e.preventDefault();
		if (value.trim() && !disabled) {
			onSubmit(value);
			value = '';
		}
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit(e);
		}
	}
</script>

<form onsubmit={handleSubmit} class="flex flex-col gap-2">
	{#if prompt}
		<label for="text-input" class="text-sm text-gray-400">{prompt}</label>
	{/if}

	<div class="flex gap-2">
		<input
			id="text-input"
			type="text"
			bind:value
			onkeydown={handleKeyDown}
			{disabled}
			placeholder="Type your response..."
			class="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
		/>

		<button
			type="submit"
			disabled={disabled || !value.trim()}
			class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors"
		>
			Send
		</button>
	</div>
</form>
