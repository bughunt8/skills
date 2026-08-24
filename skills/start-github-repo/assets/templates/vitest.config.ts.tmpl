// Workers-aware Vitest configuration.
//
// IMPORTANT: the package is `@cloudflare/vitest-plugin` and the entry point is `cloudflareTest()`.
// It was formerly `@cloudflare/vitest-pool-workers` with `defineWorkersConfig`. Do not generate the
// old shape. To migrate an existing repo:
//   npx @cloudflare/codemods vitest:pool-workers-to-vitest-plugin
//
// Tests run inside the Workers runtime, so they can assert directly against KV, R2, D1 and Durable
// Object state. `test/tsconfig.json` must list "@cloudflare/vitest-plugin" in compilerOptions.types —
// that is what defines the `cloudflare:test` module.

import { defineConfig } from 'vitest/config';
import { cloudflareTest } from '@cloudflare/vitest-plugin';

export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: './wrangler.jsonc' },
      // A `miniflare` block here takes precedence over the Wrangler configuration.
      // miniflare: { kvNamespaces: ['CACHE'] },
    }),
  ],
  test: {
    include: ['test/**/*.{test,spec}.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['src/**/*.ts'],
      exclude: ['**/*.d.ts', 'src/**/*.test.ts'],
      // perFile means a single well-covered file cannot mask an untested one.
      thresholds: {
        perFile: true,
        lines: 80,
        functions: 80,
        branches: 75,
        statements: 80,
      },
    },
  },
});
