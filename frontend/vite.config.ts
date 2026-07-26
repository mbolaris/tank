import { configDefaults, defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    // Playwright owns browser specs; Vitest's default **/*.{test,spec}.*
    // discovery would otherwise import them as unit suites.
    exclude: [...configDefaults.exclude, 'e2e/**'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined

          if (/[\\/]node_modules[\\/](react-d3-tree|d3-hierarchy)[\\/]/.test(id)) {
            return 'tree-vendor'
          }
          if (/[\\/]node_modules[\\/](recharts|victory-vendor)[\\/]/.test(id)) {
            return 'charts-vendor'
          }
          if (/[\\/]node_modules[\\/](react|react-dom|react-router)[\\/]/.test(id)) {
            return 'react-vendor'
          }

          return undefined
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
