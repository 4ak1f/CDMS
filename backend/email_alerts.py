import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# ── Configure these ──────────────────────────────
SENDER_EMAIL    = "aakifmustafa76@gmail.com"   # Your Gmail
SENDER_PASSWORD = "vule iwlh ovnz zjue"    # Your App Password
RECEIVER_EMAIL  = "gm1836@myamu.ac.in"   # Who gets the alert
# ─────────────────────────────────────────────────

EMAIL_ENABLED = True


def send_danger_alert(person_count, density_score, risk_level, message, report_path=None):
    """
    Sends an email alert when DANGER or WARNING is detected.
    Optionally attaches the PDF incident report.
    """
    if not EMAIL_ENABLED:
        print("⚠️  Email not configured — skipping email alert")
        return False

    if risk_level == "SAFE":
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚨 CDMS ALERT: {risk_level} — Crowd Density Critical"
        msg['From']    = SENDER_EMAIL
        msg['To']      = RECEIVER_EMAIL

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        risk_colors = {
            "WARNING": "#f39c12",
            "DANGER":  "#e74c3c"
        }
        color = risk_colors.get(risk_level, "#e74c3c")

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white;
                        border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">

                <div style="background: {color}; padding: 24px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">
                        🚨 {risk_level} ALERT
                    </h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0;">
                        Crowd Disaster Management System
                    </p>
                </div>

                <div style="padding: 24px;">
                    <p style="color: #333; font-size: 16px;">{message}</p>

                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 12px; font-weight: bold; color: #555;">Timestamp</td>
                            <td style="padding: 12px; color: #333;">{timestamp}</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; font-weight: bold; color: #555;">People Detected</td>
                            <td style="padding: 12px; color: #333; font-size: 18px; font-weight: bold;">{person_count}</td>
                        </tr>
                        <tr style="background: #f8f9fa;">
                            <td style="padding: 12px; font-weight: bold; color: #555;">Density Score</td>
                            <td style="padding: 12px; color: #333;">{density_score}</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; font-weight: bold; color: #555;">Risk Level</td>
                            <td style="padding: 12px;">
                                <span style="background: {color}; color: white; padding: 4px 12px;
                                             border-radius: 12px; font-weight: bold;">
                                    {risk_level}
                                </span>
                            </td>
                        </tr>
                    </table>

                    <div style="background: #fff3cd; border: 1px solid #ffc107;
                                border-radius: 8px; padding: 16px; margin: 16px 0;">
                        <p style="margin: 0; color: #856404; font-weight: bold;">
                            ⚠️ Immediate action may be required.
                            Please review the attached incident report.
                        </p>
                    </div>
                </div>

                <div style="background: #f8f9fa; padding: 16px; text-align: center;
                            border-top: 1px solid #eee;">
                    <p style="color: #999; font-size: 12px; margin: 0;">
                        Automated alert from CDMS | {timestamp}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html'))

        # Attach PDF report if provided
        if report_path and os.path.exists(report_path):
            with open(report_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{os.path.basename(report_path)}"'
                )
                msg.attach(part)

        # Send via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(
                SENDER_EMAIL,
                RECEIVER_EMAIL,
                msg.as_string().encode('utf-8')
    )
        print(f"✅ Alert email sent to {RECEIVER_EMAIL}")
        return True

    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False