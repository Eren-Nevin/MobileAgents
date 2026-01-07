<script lang="ts">
	import AnsiToHtml from 'ansi-to-html';

	interface Props {
		content: string;
		cursorX?: number; // If defined, show cursor at this column
	}

	let { content, cursorX }: Props = $props();

	// ANSI converter (shared instance across all Line components)
	const ansiConverter = new AnsiToHtml({
		fg: '#e5e7eb',
		bg: 'transparent',
		colors: {
			0: '#374151', 1: '#ef4444', 2: '#22c55e', 3: '#eab308',
			4: '#3b82f6', 5: '#a855f7', 6: '#06b6d4', 7: '#e5e7eb',
			8: '#6b7280', 9: '#f87171', 10: '#4ade80', 11: '#facc15',
			12: '#60a5fa', 13: '#c084fc', 14: '#22d3ee', 15: '#f9fafb',
		}
	});

	function convertAnsiToHtml(text: string): string {
		if (!text) return '&nbsp;';
		try {
			let processed = text;
			if (text.includes('\x1b[2m') || text.includes('\x1b[0;2m')) {
				processed = processed
					.replace(/\x1b\[0;2m/g, '{{DIM}}')
					.replace(/\x1b\[2m/g, '{{DIM}}')
					.replace(/\x1b\[22m/g, '{{/DIM}}\x1b[22m')
					.replace(/\x1b\[0m/g, '{{/DIM}}\x1b[0m');
			}

			let html = ansiConverter.toHtml(processed);

			let result = '';
			let inDim = false;
			const parts = html.split(/(\{\{DIM\}\}|\{\{\/DIM\}\})/);
			for (const part of parts) {
				if (part === '{{DIM}}') {
					if (!inDim) { result += '<span style="opacity:0.5">'; inDim = true; }
				} else if (part === '{{/DIM}}') {
					if (inDim) { result += '</span>'; inDim = false; }
				} else {
					result += part;
				}
			}
			if (inDim) result += '</span>';
			return result || '&nbsp;';
		} catch {
			return text || '&nbsp;';
		}
	}

	// Svelte action to update innerHTML only when content actually changes
	function htmlContent(node: HTMLElement, html: string) {
		let lastHtml = html;
		node.innerHTML = html;
		return {
			update(newHtml: string) {
				// Compare against what we last set, not innerHTML (browsers normalize HTML)
				if (lastHtml !== newHtml) {
					lastHtml = newHtml;
					node.innerHTML = newHtml;
				}
			}
		};
	}

	// Derive the HTML once from content
	const html = $derived(convertAnsiToHtml(content));
</script>

{#if cursorX !== undefined}
	<span class="block hover:bg-white/5 relative">
		<span use:htmlContent={html}></span>
		<span
			class="absolute top-0 h-full w-[2px] bg-green-400"
			style="left: {cursorX}ch"
		></span>
	</span>
{:else}
	<span class="block hover:bg-white/5" use:htmlContent={html}></span>
{/if}
