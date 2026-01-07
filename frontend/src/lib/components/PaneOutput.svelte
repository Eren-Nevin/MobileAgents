<script lang="ts">
	import { onMount, tick } from 'svelte';
	import Line from './Line.svelte';

	interface Props {
		lines: string[];
		lineOffset?: number; // For stable line keys across updates
		autoScroll?: boolean;
	}

	let { lines, lineOffset = 0, autoScroll = true }: Props = $props();

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
	<pre class="font-mono-output text-gray-200 whitespace-pre-wrap break-words">{#each trimmedLines as line, i (lineOffset + i)}<Line content={line} />{/each}</pre>
</div>

{#if userScrolled}
	<button
		onclick={() => {
			userScrolled = false;
			scrollToBottom();
		}}
		class="absolute bottom-16 right-4 w-10 h-10 flex items-center justify-center bg-blue-600 hover:bg-blue-500 text-white rounded-full shadow-lg transition-colors z-20"
		aria-label="Scroll to bottom"
	>
		<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
		</svg>
	</button>
{/if}
