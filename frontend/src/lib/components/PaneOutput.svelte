<script lang="ts">
	import { onMount, tick } from 'svelte';
	import AnsiToHtml from 'ansi-to-html';

	interface Props {
		lines: string[];
		autoScroll?: boolean;
	}

	let { lines, autoScroll = true }: Props = $props();

	// ANSI to HTML converter with custom colors
	const ansiConverter = new AnsiToHtml({
		fg: '#e5e7eb', // gray-200
		bg: 'transparent',
		colors: {
			0: '#374151',  // black -> gray-700
			1: '#ef4444',  // red
			2: '#22c55e',  // green
			3: '#eab308',  // yellow
			4: '#3b82f6',  // blue
			5: '#a855f7',  // magenta
			6: '#06b6d4',  // cyan
			7: '#e5e7eb',  // white -> gray-200
			8: '#6b7280',  // bright black -> gray-500
			9: '#f87171',  // bright red
			10: '#4ade80', // bright green
			11: '#facc15', // bright yellow
			12: '#60a5fa', // bright blue
			13: '#c084fc', // bright magenta
			14: '#22d3ee', // bright cyan
			15: '#f9fafb', // bright white -> gray-50
		}
	});

	// Convert ANSI codes to HTML
	function ansiToHtml(text: string): string {
		try {
			return ansiConverter.toHtml(text);
		} catch {
			return text;
		}
	}

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
	<pre class="font-mono-output text-gray-200 whitespace-pre-wrap break-words">{#each trimmedLines as line, i}<span class="block hover:bg-white/5">{@html ansiToHtml(line) || '&nbsp;'}</span>{/each}</pre>
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
