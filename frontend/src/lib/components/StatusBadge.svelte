<script lang="ts">
	import type { PaneStatus } from '$lib/types';

	interface Props {
		status: PaneStatus;
		size?: 'sm' | 'md';
	}

	let { status, size = 'md' }: Props = $props();

	const statusConfig = {
		running: {
			color: 'bg-green-500',
			label: 'Running'
		},
		waiting_input: {
			color: 'bg-yellow-500',
			label: 'Waiting'
		},
		idle: {
			color: 'bg-gray-500',
			label: 'Idle'
		},
		exited: {
			color: 'bg-red-500',
			label: 'Exited'
		}
	};

	const config = $derived(statusConfig[status] || statusConfig.idle);
	const dotSize = $derived(size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5');
	const textSize = $derived(size === 'sm' ? 'text-xs' : 'text-sm');
</script>

<span class="inline-flex items-center gap-1.5 {textSize}">
	<span class="{dotSize} rounded-full {config.color} animate-pulse"></span>
	<span class="text-gray-300">{config.label}</span>
</span>
