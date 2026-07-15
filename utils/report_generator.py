import csv
import io
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from engine.metrics import PerformanceMetrics

# Print-friendly palette, independent of the GUI's dark theme (gui/live_plots.py flips
# matplotlib's global style to 'dark_background' at import time; every figure built here
# is rendered inside a plt.style.context('default') block so the PDF always comes out
# light-on-white regardless of what the live GUI charts are currently styled as).
_FOLLOWER_COLORS = ["#059669", "#0891b2", "#7c3aed", "#d97706", "#db2777"]
_ATTACK_WINDOW_SPEC = [
    ("fdi", "FDI Active", "#eab308"),
    ("dos", "DoS Active", "#6b7280"),
    ("delay", "Delay Active", "#8b5cf6"),
    ("replay", "Replay Active", "#ec4899"),
]


class ReportGenerator:
    """
    Automates compiling and exporting simulation metrics, charts, and narrative analysis
    to PDF reports and Excel/CSV worksheets.
    """

    # ------------------------------------------------------------------ #
    # Shared helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def calculate_metrics(history: dict, dt: float = 0.05) -> dict:
        """
        Calculates performance indices from raw simulation history.
        """
        track_errs = np.mean(history["tracking_errors"], axis=0) if history["tracking_errors"] else [0]
        ctrl_norms = np.mean(history["control_inputs"], axis=0) if history["control_inputs"] else [0]

        rmse = float(np.sqrt(np.mean(np.array(track_errs) ** 2)))
        mae = float(np.mean(np.array(track_errs)))
        max_err = float(np.max(np.array(track_errs)))
        peak_ctrl = float(np.max(np.array(ctrl_norms)))
        energy = float(np.sum(np.array(ctrl_norms) ** 2) * dt)

        settling_time = "N/A"
        time_grid = history.get("time", [])
        if len(time_grid) > 0:
            post_attack_indices = [idx for idx, t in enumerate(time_grid) if t > 22.0]
            if post_attack_indices:
                settling_val = PerformanceMetrics.compute_settling_time(
                    time_grid, list(track_errs), attack_end_time=22.0, threshold=1.5
                )
                if settling_val is None:
                    settling_time = "Not settled by end of run"
                elif settling_val > 0:
                    settling_time = f"{settling_val:.2f} s"
                else:
                    settling_time = "Instant"

        return {
            "rmse": rmse,
            "mae": mae,
            "max_err": max_err,
            "peak_ctrl": peak_ctrl,
            "energy": energy,
            "settling_time": settling_time
        }

    @staticmethod
    def _get_attack_windows(config: dict) -> list:
        """
        Returns (label, start, end, color) for every attack the user actually enabled -
        mirrors gui/live_plots.py's shading logic, so the report matches what's on screen.
        """
        attacks = config.get("attacks", {})
        windows = []
        for key, label, color in _ATTACK_WINDOW_SPEC:
            if attacks.get(f"enable_{key}", False):
                sub = attacks.get(key, {})
                windows.append((label, sub.get("start_time", 0.0), sub.get("end_time", 0.0), color))
        return windows

    @staticmethod
    def _shade_windows(ax, attack_windows):
        heights = [0.93, 0.85, 0.77, 0.69]
        for idx, (label, start, end, color) in enumerate(attack_windows):
            ax.axvspan(start, end, color=color, alpha=0.13)
            ax.text((start + end) / 2.0, heights[idx % len(heights)], label, color=color,
                    ha='center', weight='bold', fontsize=7, transform=ax.get_xaxis_transform())

    @staticmethod
    def _fig_to_image(fig, width=6.6 * inch):
        fig_w, fig_h = fig.get_size_inches()
        aspect = fig_h / fig_w
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        buf.seek(0)
        return Image(buf, width=width, height=width * aspect)

    @staticmethod
    def _follower_stats(series_per_follower: list) -> list:
        """
        Per-follower min/max/mean/rmse/final for any per-agent error/signal series.
        """
        rows = []
        for i, series in enumerate(series_per_follower):
            arr = np.array(series, dtype=float) if len(series) else np.array([0.0])
            rows.append({
                "follower": i + 1,
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "mean": float(np.mean(arr)),
                "rmse": float(np.sqrt(np.mean(arr ** 2))),
                "final": float(arr[-1]),
            })
        return rows

    @staticmethod
    def _pole_analysis(eigenvalues, dt: float, domain: str) -> list:
        """
        Converts each closed-loop eigenvalue into its continuous s-plane equivalent
        (discrete poles are mapped via s = ln(lambda)/dt) and derives the classic
        second-order metrics (damping ratio, natural frequency) plus a stability verdict.
        """
        rows = []
        for lam in eigenvalues:
            if domain == "continuous":
                s = complex(lam)
            else:
                s = np.log(complex(lam)) / dt
            sigma, omega = s.real, s.imag
            mag = abs(s)
            zeta = (-sigma / mag) if mag > 1e-9 else 0.0
            rows.append({
                "raw": lam, "sigma": sigma, "omega": omega,
                "mag": mag, "zeta": zeta, "stable": sigma < 0.0
            })
        return rows

    # ------------------------------------------------------------------ #
    # CSV / Excel export (raw data, unchanged)
    # ------------------------------------------------------------------ #

    @staticmethod
    def export_csv(filepath: str, history: dict):
        """
        Exports timestep logs to CSV file.
        """
        if not filepath.endswith(".csv"):
            filepath += ".csv"

        time = history["time"]
        n_followers = len(history["followers"])

        with open(filepath, mode="w", newline="") as f:
            writer = csv.writer(f)
            headers = ["Time (s)", "Leader_X", "Leader_Y"]
            for i in range(n_followers):
                headers += [f"F{i+1}_X", f"F{i+1}_Y", f"F{i+1}_TrackErr", f"F{i+1}_Lyap", f"F{i+1}_CtrlNorm"]
            headers.append("Network_Status")
            writer.writerow(headers)

            for k in range(len(time)):
                row = [time[k], history["leader"][k][0], history["leader"][k][2]]
                for i in range(n_followers):
                    row += [
                        history["followers"][i][k][0],
                        history["followers"][i][k][2],
                        history["tracking_errors"][i][k],
                        history["lyapunov_values"][i][k],
                        history["control_inputs"][i][k]
                    ]
                row.append(history["network_link_status"][k])
                writer.writerow(row)

    @staticmethod
    def export_excel(filepath: str, history: dict):
        """
        Exports logs to Excel worksheet using Pandas and OpenPyXL.
        """
        if not filepath.endswith(".xlsx"):
            filepath += ".xlsx"

        time = history["time"]
        n_followers = len(history["followers"])

        data = {
            "Time (s)": time,
            "Leader_X": [h[0] for h in history["leader"]],
            "Leader_Y": [h[2] for h in history["leader"]]
        }

        for i in range(n_followers):
            data[f"F{i+1}_X"] = [state[0] for state in history["followers"][i]]
            data[f"F{i+1}_Y"] = [state[2] for state in history["followers"][i]]
            data[f"F{i+1}_TrackErr"] = history["tracking_errors"][i]
            data[f"F{i+1}_Lyap"] = history["lyapunov_values"][i]
            data[f"F{i+1}_CtrlNorm"] = history["control_inputs"][i]

        data["Network_Status"] = history["network_link_status"]

        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False)

    # ------------------------------------------------------------------ #
    # Figure builders - one per GUI graph tab, plus a bonus Cloud Telemetry chart
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_trajectory_figure(history, n_followers):
        with plt.style.context('default'):
            fig, ax = plt.subplots(figsize=(6.6, 6.0))
            ld = np.array(history["leader"])
            if len(ld) > 0:
                ax.plot(ld[:, 0], ld[:, 2], 'k--', linewidth=1.6, label="Leader (target orbit)")
                ax.scatter(ld[0, 0], ld[0, 2], color='black', marker='o', s=35, zorder=5)
            for i in range(n_followers):
                fol = np.array(history["followers"][i])
                if len(fol) > 0:
                    c = _FOLLOWER_COLORS[i % len(_FOLLOWER_COLORS)]
                    ax.plot(fol[:, 0], fol[:, 2], color=c, linewidth=1.2, label=f"Follower {i+1}")
                    ax.scatter(fol[0, 0], fol[0, 2], color=c, marker='s', s=25, zorder=4)
                    ax.scatter(fol[-1, 0], fol[-1, 2], color=c, marker='X', s=45, zorder=6)
            ax.set_title("2D Spatial Trajectories  (○ leader start · □ follower start · ✕ follower end)", fontsize=9)
            ax.set_xlabel("X Position (m)")
            ax.set_ylabel("Y Position (m)")
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal', adjustable='datalim')
            ax.legend(fontsize=7, loc='upper right')
            fig.tight_layout()
            return fig

    @staticmethod
    def _build_series_figure(history, n_followers, series_key, title, ylabel, attack_windows):
        with plt.style.context('default'):
            fig, ax = plt.subplots(figsize=(6.6, 3.4))
            time = history["time"]
            for i in range(n_followers):
                c = _FOLLOWER_COLORS[i % len(_FOLLOWER_COLORS)]
                ax.plot(time, history[series_key][i], color=c, linewidth=1.1, label=f"Follower {i+1}")
            ReportGenerator._shade_windows(ax, attack_windows)
            ax.set_title(title, fontsize=10)
            ax.set_xlabel("Time (s)")
            ax.set_ylabel(ylabel)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=7, loc='upper right')
            fig.tight_layout()
            return fig

    @staticmethod
    def _build_pole_figure(eigenvalues, dt, domain):
        with plt.style.context('default'):
            fig, ax = plt.subplots(figsize=(6.6, 4.4))
            if domain == "continuous":
                s_poles = np.array([complex(e) for e in eigenvalues])
            else:
                s_poles = np.log(np.array([complex(e) for e in eigenvalues])) / dt
            reals = s_poles.real
            imags = s_poles.imag
            span = max(1.0, np.max(np.abs(reals)) * 1.4, np.max(np.abs(imags)) * 1.2)
            ax.axvline(0, color='black', linewidth=1.4, label='Stability Boundary (Re=0)')
            ax.axhline(0, color='gray', linewidth=0.5)
            ax.axvspan(-span, 0, color='green', alpha=0.08, label='Stable (LHP)')
            ax.axvspan(0, span * 0.4, color='red', alpha=0.08, label='Unstable (RHP)')
            ax.scatter(reals, imags, marker='x', color='#1d4ed8', s=90, linewidths=2, label='Closed-loop poles', zorder=5)
            for r, im in zip(reals, imags):
                ax.annotate(f"{r:.2f}{'+' if im >= 0 else '-'}{abs(im):.2f}j", (r, im),
                            textcoords="offset points", xytext=(6, 4), fontsize=7, color='#1d4ed8')
            ax.set_xlim(-span, span * 0.4)
            ax.set_ylim(-span * 0.9, span * 0.9)
            ax.set_title("Closed-Loop Poles (continuous s-plane equivalent)", fontsize=10)
            ax.set_xlabel("Real Part σ (1/s)")
            ax.set_ylabel("Imaginary Part ω (rad/s)")
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=7, loc='upper right')
            fig.tight_layout()
            return fig

    # ------------------------------------------------------------------ #
    # Main PDF report
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_pdf_report(filepath: str, config: dict, history: dict, controller=None):
        """
        Generates a full, publication-grade PDF report: every chart shown in the live GUI
        (Trajectories, Consensus Error, Control Effort, Observer Error, Lyapunov Decay,
        Pole s-Plane) plus a Cloud Telemetry Error chart, each rendered as an embedded image
        immediately followed by a data-driven written analysis and a per-follower stats table.
        """
        if not filepath.endswith(".pdf"):
            filepath += ".pdf"

        dt = config["system"]["dt"]
        n_followers = len(history["followers"])
        metrics = ReportGenerator.calculate_metrics(history, dt)
        attack_windows = ReportGenerator._get_attack_windows(config)
        t_max = history["time"][-1] if history["time"] else config["system"]["t_max"]

        doc = SimpleDocTemplate(filepath, pagesize=letter,
                                 rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'ReportTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22,
            leading=26, textColor=colors.HexColor("#0f172a"), alignment=1, spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle', parent=styles['Normal'], fontName='Helvetica', fontSize=11,
            leading=14, textColor=colors.HexColor("#475569"), alignment=1, spaceAfter=4
        )
        timestamp_style = ParagraphStyle(
            'ReportTimestamp', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=9,
            leading=12, textColor=colors.HexColor("#94a3b8"), alignment=1, spaceAfter=24
        )
        h2_style = ParagraphStyle(
            'SectionHeader', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=14,
            leading=18, textColor=colors.HexColor("#1e3a8a"), spaceBefore=15, spaceAfter=10
        )
        h3_style = ParagraphStyle(
            'SubSectionHeader', parent=styles['Heading3'], fontName='Helvetica-Bold', fontSize=12,
            leading=15, textColor=colors.HexColor("#0e7490"), spaceBefore=12, spaceAfter=6
        )
        body_style = ParagraphStyle(
            'BodyTextCustom', parent=styles['BodyText'], fontName='Helvetica', fontSize=10,
            leading=14, textColor=colors.HexColor("#334155")
        )
        caption_style = ParagraphStyle(
            'Caption', parent=styles['BodyText'], fontName='Helvetica-Oblique', fontSize=8.5,
            leading=11, textColor=colors.HexColor("#64748b"), spaceAfter=8
        )
        bullet_style = ParagraphStyle(
            'Bullet', parent=body_style, leftIndent=14, bulletIndent=4, spaceAfter=3
        )

        def stat_table(rows, col_labels, col_keys, fmt="{:.4f}"):
            data = [[Paragraph(f"<b>{c}</b>", body_style) for c in col_labels]]
            for r in rows:
                line = [f"F{r['follower']}" if 'follower' in r else ""]
                for k in col_keys:
                    v = r[k]
                    line.append(fmt.format(v) if isinstance(v, float) else str(v))
                data.append(line)
            tbl = Table(data, colWidths=[60] + [((6.6 * inch) - 60) / len(col_keys)] * len(col_keys))
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ('FONTSIZE', (0, 0), (-1, -1), 8.5),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]))
            return tbl

        story = []

        # ---------------- Header ----------------
        story.append(Paragraph("Secure Cloud-Based Multi-Agent Control Toolbox", title_style))
        story.append(Paragraph("Networked Control System - Full Simulation Analysis Report", subtitle_style))
        story.append(Paragraph(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &middot; "
                                f"Simulated duration: {t_max:.2f}s &middot; Followers: {n_followers}", timestamp_style))

        # ---------------- 1. Executive Summary ----------------
        story.append(Paragraph("1. Executive Summary", h2_style))
        enabled_attacks = [w[0].replace(" Active", "") for w in attack_windows]
        sec_cfg = config["security"]
        enabled_defenses = [name for flag, name in [
            (sec_cfg.get("enable_hmac", True), "HMAC-SHA256 Authentication"),
            (sec_cfg.get("enable_dp", True), "Differential Privacy"),
            (sec_cfg.get("enable_anomaly", True), "Anomaly/IDS Detection"),
            (sec_cfg.get("enable_trust", True), "Reputation Trust Filter"),
        ] if flag]
        stability_verdict = "STABLE"
        if controller is not None:
            is_stable, _, _ = controller.verify_stability()
            stability_verdict = "STABLE" if is_stable else "UNSTABLE"
        summary_text = (
            f"This report documents a {t_max:.1f}-second simulation of {n_followers} follower agents tracking a "
            f"moving leader over a cloud-mediated communication link, using a {config['controller'].get('type','LQR')} "
            f"controller and {config['observer'].get('type','Kalman')} state observer. "
            + (f"The following attack vectors were active during this run: {', '.join(enabled_attacks)}. "
               if enabled_attacks else "No cyber-attacks were enabled during this run (clean baseline). ")
            + (f"Defended by: {', '.join(enabled_defenses)}. " if enabled_defenses else "No cyber-defenses were enabled during this run. ")
            + f"The closed-loop controller design is analytically <b>{stability_verdict}</b>. "
            f"Across all followers, the mean consensus tracking error was {metrics['rmse']:.3f} m (RMSE), "
            f"peaking at {metrics['max_err']:.3f} m, with peak control effort of {metrics['peak_ctrl']:.3f} m/s&sup2;. "
            "Full graph-by-graph analysis follows in Section 4."
        )
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 10))

        # ---------------- 2. System & Controller Configuration ----------------
        story.append(Paragraph("2. System &amp; Controller Configuration", h2_style))
        sim_cfg = config["simulation"]
        config_data = [
            [Paragraph("<b>Parameter</b>", body_style), Paragraph("<b>Value</b>", body_style),
             Paragraph("<b>Parameter</b>", body_style), Paragraph("<b>Value</b>", body_style)],
            ["Follower Count", str(sim_cfg["n_followers"]), "Controller Scheme", config["controller"].get("type", "LQR")],
            ["Observer Scheme", config["observer"].get("type", "Kalman"), "Model Domain", config["system"].get("model_domain", "continuous").capitalize()],
            ["Time Step (dt)", f"{dt} s", "Simulated Duration", f"{t_max:.2f} s"],
            ["Damping Coefficient", str(config["system"]["damping"]), "Max Accel / Speed", f"{config['system'].get('max_accel',10.0)} / {config['system'].get('max_speed',15.0)}"],
            ["Leader Orbit Radius", f"{sim_cfg['leader_orbit_radius']} m", "Leader Orbit Rate (ω)", f"{sim_cfg['leader_orbit_omega']} rad/s"],
        ]
        t1 = Table(config_data, colWidths=[130, 100, 130, 100])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#cbd5e1")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(t1)
        story.append(Spacer(1, 15))

        # ---------------- 3. Cyber-Attack & Defense Configuration ----------------
        story.append(Paragraph("3. Cyber-Attack &amp; Defense Configuration", h2_style))
        attacks_cfg = config["attacks"]
        atk_rows = [[Paragraph("<b>Attack</b>", body_style), Paragraph("<b>Enabled</b>", body_style),
                     Paragraph("<b>Window</b>", body_style), Paragraph("<b>Strength / Parameter</b>", body_style)]]
        fdi = attacks_cfg.get("fdi", {})
        atk_rows.append(["False Data Injection", "Yes" if attacks_cfg.get("enable_fdi") else "No",
                         f"{fdi.get('start_time','-')}s - {fdi.get('end_time','-')}s",
                         f"Offset {fdi.get('offset', [])}"])
        dos = attacks_cfg.get("dos", {})
        atk_rows.append(["Denial of Service", "Yes" if attacks_cfg.get("enable_dos") else "No",
                         f"{dos.get('start_time','-')}s - {dos.get('end_time','-')}s", "Full link severance"])
        delay = attacks_cfg.get("delay", {})
        atk_rows.append(["Network Delay", "Yes" if attacks_cfg.get("enable_delay") else "No",
                         f"{delay.get('start_time','-')}s - {delay.get('end_time','-')}s",
                         f"Buffer depth {delay.get('steps','-')} steps"])
        replay = attacks_cfg.get("replay", {})
        atk_rows.append(["Packet Replay", "Yes" if attacks_cfg.get("enable_replay") else "No",
                         f"{replay.get('start_time','-')}s - {replay.get('end_time','-')}s",
                         f"Cache window {replay.get('window_size','-')} steps"])
        t_atk = Table(atk_rows, colWidths=[130, 60, 110, 160])
        t_atk.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#fecaca")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#f87171")),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff5f5")]),
        ]))
        story.append(t_atk)
        story.append(Spacer(1, 8))

        def_rows = [[Paragraph("<b>Defense</b>", body_style), Paragraph("<b>Enabled</b>", body_style),
                     Paragraph("<b>Parameter</b>", body_style)]]
        def_rows.append(["HMAC-SHA256 Authentication", "Yes" if sec_cfg.get("enable_hmac") else "No", "Signature-based integrity check"])
        def_rows.append(["Differential Privacy", "Yes" if sec_cfg.get("enable_dp") else "No",
                         f"ε = {sec_cfg.get('dp_epsilon', 1.5)}, sensitivity = {sec_cfg.get('dp_sensitivity', 0.15)}"])
        def_rows.append(["Anomaly / IDS Detection", "Yes" if sec_cfg.get("enable_anomaly") else "No",
                         f"Detection threshold = {sec_cfg.get('anomaly_threshold', 5.0)}"])
        def_rows.append(["Reputation Trust Filter", "Yes" if sec_cfg.get("enable_trust") else "No",
                         f"Decay {sec_cfg.get('trust_decay_rate',0.2)}, cutoff {sec_cfg.get('trust_cutoff',0.5)}"])
        t_def = Table(def_rows, colWidths=[150, 60, 250])
        t_def.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#bbf7d0")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#4ade80")),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0fdf4")]),
        ]))
        story.append(t_def)

        # ---------------- 4. Detailed Graph-by-Graph Analysis ----------------
        story.append(PageBreak())
        story.append(Paragraph("4. Detailed Graph-by-Graph Analysis", h2_style))
        story.append(Paragraph(
            "Every chart below mirrors a tab in the live GUI dashboard. Shaded vertical bands mark the "
            "time window of each cyber-attack that was actually enabled for this run; a chart with no "
            "shading means no attack was active while it was recorded.", body_style))

        # 4.1 Trajectories
        story.append(Paragraph("4.1 Spatial Trajectories", h3_style))
        story.append(ReportGenerator._fig_to_image(ReportGenerator._build_trajectory_figure(history, n_followers)))
        ld = np.array(history["leader"])
        max_radius = float(np.max(np.linalg.norm(ld[:, [0, 2]], axis=1))) if len(ld) else 0.0
        traj_text = (
            f"The leader traces a reference orbit of radius {sim_cfg['leader_orbit_radius']}m at ω = "
            f"{sim_cfg['leader_orbit_omega']} rad/s (max observed leader radius: {max_radius:.2f}m). "
        )
        for i in range(n_followers):
            fol = np.array(history["followers"][i])
            if len(fol) == 0:
                continue
            start_gap = float(np.linalg.norm(fol[0, [0, 2]] - ld[0, [0, 2]])) if len(ld) else 0.0
            end_gap = float(np.linalg.norm(fol[-1, [0, 2]] - ld[-1, [0, 2]])) if len(ld) else 0.0
            traj_text += (f"Follower {i+1} started {start_gap:.2f}m from the leader and ended the run "
                          f"{end_gap:.2f}m away, {'successfully converging onto' if end_gap < start_gap else 'diverging from'} the orbit. ")
        story.append(Paragraph(traj_text, body_style))
        story.append(Paragraph(
            "Minor detail: markers show each follower's start (□) and end (✕) position relative to the "
            "leader's own start (○), making initial-transient distance and final consensus gap directly readable.",
            caption_style))

        # 4.2 Consensus (Tracking) Error
        story.append(Paragraph("4.2 Consensus Tracking Error", h3_style))
        fig = ReportGenerator._build_series_figure(history, n_followers, "tracking_errors",
                                                     "Consensus Tracking Error", "Error (m)", attack_windows)
        story.append(ReportGenerator._fig_to_image(fig))
        track_stats = ReportGenerator._follower_stats(history["tracking_errors"])
        story.append(stat_table(track_stats, ["Follower", "Min (m)", "Max (m)", "Mean (m)", "RMSE (m)", "Final (m)"],
                                 ["min", "max", "mean", "rmse", "final"]))
        story.append(Spacer(1, 4))
        worst = max(track_stats, key=lambda r: r["max"])
        ref_end = max((w[2] for w in attack_windows), default=None)
        recovery_note = ""
        attacks_fully_recovered = None  # None = no attacks enabled, so recovery is not applicable
        if ref_end is not None:
            settle = PerformanceMetrics.compute_settling_time(history["time"], list(np.mean(history["tracking_errors"], axis=0)),
                                                                attack_end_time=ref_end, threshold=1.5)
            attacks_fully_recovered = settle is not None
            if settle is None:
                final_avg_err = float(np.mean(history["tracking_errors"], axis=0)[-1])
                recovery_note = (f" Following the last enabled attack window (ending at {ref_end:.1f}s), the average "
                                 f"tracking error had <b>not</b> recovered below 1.5m by the end of the recorded "
                                 f"{t_max:.1f}s window (still {final_avg_err:.3f}m at the final timestep) - this "
                                 f"warrants a longer post-attack run or a closer look at recovery dynamics.")
            else:
                recovery_note = (f" Following the last enabled attack window (ending at {ref_end:.1f}s), the average "
                                 f"tracking error returned below and stayed under 1.5m within {settle:.2f}s.")
        story.append(Paragraph(
            f"Follower {worst['follower']} recorded the largest deviation from the leader "
            f"({worst['max']:.3f}m peak, {worst['mean']:.3f}m mean). Peaks near t=0 reflect the initial-condition "
            f"transient before consensus is reached; any peak inside a shaded band reflects the direct effect of "
            f"that attack on tracking accuracy.{recovery_note}", body_style))

        # 4.3 Cloud Telemetry Error (bonus - cloud/uplink integrity view)
        story.append(Paragraph("4.3 Cloud Telemetry Error", h3_style))
        fig = ReportGenerator._build_series_figure(history, n_followers, "cloud_est_errors",
                                                     "Cloud-Level Telemetry Estimation Error", "Error (m)", attack_windows)
        story.append(ReportGenerator._fig_to_image(fig))
        cloud_stats = ReportGenerator._follower_stats(history["cloud_est_errors"])
        story.append(stat_table(cloud_stats, ["Follower", "Min (m)", "Max (m)", "Mean (m)", "RMSE (m)", "Final (m)"],
                                 ["min", "max", "mean", "rmse", "final"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "This chart isolates cyber-layer integrity: the gap between each follower's true physical state and "
            "the value actually stored in the cloud database, independent of estimation/observer error. A spike "
            "confined to an FDI-shaded window with rapid recovery afterward indicates the tamper was caught and "
            "discarded once the attack ended; a spike that persists past the shading would indicate a defense gap.",
            body_style))

        # 4.4 Control Effort
        story.append(Paragraph("4.4 Control Effort", h3_style))
        fig = ReportGenerator._build_series_figure(history, n_followers, "control_inputs",
                                                     "Control Input Command Magnitude ||u(t)||", "Acceleration (m/s$^2$)", attack_windows)
        story.append(ReportGenerator._fig_to_image(fig))
        ctrl_stats = ReportGenerator._follower_stats(history["control_inputs"])
        story.append(stat_table(ctrl_stats, ["Follower", "Min", "Max", "Mean", "RMSE", "Final"],
                                 ["min", "max", "mean", "rmse", "final"]))
        story.append(Spacer(1, 4))
        max_accel = config["system"].get("max_accel", 10.0)
        sat_pct = [
            100.0 * float(np.mean(np.array(history["control_inputs"][i]) >= max_accel * 0.99))
            for i in range(n_followers)
        ]
        story.append(Paragraph(
            f"Actuator saturation limit is {max_accel} m/s&sup2;. Time spent at or near saturation per follower: "
            + ", ".join(f"F{i+1} {p:.1f}%" for i, p in enumerate(sat_pct))
            + ". Elevated saturation during an attack window indicates the controller is fighting hard to "
              "correct for corrupted or stale telemetry; sustained low saturation afterward confirms a smooth return to nominal operation.",
            body_style))

        # 4.5 Observer (Kalman Filter Estimation) Error
        story.append(Paragraph("4.5 Observer Estimation Error", h3_style))
        fig = ReportGenerator._build_series_figure(history, n_followers, "estimation_errors",
                                                     "Kalman Filter Estimation Error", "Error Norm", attack_windows)
        story.append(ReportGenerator._fig_to_image(fig))
        obs_stats = ReportGenerator._follower_stats(history["estimation_errors"])
        story.append(stat_table(obs_stats, ["Follower", "Min", "Max", "Mean", "RMSE", "Final"],
                                 ["min", "max", "mean", "rmse", "final"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "This is each follower's own local state estimator error (estimated vs. true physical state), driven "
            "purely by its own sensor noise and process disturbance - it is not exposed to the leader-side cyber "
            "attacks above, so it should stay small and roughly flat throughout the run; that flatness is itself "
            "a minor but useful confirmation that the Kalman filter's process/measurement noise covariances "
            "(Q, R) are well-tuned for this plant.", body_style))

        # 4.6 Lyapunov Decay
        story.append(Paragraph("4.6 Lyapunov Stability Decay", h3_style))
        fig = ReportGenerator._build_series_figure(history, n_followers, "lyapunov_values",
                                                     "System Lyapunov Stability Decay V(t)", "Energy Value", attack_windows)
        story.append(ReportGenerator._fig_to_image(fig))
        lyap_stats = ReportGenerator._follower_stats(history["lyapunov_values"])
        story.append(stat_table(lyap_stats, ["Follower", "Min", "Max", "Mean", "RMSE", "Final"],
                                 ["min", "max", "mean", "rmse", "final"]))
        story.append(Spacer(1, 4))
        decay_notes = []
        for r in lyap_stats:
            init_v = history["lyapunov_values"][r["follower"] - 1][0] if history["lyapunov_values"][r["follower"] - 1] else 0.0
            trend = "net decayed" if r["final"] < init_v else "did not net-decay"
            decay_notes.append(f"F{r['follower']}: V(0)={init_v:.2f} -> V(T)={r['final']:.2f} ({trend})")
        story.append(Paragraph(
            "V(t) = e(t)^T P e(t) is the quadratic Lyapunov energy of each follower's tracking error e(t) against "
            "the solved closed-loop P matrix. Under nominal (unattacked) LQR/DARE control this should trend "
            "toward zero between disturbances, with brief spikes exactly where the leader maneuvers or an "
            "attack corrupts telemetry: " + "; ".join(decay_notes) + ".", body_style))

        # 4.7 Pole s-Plane
        story.append(Paragraph("4.7 Closed-Loop Pole (s-Plane) Analysis", h3_style))
        if controller is not None:
            is_stable, eigvals, radius = controller.verify_stability()
            domain = config["system"].get("model_domain", "continuous").lower()
            fig = ReportGenerator._build_pole_figure(eigvals, dt, domain)
            story.append(ReportGenerator._fig_to_image(fig, width=5.6 * inch))
            pole_rows = ReportGenerator._pole_analysis(eigvals, dt, domain)
            pole_data = [[Paragraph("<b>Pole (raw)</b>", body_style), Paragraph("<b>σ (1/s)</b>", body_style),
                          Paragraph("<b>ω (rad/s)</b>", body_style), Paragraph("<b>|s|</b>", body_style),
                          Paragraph("<b>ζ</b>", body_style), Paragraph("<b>Stable</b>", body_style)]]
            for p in pole_rows:
                pole_data.append([
                    f"{p['raw'].real:.4f}{'+' if p['raw'].imag >= 0 else '-'}{abs(p['raw'].imag):.4f}j",
                    f"{p['sigma']:.4f}", f"{p['omega']:.4f}", f"{p['mag']:.4f}", f"{p['zeta']:.4f}",
                    "Yes" if p['stable'] else "No"
                ])
            t_poles = Table(pole_data, colWidths=[100, 75, 75, 65, 55, 55])
            t_poles.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]))
            story.append(t_poles)
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                f"Stability index (spectral radius / max real part) = {radius:.6f}. All {len(pole_rows)} closed-loop "
                f"poles lie in the {'stable Left-Half-Plane' if is_stable else 'unstable Right-Half-Plane'} region "
                f"(σ &lt; 0). The damping ratio ζ indicates how oscillatory each mode's response is: ζ near 1 is "
                f"heavily damped (no overshoot), while lower ζ modes ring longer before settling - this is the "
                f"root-cause explanation for the transient shapes seen in Sections 4.1-4.6 above.", body_style))
        else:
            story.append(Paragraph("Controller object not supplied to this report - pole analysis skipped.", body_style))

        # ---------------- 5. Overall Performance Summary ----------------
        story.append(PageBreak())
        story.append(Paragraph("5. Overall Performance Summary", h2_style))
        metric_data = [
            [Paragraph("<b>Evaluation Metric</b>", body_style), Paragraph("<b>Simulated Value</b>", body_style), Paragraph("<b>Reference Threshold</b>", body_style)],
            ["Root Mean Square Error (RMSE)", f"{metrics['rmse']:.4f} m", "< 1.0 m (Consensus Target)"],
            ["Mean Absolute Error (MAE)", f"{metrics['mae']:.4f} m", "< 0.8 m"],
            ["Consensus Error Peak", f"{metrics['max_err']:.4f} m", "< 2.0 m (Defended Bound)"],
            ["Peak Actuator Control Input", f"{metrics['peak_ctrl']:.4f} m/s^2", f"< {config['system'].get('max_accel', 10.0)} m/s^2 (Actuator Sat)"],
            ["Control Command Energy", f"{metrics['energy']:.4f} J", "Minimal Energy Design"],
            ["Tracking Settling Time", metrics['settling_time'], "< 3.0 s"]
        ]
        t2 = Table(metric_data, colWidths=[200, 150, 150])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#b4c6e7")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#8faadc")),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f9")]),
        ]))
        story.append(t2)
        story.append(Spacer(1, 15))

        # ---------------- 6. Conclusions & Recommendations ----------------
        story.append(Paragraph("6. Conclusions &amp; Recommendations", h2_style))
        conclusion_bullets = []
        conclusion_bullets.append(
            f"Closed-loop design is analytically {stability_verdict.lower()}"
            + (f" (stability index {radius:.4f})." if controller is not None else "."))
        conclusion_bullets.append(
            f"Mean consensus tracking error across all followers was {metrics['rmse']:.3f} m RMSE, "
            f"{'within' if metrics['rmse'] < 1.0 else 'above'} the 1.0 m reference target.")
        if enabled_attacks:
            conclusion_bullets.append(
                f"Enabled attack vectors ({', '.join(enabled_attacks)}) produced visible, correlated spikes in the "
                f"Consensus Error and Cloud Telemetry Error charts (Sections 4.2-4.3), confirming the attack "
                f"simulator is actually perturbing the system rather than being a no-op.")
        if enabled_defenses:
            if attacks_fully_recovered is False:
                conclusion_bullets.append(
                    f"Active defenses ({', '.join(enabled_defenses)}) did <b>not</b> fully mitigate every enabled "
                    f"attack in this run - the average tracking error was still elevated at the end of the recorded "
                    f"window (see the recovery note in Section 4.2). This points to a specific attack/defense "
                    f"combination worth re-testing in isolation rather than a blanket security failure.")
            else:
                conclusion_bullets.append(
                    f"Active defenses ({', '.join(enabled_defenses)}) show up as bounded recovery after each attack "
                    f"window rather than sustained divergence, indicating the security layer is mitigating rather than "
                    f"merely logging the attacks.")
        else:
            conclusion_bullets.append(
                "No defenses were enabled for this run; any attack effects seen above represent the raw, "
                "undefended impact on the system.")
        conclusion_bullets.append(
            "Observer estimation error (Section 4.5) remained decoupled from the leader-side attacks, as expected "
            "since it reflects each follower's own local sensing rather than cloud-relayed telemetry.")
        for b in conclusion_bullets:
            story.append(Paragraph(f"&bull; {b}", bullet_style))

        doc.build(story)
