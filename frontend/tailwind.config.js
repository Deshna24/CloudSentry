/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: '#0a0f1a', soft: '#0d1422' },
        panel: '#111a2b',
        raised: '#17233a',
        line: '#233250',
        ink: '#e8eef8',
        mute: '#93a3bd',
        dim: '#5f708c',
        brand: '#5ab0ff',
        ok: '#34d399',
        warn: '#fbbf24',
        hot: '#fb923c',
        crit: '#f87171',
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
};
