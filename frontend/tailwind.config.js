export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      colors: {
        w: {
          bg:      '#080c14',
          surface: '#0d1117',
          card:    '#161b22',
          border:  '#21262d',
          border2: '#30363d',
          accent:  '#238636',
          blue:    '#1f6feb',
          text:    '#e6edf3',
          muted:   '#8b949e',
          dim:     '#484f58',
          yellow:  '#d29922',
          red:     '#da3633',
          green:   '#3fb950',
          purple:  '#8957e5',
        }
      },
      animation: {
        'fade-in':   'fadeIn 0.35s ease-out',
        'slide-up':  'slideUp 0.3s ease-out',
        'blink':     'blink 1.2s step-end infinite',
      },
      keyframes: {
        fadeIn:  { from: { opacity: 0 },                        to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(8px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        blink:   { '0%,100%': { opacity: 1 }, '50%': { opacity: 0 } },
      },
    },
  },
  plugins: [],
}
