import os

import requests

from requests.auth import HTTPBasicAuth

from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# JIRA SERVICE
# ============================================================

class JiraService:

    def __init__(self):

        self.jira_url = os.getenv(
            "JIRA_URL"
        )

        self.jira_email = os.getenv(
            "JIRA_EMAIL"
        )

        self.jira_api_token = os.getenv(
            "JIRA_API_TOKEN"
        )

        self.jira_project_key = os.getenv(
            "JIRA_PROJECT_KEY"
        )


    # ========================================================
    # COMMON JIRA HEADERS
    # ========================================================

    def _headers(self):

        return {
            "Accept":
                "application/json",

            "Content-Type":
                "application/json"
        }


    # ========================================================
    # JIRA AUTH
    # ========================================================

    def _auth(self):

        return HTTPBasicAuth(
            self.jira_email,
            self.jira_api_token
        )


    # ========================================================
    # FIND JIRA PRIORITY
    # ========================================================

    def _get_jira_priority(self, supportpilot_priority):

        """
        Convert SupportPilot P1-P4 priority into an
        actual Jira priority.

        If Jira has P1/P2/P3/P4 priorities, they are used.

        Otherwise the standard Jira-style mapping is used:

            P1 -> Highest
            P2 -> High
            P3 -> Medium
            P4 -> Low
        """

        url = (
            f"{self.jira_url.rstrip('/')}"
            "/rest/api/3/priority/search"
        )


        try:

            response = requests.get(

                url,

                auth=self._auth(),

                headers=self._headers(),

                params={
                    "maxResults": 100
                },

                timeout=15
            )


            if response.status_code != 200:

                return {
                    "success": False,

                    "message":
                        "Could not retrieve Jira priorities.",

                    "status_code":
                        response.status_code,

                    "response":
                        response.text
                }


            data = response.json()


            priorities = data.get(
                "values",
                []
            )


            # ------------------------------------------------
            # FIRST: LOOK FOR EXACT P1/P2/P3/P4
            # ------------------------------------------------

            for jira_priority in priorities:

                if (
                    jira_priority.get("name")
                    ==
                    supportpilot_priority
                ):

                    return {

                        "success": True,

                        "id":
                            jira_priority.get(
                                "id"
                            ),

                        "name":
                            jira_priority.get(
                                "name"
                            )
                    }


            # ------------------------------------------------
            # SECOND: STANDARD MAPPING
            # ------------------------------------------------

            priority_mapping = {

                "P1":
                    "Highest",

                "P2":
                    "High",

                "P3":
                    "Medium",

                "P4":
                    "Low"

            }


            mapped_name = (
                priority_mapping.get(
                    supportpilot_priority,
                    "Low"
                )
            )


            # ------------------------------------------------
            # FIND MAPPED PRIORITY
            # ------------------------------------------------

            for jira_priority in priorities:

                if (
                    jira_priority.get("name")
                    ==
                    mapped_name
                ):

                    return {

                        "success": True,

                        "id":
                            jira_priority.get(
                                "id"
                            ),

                        "name":
                            jira_priority.get(
                                "name"
                            )
                    }


            # ------------------------------------------------
            # NO MATCHING PRIORITY
            # ------------------------------------------------

            available_priorities = [

                item.get("name")

                for item in priorities

            ]


            return {

                "success": False,

                "message":
                    "No suitable Jira priority was found.",

                "supportpilot_priority":
                    supportpilot_priority,

                "available_priorities":
                    available_priorities

            }


        except Exception as error:

            return {

                "success": False,

                "message":
                    "Could not connect to Jira "
                    "priority service.",

                "error":
                    str(error)

            }


    # ========================================================
    # CREATE JIRA ISSUE
    # ========================================================

    def create_issue(
        self,
        ticket,
        diagnosis,
        resolution,
        priority="P4"
    ):

        # ----------------------------------------------------
        # CHECK JIRA CONFIGURATION
        # ----------------------------------------------------

        if not all([
            self.jira_url,
            self.jira_email,
            self.jira_api_token,
            self.jira_project_key
        ]):

            return {

                "success":
                    False,

                "message":
                    "Jira configuration is missing.",

                "priority":
                    priority

            }


        # ----------------------------------------------------
        # JIRA API URL
        # ----------------------------------------------------

        url = (
            f"{self.jira_url.rstrip('/')}"
            "/rest/api/3/issue"
        )


        # ====================================================
        # FIND ACTUAL JIRA PRIORITY
        # ====================================================

        jira_priority = (
            self._get_jira_priority(
                priority
            )
        )


        if not jira_priority.get(
            "success",
            False
        ):

            return {

                "success":
                    False,

                "message":
                    "Jira priority could not be resolved.",

                "priority":
                    priority,

                "jira_priority_error":
                    jira_priority

            }


        actual_priority_id = (
            jira_priority.get(
                "id"
            )
        )


        actual_priority_name = (
            jira_priority.get(
                "name"
            )
        )


        # ----------------------------------------------------
        # BUILD DIAGNOSIS INFORMATION SAFELY
        # ----------------------------------------------------

        diagnosis_text = (
            diagnosis.get(
                "diagnosis",
                "No diagnosis available."
            )
        )

        diagnosis_category = (
            diagnosis.get(
                "category",
                "General IT Issue"
            )
        )

        diagnosis_confidence = (
            diagnosis.get(
                "confidence",
                0
            )
            or
            0
        )


        # ----------------------------------------------------
        # BUILD RESOLUTION INFORMATION SAFELY
        # ----------------------------------------------------

        resolution_text = (
            resolution.get(
                "response",
                "No resolution available."
            )
        )

        resolution_steps = (
            resolution.get(
                "steps",
                []
            )
            or
            []
        )


        # ----------------------------------------------------
        # BUILD DESCRIPTION
        # ----------------------------------------------------

        description = (
            "SupportPilot Escalated Ticket\n\n"

            f"Ticket:\n"
            f"{ticket}\n\n"

            f"Diagnosis:\n"
            f"{diagnosis_text}\n\n"

            f"Category:\n"
            f"{diagnosis_category}\n\n"

            f"Diagnosis Confidence:\n"
            f"{diagnosis_confidence * 100:.2f}%\n\n"

            f"SupportPilot Priority:\n"
            f"{priority}\n\n"

            f"Jira Priority:\n"
            f"{actual_priority_name}\n\n"

            "Suggested Resolution:\n"
            f"{resolution_text}\n\n"

            "Steps:\n"
        )


        for index, step in enumerate(
            resolution_steps,
            start=1
        ):

            description += (
                f"{index}. {step}\n"
            )


        # ====================================================
        # JIRA PAYLOAD
        # ====================================================

        payload = {

            "fields": {

                "project": {

                    "key":
                        self.jira_project_key

                },


                "summary": (

                    "SupportPilot Escalation - "

                    f"{diagnosis_category}"

                ),


                "description": {

                    "type":
                        "doc",

                    "version":
                        1,

                    "content": [

                        {

                            "type":
                                "paragraph",

                            "content": [

                                {

                                    "type":
                                        "text",

                                    "text":
                                        description

                                }

                            ]

                        }

                    ]

                },


                "issuetype": {

                    "name":
                        "Task"

                },


                # ------------------------------------------
                # USE JIRA PRIORITY ID
                # ------------------------------------------

                "priority": {

                    "id":
                        actual_priority_id

                }

            }

        }


        # ====================================================
        # DEBUG INFORMATION
        # ====================================================

        print()
        print(
            "=========================================="
        )
        print(
            "SUPPORTPILOT → JIRA"
        )
        print(
            "=========================================="
        )
        print(
            "Project:",
            self.jira_project_key
        )
        print(
            "SupportPilot Priority:",
            priority
        )
        print(
            "Jira Priority:",
            actual_priority_name
        )
        print(
            "Jira Priority ID:",
            actual_priority_id
        )
        print(
            "Issue Type:",
            "Task"
        )
        print(
            "=========================================="
        )


        # ====================================================
        # SEND REQUEST TO JIRA
        # ====================================================

        try:

            response = requests.post(

                url,

                json=payload,

                auth=self._auth(),

                headers=self._headers(),

                timeout=15

            )


            # =================================================
            # SUCCESS
            # =================================================

            if response.status_code in [
                200,
                201
            ]:

                data = response.json()

                issue_key = data.get(
                    "key"
                )


                print(
                    "Jira issue created:",
                    issue_key
                )


                return {

                    "success":
                        True,

                    "message":
                        "Jira issue created successfully.",

                    "issue_key":
                        issue_key,

                    "issue_url":
                        (
                            f"{self.jira_url.rstrip('/')}"
                            f"/browse/{issue_key}"
                        ),

                    "priority":
                        priority,

                    "jira_priority":
                        actual_priority_name

                }


            # =================================================
            # JIRA ERROR
            # =================================================

            print()
            print(
                "=========================================="
            )
            print(
                "JIRA ISSUE CREATION FAILED"
            )
            print(
                "=========================================="
            )
            print(
                "HTTP Status:",
                response.status_code
            )
            print(
                "Response:",
                response.text
            )
            print(
                "=========================================="
            )


            try:

                error_data = response.json()

                error_messages = (
                    error_data.get(
                        "errorMessages",
                        []
                    )
                )

                field_errors = (
                    error_data.get(
                        "errors",
                        {}
                    )
                )


                return {

                    "success":
                        False,

                    "message":
                        "Jira issue creation failed.",

                    "status_code":
                        response.status_code,

                    "error_messages":
                        error_messages,

                    "field_errors":
                        field_errors,

                    "priority":
                        priority,

                    "jira_priority":
                        actual_priority_name

                }


            except Exception:

                return {

                    "success":
                        False,

                    "message":
                        "Jira issue creation failed.",

                    "status_code":
                        response.status_code,

                    "response":
                        response.text,

                    "priority":
                        priority,

                    "jira_priority":
                        actual_priority_name

                }


        except Exception as error:

            print(
                "Jira connection error:",
                error
            )


            return {

                "success":
                    False,

                "message":
                    str(error),

                "priority":
                    priority

            }