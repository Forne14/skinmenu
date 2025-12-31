/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './config/templates/**/*.html',
    './pages/templates/**/*.html',
    './site_settings/templates/**/*.html',
    './search/templates/**/*.html',
    './**/*.py',
    './config/static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        // Theme tokens (semantic)
        bg: 'rgb(var(--bg) / <alpha-value>)',
        fg: 'rgb(var(--fg) / <alpha-value>)',
        surface: 'rgb(var(--surface) / <alpha-value>)',
        'surface-2': 'rgb(var(--surface-2) / <alpha-value>)',
        border: 'rgb(var(--border) / <alpha-value>)',
        muted: 'rgb(var(--muted) / <alpha-value>)',
        heading: 'rgb(var(--heading) / <alpha-value>)',
        accent: 'rgb(var(--accent) / <alpha-value>)',
        'accent-2': 'rgb(var(--accent-2) / <alpha-value>)',

        // Raw brand palette (occasional one-offs)
        skinmenu: {
          brown: '#786050',
          earth: '#3d2b1f',
          redbrown: '#4d2621',
          beige: '#b8a693',
          espresso: '#261b16',
          cream: '#e5e0d6',
        },
      },

      fontFamily: {
        sans: [
          '"Work Sans"',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Arial',
          'sans-serif',
        ],
        display: ['"Koh Santepheap"', '"Work Sans"', 'serif'],
      },

      letterSpacing: {
        tightish: '-0.025em',
      },

      borderRadius: {
        pill: 'var(--radius)',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
