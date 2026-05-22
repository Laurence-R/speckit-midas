"""WatchlistPage: manage tracked stocks with add, remove, search, and memo."""
from __future__ import annotations

import tkinter.messagebox

import customtkinter as ctk

from midas.exceptions import WatchlistLimitError
from midas.ui.theme import get_palette, make_font
from midas.viewmodels.watchlist_vm import WatchlistViewModel

_WATCHLIST_MAX = 30


class WatchlistPage(ctk.CTkFrame):
    """Tracked stock list with CRUD and real-time search filtering."""

    def __init__(
        self,
        master,
        view_model: WatchlistViewModel | None = None,
        controller=None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._vm = view_model
        self._controller = controller
        self._build()

    def _build(self) -> None:
        palette = get_palette()
        self.configure(fg_color=palette["bg_primary"])

        ctk.CTkLabel(
            self,
            text="自選股清單",
            font=make_font(size=18, weight="bold"),
            text_color=palette["text_primary"],
        ).pack(anchor="w", padx=20, pady=(16, 8))

        # Add row
        add_frame = ctk.CTkFrame(self, fg_color="transparent")
        add_frame.pack(fill="x", padx=20, pady=(0, 8))

        self._add_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="輸入股票代號，例如 2330",
            width=200,
            font=make_font(size=13),
        )
        self._add_entry.pack(side="left")
        self._add_entry.bind("<Return>", lambda _: self._on_add())

        ctk.CTkButton(
            add_frame, text="新增", width=80, font=make_font(size=13),
            command=self._on_add,
        ).pack(side="left", padx=(8, 0))

        self._limit_label = ctk.CTkLabel(
            add_frame, text="", font=make_font(size=11),
            text_color=palette["error"],
        )
        self._limit_label.pack(side="left", padx=(8, 0))

        # Search
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(0, 8))

        self._search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="搜尋股票代號或名稱",
            width=300,
            font=make_font(size=13),
        )
        self._search_entry.pack(side="left")
        self._search_entry.bind("<KeyRelease>", lambda *_: self._refresh_list())

        # List
        self._list_frame = ctk.CTkScrollableFrame(
            self, fg_color=palette["bg_primary"],
        )
        self._list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        self._refresh_list()

    def load(self) -> None:
        self._refresh_list()

    def _refresh_list(self) -> None:
        palette = get_palette()
        for w in self._list_frame.winfo_children():
            w.destroy()

        if self._vm is None:
            return

        query = self._search_entry.get().strip() if hasattr(self, "_search_entry") else ""
        stocks = self._vm.search(query) if query else self._vm.get_all()

        count = len(self._vm.get_all())
        if hasattr(self, "_limit_label"):
            if count >= _WATCHLIST_MAX:
                self._limit_label.configure(text=f"已達上限 {_WATCHLIST_MAX} 檔")
            else:
                self._limit_label.configure(text=f"{count}/{_WATCHLIST_MAX} 檔")

        if not stocks:
            ctk.CTkLabel(
                self._list_frame,
                text="尚未新增自選股" if not query else "找不到結果",
                text_color=palette["text_secondary"],
                font=make_font(size=13),
            ).pack(pady=40)
            return

        for stock in stocks:
            row = ctk.CTkFrame(
                self._list_frame, fg_color=palette["bg_secondary"], corner_radius=6,
            )
            row.pack(fill="x", pady=3)

            # Symbol + name
            ctk.CTkLabel(
                row,
                text=f"{stock.symbol}  {stock.company_name}",
                font=make_font(size=13),
                text_color=palette["text_primary"],
            ).pack(side="left", padx=12, pady=8)

            # Current price
            if stock.last_price is not None:
                chg = stock.last_price_change_pct
                sign = "+" if chg is not None and chg >= 0 else ""
                chg_text = f"  {sign}{chg:.2f}%" if chg is not None else ""
                price_color = (
                    palette["sentiment_positive"] if (chg or 0) >= 0
                    else palette["sentiment_negative"]
                )
                ctk.CTkLabel(
                    row,
                    text=f"{stock.last_price:,.2f}{chg_text}",
                    font=make_font(size=12),
                    text_color=price_color,
                ).pack(side="left", padx=(0, 8), pady=8)

            sym = stock.symbol

            # Delete button
            ctk.CTkButton(
                row,
                text="刪除",
                width=60,
                font=make_font(size=12),
                fg_color=palette["error"],
                hover_color="#991B1B",
                command=lambda s=sym: self._on_delete(s),
            ).pack(side="right", padx=8, pady=6)

            # Detail button
            if self._controller:
                ctk.CTkButton(
                    row,
                    text="詳情",
                    width=60,
                    font=make_font(size=12),
                    command=lambda s=sym: self._controller.show_stock_detail(s),
                ).pack(side="right", padx=(0, 4), pady=6)

            # Memo
            memo_var = ctk.StringVar(value=stock.memo or "")
            memo_frame = ctk.CTkFrame(row, fg_color="transparent")
            memo_frame.pack(side="right", padx=(0, 8), pady=6)
            ctk.CTkLabel(
                memo_frame, text="備註：",
                font=make_font(size=11),
                text_color=palette["text_secondary"],
            ).pack(side="left")
            memo_entry = ctk.CTkEntry(
                memo_frame, textvariable=memo_var, width=180,
                font=make_font(size=12),
                placeholder_text="輸入備註…",
            )
            memo_entry.pack(side="left")
            memo_entry.bind(
                "<FocusOut>",
                lambda e, s=sym, v=memo_var: self._on_memo_save(s, v.get()),
            )

    def _on_add(self) -> None:
        symbol = self._add_entry.get().strip()
        if not symbol or self._vm is None:
            return
        try:
            self._vm.add(symbol)
            self._add_entry.delete(0, "end")
            self._refresh_list()
        except WatchlistLimitError as exc:
            self._limit_label.configure(text=str(exc))
        except ValueError as exc:
            self._limit_label.configure(text=str(exc))

    def _on_delete(self, symbol: str) -> None:
        if self._vm is None:
            return
        if tkinter.messagebox.askyesno("確認刪除", f"確定要移除 {symbol} 嗎？"):
            self._vm.remove(symbol)
            self._refresh_list()

    def _on_memo_save(self, symbol: str, memo: str) -> None:
        if self._vm is None:
            return
        try:
            self._vm.update_memo(symbol, memo)
        except ValueError:
            pass
