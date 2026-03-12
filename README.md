# KEEN

**Sharper Judgment. Faster Execution.**

KEEN is the landing page for a multi-agent operational intelligence platform that replicates McKinsey-grade private equity due diligence — compressing **4 weeks of work into 4 hours** through autonomous execution across live enterprise systems.

Built as part of the **TinyFish Accelerator (2026)**.

---

## ✨ Highlights

| Metric | Value |
|---|---|
| **Time compression** | 4 weeks → 4 hours (98% reduction) |
| **Cost efficiency** | $200K → $40K (80% savings) |
| **System access** | 15+ live enterprise sources |
| **Accuracy rate** | 99.7% validated output |

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | [React 18](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) |
| **Build tool** | [Vite 5](https://vitejs.dev/) |
| **Styling** | [Tailwind CSS 3](https://tailwindcss.com/) + CSS custom properties (dark/light themes) |
| **3D / WebGL** | [Three.js](https://threejs.org/) — interactive particle background with custom GLSL shaders |
| **Animations** | [GSAP](https://gsap.com/) — scroll reveals, text reveals, parallax, count-up counters |
| **Icons** | [Lucide React](https://lucide.dev/) |
| **Backend** | [Supabase](https://supabase.com/) |

---

## 🧩 Architecture

```
src/
├── App.tsx                   # Main application — all sections & data
├── main.tsx                  # React entry point with ThemeProvider
├── index.css                 # Design tokens, animations, dark/light themes
├── components/
│   ├── WebGLBackground.tsx   # Three.js particle field (scroll + mouse reactive)
│   ├── ScrollReveal.tsx      # Intersection Observer scroll animations
│   ├── TextReveal.tsx        # Per-character / per-word text animation
│   ├── ParallaxSection.tsx   # Scroll-driven parallax wrapper
│   ├── CountUp.tsx           # Animated number counter
│   ├── MagneticElement.tsx   # Cursor-follow magnetic hover effect
│   ├── ScrollProgressBar.tsx # Top-of-page scroll progress indicator
│   ├── ScrollIndicator.tsx   # Scroll-down hint indicator
│   ├── ThemeToggle.tsx       # Dark / light theme switch
│   ├── Loader.tsx            # Animated loading screen
│   ├── SmoothScroll.tsx      # Smooth scroll utility
│   └── HorizontalScroll.tsx  # Horizontal scroll section
├── context/
│   └── ThemeContext.tsx       # React context for theme state
├── hooks/
│   └── useScrollProgress.ts  # Scroll progress & mouse position hooks
└── shaders/
    └── background.ts         # GLSL vertex/fragment shaders for WebGL
```

---

## 📄 Page Sections

1. **Hero** — Full-screen intro with animated text reveal, WebGL particle background, and CTA buttons
2. **Performance Metrics** — Animated count-up statistics (time, cost, access, accuracy)
3. **Agent Architecture** — Three autonomous agents: *Research*, *Analysis*, *Delivery* — each with live status indicators
4. **Operational Capabilities** — Stateful execution, dynamic authentication, multi-agent coordination, browser orchestration
5. **Enterprise Integrations** — 15+ connected systems (Salesforce, NetSuite, SAP, Bloomberg, SEC EDGAR, etc.)
6. **Competitive Advantage** — 19–27 month technical moat positioning, target market, ROI breakdown

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** ≥ 18
- **npm** ≥ 9

### Install & Run

```bash
# Clone the repository
git clone https://github.com/your-org/keen.git
cd keen

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at **http://localhost:5173**.

### Other Commands

```bash
npm run build      # Production build
npm run preview    # Preview production build locally
npm run lint       # Run ESLint
npm run typecheck  # TypeScript type checking
```

---

## 🎨 Theming

KEEN supports **dark** and **light** themes, toggled via the sun/moon button in the navigation bar. Themes are implemented with CSS custom properties defined in `src/index.css` and managed through React context (`src/context/ThemeContext.tsx`).

| Token | Purpose |
|---|---|
| `--color-bg` | Page background |
| `--color-surface` | Card / section surfaces |
| `--color-text` | Primary text |
| `--color-text-secondary` | Secondary text |
| `--color-border` | Default borders |
| `--color-nav-solid` | Solid nav background on scroll |

---

## 🌐 Enterprise Integrations

KEEN connects to 15+ enterprise systems for live data extraction:

> Salesforce · NetSuite · SAP · Oracle · Dynamics · QuickBooks · HubSpot · Marketo · Bloomberg · CapIQ · PitchBook · SEC EDGAR · Sales Navigator · ZoomInfo · Crunchbase

---

## 📦 Build & Deployment

The production build uses **Vite** with manual chunk splitting for optimal loading:

- `three` → separate chunk
- `gsap` → separate chunk

```bash
npm run build
```

Output is written to `dist/`. Deploy to any static hosting (Vercel, Netlify, Cloudflare Pages, etc.).

---

## 📋 License

© 2026 KEEN — Backed by TinyFish Accelerator
