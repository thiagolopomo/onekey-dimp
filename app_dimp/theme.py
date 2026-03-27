#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Theme OneKey Payments DIMP - Premium Edition
Navy #1B2E5C | Teal #4FB8A8 | Tipografia refinada
"""


def build_app_qss(font_family: str = "Segoe UI") -> str:
    ff = font_family or "Segoe UI"
    return f"""
    * {{
        font-family: '{ff}', 'Segoe UI', sans-serif;
    }}

    /* ── Shell ── */
    #ShellWindow {{
        background: qlineargradient(x1:0,y1:0,x2:0.3,y2:1,
            stop:0 #F0F4F8, stop:1 #E8EDF3);
    }}

    /* ── Top bar ── */
    #TopBar {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #0B1628, stop:0.7 #0F1D35, stop:1 #121F38);
        border: none;
    }}
    #TopBar QLabel {{
        color: white;
        background: transparent;
    }}

    /* ── Cards ── */
    #MainCard {{
        background: rgba(255, 255, 255, 1.0);
        border: 1px solid rgba(210, 218, 228, 0.9);
        border-radius: 16px;
    }}

    #MetricCard {{
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(229, 234, 240, 0.7);
        border-radius: 14px;
    }}

    #MetricCard:hover {{
        border-color: rgba(79, 184, 168, 0.4);
    }}

    /* ── Botao principal ── */
    #BtnPrimary {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 #1B6B5F, stop:0.5 #1F7A6D, stop:1 #23897B);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 10px 32px;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    #BtnPrimary:hover {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 #155A50, stop:0.5 #1A6B5F, stop:1 #1F7A6D);
    }}
    #BtnPrimary:pressed {{
        background: #104A42;
    }}
    #BtnPrimary:disabled {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #A0C4BE, stop:1 #B0D0CA);
        color: rgba(255,255,255,0.8);
    }}

    /* ── Botao secundario ── */
    #BtnSecondary {{
        background: rgba(248, 250, 252, 0.8);
        color: #475569;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 10px 24px;
        font-size: 12px;
        font-weight: 500;
    }}
    #BtnSecondary:hover {{
        background: white;
        border-color: #4FB8A8;
        color: #3DA898;
    }}

    #BtnOpen {{
        background: rgba(27, 46, 92, 0.06);
        color: #1B2E5C;
        border: 1px solid rgba(27, 46, 92, 0.15);
        border-radius: 12px;
        padding: 10px 24px;
        font-size: 12px;
        font-weight: 600;
    }}
    #BtnOpen:hover {{
        background: rgba(27, 46, 92, 0.1);
        border-color: rgba(27, 46, 92, 0.25);
    }}

    /* ── Path input ── */
    #PathInput {{
        background: rgba(248, 250, 252, 0.9);
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 10px 16px;
        font-size: 12px;
        color: #334155;
        selection-background-color: rgba(79, 184, 168, 0.2);
    }}
    #PathInput:focus {{
        border-color: #4FB8A8;
        background: white;
    }}

    /* ── Log ── */
    #LogArea {{
        background: #0F172A;
        color: #E8ECF1;
        border: none;
        border-radius: 14px;
        padding: 16px;
        font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
        font-size: 10px;
        line-height: 1.5;
        selection-background-color: rgba(79, 184, 168, 0.3);
    }}

    /* ── Progress ── */
    QProgressBar {{
        background: rgba(226, 232, 240, 0.6);
        border: none;
        border-radius: 5px;
        text-align: center;
        font-size: 0px;
    }}
    QProgressBar::chunk {{
        border-radius: 5px;
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #1B2E5C, stop:0.4 #4FB8A8, stop:0.7 #5CC3B3, stop:1 #6CCABC);
    }}

    /* ── Footer ── */
    #Footer {{
        background: transparent;
        border-top: 1px solid rgba(229, 234, 240, 0.6);
    }}
    #Footer QLabel {{
        color: #94A3B8;
        font-size: 10px;
        background: transparent;
    }}

    /* ── Scrollbar ── */
    QScrollBar:vertical {{
        width: 5px;
        background: transparent;
        margin: 4px 0;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(100, 116, 139, 0.25);
        border-radius: 2px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(100, 116, 139, 0.45);
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* ── Tooltips ── */
    QToolTip {{
        background: #1E293B;
        color: #E2E8F0;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 11px;
    }}
    """
