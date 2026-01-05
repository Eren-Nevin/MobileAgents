<script lang="ts">
	import type { InputRequest, InputType } from '$lib/types';
	import { sendInput } from '$lib/api';
	import TextInput from './TextInput.svelte';
	import ChoiceInput from './ChoiceInput.svelte';
	import ConfirmInput from './ConfirmInput.svelte';

	interface Props {
		paneId: string;
		inputRequest: InputRequest;
	}

	let { paneId, inputRequest }: Props = $props();

	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	async function handleSubmit(value: string) {
		isSubmitting = true;
		error = null;

		try {
			await sendInput(paneId, {
				input_type: inputRequest.input_type,
				value
			});
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to send input';
			console.error('Failed to send input:', e);
		} finally {
			isSubmitting = false;
		}
	}
</script>

<div class="p-4 bg-gray-800 border-t border-gray-700">
	{#if error}
		<div class="mb-3 p-2 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
			{error}
		</div>
	{/if}

	{#if inputRequest.input_type === 'text'}
		<TextInput prompt={inputRequest.prompt} onSubmit={handleSubmit} disabled={isSubmitting} />
	{:else if inputRequest.input_type === 'choice' && inputRequest.options}
		<ChoiceInput options={inputRequest.options} onSubmit={handleSubmit} disabled={isSubmitting} />
	{:else if inputRequest.input_type === 'confirm'}
		<ConfirmInput
			message={inputRequest.message}
			onSubmit={handleSubmit}
			disabled={isSubmitting}
		/>
	{:else}
		<TextInput onSubmit={handleSubmit} disabled={isSubmitting} />
	{/if}
</div>
