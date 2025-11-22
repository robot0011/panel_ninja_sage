# Ninja Sage GUI Overview

This document summarizes how `ninja_sage/gui/main.py` structures the Tkinter-based UI, the threading/action lifecycle, and helper utilities so other contributors can navigate, extend, or debug the GUI layer.

## Application startup
- `main.py` (project root) simply imports `ninja_sage.gui.main.main()` and runs it so build tools keep using the familiar entry point.
- `NinjaSageGUI.__init__` (`ninja_sage/gui/main.py:184-221`) configures styles, builds the main frame, and immediately shows the welcome screen; a `LogWindow` instance is created early so logs redirect to the floating console panel later.
- `show_welcome_screen` checks the game version on a background thread and either transitions to the login screen or shows a retry button (`ninja_sage/gui/main.py:244-292`).

## Logging panel
- `LogWindow` (`ninja_sage/gui/main.py:63-171`) spins up a detachable Toplevel that mirrors stdout/stderr, adds timestamped lines, and offers clear/copy controls. 
- `TextRedirector` forwards text output into the widget so the CLI log output is visible inside the UI.
- Each screen can call `_make_logs_button` to render a “Show Logs” button wired to the same panel (`ninja_sage/gui/main.py:223-258`).

## Login and character selection
- Login UI supports quick login when `quick_login.json` exists; quick login data is saved via `save_to_json` (`ninja_sage/gui/main.py:274-365`).
- The manual login form enforces non-empty credentials, toggles password visibility, and dispatches `perform_login` on a daemon thread to avoid freezing the UI.
- After successful login, `load_characters` populates a listbox with the account‟s characters and transitions to character selection (`ninja_sage/gui/main.py:384-458`). Double-clicking or the “Select Character” button calls `select_character`, which loads char data and enters the main menu (`ninja_sage/gui/main.py:460-502`).

## Actions & threading helpers
- `_prepare_for_action` and `_run_action_thread` centralize the action lifecycle (`ninja_sage/gui/main.py:721-768`).
  * `_prepare_for_action` shows the log window, clears the shared stop event, configures the stop button/status label, and records the current action name.
  * `_run_action_thread` wraps the passed callable inside a thread that catches exceptions and routes completion via `on_action_finished`/`on_action_error`.
- `start_action` (for main-menu buttons) and `safe_start_action` (for modal dialogs) now call those helpers so every action shares the same UX/stop semantics.
- `stop_action`, `force_stop_action`, `on_action_finished`, and `on_action_error` manage the UI controls after an action toggles or fails (`ninja_sage/gui/main.py:901-931`).

## Main menu and dialogs
- `show_main_menu` (`ninja_sage/gui/main.py:770-847`) displays character info, action buttons (leveling, boss/event fights, finisher, refresh), and a control panel that includes the log and stop buttons.
- Enemy-selection and CD-event dialogs reuse helpers `_make_logs_button` and `_center_window` for consistent layout (`ninja_sage/gui/main.py:518-719`). Event-specific functions like `show_enemy_selection_dialog` and `show_cd_event_dialog` dispatch to the shared action pipeline so they respect stop events.
- `refresh_character_info` fetches updated character data on a daemon thread and reports status text/alerts to the user when it succeeds or fails.

## Supporting utilities
- `_center_window` computes coordinates relative to the main window so dialogs always remain centered (`ninja_sage/gui/main.py:228-235`).
- `show_loading`/`hide_loading` display a modal spinner dialog while background tasks (character load, login, refresh) are running; they also use `_center_window` so the helper dialog stays centered.
- `LOG_WINDOW` button wiring ensures every screen can bring the console forward easily.

## Recommended next steps
1. When adding new actions, integrate them through `_prepare_for_action` → `_run_action_thread` so stop/exception handling stays consistent.
2. If you need additional dialogs, reuse `_center_window` and `_make_logs_button` so the user experience remains uniform.
3. Keep the entry point (`main.py`) untouched; use `ninja_sage.gui.main.main()` when running tests or packaging.
