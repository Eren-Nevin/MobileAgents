import { sveltekit } from '@sveltejs/kit/vite';
import { SvelteKitPWA } from '@vite-pwa/sveltekit';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

const backendUrl = process.env.VITE_API_URL || 'http://localhost:8765';

console.log('Vite proxy target:', backendUrl);

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit(),
		SvelteKitPWA({
			registerType: 'autoUpdate',
			devOptions: {
				enabled: true
			},
			manifest: {
				name: 'Mate',
				short_name: 'Mate',
				description: 'Monitor and control AI agents running in tmux sessions',
				theme_color: '#1f2937',
				background_color: '#111827',
				display: 'standalone',
				orientation: 'portrait',
				scope: '/',
				start_url: '/',
				icons: [
					{
						src: '/icon-192.png',
						sizes: '192x192',
						type: 'image/png'
					},
					{
						src: '/icon-512.png',
						sizes: '512x512',
						type: 'image/png'
					},
					{
						src: '/icon-512.png',
						sizes: '512x512',
						type: 'image/png',
						purpose: 'maskable'
					}
				]
			},
			workbox: {
				globPatterns: ['**/*.{js,css,html,ico,png,svg,woff,woff2}'],
				runtimeCaching: [
					{
						urlPattern: /^https?:\/\/.*\/api\/.*/i,
						handler: 'NetworkFirst',
						options: {
							cacheName: 'api-cache',
							networkTimeoutSeconds: 10,
							expiration: {
								maxEntries: 50,
								maxAgeSeconds: 60 * 5 // 5 minutes
							}
						}
					}
				]
			}
		})
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
