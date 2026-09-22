import os
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# EMAIL SERVICE
# =========================================================

class EmailService:

    def __init__(self):

        self.smtp_server = os.getenv("SMTP_SERVER")

        self.smtp_port = int(
            os.getenv("SMTP_PORT", "587")
        )

        self.email = os.getenv("SMTP_EMAIL")

        self.password = os.getenv("SMTP_PASSWORD")


    # =====================================================
    # SEND RESOLUTION EMAIL
    # =====================================================

    def send_resolution_email(
        self,
        recipient,
        ticket,
        resolution
    ):

        # Check email configuration

        if not all([
            self.smtp_server,
            self.email,
            self.password
        ]):

            return {
                "success": False,
                "message": "Email configuration is missing."
            }


        # Email subject

        subject = "SupportPilot - Ticket Resolution"


        # Email body

        body = (
            "Hello,\n\n"
            "Your IT support ticket has been automatically "
            "resolved by SupportPilot.\n\n"

            f"Ticket:\n"
            f"{ticket}\n\n"

            "Recommended troubleshooting steps:\n\n"
        )


        # Add resolution steps

        for index, step in enumerate(
            resolution["steps"],
            start=1
        ):

            body += f"{index}. {step}\n"


        body += (
            "\n"
            "If the issue is still not resolved, "
            "please contact the IT support team.\n\n"

            "Regards,\n"
            "SupportPilot"
        )


        # Create email

        message = MIMEMultipart()

        message["From"] = self.email

        message["To"] = recipient

        message["Subject"] = subject


        message.attach(
            MIMEText(
                body,
                "plain"
            )
        )


        # Send email

        try:

            with smtplib.SMTP(
                self.smtp_server,
                self.smtp_port
            ) as server:

                # Secure the SMTP connection

                server.starttls()


                # Login using Gmail App Password

                server.login(
                    self.email,
                    self.password
                )


                # Send email

                server.sendmail(
                    self.email,
                    recipient,
                    message.as_string()
                )


            return {
                "success": True,
                "message": "Resolution email sent successfully."
            }


        except Exception as error:

            return {
                "success": False,
                "message": f"Email sending failed: {error}"
            }


# =========================================================
# DIRECT EMAIL TEST
# =========================================================

if __name__ == "__main__":

    email_service = EmailService()


    print("\n======================================")
    print("       SUPPORTPILOT EMAIL TEST")
    print("======================================")


    # Check configuration

    if all([
        email_service.smtp_server,
        email_service.email,
        email_service.password
    ]):

        print("Email configuration found.")

        print("Sending test email...")


        # -------------------------------------------------
        # TEST RESOLUTION
        # -------------------------------------------------

        test_resolution = {

            "steps": [

                "Check internet connectivity.",

                "Restart the application.",

                "Try logging in again."

            ]

        }


        # -------------------------------------------------
        # SEND TEST EMAIL
        # -------------------------------------------------

        result = email_service.send_resolution_email(

            recipient="shravyabinesh005@gmail.com",

            ticket="Test ticket from SupportPilot",

            resolution=test_resolution

        )


        # -------------------------------------------------
        # DISPLAY RESULT
        # -------------------------------------------------

        print("\nEmail Result:")

        print(result)


    else:

        print(
            "Email configuration is incomplete."
        )

        print(
            "Add SMTP values to .env"
        )


    print("======================================")