import datetime
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from backend.database import get_all_detections

REPORTS_DIR = "logs/reports"


def generate_incident_report(
    trigger_event=None,
    person_count=0,
    risk_level="DANGER",
    density_score=0,
    zone_data=None,
    flow_data=None
):
    """
    Generates a professional PDF incident report.
    Called automatically when DANGER is detected,
    or manually from the dashboard.
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)

    timestamp = datetime.datetime.now()
    filename = f"CDMS_Incident_{timestamp.strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#1a1a2e'),
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        leading=16
    )

    # Risk color
    risk_colors = {
        "SAFE": colors.HexColor('#27ae60'),
        "WARNING": colors.HexColor('#f39c12'),
        "DANGER": colors.HexColor('#e74c3c')
    }
    risk_color = risk_colors.get(risk_level, colors.red)

    story = []

    # ── Header ──
    story.append(Paragraph("CROWD DISASTER MANAGEMENT SYSTEM", title_style))
    story.append(Paragraph("Automated Incident Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a1a2e')))
    story.append(Spacer(1, 0.4*cm))

    # ── Incident Summary Box ──
    risk_style = ParagraphStyle(
        'Risk',
        parent=styles['Normal'],
        fontSize=16,
        textColor=risk_color,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    summary_data = [
        ['INCIDENT CLASSIFICATION', f'{risk_level}'],
        ['Report Generated', timestamp.strftime('%Y-%m-%d %H:%M:%S')],
        ['People Detected', str(person_count)],
        ['Density Score', str(density_score)],
        ['Trigger Event', trigger_event or 'Automated detection']
    ]

    summary_table = Table(summary_data, colWidths=[8*cm, 9*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 13),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (1, 0), (1, 0), risk_color),
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Zone Analysis ──
    if zone_data:
        story.append(Paragraph("Zone Analysis", heading_style))
        story.append(Paragraph(
            "The monitored area was divided into a 3×3 grid of zones. "
            "Each zone was independently analyzed for crowd density.",
            body_style
        ))

        zone_table_data = [['Zone', 'People Count', 'Density Score', 'Risk Level']]
        for zone in zone_data:
            zone_table_data.append([
                zone.get('zone', '--'),
                str(zone.get('count', 0)),
                str(zone.get('density', 0)),
                zone.get('risk', '--')
            ])

        zone_table = Table(zone_table_data, colWidths=[4*cm, 4*cm, 4*cm, 5*cm])
        zone_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(zone_table)
        story.append(Spacer(1, 0.3*cm))

    # ── Crowd Flow Analysis ──
    if flow_data and flow_data.get('direction') != 'Unknown':
        story.append(Paragraph("Crowd Flow Analysis", heading_style))
        flow_info = [
            f"<b>Movement Direction:</b> {flow_data.get('direction', 'Unknown')}",
            f"<b>Average Speed:</b> {flow_data.get('speed', 0)} units/frame",
            f"<b>Surge Detected:</b> {'YES — IMMEDIATE ACTION REQUIRED' if flow_data.get('surge_detected') else 'No'}",
            f"<b>Flow Assessment:</b> {flow_data.get('flow_message', '--')}"
        ]
        for info in flow_info:
            story.append(Paragraph(info, body_style))
        story.append(Spacer(1, 0.3*cm))

    # ── Recent Detection History ──
    story.append(Paragraph("Recent Detection History", heading_style))
    detections = get_all_detections(limit=10)

    if detections:
        hist_data = [['Timestamp', 'People', 'Density', 'Risk']]
        for d in detections:
            hist_data.append([
                d['timestamp'],
                str(d['person_count']),
                str(d['density_score']),
                d['risk_level']
            ])

        hist_table = Table(hist_data, colWidths=[6*cm, 3*cm, 3*cm, 5*cm])
        hist_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(hist_table)

    story.append(Spacer(1, 0.5*cm))

    # ── Recommendations ──
    story.append(Paragraph("Recommended Actions", heading_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dddddd')))
    story.append(Spacer(1, 0.2*cm))

    recommendations = {
        "SAFE": [
            "Continue routine monitoring of all zones.",
            "Maintain current crowd management protocols.",
            "Log this report for baseline reference."
        ],
        "WARNING": [
            "Alert security personnel to monitor the affected zones closely.",
            "Consider redirecting crowd flow to less dense areas.",
            "Prepare emergency response protocols for rapid deployment.",
            "Increase monitoring frequency to every 30 seconds."
        ],
        "DANGER": [
            "IMMEDIATE ACTION REQUIRED — Deploy security personnel to all danger zones.",
            "Activate emergency crowd dispersal protocols immediately.",
            "Alert emergency services (police, ambulance) if not already done.",
            "Close entry points to the affected area immediately.",
            "Establish clear evacuation routes and communicate to crowd.",
            "Document all actions taken with timestamps for post-incident review."
        ]
    }

    for i, rec in enumerate(recommendations.get(risk_level, []), 1):
        style = ParagraphStyle(
            f'Rec{i}',
            parent=body_style,
            leftIndent=20,
            textColor=risk_color if risk_level == "DANGER" else colors.HexColor('#333333')
        )
        story.append(Paragraph(f"{i}. {rec}", style))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dddddd')))
    story.append(Spacer(1, 0.2*cm))

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        alignment=TA_CENTER
    )
    story.append(Paragraph(
        f"Generated by CDMS — Crowd Disaster Management System | "
        f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
        f"Trained Model MAE: 13.77",
        footer_style
    ))

    doc.build(story)
    print(f"✅ Report generated: {filepath}")
    return filepath, filename