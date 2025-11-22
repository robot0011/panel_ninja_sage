import os
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, Any, Optional, List
import sys
import io

from ..core import config, amf_req
from ..core.leveling import start_leveling
from ..core.resources import download_all_resources
from ..core.utils import save_to_json, open_json_to_dict
from ..core.eudemon import fight_eudemon_boss
from ..core.event import (
    fight_cd_event,
    fight_pumpkin_event,
    fight_yinyang_event,
    fight_gi_event,
)
from ..core.event_finisher import event_finisher
from ..core.shadow_war import shadow_war_event


class TextRedirector(io.TextIOBase):
    """Redirects stdout/stderr to a Tkinter Text widget"""
    
    def __init__(self, text_widget, tag="stdout"):
        self.text_widget = text_widget
        self.tag = tag
        
    def write(self, string):
        self.text_widget.insert(tk.END, string, (self.tag,))
        self.text_widget.see(tk.END)
        self.text_widget.update_idletasks()
        
    def flush(self):
        pass


class LogWindow:
    """Separate window for displaying logs and terminal output"""
    
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.text_widget = None
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
    def show(self):
        """Show the log window"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
            
        self.window = tk.Toplevel(self.parent)
        self.window.title("Ninja Sage Bot - Logs & Terminal Output")
        self.window.geometry("800x500")
        self.window.minsize(600, 400)
        
        # Create menu
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Clear Logs", command=self.clear_logs)
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self.hide)
        
        # Create main frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        clear_btn = ttk.Button(toolbar, text="Clear Logs", command=self.clear_logs)
        clear_btn.pack(side=tk.LEFT, padx=2)
        
        copy_btn = ttk.Button(toolbar, text="Copy", command=self.copy_text)
        copy_btn.pack(side=tk.LEFT, padx=2)
        
        auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_cb = ttk.Checkbutton(toolbar, text="Auto Scroll", 
                                       variable=auto_scroll_var)
        auto_scroll_cb.pack(side=tk.RIGHT, padx=2)
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(text_frame)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Text widget
        self.text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            font=('Consolas', 10),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white',
            selectbackground='#264f78'
        )
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbars
        v_scrollbar.config(command=self.text_widget.yview)
        h_scrollbar.config(command=self.text_widget.xview)
        
        # Configure tags for different log types
        self.text_widget.tag_configure('stdout', foreground='#d4d4d4')
        self.text_widget.tag_configure('stderr', foreground='#f44747')
        self.text_widget.tag_configure('success', foreground='#4ec9b0')
        self.text_widget.tag_configure('warning', foreground='#ffcc02')
        self.text_widget.tag_configure('info', foreground='#9cdcfe')
        self.text_widget.tag_configure('timestamp', foreground='#6a9955')
        
        # Redirect stdout and stderr
        sys.stdout = TextRedirector(self.text_widget, 'stdout')
        sys.stderr = TextRedirector(self.text_widget, 'stderr')
        
        # Add welcome message
        self.add_timestamped_message("Log window started. All terminal output will be shown here.", 'info')
        
        # Bind window close event
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Auto-scroll functionality
        def auto_scroll():
            if auto_scroll_var.get() and self.text_widget:
                self.text_widget.see(tk.END)
            if self.window and self.window.winfo_exists():
                self.window.after(100, auto_scroll)
            
        auto_scroll()
        
    def hide(self):
        """Hide the log window without destroying it"""
        if self.window:
            # Restore original stdout/stderr when hiding
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            self.window.withdraw()
            
    def clear_logs(self):
        """Clear all log text"""
        if self.text_widget:
            self.text_widget.delete(1.0, tk.END)
            self.add_timestamped_message("Logs cleared.", 'info')
            
    def copy_text(self):
        """Copy selected text to clipboard"""
        if self.text_widget:
            try:
                selected_text = self.text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.window.clipboard_clear()
                self.window.clipboard_append(selected_text)
            except tk.TclError:
                # No text selected
                pass
                
    def add_timestamped_message(self, message, tag='stdout'):
        """Add a message with timestamp"""
        if self.text_widget:
            timestamp = time.strftime("%H:%M:%S")
            self.text_widget.insert(tk.END, f"[{timestamp}] ", 'timestamp')
            self.text_widget.insert(tk.END, f"{message}\n", tag)
            self.text_widget.see(tk.END)
            
    def is_visible(self):
        """Check if log window is visible"""
        return self.window and self.window.winfo_exists()


class NinjaSageGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Ninja Sage Bot by robot0011")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        config.main_window = self.root
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        self.style.configure('Title.TLabel', background='#f0f0f0', font=('Arial', 16, 'bold'))
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('Action.TButton', font=('Arial', 9), width=20)
        self.style.configure('Big.TButton', font=('Arial', 12))
        
        self.QUICK_LOGIN_FILE = 'quick_login.json'
        self.running = True
        self.current_character = None
        self.action_thread = None
        self.stop_event = threading.Event()
        self.current_action = None
        
        # Initialize GUI components to avoid AttributeError
        self.stop_btn = None
        self.status_label = None
        
        # Create log window
        self.log_window = LogWindow(self.root)
        
        # Create main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.current_frame = None
        self.show_welcome_screen()
    
    def show_log_window(self):
        """Force show the log window"""
        self.log_window.show()

    def _make_logs_button(self, parent, text="📋 Show Logs"):
        """Create a logs button to reuse across screens"""
        return ttk.Button(parent, text=text, command=self.show_log_window)

    def _center_window(self, window, width, height):
        """Center a window relative to the main application"""
        window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (width // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (height // 2)
        window.geometry(f"+{x}+{y}")

    def clear_frame(self):
        """Clear all widgets from current frame"""
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = ttk.Frame(self.main_frame)
        self.current_frame.pack(fill=tk.BOTH, expand=True)
    
    def show_welcome_screen(self):
        """Display welcome screen"""
        self.clear_frame()
        
        title_label = ttk.Label(self.current_frame, text="Ninja Sage Bot by robot0011", 
                               style='Title.TLabel', foreground='#2c3e50')
        title_label.pack(pady=30)
        
        version_label = ttk.Label(self.current_frame, text="Checking game version...", 
                                 font=('Arial', 12))
        version_label.pack(pady=10)
        
        # Add show logs button
        logs_btn = self._make_logs_button(self.current_frame, "📋 Show Logs Window")
        logs_btn.pack(pady=10)
        
        self.root.update()
        
        # Check version in a thread to avoid freezing GUI
        def check_version():
            success = self.check_game_version()
            self.root.after(0, lambda: self.on_version_checked(success, version_label))
        
        threading.Thread(target=check_version, daemon=True).start()
    
    def on_version_checked(self, success, version_label):
        """Handle version check result"""
        if success:
            version_label.config(text="✅ Game version: Compatible", foreground='green')
            self.root.after(1000, self.show_login_screen)
        else:
            version_label.config(text="❌ Game version not compatible!", foreground='red')
            retry_btn = ttk.Button(self.current_frame, text="Retry", command=self.show_welcome_screen)
            retry_btn.pack(pady=10)
    
    def check_game_version(self) -> bool:
        """Check if game version is compatible"""
        config.game_data = amf_req.check_version()
        return config.game_data.get("status") == 1
    
    def show_login_screen(self):
        """Display login screen"""
        self.clear_frame()
        
        # Bigger login title
        title_label = tk.Label(self.current_frame, text="LOGIN", 
                              font=('Arial', 28, 'bold'), foreground='#2c3e50', bg='#f0f0f0')
        title_label.pack(pady=40)
        
        login_frame = ttk.Frame(self.current_frame)
        login_frame.pack(pady=20)
        
        # Quick login button if available
        if self.quick_login_exists():
            quick_login_btn = ttk.Button(login_frame, text="Quick Login", 
                                       command=self.quick_login, width=20, style='Big.TButton')
            quick_login_btn.pack(pady=15)
            
            tk.Label(login_frame, text="OR", font=('Arial', 14), bg='#f0f0f0').pack(pady=15)
        
        # Manual login form
        form_frame = ttk.Frame(login_frame)
        form_frame.pack(pady=20)
        
        # Username field
        tk.Label(form_frame, text="Username:", font=('Arial', 14), bg='#f0f0f0').grid(row=0, column=0, padx=10, pady=12, sticky=tk.W)
        self.username_entry = ttk.Entry(form_frame, width=25, font=('Arial', 12))
        self.username_entry.grid(row=0, column=1, padx=10, pady=12)
        
        # Password field
        tk.Label(form_frame, text="Password:", font=('Arial', 14), bg='#f0f0f0').grid(row=1, column=0, padx=10, pady=12, sticky=tk.W)
        self.password_entry = ttk.Entry(form_frame, width=25, show="*", font=('Arial', 12))
        self.password_entry.grid(row=1, column=1, padx=10, pady=12)
        
        # Show password checkbox
        self.show_password_var = tk.BooleanVar()
        show_password_cb = tk.Checkbutton(form_frame, text="Show Password", 
                                         variable=self.show_password_var,
                                         command=self.toggle_password_visibility,
                                         font=('Arial', 11), bg='#f0f0f0')
        show_password_cb.grid(row=2, column=1, padx=10, pady=8, sticky=tk.W)
        
        def perform_login():
            username = self.username_entry.get().strip()
            password = self.password_entry.get().strip()
            if username and password:
                self.manual_login(username, password)
            else:
                messagebox.showwarning("Input Error", "Please enter both username and password")
        
        login_btn = ttk.Button(form_frame, text="Login", command=perform_login, width=15, style='Big.TButton')
        login_btn.grid(row=3, column=0, columnspan=2, pady=20)
        
        # Show logs button
        logs_btn = self._make_logs_button(form_frame, "📋 Show Logs Window")
        logs_btn.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Bind Enter key to login
        self.password_entry.bind('<Return>', lambda e: perform_login())
        self.username_entry.focus()
    
    def toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.show_password_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")
    
    def quick_login_exists(self) -> bool:
        """Check if quick login data exists"""
        return os.path.exists(self.QUICK_LOGIN_FILE)
    
    def load_quick_login(self) -> Optional[Dict[str, str]]:
        """Load quick login data from file"""
        try:
            with open(self.QUICK_LOGIN_FILE, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    def quick_login(self):
        """Perform quick login"""
        login_data = self.load_quick_login()
        if login_data:
            self.perform_login(login_data["username"], login_data["password"])
        else:
            messagebox.showerror("Quick Login Failed", "No quick login data found")
    
    def manual_login(self, username: str, password: str):
        """Perform manual login"""
        self.perform_login(username, password)
    
    def perform_login(self, username: str, password: str):
        """Perform login in a separate thread"""
        def login_thread():
            config.login_data = amf_req.login(
                username, 
                password, 
                config.game_data["__"], 
                str(int(config.game_data["_"]))
            )
            
            self.root.after(0, lambda: self.on_login_result(config.login_data.get('status') == 1, username, password))
        
        self.show_loading("Logging in...")
        threading.Thread(target=login_thread, daemon=True).start()
    
    def on_login_result(self, success: bool, username: str, password: str):
        """Handle login result"""
        self.hide_loading()
        
        if success:
            self.save_quick_login(username, password)
            self.show_character_selection()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")
    
    def save_quick_login(self, username: str, password: str):
        """Save login credentials for quick login"""
        login_data = {"username": username, "password": password}
        save_to_json(login_data, "quick_login")
    
    def show_character_selection(self):
        """Show character selection screen"""
        self.clear_frame()
        
        title_label = ttk.Label(self.current_frame, text="Select Character", 
                               style='Title.TLabel', foreground='#2c3e50')
        title_label.pack(pady=20)
        
        # Create a frame for the listbox with scrollbar
        list_frame = ttk.Frame(self.current_frame)
        list_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Add scrollbar to listbox
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.char_listbox = tk.Listbox(list_frame, width=60, height=12, 
                                      font=('Arial', 11),
                                      yscrollcommand=scrollbar.set)
        self.char_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.char_listbox.yview)
        
        # Bind double-click to select character
        self.char_listbox.bind('<Double-Button-1>', lambda e: self.select_character())
        
        button_frame = ttk.Frame(self.current_frame)
        button_frame.pack(pady=15)
        
        refresh_btn = ttk.Button(button_frame, text="Refresh Characters", 
                               command=self.load_characters)
        refresh_btn.pack(side=tk.LEFT, padx=10)
        
        select_btn = ttk.Button(button_frame, text="Select Character", 
                              command=self.select_character)
        select_btn.pack(side=tk.LEFT, padx=10)
        
        logs_btn = self._make_logs_button(button_frame, "📋 Show Logs")
        logs_btn.pack(side=tk.LEFT, padx=10)
        
        self.load_characters()
    
    def load_characters(self):
        """Load characters in a separate thread"""
        def load_thread():
            all_char = amf_req.get_all_characters()
            self.root.after(0, lambda: self.on_characters_loaded(all_char))
        
        self.show_loading("Loading characters...")
        threading.Thread(target=load_thread, daemon=True).start()
    
    def on_characters_loaded(self, all_char):
        """Handle characters loaded"""
        self.hide_loading()
        
        self.char_listbox.delete(0, tk.END)
        self.all_characters = all_char
        
        if not all_char:
            self.char_listbox.insert(tk.END, "No characters found!")
            return
        
        # Handle both list of integers and list of dictionaries
        for i, char in enumerate(config.all_char['account_data'], 1):
            if isinstance(char, dict):
                # It's a dictionary with character data
                char_name = char.get('character_name', f'Character {i}')
                char_level = char.get('character_level')
                self.char_listbox.insert(tk.END, f"{i}. {char_name} || Level: {char_level}")
            else:
                # It's probably a character ID or other identifier
                self.char_listbox.insert(tk.END, f"{i}. Char Name: Character || Level: {char}")
    
    def select_character(self):
        """Select character from list"""
        selection = self.char_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select a character")
            return
        
        char_index = selection[0]
        if not self.all_characters or char_index >= len(self.all_characters):
            messagebox.showerror("Error", "Invalid character selection")
            return
        
        def load_thread():
            selected_char = self.all_characters[char_index]
            
            # Handle both dictionary and integer character references
            if isinstance(selected_char, dict):
                # If it's already a dictionary, use it directly
                config.char_data = amf_req.get_character_data(selected_char)
            else:
                # If it's an integer/ID, we need to pass the appropriate data structure
                config.char_data = amf_req.get_character_data(selected_char)
            
            success = config.char_data is not None and "character_data" in config.char_data
            self.root.after(0, lambda: self.on_character_loaded(success))
        
        self.show_loading("Loading character data...")
        threading.Thread(target=load_thread, daemon=True).start()
    
    def on_character_loaded(self, success: bool):
        """Handle character loaded"""
        self.hide_loading()
        
        if success:
            self.current_character = config.char_data["character_data"]
            self.show_main_menu()
        else:
            messagebox.showerror("Error", "Failed to load character data")
    
    def show_enemy_selection_dialog(self, event_type):
        """Show enemy selection dialog for events that require it"""
        event_enemies = {
            "pumpkin": {
                "1": ("ene_2104", "Pumpkin Minion"),
                "2": ("ene_2105", "Skeleton Ninja"), 
                "3": ("ene_2106", "Zombie Samurai"),
                "4": ("ene_2103", "Headless Pumpkin Horseman"),
                "5": ("ene_2102", "Cursed Pumpkin King"),
            },
            "yinyang": {
                "1": ("ene_2100", "Yin Tiger"),
                "2": ("ene_2101", "Yang Dragon"),
            }
        }
        
        if event_type not in event_enemies:
            # For events that don't require enemy selection (like CD event)
            self.start_action(lambda: None, f"Fight {event_type.replace('_', ' ').title()} Event")
            return
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Select Enemy - {event_type.replace('_', ' ').title()} Event")
        dialog.geometry("450x400")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        self._center_window(dialog, 450, 400)
        
        # Main content frame
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text=f"{event_type.replace('_', ' ').title()} Event", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 15))
        
        # Enemy selection section
        selection_frame = ttk.LabelFrame(main_frame, text="Select Enemy to Fight")
        selection_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Enemy list with scrollbar
        list_frame = ttk.Frame(selection_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enemy listbox
        enemy_listbox = tk.Listbox(
            list_frame, 
            font=('Arial', 11), 
            height=8,
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE
        )
        enemy_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar.config(command=enemy_listbox.yview)
        
        # Populate enemy list
        for num, (enemy_id, enemy_name) in event_enemies[event_type].items():
            enemy_listbox.insert(tk.END, f"{num}. {enemy_name}")
        
        # Info section
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=10)
        
        info_label = ttk.Label(
            info_frame, 
            text="ℹ️  Will use all available energy for selected enemy",
            font=('Arial', 9),
            foreground='blue'
        )
        info_label.pack()
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def start_fight():
            selection = enemy_listbox.curselection()
            if not selection:
                messagebox.showwarning("Selection Required", "Please select an enemy to fight!")
                return
            
            selected_index = selection[0]
            enemy_choice = list(event_enemies[event_type].keys())[selected_index]
            enemy_id = event_enemies[event_type][enemy_choice][0]
            enemy_name = event_enemies[event_type][enemy_choice][1]
            
            # Create a wrapper function that includes the enemy selection
            def fight_with_enemy():
                if event_type == "pumpkin":
                    fight_pumpkin_event(enemy_id)
                elif event_type == "yinyang":
                    fight_yinyang_event(enemy_id)
            
            dialog.destroy()
            self.start_action(fight_with_enemy, f"Fight {enemy_name}")
        
        def cancel():
            dialog.destroy()
        
        # Fight button (primary action)
        fight_btn = ttk.Button(
            button_frame, 
            text="⚔️  Start Fighting", 
            command=start_fight,
            style='Action.TButton',
            width=15
        )
        fight_btn.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_btn = ttk.Button(
            button_frame, 
            text="Cancel", 
            command=cancel,
            width=10
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Bind double-click to start fight
        enemy_listbox.bind('<Double-Button-1>', lambda e: start_fight())
        
        # Select first enemy by default and set focus
        enemy_listbox.selection_set(0)
        enemy_listbox.see(0)
        fight_btn.focus_set()


    def show_cd_event_dialog(self):
        """Show CD Event confirmation dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("CD Event - Confirmation")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        self._center_window(dialog, 400, 200)
        
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Confronting Death Event", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=10)
        
        # Info text
        info_label = ttk.Label(
            main_frame, 
            text="This will use all available CD Event energy to fight the Death Boss.",
            font=('Arial', 10),
            wraplength=350
        )
        info_label.pack(pady=10)
        
        warning_label = ttk.Label(
            main_frame, 
            text="ℹ️  Will use all available energy",
            font=('Arial', 9),
            foreground='blue'
        )
        warning_label.pack(pady=5)
        
        def start_fight():
            def fight_cd():
                fight_cd_event()
            
            dialog.destroy()
            self.safe_start_action(fight_cd, "Fight CD Event")
        
        def cancel():
            dialog.destroy()
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=15)
        
        fight_btn = ttk.Button(
            button_frame, 
            text="⚔️  Start Fighting", 
            command=start_fight,
            style='Action.TButton'
        )
        fight_btn.pack(side=tk.RIGHT, padx=5)
        
        cancel_btn = ttk.Button(
            button_frame, 
            text="Cancel", 
            command=cancel
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        fight_btn.focus_set()
    
    def _prepare_for_action(self, action_name: str, use_gui_controls: bool) -> bool:
        """Common preparation logic before starting any threaded action"""
        if self.action_thread and self.action_thread.is_alive():
            messagebox.showwarning("Action Running", "Please stop the current action first")
            return False

        self.show_log_window()
        self.stop_event.clear()
        config.stop_event = self.stop_event

        if use_gui_controls and self.stop_btn:
            self.stop_btn.config(state=tk.NORMAL)
        if use_gui_controls and self.status_label:
            self.status_label.config(text=f"🟡 Running: {action_name}...", foreground='orange')
        else:
            print(f"🟡 Starting: {action_name}...")

        self.current_action = action_name
        return True

    def _run_action_thread(self, action_func):
        """Execute the provided action in a background thread"""
        def action_wrapper():
            try:
                action_func()
            except Exception as e:
                print(f"Action error: {e}")
                self.root.after(0, lambda: self.on_action_error(str(e)))
            finally:
                self.root.after(0, self.on_action_finished)

        self.action_thread = threading.Thread(target=action_wrapper, daemon=True)
        self.action_thread.start()

    def safe_start_action(self, action_func, action_name):
        """Safe version of start_action that works from any screen"""
        use_gui_controls = bool(getattr(self, 'stop_btn', None))
        if not self._prepare_for_action(action_name, use_gui_controls):
            return

        self._run_action_thread(action_func)
    
    def start_action(self, action_func, action_name):
        """Start an action in separate thread - for use in main menu only"""
        if not self._prepare_for_action(action_name, True):
            return

        self._run_action_thread(action_func)

    def show_main_menu(self):
        """Show main menu with actions"""
        self.clear_frame()
        
        # Character info at top
        char_info_frame = tk.LabelFrame(self.current_frame, text="Character Information", 
                                       font=('Arial', 12, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        char_info_frame.pack(fill=tk.X, padx=15, pady=15)
        
        if self.current_character:
            char_name = self.current_character.get('character_name', 'Unknown')
            char_xp = self.current_character.get('character_xp', 0)
            char_gold = self.current_character.get('character_gold', 0)
            tokens = config.all_char.get('tokens', 0) if hasattr(config, 'all_char') else 0
            
            info_text = f"👤 Name: {char_name} | ⭐ Exp: {char_xp} | 💰 Gold: {char_gold} | 🪙 Token: {tokens}"
            info_label = tk.Label(char_info_frame, text=info_text, font=('Arial', 11), bg='#f0f0f0')
            info_label.pack(pady=10)
        
        # Actions frame
        actions_frame = tk.LabelFrame(self.current_frame, text="Available Actions", 
                                     font=('Arial', 12, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        actions_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Create action buttons - updated to use dialogs where needed
        actions = [
            ("🚀 Start Leveling", lambda: self.start_action(start_leveling, "Start Leveling")),
            ("👹 Fight Eudemon Boss", lambda: self.start_action(fight_eudemon_boss, "Fight Eudemon Boss")),
            ("⚡ Fight CD Event Boss", self.show_cd_event_dialog),
            ("🎃 Fight Pumpkin Event Boss", lambda: self.show_enemy_selection_dialog("pumpkin")),
            ("☯️ Fight Yin Yang Event Boss", lambda: self.show_enemy_selection_dialog("yinyang")),
            ("🏁 Event Finisher", lambda: self.start_action(event_finisher, "Event Finisher")),
            ("🔄 Refresh Character Info", self.refresh_character_info)
        ]
        
        # Arrange buttons in a grid
        for i, (text, action) in enumerate(actions):
            row = i // 3
            col = i % 3
            btn = ttk.Button(actions_frame, text=text, 
                           command=action,
                           style='Action.TButton')
            btn.grid(row=row, column=col, padx=8, pady=8, sticky=tk.NSEW)
        
        # Configure grid weights
        for i in range(3):
            actions_frame.columnconfigure(i, weight=1)
        for i in range((len(actions) + 2) // 3):
            actions_frame.rowconfigure(i, weight=1)
        
        # Control frame with stop button and status
        control_frame = tk.LabelFrame(self.current_frame, text="Controls", 
                                     font=('Arial', 12, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        control_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Stop button and status in control frame
        stop_status_frame = ttk.Frame(control_frame)
        stop_status_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Initialize stop_btn and status_label here
        self.stop_btn = ttk.Button(stop_status_frame, text="🛑 Stop Current Action", 
                                 command=self.stop_action, state=tk.DISABLED,
                                 style='Action.TButton')
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Logs button
        logs_btn = self._make_logs_button(stop_status_frame, "📋 Show Logs Window")
        logs_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_label = tk.Label(stop_status_frame, text="✅ Ready", 
                                    font=('Arial', 11), foreground='green', bg='#f0f0f0')
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # Exit button
        exit_btn = ttk.Button(control_frame, text="🚪 Exit", 
                            command=self.root.quit, style='Action.TButton')
        exit_btn.pack(pady=5)
    
    def refresh_character_info(self):
        """Refresh character information"""
        def refresh_thread():
            try:
                # Get fresh character list
                all_char = amf_req.get_all_characters()
                if not all_char:
                    print("No characters found during refresh")
                    self.root.after(0, lambda: self.status_label.config(text="❌ No characters found", foreground='red'))
                    return
                    
                if self.current_character:
                    current_name = self.current_character.get('character_name')
                    print(f"Refreshing data for character: {current_name}")
                    
                    # Find the current character in the fresh list
                    character_found = False
                    for char in all_char:
                        if isinstance(char, dict) and char.get('character_name') == current_name:
                            # Found our character, get fresh data
                            config.char_data = amf_req.get_character_data(char)
                            if config.char_data and "character_data" in config.char_data:
                                self.current_character = config.char_data["character_data"]
                                character_found = True
                                print("Character data refreshed successfully")
                            break
                        elif not isinstance(char, dict):
                            # Handle integer character IDs
                            config.char_data = amf_req.get_character_data(char)
                            new_char_data = config.char_data.get("character_data", {})
                            if new_char_data.get('character_name') == current_name:
                                self.current_character = new_char_data
                                character_found = True
                                print("Character data refreshed successfully")
                                break
                    
                    if not character_found:
                        print("Current character not found in character list")
                        self.root.after(0, lambda: self.status_label.config(text="❌ Character not found", foreground='red'))
                        return
                
                # Update the main menu with fresh data
                self.root.after(0, self.show_main_menu)
                self.root.after(0, lambda: self.status_label.config(text="✅ Character info refreshed", foreground='green'))
                
            except Exception as e:
                print(f"Error refreshing character info: {e}")
                self.root.after(0, lambda: self.status_label.config(text=f"❌ Refresh failed: {e}", foreground='red'))
                self.root.after(0, lambda: messagebox.showerror("Refresh Error", f"Failed to refresh character info: {e}"))
        
        self.status_label.config(text="🔄 Refreshing character info...", foreground='blue')
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    def stop_action(self):
        """Stop current action"""
        if self.action_thread and self.action_thread.is_alive():
            self.stop_event.set()
            self.status_label.config(text="🟠 Stopping action... Please wait", foreground='orange')
            # Force stop after 3 seconds if not responding
            self.root.after(3000, self.force_stop_action)
        else:
            self.status_label.config(text="✅ No action running", foreground='green')
    
    def force_stop_action(self):
        """Force stop action if normal stop doesn't work"""
        if self.action_thread and self.action_thread.is_alive():
            self.status_label.config(text="🔴 Action stopped", foreground='red')
            self.stop_btn.config(state=tk.DISABLED)
            self.current_action = None
    
    def on_action_finished(self):
        """Handle action finished"""
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="✅ Action completed", foreground='green')
        self.current_action = None
        # Auto-refresh character info after action
        self.refresh_character_info()
    
    def on_action_error(self, error_msg):
        """Handle action error"""
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text=f"❌ Error: {error_msg}", foreground='red')
        self.current_action = None
        messagebox.showerror("Action Error", f"An error occurred:\n{error_msg}")
    
    def show_loading(self, message="Loading..."):
        """Show loading indicator"""
        if hasattr(self, 'loading_frame') and self.loading_frame:
            self.loading_frame.destroy()
        
        self.loading_frame = tk.Toplevel(self.root)
        self.loading_frame.title("Please Wait")
        self.loading_frame.geometry("350x120")
        self.loading_frame.transient(self.root)
        self.loading_frame.grab_set()
        self.loading_frame.configure(bg='white')
        
        self._center_window(self.loading_frame, 350, 120)
        
        # Loading message
        label = tk.Label(self.loading_frame, text=message, font=('Arial', 12), bg='white')
        label.pack(expand=True, pady=10)
        
        # Progress bar
        progress = ttk.Progressbar(self.loading_frame, mode='indeterminate', length=300)
        progress.pack(fill=tk.X, padx=25, pady=10)
        progress.start()
        
        # Make sure it appears on top
        self.loading_frame.lift()
        self.loading_frame.focus_force()
    
    def hide_loading(self):
        """Hide loading indicator"""
        if hasattr(self, 'loading_frame') and self.loading_frame:
            self.loading_frame.destroy()
            self.loading_frame = None
    
    def run(self):
        """Start the GUI application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.root.quit()
        finally:
            # Restore original stdout/stderr when closing
            if hasattr(self, 'log_window') and hasattr(self.log_window, 'original_stdout'):
                sys.stdout = self.log_window.original_stdout
                sys.stderr = self.log_window.original_stderr


def main():
    app = NinjaSageGUI()
    app.run()


if __name__ == "__main__":
    main()
