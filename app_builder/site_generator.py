"""
SiteGenerator — HTML/React Site Generator for SintraPrime App Builder
=====================================================================
Generates full web apps using Tailwind CSS + DaisyUI.
Produces responsive, accessible HTML and React TSX files.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .app_types import AppSpec, Component, ComponentType, Page


# ---------------------------------------------------------------------------
# Tailwind / DaisyUI Theme Config
# ---------------------------------------------------------------------------

TAILWIND_CDN = """<script src="https://cdn.tailwindcss.com"></script>
<link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet" type="text/css"/>"""

INTER_FONT = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">"""

CHART_JS = """<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>"""


class SiteGenerator:
    """
    Generates HTML/React sites from AppSpec definitions.
    Uses Tailwind CSS + DaisyUI for styling.
    """

    THEMES = {
        "sintra": {"primary": "#1e40af", "secondary": "#7c3aed", "accent": "#0ea5e9"},
        "legal": {"primary": "#1e3a5f", "secondary": "#b45309", "accent": "#047857"},
        "financial": {"primary": "#065f46", "secondary": "#1e40af", "accent": "#b45309"},
        "minimal": {"primary": "#111827", "secondary": "#6b7280", "accent": "#3b82f6"},
    }

    def __init__(self):
        self._components_registry: Dict[ComponentType, str] = {}

    # ------------------------------------------------------------------
    # HTML Site Generation
    # ------------------------------------------------------------------

    def generate_html_site(self, spec: AppSpec) -> Dict[str, str]:
        """
        Generate a complete HTML site from an AppSpec.
        Returns dict of {filename: content}.
        """
        files: Dict[str, str] = {}

        # Global CSS
        files["styles.css"] = self._generate_global_css(spec)

        # Main JS
        files["app.js"] = self._generate_global_js(spec)

        # Generate each page
        for page in spec.pages:
            filename = "index.html" if page.route == "/" else f"{page.route.lstrip('/')}.html"
            files[filename] = self._generate_page_html(page, spec)

        # Generate 404
        files["404.html"] = self._generate_404(spec)

        # Sitemap
        files["sitemap.xml"] = self._generate_sitemap(spec)

        # robots.txt
        files["robots.txt"] = "User-agent: *\nAllow: /\n"

        return files

    def _generate_page_html(self, page: Page, spec: AppSpec) -> str:
        theme = self.THEMES.get(spec.theme, self.THEMES["sintra"])
        components_html = "\n".join(self.generate_component(c) for c in page.components)

        seo_title = page.title or f"{spec.name} - {page.name}"
        seo_desc = page.description or spec.seo.get("description", spec.description[:160])
        seo_kw = spec.seo.get("keywords", "")

        return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{seo_title}</title>
  <meta name="description" content="{seo_desc}"/>
  <meta name="keywords" content="{seo_kw}"/>
  <meta property="og:title" content="{seo_title}"/>
  <meta property="og:description" content="{seo_desc}"/>
  <meta property="og:type" content="website"/>
  {INTER_FONT}
  {TAILWIND_CDN}
  {CHART_JS}
  <link rel="stylesheet" href="/styles.css"/>
  <style>
    :root {{
      --sintra-primary: {theme["primary"]};
      --sintra-secondary: {theme["secondary"]};
      --sintra-accent: {theme["accent"]};
    }}
    body {{ font-family: 'Inter', sans-serif; }}
  </style>
</head>
<body class="min-h-screen bg-base-100">
{components_html}
<script src="/app.js"></script>
</body>
</html>"""

    def _generate_global_css(self, spec: AppSpec) -> str:
        theme = self.THEMES.get(spec.theme, self.THEMES["sintra"])
        return f"""/* SintraPrime Generated CSS - {spec.name} */
:root {{
  --primary: {theme["primary"]};
  --secondary: {theme["secondary"]};
  --accent: {theme["accent"]};
}}

.sintra-hero {{
  background: linear-gradient(135deg, {theme["primary"]} 0%, {theme["secondary"]} 100%);
}}

.sintra-card {{
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}}

.sintra-card:hover {{
  transform: translateY(-4px);
  box-shadow: 0 20px 40px rgba(0,0,0,0.12);
}}

.sintra-nav {{
  backdrop-filter: blur(10px);
  background: rgba(255,255,255,0.95);
}}

@media (max-width: 768px) {{
  .sintra-hero h1 {{ font-size: 2rem; }}
  .sintra-hero p {{ font-size: 1rem; }}
}}

/* Accessibility */
:focus-visible {{
  outline: 3px solid {theme["accent"]};
  outline-offset: 2px;
}}

.sr-only {{
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
}}
"""

    def _generate_global_js(self, spec: AppSpec) -> str:
        return f"""// SintraPrime App JS - {spec.name}
'use strict';

// Mobile nav toggle
document.addEventListener('DOMContentLoaded', function() {{
  const menuBtn = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  if (menuBtn && mobileMenu) {{
    menuBtn.addEventListener('click', () => {{
      mobileMenu.classList.toggle('hidden');
    }});
  }}

  // Form submissions
  document.querySelectorAll('form[data-ajax]').forEach(form => {{
    form.addEventListener('submit', async function(e) {{
      e.preventDefault();
      const data = Object.fromEntries(new FormData(form).entries());
      try {{
        const res = await fetch(form.action || '/api/submit', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify(data)
        }});
        const json = await res.json();
        if (json.success) {{
          const msg = form.querySelector('.success-msg');
          if (msg) msg.classList.remove('hidden');
          form.reset();
        }}
      }} catch(err) {{
        console.error('Form error:', err);
      }}
    }});
  }});

  // Charts (if Chart.js loaded)
  if (window.Chart) {{
    document.querySelectorAll('[data-chart]').forEach(canvas => {{
      const cfg = JSON.parse(canvas.dataset.chart || '{{}}');
      new Chart(canvas, cfg);
    }});
  }}
}});

// Utility functions
window.SintraPrime = {{
  notify: function(msg, type='info') {{
    const div = document.createElement('div');
    div.className = `alert alert-${{type}} fixed top-4 right-4 z-50 w-80 shadow-lg`;
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 4000);
  }},
  formatCurrency: function(amount) {{
    return new Intl.NumberFormat('en-US', {{style:'currency', currency:'USD'}}).format(amount);
  }},
  formatDate: function(d) {{
    return new Date(d).toLocaleDateString('en-US', {{year:'numeric',month:'long',day:'numeric'}});
  }}
}};
"""

    def _generate_404(self, spec: AppSpec) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Page Not Found - {spec.name}</title>
  {INTER_FONT}
  {TAILWIND_CDN}
</head>
<body class="min-h-screen flex items-center justify-center bg-base-100">
  <div class="text-center">
    <h1 class="text-9xl font-bold text-primary">404</h1>
    <p class="text-2xl mt-4 text-gray-600">Page Not Found</p>
    <a href="/" class="btn btn-primary mt-8">Go Home</a>
  </div>
</body>
</html>"""

    def _generate_sitemap(self, spec: AppSpec) -> str:
        urls = "\n".join(
            f"  <url><loc>https://example.com{page.route}</loc></url>"
            for page in spec.pages
        )
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>"""

    # ------------------------------------------------------------------
    # React TSX Generation
    # ------------------------------------------------------------------

    def generate_react_app(self, spec: AppSpec) -> Dict[str, str]:
        """Generate a complete React TSX app from an AppSpec."""
        files: Dict[str, str] = {}

        files["package.json"] = json.dumps({
            "name": spec.name.lower().replace(" ", "-"),
            "version": "1.0.0",
            "private": True,
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-router-dom": "^6.0.0",
                "@types/react": "^18.2.0",
                "tailwindcss": "^3.4.0",
                "daisyui": "^4.0.0",
                "chart.js": "^4.0.0",
                "react-chartjs-2": "^5.0.0",
            },
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview",
            },
            "devDependencies": {
                "vite": "^5.0.0",
                "@vitejs/plugin-react": "^4.0.0",
                "typescript": "^5.0.0",
            },
        }, indent=2)

        files["src/App.tsx"] = self._generate_react_app_tsx(spec)
        files["src/main.tsx"] = self._generate_react_main_tsx()
        files["tailwind.config.js"] = self._generate_tailwind_config(spec)
        files["index.html"] = self._generate_react_index_html(spec)

        for page in spec.pages:
            component_name = page.name.replace(" ", "")
            files[f"src/pages/{component_name}.tsx"] = self._generate_react_page(page, spec)

        files["src/components/Navbar.tsx"] = self._generate_react_navbar(spec)
        files["src/components/Footer.tsx"] = self._generate_react_footer(spec)

        return files

    def _generate_react_app_tsx(self, spec: AppSpec) -> str:
        routes = "\n".join(
            f'        <Route path="{page.route}" element={{<{page.name.replace(" ", "")} />}} />'
            for page in spec.pages
        )
        imports = "\n".join(
            f'import {page.name.replace(" ", "")} from "./pages/{page.name.replace(" ", "")}";'
            for page in spec.pages
        )
        return f"""import React from 'react';
import {{ BrowserRouter, Routes, Route }} from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
{imports}

function App() {{
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-base-100">
        <Navbar />
        <main className="flex-1">
          <Routes>
{routes}
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}}

export default App;
"""

    def _generate_react_main_tsx(self) -> str:
        return """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""

    def _generate_react_index_html(self, spec: AppSpec) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{spec.name}</title>
  <meta name="description" content="{spec.seo.get('description', spec.description[:160])}"/>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>"""

    def _generate_tailwind_config(self, spec: AppSpec) -> str:
        theme = self.THEMES.get(spec.theme, self.THEMES["sintra"])
        return f"""/** @type {{import('tailwindcss').Config}} */
export default {{
  content: ['./index.html', './src/**/*.{{ts,tsx}}'],
  theme: {{
    extend: {{
      colors: {{
        primary: '{theme["primary"]}',
        secondary: '{theme["secondary"]}',
        accent: '{theme["accent"]}',
      }},
      fontFamily: {{
        sans: ['Inter', 'sans-serif'],
      }},
    }},
  }},
  plugins: [require('daisyui')],
  daisyui: {{
    themes: ['light', 'dark'],
  }},
}};
"""

    def _generate_react_navbar(self, spec: AppSpec) -> str:
        nav_links = "\n".join(
            f'          <li><a href="{page.route}" className="hover:text-primary font-medium">'
            f'{page.name}</a></li>'
            for page in spec.pages[:5]
        )
        return f"""import React from 'react';

export default function Navbar() {{
  return (
    <nav className="navbar bg-base-100 shadow-md sticky top-0 z-50">
      <div className="navbar-start">
        <div className="dropdown">
          <label tabIndex={{0}} className="btn btn-ghost lg:hidden">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={{2}} d="M4 6h16M4 12h8m-8 6h16"/>
            </svg>
          </label>
          <ul tabIndex={{0}} className="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
{nav_links}
          </ul>
        </div>
        <a href="/" className="text-xl font-bold text-primary">{spec.name}</a>
      </div>
      <div className="navbar-center hidden lg:flex">
        <ul className="menu menu-horizontal px-1">
{nav_links}
        </ul>
      </div>
      <div className="navbar-end">
        <a href="/contact" className="btn btn-primary btn-sm">Get Started</a>
      </div>
    </nav>
  );
}}
"""

    def _generate_react_footer(self, spec: AppSpec) -> str:
        return f"""import React from 'react';

export default function Footer() {{
  return (
    <footer className="footer footer-center p-10 bg-base-300 text-base-content">
      <div>
        <p className="font-bold text-lg">{spec.name}</p>
        <p>{spec.description[:80]}</p>
        <p>© {{new Date().getFullYear()}} {spec.name}. All rights reserved.</p>
      </div>
    </footer>
  );
}}
"""

    def _generate_react_page(self, page: Page, spec: AppSpec) -> str:
        component_name = page.name.replace(" ", "")
        body = f"""  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-primary mb-6">{page.name}</h1>
      <p className="text-gray-600">{page.description or f"Welcome to {page.name}"}</p>
    </div>
  );"""
        return f"""import React from 'react';

export default function {component_name}() {{
{body}
}}
"""

    # ------------------------------------------------------------------
    # Component Generation
    # ------------------------------------------------------------------

    def generate_component(self, component: Component) -> str:
        """Generate HTML for a single component."""
        generators = {
            ComponentType.NAVBAR: self._gen_navbar,
            ComponentType.HERO: self._gen_hero,
            ComponentType.FOOTER: self._gen_footer,
            ComponentType.FORM: self._gen_form,
            ComponentType.TABLE: self._gen_table,
            ComponentType.CARD: self._gen_card,
            ComponentType.CHART: self._gen_chart,
            ComponentType.STAT: self._gen_stat,
            ComponentType.SIDEBAR: self._gen_sidebar,
            ComponentType.BUTTON: self._gen_button,
            ComponentType.MODAL: self._gen_modal,
            ComponentType.ALERT: self._gen_alert,
            ComponentType.TIMELINE: self._gen_timeline,
            ComponentType.CALENDAR: self._gen_calendar,
            ComponentType.FILE_UPLOAD: self._gen_file_upload,
            ComponentType.BADGE: self._gen_badge,
        }
        ctype = component.type
        if isinstance(ctype, str):
            try:
                ctype = ComponentType(ctype)
            except ValueError:
                return f"<!-- Unknown component: {ctype} -->"
        gen = generators.get(ctype, lambda c: f"<!-- Component: {ctype} -->")
        return gen(component)

    def _gen_navbar(self, c: Component) -> str:
        title = c.props.get("title", "SintraPrime")
        return f"""<nav class="navbar bg-base-100 shadow-md sticky top-0 z-50 sintra-nav">
  <div class="navbar-start">
    <div class="dropdown">
      <label tabindex="0" class="btn btn-ghost lg:hidden" id="mobile-menu-btn" aria-label="Open menu">☰</label>
      <ul id="mobile-menu" tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52 hidden">
        <li><a href="/">Home</a></li>
        <li><a href="/practice-areas">Services</a></li>
        <li><a href="/contact">Contact</a></li>
      </ul>
    </div>
    <a class="btn btn-ghost text-xl font-bold text-primary" href="/">{title}</a>
  </div>
  <div class="navbar-center hidden lg:flex">
    <ul class="menu menu-horizontal px-1">
      <li><a href="/" class="font-medium hover:text-primary">Home</a></li>
      <li><a href="/practice-areas" class="font-medium hover:text-primary">Services</a></li>
      <li><a href="/contact" class="font-medium hover:text-primary">Contact</a></li>
    </ul>
  </div>
  <div class="navbar-end">
    <a href="/contact" class="btn btn-primary btn-sm">Get Started</a>
  </div>
</nav>"""

    def _gen_hero(self, c: Component) -> str:
        title = c.props.get("title", "Welcome")
        subtitle = c.props.get("subtitle", "Professional Services")
        cta = c.props.get("cta", "Get Started")
        cta_link = c.props.get("cta_link", "/contact")
        return f"""<section class="hero min-h-[80vh] sintra-hero text-white" role="banner">
  <div class="hero-content text-center max-w-4xl mx-auto px-4">
    <div>
      <h1 class="text-5xl lg:text-7xl font-bold mb-6 leading-tight">{title}</h1>
      <p class="text-xl lg:text-2xl mb-10 opacity-90 max-w-2xl mx-auto">{subtitle}</p>
      <div class="flex flex-col sm:flex-row gap-4 justify-center">
        <a href="{cta_link}" class="btn btn-white btn-lg text-primary font-bold shadow-lg hover:scale-105 transition">{cta}</a>
        <a href="/contact" class="btn btn-outline btn-white btn-lg">Learn More</a>
      </div>
    </div>
  </div>
</section>"""

    def _gen_footer(self, c: Component) -> str:
        firm = c.props.get("firm_name", "SintraPrime")
        return f"""<footer class="footer footer-center p-10 bg-base-300 text-base-content" role="contentinfo">
  <div class="grid grid-cols-1 md:grid-cols-3 gap-8 text-left w-full max-w-6xl mx-auto">
    <div>
      <h3 class="footer-title">{firm}</h3>
      <p class="text-sm text-gray-600">Professional legal and financial services powered by AI.</p>
    </div>
    <div>
      <h3 class="footer-title">Quick Links</h3>
      <a href="/" class="link link-hover">Home</a>
      <a href="/practice-areas" class="link link-hover">Services</a>
      <a href="/contact" class="link link-hover">Contact</a>
    </div>
    <div>
      <h3 class="footer-title">Legal</h3>
      <a href="/privacy" class="link link-hover">Privacy Policy</a>
      <a href="/terms" class="link link-hover">Terms of Service</a>
    </div>
  </div>
  <div class="border-t border-base-content/10 w-full mt-8 pt-8">
    <p>© {'{new Date().getFullYear()}'} {firm}. All rights reserved. | Built with SintraPrime</p>
  </div>
</footer>"""

    def _gen_form(self, c: Component) -> str:
        form_type = c.props.get("form_type", "contact")
        if form_type == "legal_intake":
            return self.generate_legal_intake_form("General", [])
        return self.generate_legal_intake_form("Contact", ["name", "email", "message"])

    def _gen_table(self, c: Component) -> str:
        data_type = c.props.get("data_type", "items")
        return f"""<div class="overflow-x-auto rounded-xl shadow">
  <table class="table table-zebra w-full" role="grid" aria-label="{data_type} table">
    <thead class="bg-primary text-white">
      <tr>
        <th scope="col">ID</th>
        <th scope="col">Name</th>
        <th scope="col">Status</th>
        <th scope="col">Date</th>
        <th scope="col">Actions</th>
      </tr>
    </thead>
    <tbody id="{data_type}-table-body">
      <tr class="hover">
        <td>001</td>
        <td>Sample {data_type.title()}</td>
        <td><span class="badge badge-success">Active</span></td>
        <td>{'{new Date().toLocaleDateString()}'}</td>
        <td>
          <button class="btn btn-xs btn-ghost" aria-label="View">View</button>
          <button class="btn btn-xs btn-ghost text-error" aria-label="Delete">Delete</button>
        </td>
      </tr>
    </tbody>
  </table>
</div>"""

    def _gen_card(self, c: Component) -> str:
        variant = c.props.get("variant", "default")
        cards = {
            "practice_area": self._practice_area_cards(),
            "attorney_bio": self._attorney_bio_cards(),
            "feature": self._feature_cards(),
        }
        return cards.get(variant, self._feature_cards())

    def _practice_area_cards(self) -> str:
        areas = [
            ("⚖️", "Estate Planning", "Wills, trusts, and estate administration to protect your legacy."),
            ("🏛️", "Trust Law", "Revocable and irrevocable trusts, trust administration and litigation."),
            ("📋", "Probate", "Guiding estates through the probate process efficiently."),
            ("🤝", "Business Law", "Formation, contracts, partnerships, and corporate governance."),
            ("🏠", "Real Estate", "Residential and commercial real estate transactions."),
            ("⚡", "Debt Settlement", "Negotiating settlements and protecting client financial interests."),
        ]
        cards_html = "\n".join(f"""    <div class="card bg-base-100 shadow-xl sintra-card">
      <div class="card-body">
        <div class="text-4xl mb-4">{icon}</div>
        <h2 class="card-title text-primary">{name}</h2>
        <p class="text-gray-600">{desc}</p>
        <div class="card-actions justify-end mt-4">
          <a href="/contact" class="btn btn-primary btn-sm">Learn More</a>
        </div>
      </div>
    </div>""" for icon, name, desc in areas)
        return f"""<section class="py-16 px-4 bg-base-200">
  <div class="max-w-6xl mx-auto">
    <h2 class="text-4xl font-bold text-center text-primary mb-12">Our Practice Areas</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
{cards_html}
    </div>
  </div>
</section>"""

    def _attorney_bio_cards(self) -> str:
        return """<section class="py-16 px-4">
  <div class="max-w-6xl mx-auto">
    <h2 class="text-4xl font-bold text-center text-primary mb-12">Our Team</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
      <div class="card bg-base-100 shadow-xl sintra-card">
        <figure class="px-10 pt-10">
          <div class="avatar placeholder">
            <div class="bg-primary text-white rounded-full w-24 text-3xl">
              <span>JD</span>
            </div>
          </div>
        </figure>
        <div class="card-body text-center">
          <h2 class="card-title justify-center">Jane Doe, Esq.</h2>
          <p class="text-primary font-medium">Managing Partner</p>
          <p class="text-gray-600 text-sm">20+ years in estate planning and trust law. Bar-certified in CA, NY.</p>
          <div class="flex justify-center gap-2 mt-2">
            <span class="badge badge-outline">Estate Planning</span>
            <span class="badge badge-outline">Trust Law</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>"""

    def _feature_cards(self) -> str:
        return """<section class="py-16 px-4">
  <div class="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
    <div class="card bg-base-100 shadow-lg sintra-card">
      <div class="card-body">
        <h2 class="card-title text-primary">🔒 Secure</h2>
        <p>Bank-grade security for all your sensitive documents and data.</p>
      </div>
    </div>
    <div class="card bg-base-100 shadow-lg sintra-card">
      <div class="card-body">
        <h2 class="card-title text-primary">⚡ Fast</h2>
        <p>Get answers and take action quickly with AI-powered assistance.</p>
      </div>
    </div>
    <div class="card bg-base-100 shadow-lg sintra-card">
      <div class="card-body">
        <h2 class="card-title text-primary">🤖 Smart</h2>
        <p>Intelligent automation that learns your preferences over time.</p>
      </div>
    </div>
  </div>
</section>"""

    def _gen_chart(self, c: Component) -> str:
        chart_type = c.props.get("chart_type", "line")
        canvas_id = f"chart-{chart_type}-{id(c)}"
        return f"""<div class="card bg-base-100 shadow-xl p-6">
  <h3 class="text-lg font-bold text-primary mb-4">Analytics Overview</h3>
  <canvas id="{canvas_id}" data-chart='{{"type":"{chart_type}","data":{{"labels":["Jan","Feb","Mar","Apr","May","Jun"],"datasets":[{{"label":"Data","data":[12,19,3,5,2,3],"borderColor":"#1e40af","backgroundColor":"rgba(30,64,175,0.1)","fill":true}}]}},"options":{{"responsive":true,"plugins":{{"legend":{{"position":"top"}}}}}}}}'
    aria-label="{chart_type} chart" role="img"></canvas>
</div>"""

    def _gen_stat(self, c: Component) -> str:
        metrics = c.props.get("metrics", ["total", "active", "pending"])
        stats_html = "\n".join(f"""  <div class="stat">
    <div class="stat-title">{m.replace('_', ' ').title()}</div>
    <div class="stat-value text-primary">—</div>
    <div class="stat-desc">Updated in real-time</div>
  </div>""" for m in metrics)
        return f"""<div class="stats stats-vertical lg:stats-horizontal shadow w-full">
{stats_html}
</div>"""

    def _gen_sidebar(self, c: Component) -> str:
        return """<div class="drawer lg:drawer-open">
  <input id="sidebar-drawer" type="checkbox" class="drawer-toggle" aria-label="Toggle sidebar"/>
  <div class="drawer-content flex flex-col">
    <label for="sidebar-drawer" class="btn btn-primary drawer-button lg:hidden m-4">☰ Menu</label>
    <main class="p-6 flex-1">
      <!-- Page content goes here -->
    </main>
  </div>
  <div class="drawer-side">
    <label for="sidebar-drawer" class="drawer-overlay" aria-label="Close sidebar"></label>
    <ul class="menu p-4 w-64 min-h-full bg-base-200 text-base-content gap-1">
      <li class="menu-title"><span>Navigation</span></li>
      <li><a href="/dashboard" class="active">📊 Dashboard</a></li>
      <li><a href="/matters">⚖️ Matters</a></li>
      <li><a href="/documents">📄 Documents</a></li>
      <li><a href="/calendar">📅 Calendar</a></li>
      <li><a href="/billing">💰 Billing</a></li>
      <li class="mt-auto"><a href="/settings">⚙️ Settings</a></li>
    </ul>
  </div>
</div>"""

    def _gen_button(self, c: Component) -> str:
        label = c.props.get("label", "Click Me")
        href = c.props.get("href", "#")
        variant = c.props.get("variant", "primary")
        return f'<a href="{href}" class="btn btn-{variant}">{label}</a>'

    def _gen_modal(self, c: Component) -> str:
        modal_id = c.props.get("id", "modal-1")
        title = c.props.get("title", "Confirm Action")
        return f"""<dialog id="{modal_id}" class="modal" role="dialog" aria-labelledby="{modal_id}-title">
  <div class="modal-box">
    <h3 class="font-bold text-lg" id="{modal_id}-title">{title}</h3>
    <p class="py-4">Are you sure you want to proceed?</p>
    <div class="modal-action">
      <form method="dialog">
        <button class="btn btn-ghost">Cancel</button>
        <button class="btn btn-primary">Confirm</button>
      </form>
    </div>
  </div>
</dialog>"""

    def _gen_alert(self, c: Component) -> str:
        alert_type = c.props.get("type", "info")
        message = c.props.get("message", "This is an informational message.")
        icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
        icon = icons.get(alert_type, "ℹ️")
        return f"""<div class="alert alert-{alert_type}" role="alert">
  <span>{icon} {message}</span>
</div>"""

    def _gen_timeline(self, c: Component) -> str:
        return """<ul class="timeline timeline-vertical">
  <li>
    <div class="timeline-start">2024-01</div>
    <div class="timeline-middle"><div class="w-4 h-4 rounded-full bg-primary"></div></div>
    <div class="timeline-end timeline-box">Matter Opened</div>
    <hr/>
  </li>
  <li>
    <hr/>
    <div class="timeline-start">2024-03</div>
    <div class="timeline-middle"><div class="w-4 h-4 rounded-full bg-primary"></div></div>
    <div class="timeline-end timeline-box">Documents Filed</div>
    <hr/>
  </li>
  <li>
    <hr/>
    <div class="timeline-start">2024-06</div>
    <div class="timeline-middle"><div class="w-4 h-4 rounded-full bg-success"></div></div>
    <div class="timeline-end timeline-box">Resolved</div>
  </li>
</ul>"""

    def _gen_calendar(self, c: Component) -> str:
        return """<div class="card bg-base-100 shadow-xl">
  <div class="card-body">
    <h3 class="card-title text-primary">📅 Calendar</h3>
    <div id="calendar-grid" class="grid grid-cols-7 gap-1 text-center text-sm">
      <div class="font-bold text-gray-500">Sun</div>
      <div class="font-bold text-gray-500">Mon</div>
      <div class="font-bold text-gray-500">Tue</div>
      <div class="font-bold text-gray-500">Wed</div>
      <div class="font-bold text-gray-500">Thu</div>
      <div class="font-bold text-gray-500">Fri</div>
      <div class="font-bold text-gray-500">Sat</div>
    </div>
    <p class="text-xs text-gray-500 mt-2">Calendar powered by SintraPrime</p>
  </div>
</div>"""

    def _gen_file_upload(self, c: Component) -> str:
        return """<div class="card bg-base-100 shadow border-2 border-dashed border-primary/30 hover:border-primary transition">
  <div class="card-body items-center text-center">
    <div class="text-5xl mb-4">📁</div>
    <h3 class="text-lg font-bold text-primary">Upload Document</h3>
    <p class="text-gray-500 text-sm mb-4">Drag and drop files here or click to browse</p>
    <input type="file" class="file-input file-input-bordered file-input-primary w-full max-w-xs" 
           accept=".pdf,.doc,.docx,.jpg,.png" aria-label="Upload file"/>
    <p class="text-xs text-gray-400 mt-2">Supported: PDF, DOC, DOCX, JPG, PNG — Max 25MB</p>
  </div>
</div>"""

    def _gen_badge(self, c: Component) -> str:
        label = c.props.get("label", "Badge")
        variant = c.props.get("variant", "primary")
        return f'<span class="badge badge-{variant}">{label}</span>'

    # ------------------------------------------------------------------
    # Specialized Page Generators
    # ------------------------------------------------------------------

    def generate_landing_page(
        self,
        title: str,
        subtitle: str,
        features: List[str],
        cta: str = "Get Started",
    ) -> str:
        """Generate a marketing landing page."""
        feature_cards = "\n".join(
            f"""    <div class="card bg-base-100 shadow-lg sintra-card">
      <div class="card-body">
        <h3 class="card-title text-primary">✓ {f.replace('_', ' ').title()}</h3>
        <p class="text-gray-600">Powerful {f.replace('_', ' ')} built in.</p>
      </div>
    </div>"""
            for f in features[:6]
        )
        return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <meta name="description" content="{subtitle[:160]}"/>
  {INTER_FONT}
  {TAILWIND_CDN}
  <style>body {{font-family:'Inter',sans-serif;}}.sintra-hero{{background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);}}</style>
</head>
<body class="min-h-screen bg-base-100">
  <nav class="navbar bg-base-100 shadow sticky top-0 z-50">
    <div class="navbar-start">
      <a class="btn btn-ghost text-xl font-bold text-primary" href="/">{title}</a>
    </div>
    <div class="navbar-end">
      <a href="#features" class="btn btn-ghost">Features</a>
      <a href="#contact" class="btn btn-primary btn-sm">{cta}</a>
    </div>
  </nav>

  <section class="hero min-h-[85vh] sintra-hero text-white">
    <div class="hero-content text-center max-w-5xl mx-auto px-4">
      <div>
        <h1 class="text-6xl font-bold mb-6 leading-tight">{title}</h1>
        <p class="text-2xl mb-10 opacity-90 max-w-3xl mx-auto">{subtitle}</p>
        <a href="#features" class="btn btn-white btn-lg text-primary font-bold shadow-xl">{cta}</a>
      </div>
    </div>
  </section>

  <section id="features" class="py-20 px-4 bg-base-200">
    <div class="max-w-6xl mx-auto">
      <h2 class="text-4xl font-bold text-center text-primary mb-12">Features</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
{feature_cards}
      </div>
    </div>
  </section>

  <section id="contact" class="py-20 px-4">
    <div class="max-w-2xl mx-auto text-center">
      <h2 class="text-4xl font-bold text-primary mb-6">Ready to Get Started?</h2>
      <p class="text-gray-600 mb-8">Join thousands of professionals already using {title}.</p>
      <a href="/contact" class="btn btn-primary btn-lg">{cta}</a>
    </div>
  </section>

  <footer class="footer footer-center p-6 bg-base-300 text-base-content">
    <p>© 2026 {title}. All rights reserved. | Built with SintraPrime</p>
  </footer>
</body>
</html>"""

    def generate_legal_intake_form(self, practice_area: str, fields: List[str]) -> str:
        """Generate a legal client intake form."""
        default_fields = [
            ("Full Name", "text", "full_name", "Your full legal name"),
            ("Email Address", "email", "email", "your@email.com"),
            ("Phone Number", "tel", "phone", "(555) 000-0000"),
            ("City / State", "text", "location", "Newark, NJ"),
            ("Describe Your Legal Matter", "textarea", "description", "Please describe your situation in detail..."),
        ]
        fields_html = "\n".join(
            f"""      <div class="form-control">
        <label class="label" for="{fid}"><span class="label-text font-medium">{label}</span></label>
        {'<textarea class="textarea textarea-bordered h-32" id="'+fid+'" name="'+fid+'" placeholder="'+placeholder+'" required></textarea>' if ftype == "textarea" else f'<input type="{ftype}" class="input input-bordered" id="{fid}" name="{fid}" placeholder="{placeholder}" required/>'}
      </div>"""
            for label, ftype, fid, placeholder in default_fields
        )
        return f"""<section class="py-16 px-4 bg-base-200" id="intake-form">
  <div class="max-w-2xl mx-auto">
    <h2 class="text-3xl font-bold text-primary text-center mb-8">Free {practice_area} Consultation</h2>
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <form action="/api/intake" method="POST" data-ajax class="space-y-4">
          <input type="hidden" name="practice_area" value="{practice_area}"/>
{fields_html}
          <div class="form-control mt-6">
            <button type="submit" class="btn btn-primary btn-lg w-full">
              Submit — Free Consultation
            </button>
          </div>
          <div class="success-msg hidden alert alert-success">
            ✅ Thank you! We'll contact you within 24 hours.
          </div>
          <p class="text-xs text-gray-500 text-center">
            By submitting this form, you agree to our privacy policy. 
            Attorney-client privilege applies. Confidential.
          </p>
        </form>
      </div>
    </div>
  </div>
</section>"""

    def generate_dashboard(self, data_schema: Dict[str, Any], charts: List[str]) -> str:
        """Generate an analytics dashboard HTML."""
        chart_canvases = "\n".join(
            f'  <canvas id="chart-{i}" class="rounded-xl" aria-label="{chart} chart" role="img"></canvas>'
            for i, chart in enumerate(charts)
        )
        return f"""<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
  <div class="stats stats-vertical shadow col-span-3">
    <div class="stat"><div class="stat-title">Total Records</div><div class="stat-value text-primary">—</div></div>
    <div class="stat"><div class="stat-title">Active</div><div class="stat-value text-success">—</div></div>
    <div class="stat"><div class="stat-title">Pending</div><div class="stat-value text-warning">—</div></div>
  </div>
  <div class="col-span-2 card bg-base-100 shadow-xl p-6">
    <h3 class="font-bold text-primary mb-4">Overview</h3>
{chart_canvases}
  </div>
  <div class="card bg-base-100 shadow-xl p-6">
    <h3 class="font-bold text-primary mb-4">Recent Activity</h3>
    <ul class="space-y-3" aria-label="Recent activity">
      <li class="flex items-center gap-2"><span class="badge badge-success">New</span> <span class="text-sm">Record added</span></li>
      <li class="flex items-center gap-2"><span class="badge badge-warning">Updated</span> <span class="text-sm">Record modified</span></li>
    </ul>
  </div>
</div>"""
