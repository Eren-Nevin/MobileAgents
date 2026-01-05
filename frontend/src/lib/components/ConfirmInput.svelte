<script lang="ts">
	interface Props {
		message?: string;
		onSubmit: (value: string) => void;
		disabled?: boolean;
	}

	let { message, onSubmit, disabled = false }: Props = $props();
</script>

<div class="space-y-3">
	{#if message}
		<p class="text-white font-medium">{message}</p>
	{/if}

	<div class="flex gap-3">
		<button
			onclick={() => onSubmit('yes')}
			{disabled}
			class="flex-1 px-4 py-2.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white font-medium rounded-lg transition-colors active:scale-95"
		>
			Approve
		</button>

		<button
			onclick={() => onSubmit('no')}
			{disabled}
			class="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-medium rounded-lg transition-colors active:scale-95"
		>
			Cancel
		</button>
	</div>
</div>
