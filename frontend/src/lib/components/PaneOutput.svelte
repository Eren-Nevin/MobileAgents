<script lang="ts">
	import { onMount, tick } from 'svelte';

	interface Props {
		lines: string[];
		autoScroll?: boolean;
	}

	let { lines, autoScroll = true }: Props = $props();

	// Trim trailing empty lines
	const trimmedLines = $derived.by(() => {
		let end = lines.length;
		while (end > 0 && !lines[end - 1]?.trim()) {
			end--;
		}
		return lines.slice(0, end);
	});

	let containerRef: HTMLDivElement;
	let userScrolled = $state(false);
	let prevLineCount = $state(0);

	function scrollToBottom() {
		if (containerRef) {
			containerRef.scrollTop = containerRef.scrollHeight;
		}
	}

	function handleScroll() {
		if (!containerRef) return;

		const { scrollTop, scrollHeight, clientHeight } = containerRef;
		const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

		userScrolled = !isAtBottom;
	}

	// Auto-scroll when new lines are added (not just any change)
	$effect(() => {
		const currentCount = trimmedLines.length;
		if (autoScroll && currentCount > prevLineCount && !userScrolled) {
			tick().then(scrollToBottom);
		}
		prevLineCount = currentCount;
	});

	onMount(() => {
		scrollToBottom();
	});
</script>

<div
	bind:this={containerRef}
	onscroll={handleScroll}
	class="h-full overflow-y-auto rounded-lg p-3 scrollbar-thin bg-terminal"
>
	<pre class="font-mono-output text-gray-200 whitespace-pre-wrap break-words">{#each trimmedLines as line, i}<span class="block hover:bg-white/5">{line || ' '}</span>{/each}</pre>
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
