"""
theme_system.py — Twin-inspired Theme System for SintraPrime

Based on twin's server/palette.cpp and server/ini.cpp with theme.ini support.
Provides named color themes, INI-based config, CSS export, and accessibility checking.
"""

import configparser
import logging
import math
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Color utilities ──────────────────────────────────────────────────────────

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color (#RRGGBB or RRGGBB) to (r, g, b) tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"Invalid hex color: {hex_color!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (r, g, b) to #RRGGBB string."""
    return f"#{r:02x}{g:02x}{b:02x}"


def rgb_to_ansi256(r: int, g: int, b: int) -> int:
    """Map an RGB color to the nearest ANSI 256-color index."""
    # Grayscale ramp: indices 232-255
    if r == g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return round((r - 8) / 247 * 24) + 232
    # 6x6x6 color cube: indices 16-231
    ri = round(r / 255 * 5)
    gi = round(g / 255 * 5)
    bi = round(b / 255 * 5)
    return 16 + 36 * ri + 6 * gi + bi


def ansi_truecolor_fg(r: int, g: int, b: int) -> str:
    """24-bit truecolor foreground escape."""
    return f"\033[38;2;{r};{g};{b}m"


def ansi_truecolor_bg(r: int, g: int, b: int) -> str:
    """24-bit truecolor background escape."""
    return f"\033[48;2;{r};{g};{b}m"


def ansi_256_fg(index: int) -> str:
    return f"\033[38;5;{index}m"


def ansi_256_bg(index: int) -> str:
    return f"\033[48;5;{index}m"


def relative_luminance(r: int, g: int, b: int) -> float:
    """
    Calculate relative luminance for WCAG contrast ratio.
    See: https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
    """
    def linearize(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """
    Calculate WCAG contrast ratio between two colors.

    Returns:
        Ratio from 1:1 (no contrast) to 21:1 (max contrast).
    """
    l1 = relative_luminance(*rgb1)
    l2 = relative_luminance(*rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def is_accessible(fg: Tuple[int, int, int], bg: Tuple[int, int, int],
                  level: str = "AA") -> bool:
    """
    Check if fg/bg color combination meets WCAG accessibility standard.

    Args:
        fg: Foreground RGB.
        bg: Background RGB.
        level: "AA" (4.5:1) or "AAA" (7:1).

    Returns:
        True if contrast ratio meets the required level.
    """
    ratio = contrast_ratio(fg, bg)
    threshold = 7.0 if level == "AAA" else 4.5
    return ratio >= threshold


# ─── ColorTheme ───────────────────────────────────────────────────────────────

@dataclass
class ColorTheme:
    """
    Complete color theme for all UI elements.
    Inspired by twin's theme.ini palette system.

    Colors are stored as (R, G, B) tuples.
    """
    name: str

    # Window chrome
    title_fg: Tuple[int, int, int] = (255, 255, 255)
    title_bg: Tuple[int, int, int] = (30, 80, 180)
    title_focused_fg: Tuple[int, int, int] = (255, 255, 255)
    title_focused_bg: Tuple[int, int, int] = (0, 100, 220)
    border_fg: Tuple[int, int, int] = (160, 160, 160)
    border_focused_fg: Tuple[int, int, int] = (80, 160, 255)

    # Content area
    content_fg: Tuple[int, int, int] = (220, 220, 220)
    content_bg: Tuple[int, int, int] = (20, 20, 30)

    # Widgets
    widget_header_fg: Tuple[int, int, int] = (255, 255, 255)
    widget_header_bg: Tuple[int, int, int] = (40, 40, 80)
    button_fg: Tuple[int, int, int] = (0, 0, 0)
    button_bg: Tuple[int, int, int] = (80, 150, 255)
    button_hover_bg: Tuple[int, int, int] = (100, 180, 255)

    # Status indicators
    status_ok: Tuple[int, int, int] = (0, 200, 80)
    status_warn: Tuple[int, int, int] = (220, 170, 0)
    status_error: Tuple[int, int, int] = (220, 50, 50)
    status_info: Tuple[int, int, int] = (60, 160, 255)

    # Menu bar
    menubar_fg: Tuple[int, int, int] = (200, 200, 255)
    menubar_bg: Tuple[int, int, int] = (30, 30, 80)
    menu_selected_fg: Tuple[int, int, int] = (255, 255, 255)
    menu_selected_bg: Tuple[int, int, int] = (80, 80, 180)

    # Progress bars
    progress_fg: Tuple[int, int, int] = (0, 150, 255)
    progress_bg: Tuple[int, int, int] = (40, 40, 60)

    # Log viewer
    log_error_fg: Tuple[int, int, int] = (220, 80, 80)
    log_warn_fg: Tuple[int, int, int] = (220, 170, 0)
    log_info_fg: Tuple[int, int, int] = (100, 200, 100)
    log_debug_fg: Tuple[int, int, int] = (100, 100, 200)

    # Notifications
    notif_info_bg: Tuple[int, int, int] = (0, 80, 180)
    notif_warn_bg: Tuple[int, int, int] = (160, 100, 0)
    notif_error_bg: Tuple[int, int, int] = (160, 0, 0)
    notif_success_bg: Tuple[int, int, int] = (0, 120, 0)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def ansi_content(self) -> str:
        """Return ANSI codes for content area colors."""
        r, g, b = self.content_fg
        br, bg_, bb = self.content_bg
        return ansi_truecolor_fg(r, g, b) + ansi_truecolor_bg(br, bg_, bb)

    def ansi_title(self, focused: bool = False) -> str:
        """Return ANSI codes for title bar."""
        if focused:
            r, g, b = self.title_focused_fg
            br, bg_, bb = self.title_focused_bg
        else:
            r, g, b = self.title_fg
            br, bg_, bb = self.title_bg
        return ansi_truecolor_fg(r, g, b) + ansi_truecolor_bg(br, bg_, bb)

    def to_css(self, prefix: str = ".sintraprime") -> str:
        """
        Export theme as CSS variables for web UI integration.

        Args:
            prefix: CSS selector prefix.

        Returns:
            CSS string with custom properties.
        """
        lines = [f"{prefix} {{"]
        for attr, val in self.to_dict().items():
            if attr == "name":
                continue
            if isinstance(val, (list, tuple)) and len(val) == 3:
                r, g, b = val
                lines.append(f"  --{attr.replace('_', '-')}: rgb({r}, {g}, {b});")
        lines.append("}")
        return "\n".join(lines)

    def check_accessibility(self) -> List[Dict[str, Any]]:
        """
        Check WCAG contrast ratios for key color pairs.

        Returns:
            List of dicts with pair names, ratios, and pass/fail status.
        """
        pairs = [
            ("title", self.title_fg, self.title_bg),
            ("title_focused", self.title_focused_fg, self.title_focused_bg),
            ("content", self.content_fg, self.content_bg),
            ("button", self.button_fg, self.button_bg),
            ("menubar", self.menubar_fg, self.menubar_bg),
            ("menu_selected", self.menu_selected_fg, self.menu_selected_bg),
        ]
        results = []
        for name, fg, bg in pairs:
            ratio = contrast_ratio(fg, bg)
            results.append({
                "pair": name,
                "fg": rgb_to_hex(*fg),
                "bg": rgb_to_hex(*bg),
                "ratio": round(ratio, 2),
                "AA": ratio >= 4.5,
                "AAA": ratio >= 7.0,
            })
        return results


# ─── Built-in themes ──────────────────────────────────────────────────────────

def _theme_dark() -> ColorTheme:
    """Dark theme (default)."""
    return ColorTheme(name="dark")


def _theme_light() -> ColorTheme:
    """Light theme for bright environments."""
    return ColorTheme(
        name="light",
        title_fg=(0, 0, 0),
        title_bg=(180, 200, 240),
        title_focused_fg=(0, 0, 80),
        title_focused_bg=(100, 160, 255),
        border_fg=(100, 100, 100),
        border_focused_fg=(0, 80, 200),
        content_fg=(20, 20, 40),
        content_bg=(240, 240, 245),
        widget_header_fg=(0, 0, 80),
        widget_header_bg=(180, 200, 240),
        button_fg=(255, 255, 255),
        button_bg=(0, 100, 200),
        menubar_fg=(0, 0, 80),
        menubar_bg=(180, 200, 240),
        menu_selected_fg=(255, 255, 255),
        menu_selected_bg=(0, 80, 200),
        progress_fg=(0, 120, 200),
        progress_bg=(200, 210, 230),
        log_error_fg=(180, 0, 0),
        log_warn_fg=(160, 100, 0),
        log_info_fg=(0, 120, 0),
        log_debug_fg=(0, 0, 180),
    )


def _theme_matrix() -> ColorTheme:
    """Matrix theme: green on black."""
    return ColorTheme(
        name="matrix",
        title_fg=(0, 255, 70),
        title_bg=(0, 20, 0),
        title_focused_fg=(0, 255, 70),
        title_focused_bg=(0, 40, 0),
        border_fg=(0, 180, 50),
        border_focused_fg=(0, 255, 70),
        content_fg=(0, 200, 50),
        content_bg=(0, 0, 0),
        widget_header_fg=(0, 255, 70),
        widget_header_bg=(0, 30, 0),
        button_fg=(0, 0, 0),
        button_bg=(0, 200, 50),
        button_hover_bg=(0, 255, 70),
        status_ok=(0, 255, 70),
        status_warn=(180, 255, 0),
        status_error=(255, 50, 50),
        menubar_fg=(0, 200, 50),
        menubar_bg=(0, 10, 0),
        menu_selected_fg=(0, 0, 0),
        menu_selected_bg=(0, 200, 50),
        progress_fg=(0, 200, 50),
        progress_bg=(0, 20, 0),
        log_error_fg=(255, 50, 50),
        log_warn_fg=(180, 255, 0),
        log_info_fg=(0, 200, 50),
        log_debug_fg=(0, 120, 30),
        notif_info_bg=(0, 60, 0),
        notif_warn_bg=(60, 60, 0),
        notif_error_bg=(80, 0, 0),
        notif_success_bg=(0, 80, 0),
    )


def _theme_ocean() -> ColorTheme:
    """Ocean theme: deep blues."""
    return ColorTheme(
        name="ocean",
        title_fg=(200, 240, 255),
        title_bg=(0, 60, 120),
        title_focused_fg=(255, 255, 255),
        title_focused_bg=(0, 80, 160),
        border_fg=(80, 160, 200),
        border_focused_fg=(100, 200, 255),
        content_fg=(200, 230, 255),
        content_bg=(5, 20, 45),
        widget_header_fg=(200, 240, 255),
        widget_header_bg=(0, 50, 100),
        button_fg=(0, 0, 0),
        button_bg=(0, 150, 220),
        button_hover_bg=(0, 180, 255),
        status_ok=(0, 220, 150),
        status_warn=(220, 180, 0),
        status_error=(220, 60, 60),
        menubar_fg=(200, 230, 255),
        menubar_bg=(0, 40, 80),
        menu_selected_fg=(255, 255, 255),
        menu_selected_bg=(0, 100, 180),
        progress_fg=(0, 180, 255),
        progress_bg=(0, 30, 60),
        log_error_fg=(255, 80, 80),
        log_warn_fg=(255, 200, 0),
        log_info_fg=(0, 220, 180),
        log_debug_fg=(80, 160, 220),
    )


def _theme_fire() -> ColorTheme:
    """Fire theme: red and orange."""
    return ColorTheme(
        name="fire",
        title_fg=(255, 240, 200),
        title_bg=(160, 40, 0),
        title_focused_fg=(255, 255, 200),
        title_focused_bg=(200, 60, 0),
        border_fg=(220, 100, 0),
        border_focused_fg=(255, 150, 0),
        content_fg=(255, 220, 180),
        content_bg=(20, 5, 0),
        widget_header_fg=(255, 240, 200),
        widget_header_bg=(120, 30, 0),
        button_fg=(0, 0, 0),
        button_bg=(220, 80, 0),
        button_hover_bg=(255, 120, 0),
        status_ok=(0, 200, 80),
        status_warn=(255, 220, 0),
        status_error=(255, 50, 0),
        menubar_fg=(255, 220, 180),
        menubar_bg=(100, 20, 0),
        menu_selected_fg=(0, 0, 0),
        menu_selected_bg=(220, 80, 0),
        progress_fg=(255, 120, 0),
        progress_bg=(60, 15, 0),
        log_error_fg=(255, 60, 0),
        log_warn_fg=(255, 200, 0),
        log_info_fg=(220, 150, 50),
        log_debug_fg=(180, 100, 0),
        notif_info_bg=(120, 40, 0),
        notif_warn_bg=(160, 100, 0),
        notif_error_bg=(180, 0, 0),
        notif_success_bg=(0, 100, 0),
    )


BUILTIN_THEMES: Dict[str, ColorTheme] = {
    "dark": _theme_dark(),
    "light": _theme_light(),
    "matrix": _theme_matrix(),
    "ocean": _theme_ocean(),
    "fire": _theme_fire(),
}


# ─── ThemeManager ─────────────────────────────────────────────────────────────

class ThemeManager:
    """
    Load, save, switch, and apply color themes.

    Supports INI-format theme files (like twin's theme.ini) and live switching.

    Usage:
        tm = ThemeManager()
        tm.switch_theme("matrix")
        ansi_codes = tm.current.ansi_content()
        css = tm.current.to_css()
        tm.save_to_ini("/tmp/my_theme.ini")
    """

    def __init__(self, initial_theme: str = "dark",
                 theme_dir: Optional[Path] = None):
        """
        Initialize ThemeManager.

        Args:
            initial_theme: Name of the default theme.
            theme_dir: Directory to search for custom theme INI files.
        """
        self._themes: Dict[str, ColorTheme] = dict(BUILTIN_THEMES)
        self._current_name: str = initial_theme
        self._theme_dir = theme_dir
        self._switch_callbacks: List[Any] = []

        if theme_dir and theme_dir.exists():
            self._load_theme_dir(theme_dir)

        logger.info("ThemeManager initialized with theme '%s'", initial_theme)

    @property
    def current(self) -> ColorTheme:
        """Return the currently active theme."""
        return self._themes.get(self._current_name, BUILTIN_THEMES["dark"])

    @property
    def current_name(self) -> str:
        return self._current_name

    def switch_theme(self, name: str) -> bool:
        """
        Switch to a named theme. Live switch — no restart needed.

        Args:
            name: Theme name.

        Returns:
            True if theme was found and switched.
        """
        if name not in self._themes:
            logger.warning("Theme '%s' not found; available: %s",
                           name, list(self._themes.keys()))
            return False
        old_name = self._current_name
        self._current_name = name
        logger.info("Switched theme: %s → %s", old_name, name)
        for cb in self._switch_callbacks:
            try:
                cb(name, self._themes[name])
            except Exception as exc:
                logger.warning("Theme switch callback error: %s", exc)
        return True

    def add_switch_callback(self, callback: Any):
        """Register a callback invoked when theme changes."""
        self._switch_callbacks.append(callback)

    def register_theme(self, theme: ColorTheme):
        """Register a custom theme."""
        self._themes[theme.name] = theme
        logger.info("Registered custom theme '%s'", theme.name)

    def list_themes(self) -> List[str]:
        """Return names of all available themes."""
        return list(self._themes.keys())

    # ── INI file support (like twin's theme.ini) ──────────────────────────────

    def load_from_ini(self, path: Path) -> Optional[ColorTheme]:
        """
        Load a theme from an INI file.

        INI format:
            [theme]
            name = my_theme

            [colors]
            content_fg = #e0e0e0
            content_bg = #1a1a2e
            ...

        Args:
            path: Path to the INI file.

        Returns:
            The loaded ColorTheme, or None on error.
        """
        try:
            config = configparser.ConfigParser()
            config.read(str(path))
            name = config.get("theme", "name", fallback=path.stem)
            theme = ColorTheme(name=name)

            if "colors" in config:
                for key, val in config["colors"].items():
                    val = val.strip()
                    if hasattr(theme, key):
                        try:
                            if val.startswith("#"):
                                setattr(theme, key, hex_to_rgb(val))
                            elif val.startswith("(") or "," in val:
                                parts = val.strip("() ").split(",")
                                setattr(theme, key, tuple(int(p.strip()) for p in parts))
                        except Exception as exc:
                            logger.warning("Skipping invalid color '%s=%s': %s", key, val, exc)

            self._themes[name] = theme
            logger.info("Loaded theme '%s' from %s", name, path)
            return theme
        except Exception as exc:
            logger.error("Failed to load theme from %s: %s", path, exc)
            return None

    def save_to_ini(self, path: Path, theme_name: Optional[str] = None):
        """
        Save a theme to an INI file.

        Args:
            path: Output file path.
            theme_name: Theme to save (current if None).
        """
        theme = self._themes.get(theme_name or self._current_name, self.current)
        config = configparser.ConfigParser()
        config["theme"] = {"name": theme.name}
        config["colors"] = {}

        for attr, val in theme.to_dict().items():
            if attr == "name":
                continue
            if isinstance(val, (list, tuple)) and len(val) == 3:
                config["colors"][attr] = rgb_to_hex(*val)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                config.write(f)
            logger.info("Saved theme '%s' to %s", theme.name, path)
        except Exception as exc:
            logger.error("Failed to save theme to %s: %s", path, exc)

    def _load_theme_dir(self, theme_dir: Path):
        """Auto-load all .ini files from a theme directory."""
        for ini_file in theme_dir.glob("*.ini"):
            self.load_from_ini(ini_file)

    # ── CSS export ────────────────────────────────────────────────────────────

    def export_all_css(self) -> str:
        """
        Export all themes as CSS data-theme attributes.

        Returns:
            Multi-theme CSS string.
        """
        parts: List[str] = ["/* SintraPrime TUI Themes — generated by ThemeManager */\n"]
        for name, theme in self._themes.items():
            parts.append(f"\n/* Theme: {name} */")
            parts.append(f'[data-theme="{name}"] {{')
            for attr, val in theme.to_dict().items():
                if attr == "name":
                    continue
                if isinstance(val, (list, tuple)) and len(val) == 3:
                    r, g, b = val
                    parts.append(f"  --{attr.replace('_', '-')}: rgb({r}, {g}, {b});")
            parts.append("}")
        return "\n".join(parts)

    # ── Accessibility ─────────────────────────────────────────────────────────

    def accessibility_report(self, theme_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a WCAG accessibility report for a theme.

        Args:
            theme_name: Theme to check (current if None).

        Returns:
            Dict with results and pass/fail summary.
        """
        theme = self._themes.get(theme_name or self._current_name, self.current)
        checks = theme.check_accessibility()
        passed_aa = sum(1 for c in checks if c["AA"])
        passed_aaa = sum(1 for c in checks if c["AAA"])
        return {
            "theme": theme.name,
            "total_checks": len(checks),
            "AA_passed": passed_aa,
            "AAA_passed": passed_aaa,
            "AA_failed": len(checks) - passed_aa,
            "details": checks,
        }

    def __repr__(self) -> str:
        return f"ThemeManager(current={self._current_name!r}, themes={list(self._themes.keys())})"
