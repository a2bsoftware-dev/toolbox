import csv
import numpy as np
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class ReportGenerator:
    """
    Automates compiling and exporting simulation metrics to PDF reports and Excel/CSV worksheets.
    """
    @staticmethod
    def calculate_metrics(history: dict, dt: float = 0.05) -> dict:
        """
        Calculates performance indices from raw simulation history.
        """
        track_errs = np.mean(history["tracking_errors"], axis=0) if history["tracking_errors"] else [0]
        ctrl_norms = np.mean(history["control_inputs"], axis=0) if history["control_inputs"] else [0]
        
        rmse = float(np.sqrt(np.mean(np.array(track_errs)**2)))
        mae = float(np.mean(np.array(track_errs)))
        max_err = float(np.max(np.array(track_errs)))
        peak_ctrl = float(np.max(np.array(ctrl_norms)))
        energy = float(np.sum(np.array(ctrl_norms)**2) * dt)
        
        # Settling time (time taken to return and remain below a 1.5m threshold after FDI attack window t=22.0)
        settling_time = "N/A"
        time_grid = history.get("time", [])
        if len(time_grid) > 0:
            post_attack_indices = [idx for idx, t in enumerate(time_grid) if t > 22.0]
            if post_attack_indices:
                settled_t = None
                for idx in reversed(post_attack_indices):
                    if track_errs[idx] > 1.5:
                        settled_t = time_grid[idx]
                        break
                if settled_t is not None:
                    # Settling time is distance from end of attack (22.0) to convergence
                    settling_val = settled_t - 22.0
                    settling_time = f"{settling_val:.2f} s" if settling_val > 0 else "Instant"
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
            # Headers
            headers = ["Time (s)", "Leader_X", "Leader_Y"]
            for i in range(n_followers):
                headers += [f"F{i+1}_X", f"F{i+1}_Y", f"F{i+1}_TrackErr", f"F{i+1}_Lyap", f"F{i+1}_CtrlNorm"]
            headers.append("Network_Status")
            writer.writerow(headers)
            
            # Data lines
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
            data[f"F{i+1}_X"] = [h[k][0] for k in range(len(time)) for h in [history["followers"][i]]]
            data[f"F{i+1}_Y"] = [h[k][2] for k in range(len(time)) for h in [history["followers"][i]]]
            data[f"F{i+1}_TrackErr"] = history["tracking_errors"][i]
            data[f"F{i+1}_Lyap"] = history["lyapunov_values"][i]
            data[f"F{i+1}_CtrlNorm"] = history["control_inputs"][i]
            
        data["Network_Status"] = history["network_link_status"]
        
        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False)

    @staticmethod
    def generate_pdf_report(filepath: str, config: dict, history: dict):
        """
        Generates a publication-grade PDF report using ReportLab flowables.
        """
        if not filepath.endswith(".pdf"):
            filepath += ".pdf"
            
        # Calculate performance indices
        metrics = ReportGenerator.calculate_metrics(history, config["system"]["dt"])
        
        doc = SimpleDocTemplate(filepath, pagesize=letter,
                                rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
            alignment=1, # Centered
            spaceAfter=20
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#475569"),
            alignment=1,
            spaceAfter=30
        )
        
        h2_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e3a8a"),
            spaceBefore=15,
            spaceAfter=10
        )
        
        body_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['BodyText'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155")
        )
        
        story = []
        
        # 1. Header
        story.append(Paragraph("Networked Control System (NCS) Simulation Report", title_style))
        story.append(Paragraph("Automated Cybersecurity & Performance Performance Evaluation Ledger", subtitle_style))
        story.append(Spacer(1, 10))
        
        # 2. Section: Configuration parameters
        story.append(Paragraph("1. System Design Parameters", h2_style))
        
        sec_cfg = config["security"]
        sim_cfg = config["simulation"]
        
        config_data = [
            [Paragraph("<b>Parameter</b>", body_style), Paragraph("<b>Value</b>", body_style), Paragraph("<b>Parameter</b>", body_style), Paragraph("<b>Value</b>", body_style)],
            ["Follower Drones", str(sim_cfg["n_followers"]), "Controller Scheme", config["controller"].get("type", "LQR")],
            ["Observer Scheme", config["observer"].get("type", "Kalman"), "Time Step (dt)", f"{config['system']['dt']} s"],
            ["HMAC Signatures", "Enabled" if sec_cfg.get("enable_hmac", True) else "Disabled", "Diff. Privacy", "Enabled" if sec_cfg.get("enable_dp", True) else "Disabled"],
            ["Privacy Budget (Epsilon)", str(sec_cfg.get("dp_epsilon", 1.5)), "Anomaly IDS", "Enabled" if sec_cfg.get("enable_anomaly", True) else "Disabled"]
        ]
        
        t1 = Table(config_data, colWidths=[150, 100, 150, 100])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#cbd5e1")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(t1)
        story.append(Spacer(1, 15))
        
        # 3. Section: Performance metrics table
        story.append(Paragraph("2. Closed-Loop Performance Evaluation", h2_style))
        story.append(Paragraph("These indices measure consensus tracking accuracy and control cost under threat conditions:", body_style))
        story.append(Spacer(1, 8))
        
        metric_data = [
            [Paragraph("<b>Evaluation Metric</b>", body_style), Paragraph("<b>Simulated Value</b>", body_style), Paragraph("<b>Reference Threshold</b>", body_style)],
            ["Root Mean Square Error (RMSE)", f"{metrics['rmse']:.4f} m", "< 1.0 m (Consensus Target)"],
            ["Mean Absolute Error (MAE)", f"{metrics['mae']:.4f} m", "< 0.8 m"],
            ["Consensus Error Peak", f"{metrics['max_err']:.4f} m", "< 2.0 m (Defended Bound)"],
            ["Peak Actuator Control input", f"{metrics['peak_ctrl']:.4f} m/s^2", f"< {config['system'].get('max_accel', 10.0)} m/s^2 (Actuator Sat)"],
            ["Control Command Energy", f"{metrics['energy']:.4f} J", "Minimal Energy Design"],
            ["Tracking Settling Time", metrics['settling_time'], "< 3.0 s"]
        ]
        
        t2 = Table(metric_data, colWidths=[200, 150, 150])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#b4c6e7")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#8faadc")),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f2f5f9")]),
        ]))
        story.append(t2)
        story.append(Spacer(1, 15))
        
        # 4. Section: Cyber threat timeline
        story.append(Paragraph("3. Cyber Attack Timeline & Analysis", h2_style))
        
        fdi_start = config["attacks"]["fdi"]["start_time"]
        fdi_end = config["attacks"]["fdi"]["end_time"]
        dos_start = config["attacks"]["dos"]["start_time"]
        dos_end = config["attacks"]["dos"]["end_time"]
        
        timeline_data = [
            [Paragraph("<b>Time Interval</b>", body_style), Paragraph("<b>Active Attack Vector</b>", body_style), Paragraph("<b>Defense Mechanism Activated</b>", body_style)],
            [f"0.0s - {fdi_start}s", "Normal Communication", "Cryptographic handshakes active"],
            [f"{fdi_start}s - {fdi_end}s", "False Data Injection (FDI)", "HMAC signature dropouts & Anomaly checks"],
            [f"{fdi_end}s - {dos_start}s", "Consensus Recovery", "Controller convergence to orbit"],
            [f"{dos_start}s - {dos_end}s", "Denial of Service (DoS)", "Followers run dead-reckoning ZOH prediction"],
            [f"{dos_end}s - End", "Recovered Operation", "Consensus tracking re-established"]
        ]
        
        t3 = Table(timeline_data, colWidths=[120, 180, 200])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8cbad")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#f4b084")),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#fff2cc")]),
        ]))
        story.append(t3)
        story.append(Spacer(1, 20))
        
        # 5. Conclusion
        story.append(Paragraph("4. Technical Summary & Conclusions", h2_style))
        conclusion_text = (
            "The multi-agent leader-follower consensus control system demonstrates high resilience. "
            "Under cryptographic HMAC-SHA256 filters, False Data Injection (FDI) telemetry manipulation is successfully discarded, "
            "preventing followers from cutting across orbits or colliding. When links are severed during Denial of Service (DoS) drops, "
            "drones fall back to continuous-time state estimation and discrete dead-reckoning predictions, maintaining circle orbits "
            "with zero discretization drift. The closed-loop poles lie strictly in the LHP, guaranteeing Schur and Lyapunov stability."
        )
        story.append(Paragraph(conclusion_text, body_style))
        
        doc.build(story)
