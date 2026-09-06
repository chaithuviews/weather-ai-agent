import os
import json
import time
import requests
import smtplib

from pathlib import Path
from email.message import EmailMessage

from dotenv import load_dotenv
from google import genai


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env.txt")


api_key = os.getenv("GEMINI_API_KEY")
gmail_address = os.getenv("GMAIL_ADDRESS")
gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
email_to = os.getenv("EMAIL_TO")


if not api_key:
    raise ValueError("GEMINI_API_KEY not found")

if not gmail_address:
    raise ValueError("GMAIL_ADDRESS not found")

if not gmail_app_password:
    raise ValueError("GMAIL_APP_PASSWORD not found")

if not email_to:
    raise ValueError("EMAIL_TO not found")


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(api_key=api_key)


# ============================================================
# WEATHER TOOL
# ============================================================

def get_weather(city):

    print(f"\n🔧 TOOL CALLED: get_weather({city})")

    # Vijayawada coordinates
    latitude = 16.5062
    longitude = 80.6480

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "wind_speed_10m"
        ),
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_probability_max"
        ),
        "timezone": "Asia/Kolkata"
    }


    # --------------------------------------------------------
    # RETRY WEATHER API UP TO 3 TIMES
    # --------------------------------------------------------

    for attempt in range(3):

        try:

            response = requests.get(
                url,
                params=params,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            print(
                f"✅ Weather API succeeded "
                f"on attempt {attempt + 1}"
            )

            break


        except requests.exceptions.RequestException as e:

            print(
                f"⚠️ Weather API attempt "
                f"{attempt + 1} failed: {e}"
            )


            # Final attempt failed
            if attempt == 2:

                raise RuntimeError(
                    "Weather API unavailable after 3 attempts."
                )


            # Wait before retrying
            wait_seconds = 2 * (attempt + 1)

            print(
                f"⏳ Waiting {wait_seconds} seconds "
                f"before retry..."
            )

            time.sleep(wait_seconds)


    # --------------------------------------------------------
    # EXTRACT WEATHER DATA
    # --------------------------------------------------------

    current = data["current"]

    daily = data["daily"]


    return {

        "city": city,

        "current_temperature_c":
            current["temperature_2m"],

        "humidity_percent":
            current["relative_humidity_2m"],

        "wind_speed_kmh":
            current["wind_speed_10m"],

        "today_high_c":
            daily["temperature_2m_max"][0],

        "today_low_c":
            daily["temperature_2m_min"][0],

        "rain_probability_percent":
            daily["precipitation_probability_max"][0]
    }


# ============================================================
# EMAIL TOOL
# ============================================================

def send_email(subject, body):

    print("\n🔧 TOOL CALLED: send_email()")


    message = EmailMessage()

    message["Subject"] = subject

    message["From"] = gmail_address


    # Support multiple recipients
    recipients = [

        email.strip()

        for email in email_to.split(",")

        if email.strip()
    ]


    message["To"] = ", ".join(recipients)


    message.set_content(body)


    # Connect to Gmail SMTP
    with smtplib.SMTP(
        "smtp.gmail.com",
        587
    ) as server:

        server.starttls()

        server.login(
            gmail_address,
            gmail_app_password
        )

        server.send_message(message)


    return {

        "status": "success",

        "message":
            "Email sent successfully"
    }


# ============================================================
# GEMINI WEATHER TOOL DEFINITION
# ============================================================

weather_tool = {

    "type": "function",

    "name": "get_weather",

    "description":
        "Gets today's weather information for a city.",

    "parameters": {

        "type": "object",

        "properties": {

            "city": {

                "type": "string",

                "description":
                    "The city to get weather information for."
            }
        },

        "required": [
            "city"
        ]
    }
}


# ============================================================
# GEMINI EMAIL TOOL DEFINITION
# ============================================================

email_tool = {

    "type": "function",

    "name": "send_email",

    "description":
        "Sends an email containing a subject and message.",

    "parameters": {

        "type": "object",

        "properties": {

            "subject": {

                "type": "string",

                "description":
                    "The subject of the email."
            },

            "body": {

                "type": "string",

                "description":
                    "The complete message to send."
            }
        },

        "required": [
            "subject",
            "body"
        ]
    }
}


# ============================================================
# AVAILABLE TOOLS
# ============================================================

tools = [

    weather_tool,

    email_tool

]


# ============================================================
# AGENT INSTRUCTION
# ============================================================

user_question = """

You are a helpful daily weather assistant.

Get today's weather for Vijayawada.

Create a concise and friendly morning weather email.

The email must:

1. Start with exactly:

Good morning! 🌅

2. Clearly show:

- Current temperature
- Today's high
- Today's low
- Humidity
- Rain probability
- Wind speed

3. Give a practical recommendation based on
the actual weather conditions.

For example, if there is a high chance of rain,
recommend carrying an umbrella or raincoat.

4. Keep the wording natural and friendly.

5. End with exactly:

Have a great day! 😊

Do NOT use:

Best regards
Your Weather AI Agent
Formal email signatures

The email should feel like a friendly daily
weather update.

IMPORTANT:

First get the weather data.

Only after getting the weather data,
use the send_email tool to send the report.

Do not send the email before obtaining the
weather data.

"""


# ============================================================
# START AGENT
# ============================================================

print("\n🤖 STARTING WEATHER AI AGENT")

print("============================")


# ============================================================
# FIRST GEMINI INTERACTION
# ============================================================

interaction = client.interactions.create(

    model="gemini-3.5-flash-lite",

    input=user_question,

    tools=tools
)


# ============================================================
# AGENT LOOP
# ============================================================

while True:

    tool_call = None


    # --------------------------------------------------------
    # LOOK FOR A TOOL CALL
    # --------------------------------------------------------

    for step in interaction.steps:

        if step.type == "function_call":

            tool_call = step

            print(
                "\n🤖 GEMINI DECIDED TO USE A TOOL"
            )

            print(
                f"Tool: {step.name}"
            )

            print(
                f"Arguments: {step.arguments}"
            )

            break


    # --------------------------------------------------------
    # NO MORE TOOLS = AGENT FINISHED
    # --------------------------------------------------------

    if not tool_call:

        print(
            "\n🤖 FINAL AI RESPONSE"
        )

        print(
            "===================="
        )

        print(
            interaction.output_text
        )

        break


    # --------------------------------------------------------
    # READ TOOL ARGUMENTS
    # --------------------------------------------------------

    arguments = tool_call.arguments


    if isinstance(arguments, str):

        arguments = json.loads(arguments)


    # --------------------------------------------------------
    # EXECUTE WEATHER TOOL
    # --------------------------------------------------------

    if tool_call.name == "get_weather":

        city = arguments["city"]

        result = get_weather(city)


    # --------------------------------------------------------
    # EXECUTE EMAIL TOOL
    # --------------------------------------------------------

    elif tool_call.name == "send_email":

        subject = arguments["subject"]

        body = arguments["body"]

        result = send_email(
            subject,
            body
        )


    # --------------------------------------------------------
    # UNKNOWN TOOL
    # --------------------------------------------------------

    else:

        result = {

            "status": "error",

            "message":
                f"Unknown tool: {tool_call.name}"
        }


    # --------------------------------------------------------
    # DISPLAY TOOL RESULT
    # --------------------------------------------------------

    print(
        "\n🔧 TOOL RESULT"
    )

    print(
        "=============="
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )


    # --------------------------------------------------------
    # SEND TOOL RESULT BACK TO GEMINI
    # --------------------------------------------------------

    interaction = client.interactions.create(

        model="gemini-3.5-flash-lite",

        previous_interaction_id=interaction.id,

        input=[

            {

                "type":
                    "function_result",

                "name":
                    tool_call.name,

                "call_id":
                    tool_call.id,

                "result": [

                    {

                        "type":
                            "text",

                        "text":
                            json.dumps(result)
                    }
                ]
            }
        ],

        tools=tools
    )