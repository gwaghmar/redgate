"""Professional branding and about dialog."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox
import webbrowser
from pathlib import Path

# Application metadata
APP_NAME = "SQL Schema Compare Pro"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Your Company Name"
APP_COPYRIGHT = f"© 2026 {APP_AUTHOR}. All rights reserved."
APP_WEBSITE = "https://your-website.com"
APP_SUPPORT_EMAIL = "support@your-website.com"
APP_DESCRIPTION = "Professional SQL Server schema comparison and synchronization tool"

# Feature sets by edition
FEATURES = {
    "trial": [
        "Compare database schemas",
        "Generate deployment scripts",
        "Basic export formats (CSV, JSON)",
        "30-day trial period"
    ],
    "standard": [
        "All trial features",
        "Unlimited comparisons",
        "Advanced export (Excel, PDF, HTML)",
        "Schema snapshots",
        "Email support"
    ],
    "professional": [
        "All standard features",
        "Rollback script generation",
        "Dependency analysis",
        "Automated scheduling",
        "Command-line interface",
        "Priority support"
    ],
    "enterprise": [
        "All professional features",
        "Multi-database comparison",
        "Custom scripting",
        "API access",
        "Dedicated support",
        "Custom branding"
    ]
}


class AboutDialog(ctk.CTkToplevel):
    """Professional About dialog with licensing info."""
    
    def __init__(self, parent, license_info: dict = None):
        super().__init__(parent)
        
        self.title(f"About {APP_NAME}")
        self.geometry("550x600")
        self.resizable(False, False)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 550) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 600) // 2
        self.geometry(f"+{x}+{y}")
        
        self._create_widgets(license_info or {})
    
    def _create_widgets(self, license_info: dict):
        """Create dialog widgets."""
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Logo/Icon area (you can add an actual logo image here)
        logo_frame = ctk.CTkFrame(main_frame, height=80, fg_color=( "#3B8ED0", "#1F6AA5"))
        logo_frame.pack(fill="x", pady=(0, 20))
        logo_frame.pack_propagate(False)
        
        app_title = ctk.CTkLabel(
            logo_frame,
            text=APP_NAME,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="white"
        )
        app_title.place(relx=0.5, rely=0.5, anchor="center")
        
        # Version info
        version_label = ctk.CTkLabel(
            main_frame,
            text=f"Version {APP_VERSION}",
            font=ctk.CTkFont(size=14)
        )
        version_label.pack(pady=(0, 5))
        
        # Description
        desc_label = ctk.CTkLabel(
            main_frame,
            text=APP_DESCRIPTION,
            font=ctk.CTkFont(size=11),
            wraplength=500
        )
        desc_label.pack(pady=(0, 15))
        
        # Copyright
        copy_label = ctk.CTkLabel(
            main_frame,
            text=APP_COPYRIGHT,
            font=ctk.CTkFont(size=10)
        )
        copy_label.pack(pady=(0, 20))
        
        # License Information
        license_frame = ctk.CTkFrame(main_frame)
        license_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            license_frame,
            text="License Information",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 10))
        
        # License status
        license_type = license_info.get("type", "trial").upper()
        is_valid = license_info.get("is_valid", False)
        
        status_color = "#2CC985" if is_valid else "#F44336"
        status_text = "✓ ACTIVE" if is_valid else "✗ INACTIVE"
        
        status_label = ctk.CTkLabel(
            license_frame,
            text=f"{license_type} LICENSE - {status_text}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=status_color
        )
        status_label.pack(pady=(0, 10))
        
        # License details
        if license_info.get("user_name"):
            ctk.CTkLabel(
                license_frame,
                text=f"Licensed to: {license_info['user_name']}",
                font=ctk.CTkFont(size=10)
            ).pack()
        
        if license_info.get("company"):
            ctk.CTkLabel(
                license_frame,
                text=f"Company: {license_info['company']}",
                font=ctk.CTkFont(size=10)
            ).pack()
        
        if license_info.get("expiry"):
            expiry_date = license_info["expiry"]
            expiry_str = expiry_date.strftime("%B %d, %Y") if hasattr(expiry_date, 'strftime') else str(expiry_date)
            ctk.CTkLabel(
                license_frame,
                text=f"Expires: {expiry_str}",
                font=ctk.CTkFont(size=10)
            ).pack(pady=(0, 10))
        
        # System Information
        system_frame = ctk.CTkFrame(main_frame)
        system_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            system_frame,
            text="System Information",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 10))
        
        import platform
        import sys
        
        info_text = f"Python {sys.version.split()[0]} | {platform.system()} {platform.release()}"
        ctk.CTkLabel(
            system_frame,
            text=info_text,
            font=ctk.CTkFont(size=10)
        ).pack(pady=(0, 10))
        
        # Action buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkButton(
            button_frame,
            text="Visit Website",
            command=self._open_website,
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Contact Support",
            command=self._contact_support,
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
            width=100
        ).pack(side="right", padx=5)
    
    def _open_website(self):
        """Open company website."""
        try:
            webbrowser.open(APP_WEBSITE)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open website: {e}")
    
    def _contact_support(self):
        """Open email client for support."""
        try:
            import urllib.parse
            subject = urllib.parse.quote(f"{APP_NAME} Support Request")
            webbrowser.open(f"mailto:{APP_SUPPORT_EMAIL}?subject={subject}")
        except Exception as e:
            messagebox.showinfo(
                "Support Contact",
                f"Please email us at:\n{APP_SUPPORT_EMAIL}"
            )


class LicenseActivationDialog(ctk.CTkToplevel):
    """Dialog for entering and activating license keys."""
    
    def __init__(self, parent, license_manager):
        super().__init__(parent)
        
        self.license_manager = license_manager
        self.license_key = None
        
        self.title("Activate License")
        self.geometry("450x300")
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 300) // 2
        self.geometry(f"+{x}+{y}")
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create activation widgets."""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Enter Your License Key",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Instructions
        instructions = (
            "Please enter your license key below.\n"
            "Format: XXXX-XXXX-XXXX-XXXX-XXXX"
        )
        ctk.CTkLabel(
            main_frame,
            text=instructions,
            font=ctk.CTkFont(size=11)
        ).pack(pady=(0, 20))
        
        # License key entry
        self.key_entry = ctk.CTkEntry(
            main_frame,
            width=350,
            height=40,
            placeholder_text="XXXX-XXXX-XXXX-XXXX-XXXX",
            font=ctk.CTkFont(size=14)
        )
        self.key_entry.pack(pady=(0, 10))
        
        # Status label
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=10)
        )
        self.status_label.pack(pady=(0, 20))
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(10, 0))
        
        ctk.CTkButton(
            button_frame,
            text="Activate",
            command=self._activate,
            width=120,
            height=35
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Purchase License",
            command=self._purchase_license,
            width=140,
            height=35,
            fg_color="transparent",
            border_width=2
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=100,
            height=35,
            fg_color="gray"
        ).pack(side="left", padx=5)
    
    def _activate(self):
        """Activate the entered license key."""
        license_key = self.key_entry.get().strip().upper()
        
        if not license_key:
            self.status_label.configure(
                text="Please enter a license key",
                text_color="red"
            )
            return
        
        self.status_label.configure(text="Activating...", text_color="gray")
        self.update()
        
        success, message = self.license_manager.activate_commercial_license(license_key)
        
        if success:
            self.status_label.configure(
                text="✓ " + message,
                text_color="green"
            )
            self.license_key = license_key
            self.after(1500, self.destroy)
        else:
            self.status_label.configure(
                text="✗ " + message,
                text_color="red"
            )
    
    def _purchase_license(self):
        """Open website to purchase license."""
        try:
            webbrowser.open(f"{APP_WEBSITE}/purchase")
        except:
            messagebox.showinfo(
                "Purchase License",
                f"Visit {APP_WEBSITE}/purchase to buy a license."
            )


class UpgradePromptDialog(ctk.CTkToplevel):
    """Dialog prompting users to upgrade from trial."""
    
    def __init__(self, parent, days_left: int):
        super().__init__(parent)
        
        self.result = None
        
        self.title("Upgrade to Full Version")
        self.geometry("500x400")
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 500) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 400) // 2
        self.geometry(f"+{x}+{y}")
        
        self._create_widgets(days_left)
    
    def _create_widgets(self, days_left: int):
        """Create upgrade prompt widgets."""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        if days_left > 0:
            title_text = f"Trial Period: {days_left} {'day' if days_left == 1 else 'days'} remaining"
        else:
            title_text = "Trial Period Expired"
        
        title_label = ctk.CTkLabel(
            main_frame,
            text=title_text,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Message
        message = (
            "Upgrade to the full version to unlock all features and continue\n"
            "using SQL Schema Compare Pro without limitations."
        )
        ctk.CTkLabel(
            main_frame,
            text=message,
            font=ctk.CTkFont(size=12)
        ).pack(pady=(0, 20))
        
        # Features comparison
        features_frame = ctk.CTkFrame(main_frame)
        features_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        ctk.CTkLabel(
            features_frame,
            text="Full Version Features:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 10))
        
        for feature in FEATURES["professional"][:6]:  # Show first 6 features
            ctk.CTkLabel(
                features_frame,
                text=f"✓ {feature}",
                font=ctk.CTkFont(size=11),
                anchor="w"
            ).pack(padx=20, pady=2, anchor="w")
        
        # Action buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(10, 0))
        
        ctk.CTkButton(
            button_frame,
            text="Purchase License",
            command=lambda: self._set_result("purchase"),
            width=150,
            height=40
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Enter License Key",
            command=lambda: self._set_result("activate"),
            width=150,
            height=40,
            fg_color="transparent",
            border_width=2
        ).pack(side="left", padx=5)
        
        if days_left > 0:
            ctk.CTkButton(
                button_frame,
                text="Continue Trial",
                command=lambda: self._set_result("continue"),
                width=120,
                height=40,
                fg_color="gray"
            ).pack(side="left", padx=5)
    
    def _set_result(self, result: str):
        """Set result and close dialog."""
        self.result = result
        self.destroy()


def show_feature_locked_message(parent, feature_name: str, required_edition: str = "professional"):
    """Show a message that a feature is locked in trial version."""
    message = (
        f"The '{feature_name}' feature is only available in the\n"
        f"{required_edition.title()} edition or higher.\n\n"
        "Would you like to upgrade now?"
    )
    
    result = messagebox.askyesno(
        "Feature Locked",
        message,
        icon=messagebox.INFO
    )
    
    if result:
        try:
            webbrowser.open(f"{APP_WEBSITE}/purchase")
        except:
            pass
    
    return result
