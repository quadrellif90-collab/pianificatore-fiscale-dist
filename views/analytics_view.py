"""Vista Analytics: dashboard metriche e report utilizzo."""
from __future__ import annotations

import customtkinter as ctk
import threading
from datetime import datetime, timedelta

from analytics import get_analytics, EventType
from models.theme import C
from views.widgets import Card, SectionHeader, GhostButton, PrimaryButton


class AnalyticsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.analytics = get_analytics("PianificatoreFiscale")
        self._build()
        self._refresh_data()
    
    def _build(self):
        SectionHeader(self, "📊 Analytics Dashboard",
                      "Metriche utilizzo, performance e reportistica.")
        
        # Cards KPI
        kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 16))
        
        self.card_sessions = self._kpi_card(kpi_frame, "📈", "Sessioni (30g)", "–", C["primary"], 0)
        self.card_events = self._kpi_card(kpi_frame, "📊", "Eventi totali", "–", C["accent"], 1)
        self.card_ai_queries = self._kpi_card(kpi_frame, "🤖", "Query AI", "–", C["success"], 2)
        self.card_avg_duration = self._kpi_card(kpi_frame, "⚡", "Durata media", "–", C["warning"], 3)
        
        # Azioni
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 12))
        PrimaryButton(action_frame, text="🔄 Aggiorna", width=120,
                     command=self._refresh_data).pack(side="left", padx=6)
        GhostButton(action_frame, text="📊 Esporta Report", width=140,
                   command=self._export_report).pack(side="left", padx=6)
        GhostButton(action_frame, text="🧹 Pulisci Dati", width=140,
                   command=self._clear_data).pack(side="left", padx=6)
        
        # Tabella eventi per tipo
        ctk.CTkLabel(self, text="Eventi per tipo (ultimi 30 giorni)", anchor="w",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(fill="x", pady=(4, 4))
        
        table_card = Card(self)
        table_card.pack(fill="x", pady=(0, 12))
        
        self.events_tree = self._create_tree(table_card, [
            ("tipo", "Tipo Evento", 250),
            ("count", "Conteggio", 100),
            ("avg_duration", "Durata media (ms)", 120),
            ("success_rate", "Successo %", 100),
        ])
        
        # Trend giornaliero
        ctk.CTkLabel(self, text="Trend giornaliero (ultimi 30 giorni)", anchor="w",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(fill="x", pady=(4, 4))
        
        self.trend_card = Card(self, height=200)
        self.trend_card.pack(fill="x", pady=(0, 12))
        self.trend_frame = ctk.CTkFrame(self.trend_card, fg_color="transparent")
        self.trend_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # AI Usage
        ctk.CTkLabel(self, text="Utilizzo AI", anchor="w",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(fill="x", pady=(4, 4))
        
        ai_card = Card(self)
        ai_card.pack(fill="x", pady=(0, 12))
        self.ai_frame = ctk.CTkFrame(ai_card, fg_color="transparent")
        self.ai_frame.pack(fill="x", padx=18, pady=12)
    
    def _kpi_card(self, parent, icon, label, value, color, col):
        card = Card(parent, width=250, height=112)
        card.grid(row=0, column=col, padx=6)
        card.pack_propagate(False)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 0))
        chip = ctk.CTkFrame(top, width=40, height=40, corner_radius=10, fg_color=C["chip_bg"])
        chip.pack(side="left")
        chip.pack_propagate(False)
        ctk.CTkLabel(chip, text=icon, font=ctk.CTkFont(size=20)).pack(expand=True)
        ctk.CTkLabel(top, text=label, font=ctk.CTkFont(size=12), text_color=C["muted"]).pack(side="left", padx=(10, 0))
        val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=24, weight="bold"), text_color=color)
        val.pack(anchor="w", padx=14, pady=(6, 10))
        return val
    
    def _create_tree(self, parent, columns):
        cols = [c[0] for c in columns]
        tree = ctk.CTkFrame(parent, fg_color="transparent")
        tree.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Use CTkScrollableFrame with labels
        frame = ctk.CTkScrollableFrame(parent, height=200)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Header
        header = ctk.CTkFrame(frame, fg_color=C["head_bg"], corner_radius=8)
        header.pack(fill="x", pady=(0, 4))
        for i, (_, t, w) in enumerate(columns):
            ctk.CTkLabel(header, text=t, width=w, anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=C["head_fg"]).pack(side="left", padx=6, pady=6)
        
        self._tree_rows_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._tree_rows_frame.pack(fill="both", expand=True)
        
        return frame
    
    def _refresh_data(self):
        """Aggiorna dati analytics in background."""
        def worker():
            try:
                stats = self.analytics.get_usage_report(30)
                session_stats = self.analytics.get_session_stats()
                
                # Update UI in main thread
                self.after(0, lambda: self._update_ui(stats, session_stats))
            except Exception as e:
                self.after(0, lambda: self._show_error(str(e)))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _update_ui(self, stats: dict, session_stats: dict):
        """Aggiorna UI con dati."""
        # KPI Cards
        self.card_sessions.configure(text=str(stats.get("total_sessions", 0)))
        
        total_events = sum(e["count"] for e in stats.get("events_by_type", []))
        self.card_events.configure(text=f"{total_events:,}")
        
        ai_events = next((e for e in stats.get("events_by_type", []) 
                         if "ai" in e["event_type"] or "query" in e["event_type"]), None)
        self.card_ai_queries.configure(text=str(ai_events["count"] if ai_events else 0))
        
        avg_dur = sum(e.get("avg_duration", 0) or 0 for e in stats.get("events_by_type", []))
        count_types = len(stats.get("events_by_type", []))
        self.card_avg_duration.configure(text=f"{int(avg_dur / count_types) if count_types else 0} ms")
        
        # Update events tree
        self._update_events_tree(stats.get("events_by_type", []))
        self._update_trend_chart(stats.get("daily_trend", []))
        self._update_ai_usage(stats.get("events_by_type", []))
    
    def _update_events_tree(self, events):
        for widget in self._tree_rows_frame.winfo_children():
            widget.destroy()
        
        for e in events:
            row = ctk.CTkFrame(self._tree_rows_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            vals = [
                e["event_type"].replace("_", " ").title(),
                str(e["count"]),
                f"{int(e.get('avg_duration', 0) or 0)} ms",
                f"{float(e.get('success_rate', 100)):.1f}%"
            ]
            widths = [250, 100, 120, 100]
            for i, (v, w) in enumerate(zip(vals, [250, 100, 120, 100])):
                color = C["success"] if i == 3 and float(e.get('success_rate', 100)) > 95 else None
                ctk.CTkLabel(self._tree_rows_frame, text=v, width=w, anchor="w",
                             font=ctk.CTkFont(size=11), text_color=color).pack(side="left", padx=6)
    
    def _update_trend_chart(self, daily):
        for widget in self.trend_frame.winfo_children():
            widget.destroy()
        
        if not daily:
            ctk.CTkLabel(self.trend_frame, text="Nessun dato disponibile",
                         text_color=C["muted"]).pack(pady=20)
            return
        
        # Simple bar chart
        max_count = max(d["count"] for d in daily) if daily else 1
        
        for d in daily[-30:]:  # Last 30 days
            bar_frame = ctk.CTkFrame(self.trend_frame, fg_color="transparent")
            bar_frame.pack(fill="x", pady=1)
            
            ctk.CTkLabel(bar_frame, text=d["day"], width=100, anchor="w",
                         font=ctk.CTkFont(size=10)).pack(side="left", padx=6)
            
            bar_width = max(10, int(200 * d["count"] / max_count))
            bar = ctk.CTkFrame(bar_frame, width=bar_width, height=16,
                              corner_radius=4, fg_color=C["primary"])
            bar.pack(side="left", padx=6)
            
            ctk.CTkLabel(bar_frame, text=str(d["count"]), width=50, anchor="w",
                         font=ctk.CTkFont(size=10)).pack(side="left", padx=6)
    
    def _update_ai_usage(self, events):
        for widget in self.ai_frame.winfo_children():
            widget.destroy()
        
        ai_events = [e for e in events if "ai" in e["event_type"] or "query" in e["event_type"]]
        
        if not ai_events:
            ctk.CTkLabel(self.ai_frame, text="Nessun utilizzo AI registrato",
                         text_color=C["muted"]).pack(pady=20)
            return
        
        for e in ai_events:
            row = ctk.CTkFrame(self.ai_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=e["event_type"].replace("_", " ").title(),
                         width=250, anchor="w", font=ctk.CTkFont(size=11)).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=str(e["count"]), width=100, anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=C["primary"]).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=f"{float(e.get('success_rate', 100)):.1f}%",
                         width=100, anchor="w", font=ctk.CTkFont(size=11)).pack(side="left", padx=6)
    
    def _export_report(self):
        try:
            data = self.analytics.export_analytics(30)
            import json
            from tkinter import filedialog
            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Esporta Analytics Report"
            )
            if filepath:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                import tkinter.messagebox as mb
                mb.showinfo("Export", f"Report esportato in:\n{filepath}")
        except Exception as e:
            import tkinter.messagebox as mb
            mb.showerror("Errore", f"Errore export: {e}")
    
    def _clear_data(self):
        import tkinter.messagebox as mb
        if mb.askyesno("Conferma", "Eliminare tutti i dati analytics?"):
            # TODO: implement clear
            mb.showinfo("Info", "Funzione da implementare")
    
    def _show_error(self, msg):
        import tkinter.messagebox as mb
        mb.showerror("Errore Analytics", msg)
    
    def refresh(self):
        self._refresh_data()