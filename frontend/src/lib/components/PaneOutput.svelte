<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		lines: string[];
		autoScroll?: boolean;
	}

	let { lines, autoScroll = true }: Props = $props();

	let containerRef: HTMLDivElement;
	let userScrolled = $state(false);

	function scrollToBottom() {
		if (containerRef && !userScrolled) {
			containerRef.scrollTop = containerRef.scrollHeight;
		}
	}

	function handleScroll() {
		if (!containerRef) return;

		const { scrollTop, scrollHeight, clientHeight } = containerRef;
		const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

		userScrolled = !isAtBottom;
	}

	$effect(() => {
		// Scroll when lines change
		if (autoScroll && lines.length) {
			scrollToBottom();
		}
	});

	onMount(() => {
		scrollToBottom();
	});
</script>

<div
	bind:this={containerRef}
	onscroll={handleScroll}
	class="flex-1 overflow-y-auto rounded-lg p-3 scrollbar-thin bg-terminal"
>
	<pre class="font-mono-output text-gray-200 whitespace-pre-wrap break-words">{#each lines as line, i}<span class="block hover:bg-white/5">{line || ' '}</span>{/each}</pre>
</div>

{#if userScrolled}
	<button
		onclick={() => {
			userScrolled = false;
			scrollToBottom();
		}}
		class="absolute bottom-20 right-4 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-full shadow-lg transition-colors"
	>
		Scroll to bottom
	</button>
{/if}
