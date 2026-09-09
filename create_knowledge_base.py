import pandas as pd
import json


# ============================================================
# LOAD DATASET
# ============================================================

df = pd.read_csv("dataset/helpdesk_tickets_100.csv")


# ============================================================
# ISSUE-SPECIFIC KNOWLEDGE
# ============================================================

def generate_troubleshooting_content(category, subcategory):

    issue = str(subcategory).lower()

    # --------------------------------------------------------
    # TOUCHPAD
    # --------------------------------------------------------

    if "touchpad" in issue:
        return (
            f"This guide covers {subcategory}. "
            "The issue may occur if the touchpad is disabled, if the "
            "touchpad settings are incorrect, if its device driver is "
            "not functioning correctly, or if there is a hardware problem. "
            "Troubleshooting should begin by checking whether the touchpad "
            "has been disabled using the laptop settings or function keys. "
            "Check the operating-system touchpad settings and confirm that "
            "the device is enabled. Next, check the touchpad device and "
            "driver status. Restart the laptop and test the touchpad again. "
            "If the touchpad is still not responding, inspect the hardware "
            "for possible physical or connectivity problems. If these "
            "checks do not resolve the issue, additional hardware or "
            "driver investigation is required."
        )

    # --------------------------------------------------------
    # KEYBOARD
    # --------------------------------------------------------

    if "keyboard" in issue:
        return (
            f"This guide covers {subcategory}. "
            "First check whether the keyboard is connected and recognized "
            "by the computer. Restart the computer and test the keyboard "
            "again. Check the keyboard settings and verify that the "
            "keyboard device and driver are functioning correctly. "
            "For an external keyboard, check the cable, USB connection, "
            "or wireless connection. If specific keys remain unresponsive, "
            "inspect the keyboard for physical damage. If the problem "
            "continues, additional hardware or driver investigation is "
            "required."
        )

    # --------------------------------------------------------
    # SCREEN / DISPLAY
    # --------------------------------------------------------

    if any(word in issue for word in [
        "screen", "display", "monitor", "brightness", "dim"
    ]):
        return (
            f"This guide covers {subcategory}. "
            "First check the display brightness and operating-system "
            "display settings. Verify that the display is receiving power "
            "and that the display connection is secure when applicable. "
            "Restart the computer and test the display again. "
            "Check the graphics or display driver status if the problem "
            "continues. Look for visible physical damage to the display. "
            "If the display remains abnormal after these checks, "
            "additional hardware or display-driver investigation is required."
        )

    # --------------------------------------------------------
    # MOUSE
    # --------------------------------------------------------

    if "mouse" in issue:
        return (
            f"This guide covers {subcategory}. "
            "Check whether the mouse is properly connected or paired. "
            "For a wireless mouse, check the power and wireless connection. "
            "For a wired mouse, check the cable and USB connection. "
            "Restart the computer and test the mouse again. "
            "Check the mouse device and driver status. "
            "If the mouse still does not work, test another compatible "
            "mouse to help determine whether the problem is hardware related."
        )

    # --------------------------------------------------------
    # BATTERY
    # --------------------------------------------------------

    if "battery" in issue:
        return (
            f"This guide covers {subcategory}. "
            "Check the battery level and confirm that the charger is "
            "properly connected. Verify that the operating system detects "
            "the battery and charger correctly. Restart the computer and "
            "check the battery status again. Inspect the charging cable "
            "and power connection for visible problems. "
            "If charging or battery problems continue, additional battery "
            "or hardware investigation is required."
        )

    # --------------------------------------------------------
    # PRINTER
    # --------------------------------------------------------

    if "printer" in issue:
        return (
            f"This guide covers {subcategory}. "
            "Check that the printer is powered on and connected to the "
            "computer or network. Verify that the correct printer is "
            "selected and that there are no pending or failed print jobs. "
            "Check the printer driver and connection status. "
            "Restart the printer and test printing again. "
            "If the problem continues, check for printer hardware or "
            "network connectivity problems."
        )

    # --------------------------------------------------------
    # APPLICATION INSTALLATION
    # --------------------------------------------------------

    if "install" in issue or "installation" in issue:
        return (
            f"This guide covers {subcategory}. "
            "First record any error message displayed during installation. "
            "Verify that the application version is compatible with the "
            "operating system and that the required installation files "
            "are available. Check available storage and required user "
            "permissions. Restart the computer and attempt the installation "
            "again. If installation continues to fail, review the error "
            "information and investigate application dependencies."
        )

    # --------------------------------------------------------
    # APPLICATION CRASHING
    # --------------------------------------------------------

    if "crash" in issue:
        return (
            f"This guide covers {subcategory}. "
            "Reproduce the problem and record any error message generated "
            "when the application crashes. Restart the application and "
            "test again. Check whether the application is updated and "
            "whether the system meets its requirements. "
            "Review application settings and relevant error logs. "
            "If the application continues to crash, additional software "
            "or dependency investigation is required."
        )

    # --------------------------------------------------------
    # APPLICATION NOT RESPONDING
    # --------------------------------------------------------

    if "not responding" in issue:
        return (
            f"This guide covers {subcategory}. "
            "First check whether the application is still processing an "
            "operation or has become unresponsive. Wait briefly and test "
            "again. If it remains unresponsive, restart the application. "
            "Check available system resources and application settings. "
            "Verify that the application and its required components are "
            "properly installed and updated. If the issue continues, "
            "review relevant application logs and investigate further."
        )

    # --------------------------------------------------------
    # BROWSER
    # --------------------------------------------------------

    if "browser" in issue:
        return (
            f"This guide covers {subcategory}. "
            "Restart the browser and reproduce the problem. "
            "Check whether the browser is updated to a supported version. "
            "Review browser extensions and settings that may affect "
            "operation. Clear temporary browser data when appropriate "
            "and test again. Check whether the problem occurs with another "
            "website or browser. If the issue persists, review browser "
            "logs or perform additional software investigation."
        )

    # --------------------------------------------------------
    # PASSWORD / ACCOUNT / LOGIN
    # --------------------------------------------------------

    if any(word in issue for word in [
        "password", "account", "login", "authentication",
        "authorization", "permission", "access", "credential"
    ]):
        return (
            f"This guide covers {subcategory}. "
            "First identify the affected user account and the resource "
            "the user is trying to access. Verify that the credentials "
            "are entered correctly. Check whether the account is active "
            "and whether it has the required permissions. "
            "Check for account restrictions or authentication problems. "
            "Retry the login or access operation after correcting any "
            "identified issue. If access remains unavailable, additional "
            "account or permission investigation is required."
        )

    # --------------------------------------------------------
    # VPN
    # --------------------------------------------------------

    if "vpn" in issue:
        return (
            f"This guide covers {subcategory}. "
            "Check the network connection before starting the VPN. "
            "Verify the VPN configuration and confirm that the correct "
            "credentials are being used. Restart the VPN connection and "
            "test again. Check whether the required network service is "
            "reachable. If the VPN still fails, investigate configuration, "
            "authentication, or network connectivity problems."
        )

    # --------------------------------------------------------
    # DNS
    # --------------------------------------------------------

    if "dns" in issue:
        return (
            f"This guide covers {subcategory}. "
            "Check whether the device has a valid network connection. "
            "Verify the configured DNS settings and test whether the "
            "required hostname can be resolved. Restart the network "
            "connection and test again. If the issue continues, investigate "
            "DNS configuration and network connectivity."
        )

    # --------------------------------------------------------
    # NETWORK CONNECTION
    # --------------------------------------------------------

    if any(word in issue for word in [
        "network", "connection", "connectivity",
        "internet", "wifi", "wi-fi"
    ]):
        return (
            f"This guide covers {subcategory}. "
            "First verify that the affected device is connected to the "
            "correct network. Check the network adapter and confirm that "
            "the device has a valid network configuration. Test connectivity "
            "to the required service or destination. Restart the network "
            "connection and test again. If the problem continues, compare "
            "the affected device with a working device and investigate "
            "network configuration or infrastructure problems."
        )

    # --------------------------------------------------------
    # SECURITY / SUSPICIOUS ACTIVITY
    # --------------------------------------------------------

    if any(word in issue for word in [
        "suspicious", "security", "malware", "phishing",
        "spoof", "attack", "unauthorized", "compromise",
        "breach", "threat"
    ]):
        return (
            f"This guide covers {subcategory}. "
            "Identify the affected account, device, or network activity. "
            "Review available security and authentication logs for "
            "unusual activity. Check for unexpected processes, connections, "
            "or access attempts. Preserve relevant information for further "
            "investigation. Do not assume the cause without sufficient "
            "evidence. If suspicious activity remains present or indicates "
            "a possible security incident, additional security investigation "
            "is required."
        )

    # --------------------------------------------------------
    # GENERAL FALLBACK
    # --------------------------------------------------------

    return (
        f"This guide covers {subcategory}. "
        "Begin by reproducing the reported problem and identifying the "
        "affected system or component. Check relevant configuration, "
        "connectivity, permissions, software components, and system status "
        "where applicable. Review available error messages or logs. "
        "Restart the affected component and test again. If the problem "
        "continues, additional investigation is required."
    )


# ============================================================
# CREATE KNOWLEDGE BASE
# ============================================================

knowledge_base = []

unique_issues = df.drop_duplicates(
    subset=["Category", "Subcategory"]
)


for _, row in unique_issues.iterrows():

    category = row["Category"]
    subcategory = row["Subcategory"]

    document = {
        "id": len(knowledge_base) + 1,
        "category": category,
        "subcategory": subcategory,
        "priority": row["Priority"],
        "title": f"{subcategory} Troubleshooting Guide",
        "content": generate_troubleshooting_content(
            category,
            subcategory
        )
    }

    knowledge_base.append(document)


# ============================================================
# SAVE KNOWLEDGE BASE
# ============================================================

with open("data/knowledge_base.json", "w") as file:
    json.dump(knowledge_base, file, indent=4)


# ============================================================
# RESULT
# ============================================================

print("==============================================")
print("KNOWLEDGE BASE CREATED SUCCESSFULLY")
print("==============================================")
print("Number of documents:", len(knowledge_base))
print("\nSaved to: data/knowledge_base.json")