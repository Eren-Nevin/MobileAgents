import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

const backendUrl = process.env.VITE_API_URL || 'http://localhost:8765';

console.log('Vite proxy target:', backendUrl);

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit()
	],
	server: {
		host: '0.0.0.0', // Listen on all interfaces for mobile access
		port: parseInt(process.env.VITE_PORT || '5678'),
		strictPort: true,
		proxy: {
			'/api': {
				target: backendUrl,
				changeOrigin: true,
				secure: false
			},
			'/ws': {
				target: backendUrl,
				changeOrigin: true,
				ws: true,
				secure: false
			}
		}
	}
});
