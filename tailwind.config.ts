import type { Config } from "tailwindcss";

// all in fixtures is set to tailwind v3 as interims solutions

const config: Config = {
    darkMode: ["class"],
    content: [
        "*.{js,ts,jsx,tsx,mdx}",
        "./templates/**/*.html",
        "./accounts/templates/**/*.html",
        "./empresas/templates/**/*.html",
        "./static/src/**/*.{js,ts}",
        "./**/*.py"
    ],
  theme: {
  	extend: {
                colors: {
                        primary: {
                                50: '#eff6ff',
                                100: '#dbeafe',
                                200: '#bfdbfe',
                                300: '#93c5fd',
                                400: '#60a5fa',
                                500: '#3b82f6',
                                600: '#2563eb',
                                700: '#1d4ed8',
                                800: '#1e40af',
                                900: '#1e3a8a',
                                DEFAULT: '#3b82f6',
                                foreground: '#ffffff'
                        },
                        accent: {
                                50: 'var(--color-accent-50)',
                                100: 'var(--color-accent-100)',
                                200: 'var(--color-accent-200)',
                                300: 'var(--color-accent-300)',
                                400: 'var(--color-accent-400)',
                                500: 'var(--color-accent-500)',
                                600: 'var(--color-accent-600)',
                                700: 'var(--color-accent-700)',
                                800: 'var(--color-accent-800)',
                                900: 'var(--color-accent-900)',
                                DEFAULT: 'var(--accent)',
                                light: 'var(--accent-light)',
                                dark: 'var(--accent-dark)',
                                foreground: 'var(--text-inverse)'
                        },
                        success: {
                                50: 'var(--color-success-50)',
                                100: 'var(--color-success-100)',
                                200: 'var(--color-success-200)',
                                300: 'var(--color-success-300)',
                                400: 'var(--color-success-400)',
                                500: 'var(--color-success-500)',
                                600: 'var(--color-success-600)',
                                700: 'var(--color-success-700)',
                                800: 'var(--color-success-800)',
                                900: 'var(--color-success-900)',
                                DEFAULT: 'var(--color-success-500)',
                                foreground: 'var(--text-inverse)'
                        },
                        warning: {
                                50: 'var(--color-warning-50)',
                                100: 'var(--color-warning-100)',
                                200: 'var(--color-warning-200)',
                                300: 'var(--color-warning-300)',
                                400: 'var(--color-warning-400)',
                                500: 'var(--color-warning-500)',
                                600: 'var(--color-warning-600)',
                                700: 'var(--color-warning-700)',
                                800: 'var(--color-warning-800)',
                                900: 'var(--color-warning-900)',
                                DEFAULT: 'var(--color-warning-500)',
                                foreground: 'var(--text-inverse)'
                        },
                        error: {
                                50: 'var(--color-error-50)',
                                100: 'var(--color-error-100)',
                                200: 'var(--color-error-200)',
                                300: 'var(--color-error-300)',
                                400: 'var(--color-error-400)',
                                500: 'var(--color-error-500)',
                                600: 'var(--color-error-600)',
                                700: 'var(--color-error-700)',
                                800: 'var(--color-error-800)',
                                900: 'var(--color-error-900)',
                                DEFAULT: 'var(--color-error-500)',
                                foreground: 'var(--text-inverse)'
                        }
                },
                fontFamily: {
                        sans: ['Inter', 'ui-sans-serif', 'system-ui']
                },
                borderRadius: {
                        lg: 'var(--radius)',
                        md: 'calc(var(--radius) - 2px)',
                        sm: 'calc(var(--radius) - 4px)'
                },
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [
        require("@tailwindcss/forms"),
        require("@tailwindcss/typography"),
        require("tailwindcss-animate")
  ],
};
export default config;
