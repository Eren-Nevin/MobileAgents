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
	// Also handle dim text (ESC[2m) which ansi-to-html ignores
	function ansiToHtml(text: string): string {
		try {
			// ansi-to-html consumes dim codes (\x1b[2m) but doesn't apply any styling
			// We need to insert markers before conversion, then convert markers to spans after

			let processed = text;

			// Insert markers around dim sections
			// \x1b[2m = dim start, \x1b[22m = dim end (normal intensity), \x1b[0m = full reset
			if (text.includes('\x1b[2m') || text.includes('\x1b[0;2m')) {
				// Replace dim codes with marker + dim code (so ansi-to-html still processes the sequence)
				processed = processed
					.replace(/\x1b\[0;2m/g, '{{DIM}}')      // combined reset+dim
					.replace(/\x1b\[2m/g, '{{DIM}}');        // standalone dim

				// Mark where dim ends - before \x1b[0m or \x1b[22m
				processed = processed
					.replace(/\x1b\[22m/g, '{{/DIM}}\x1b[22m')  // normal intensity
					.replace(/\x1b\[0m/g, '{{/DIM}}\x1b[0m');   // full reset
			}

			// Convert to HTML
			let html = ansiConverter.toHtml(processed);

			// Replace markers with opacity spans
			// Use a simple state machine to handle unbalanced markers
			let result = '';
			let inDim = false;

			const parts = html.split(/(\{\{DIM\}\}|\{\{\/DIM\}\})/);
			for (const part of parts) {
				if (part === '{{DIM}}') {
					if (!inDim) {
						result += '<span style="opacity:0.5">';
						inDim = true;
					}
				} else if (part === '{{/DIM}}') {
					if (inDim) {
						result += '</span>';
						inDim = false;
					}
				} else {
					result += part;
				}
			}

			// Close any unclosed dim span at end of line
			if (inDim) {
				result += '</span>';
			}

			return result;
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
