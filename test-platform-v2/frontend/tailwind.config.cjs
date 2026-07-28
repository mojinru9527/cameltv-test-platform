/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
        },
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        status: {
          success: {
            DEFAULT: "var(--color-status-success)",
            solid: "var(--color-status-success-solid)",
            muted: "var(--color-status-success-bg)",
            border: "var(--color-status-success-border)",
          },
          warning: {
            DEFAULT: "var(--color-status-warning)",
            solid: "var(--color-status-warning-solid)",
            muted: "var(--color-status-warning-bg)",
            border: "var(--color-status-warning-border)",
          },
          danger: {
            DEFAULT: "var(--color-status-danger)",
            solid: "var(--color-status-danger-solid)",
            muted: "var(--color-status-danger-bg)",
            border: "var(--color-status-danger-border)",
          },
          info: {
            DEFAULT: "var(--color-status-info)",
            solid: "var(--color-status-info-solid)",
            muted: "var(--color-status-info-bg)",
            border: "var(--color-status-info-border)",
          },
          accent: {
            DEFAULT: "var(--color-status-accent)",
            solid: "var(--color-status-accent-solid)",
            muted: "var(--color-status-accent-bg)",
            border: "var(--color-status-accent-border)",
          },
        },
        'muted-hc': 'var(--text-muted-high-contrast)',
        'border-hc': 'var(--border-high-contrast)',
        sidebar: {
          DEFAULT: "var(--sidebar-background)",
          foreground: "var(--sidebar-foreground)",
          primary: "var(--sidebar-primary)",
          "primary-foreground": "var(--sidebar-primary-foreground)",
          accent: "var(--sidebar-accent)",
          "accent-foreground": "var(--sidebar-accent-foreground)",
          border: "var(--sidebar-border)",
          ring: "var(--sidebar-ring)",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontSize: {
	        xs: '0.8125rem',   // 13px
	        sm: '0.9375rem',   // 15px
	        base: '1.0625rem', // 17px
	        lg: '1.1875rem',   // 19px
	        xl: '1.3125rem',   // 21px
	        '2xl': '1.625rem', // 26px
	      },
	      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          '"Helvetica Neue"',
          "Arial",
          '"Noto Sans"',
          '"PingFang SC"',
          '"Microsoft YaHei"',
          "sans-serif",
        ],
        heading: ["var(--font-heading)"],
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
    require("@tailwindcss/container-queries"),
  ],
}
