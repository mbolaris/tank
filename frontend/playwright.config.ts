import { defineConfig, devices } from '@playwright/test';

const isWindows = process.platform === 'win32';
// CI installs the backend into the runner's own interpreter rather than a
// venv, so it overrides this rather than carrying a fake .venv around.
const python =
    process.env.TANK_E2E_PYTHON ??
    (isWindows ? '..\\.venv\\Scripts\\python.exe' : '../.venv/bin/python');

/**
 * The first browser-level contract for the product surface. It intentionally
 * starts the real backend rather than mocking WebSocket state, so a passing
 * test exercises the application shell and its live connection lifecycle.
 */
export default defineConfig({
    testDir: './e2e',
    fullyParallel: false,
    forbidOnly: Boolean(process.env.CI),
    retries: process.env.CI ? 2 : 0,
    reporter: process.env.CI ? 'github' : 'list',
    use: {
        baseURL: 'http://127.0.0.1:5173',
        trace: 'on-first-retry',
    },
    projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
    webServer: [
        {
            command: `"${python}" ../main.py`,
            url: 'http://127.0.0.1:8000/api/worlds',
            timeout: 30_000,
            reuseExistingServer: !process.env.CI,
        },
        {
            command: 'npm run dev -- --host 127.0.0.1 --port 5173',
            url: 'http://127.0.0.1:5173',
            timeout: 30_000,
            reuseExistingServer: !process.env.CI,
        },
    ],
});
