import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
from openai import OpenAI
from docx import Document

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

print("Campaign Launch Agent ready!")


def orchestrator(brief):
    print(f"\nOrchestrator reading brief...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a campaign orchestrator. Break down a campaign brief into clear tasks for a copywriter and a strategist."
            },
            {
                "role": "user",
                "content": (
                    f"Read this campaign brief and break it into exactly 2 tasks:\n\n"
                    f"1. COPY TASK: What should the copywriter write?\n"
                    f"2. STRATEGY TASK: What should the strategist define?\n\n"
                    f"Brief: {brief}\n\n"
                    f"Format exactly like this:\n"
                    f"COPY TASK: ...\n"
                    f"STRATEGY TASK: ..."
                )
            }
        ]
    )

    output = response.choices[0].message.content
    lines = output.strip().split('\n')
    copy_task = next((l.replace('COPY TASK:', '').strip() for l in lines if 'COPY TASK:' in l), '')
    strategy_task = next((l.replace('STRATEGY TASK:', '').strip() for l in lines if 'STRATEGY TASK:' in l), '')

    print(f"Copy task: {copy_task}")
    print(f"Strategy task: {strategy_task}")

    return copy_task, strategy_task


def researcher_agent(brief):
    print(f"\nResearcher Agent searching for current travel context...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Extract the destination and travel months from a campaign brief in a few words suitable for a web search."
            },
            {
                "role": "user",
                "content": f"Extract the destination and travel months from this brief for a web search query: {brief}"
            }
        ]
    )
    search_query = response.choices[0].message.content.strip() + " travel conditions 2026"
    print(f"  Searching for: {search_query}")

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        search_response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(search_response.text, "html.parser")

        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        text = " ".join(line for line in lines if line)
        text = text[:3000]
    except Exception as e:
        text = f"Could not retrieve search results: {str(e)}"

    summary_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a travel industry analyst supporting a luxury cruise marketing team. "
                    "Your job is to give the copywriter and strategist the real-world context they need "
                    "to write accurate, authentic, and compelling campaign materials. "
                    "You are not evaluating whether a destination is pleasant — you are describing what it actually is "
                    "so copy can be written to match reality. Cold, dramatic, rugged destinations are as sellable as warm ones "
                    "if the copy is honest and evocative."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Based on this search content and the campaign brief, answer these 4 questions:\n\n"
                    f"1. ACTUAL CONDITIONS: What are the real climate and physical conditions at this destination during the travel months? "
                    f"Be specific and factual — not whether it is good or bad, but what it actually is.\n"
                    f"2. EXPERIENTIAL HIGHLIGHTS: What makes this destination uniquely compelling in this specific season? "
                    f"What experiences, sights, or moments define it right now?\n"
                    f"3. TRAVEL ADVISORIES: Are there any current travel advisories, safety concerns, political issues, "
                    f"or news stories that could make this campaign tone-deaf or problematic?\n"
                    f"4. TRAVELER SENTIMENT: What are travelers currently saying about this destination? "
                    f"Is demand high, low, or shifting?\n\n"
                    f"Campaign brief: {brief}\n\n"
                    f"Search content: {text}\n\n"
                    f"Format exactly like this:\n"
                    f"ACTUAL CONDITIONS: ...\n"
                    f"EXPERIENTIAL HIGHLIGHTS: ...\n"
                    f"TRAVEL ADVISORIES: ...\n"
                    f"TRAVELER SENTIMENT: ..."
                )
            }
        ]
    )

    output = summary_response.choices[0].message.content
    lines = output.strip().split('\n')
    conditions = next((l.replace('ACTUAL CONDITIONS:', '').strip() for l in lines if 'ACTUAL CONDITIONS:' in l), '')
    highlights = next((l.replace('EXPERIENTIAL HIGHLIGHTS:', '').strip() for l in lines if 'EXPERIENTIAL HIGHLIGHTS:' in l), '')
    advisories = next((l.replace('TRAVEL ADVISORIES:', '').strip() for l in lines if 'TRAVEL ADVISORIES:' in l), '')
    sentiment = next((l.replace('TRAVELER SENTIMENT:', '').strip() for l in lines if 'TRAVELER SENTIMENT:' in l), '')

    print(f"  Conditions: {conditions}")
    print(f"  Highlights: {highlights}")
    print(f"  Advisories: {advisories}")
    print(f"  Sentiment: {sentiment}")

    return conditions, highlights, advisories, sentiment


def strategist_agent(strategy_task, conditions, highlights, sentiment):
    print(f"\nStrategist Agent working...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert marketing strategist specializing in luxury travel and cruise brands. Define precise audience targeting and tailor messaging for each marketing channel."
            },
            {
                "role": "user",
                "content": (
                    f"Complete this strategy task using the real-world research context provided.\n\n"
                    f"RESEARCH CONTEXT:\n"
                    f"Actual destination conditions: {conditions}\n"
                    f"What makes it compelling right now: {highlights}\n"
                    f"Current traveler sentiment: {sentiment}\n\n"
                    f"Give me exactly 6 things:\n\n"
                    f"1. TARGET AUDIENCE: Who specifically should this campaign target? Be precise about demographics, psychographics, and behaviors.\n"
                    f"2. KEY MESSAGE: The single most compelling message for this audience, informed by the real destination experience.\n"
                    f"3. EMAIL ANGLE: How should the message be framed for a full promotional email?\n"
                    f"4. PAID SOCIAL ANGLE: How should the message be adapted for paid social ads? Keep it punchy and visual.\n"
                    f"5. DIRECT MAIL ANGLE: How should the message be framed for a premium physical mailer?\n"
                    f"6. SMS ANGLE: How should the message be distilled into a single elegant SMS under 160 characters? No exclamation points.\n\n"
                    f"Task: {strategy_task}\n\n"
                    f"Format exactly like this:\n"
                    f"TARGET AUDIENCE: ...\n"
                    f"KEY MESSAGE: ...\n"
                    f"EMAIL ANGLE: ...\n"
                    f"PAID SOCIAL ANGLE: ...\n"
                    f"DIRECT MAIL ANGLE: ...\n"
                    f"SMS ANGLE: ..."
                )
            }
        ]
    )

    output = response.choices[0].message.content
    lines = output.strip().split('\n')
    audience = next((l.replace('TARGET AUDIENCE:', '').strip() for l in lines if 'TARGET AUDIENCE:' in l), '')
    message = next((l.replace('KEY MESSAGE:', '').strip() for l in lines if 'KEY MESSAGE:' in l), '')
    email_angle = next((l.replace('EMAIL ANGLE:', '').strip() for l in lines if 'EMAIL ANGLE:' in l), '')
    social_angle = next((l.replace('PAID SOCIAL ANGLE:', '').strip() for l in lines if 'PAID SOCIAL ANGLE:' in l), '')
    mail_angle = next((l.replace('DIRECT MAIL ANGLE:', '').strip() for l in lines if 'DIRECT MAIL ANGLE:' in l), '')
    sms_angle = next((l.replace('SMS ANGLE:', '').strip() for l in lines if 'SMS ANGLE:' in l), '')

    print(f"Audience: {audience}")
    print(f"Key message: {message}")
    print(f"Email angle: {email_angle}")
    print(f"Paid social angle: {social_angle}")
    print(f"Direct mail angle: {mail_angle}")
    print(f"SMS angle: {sms_angle}")

    return audience, message, email_angle, social_angle, mail_angle, sms_angle


def copywriter_agent(copy_task, email_angle, key_message, conditions, highlights):
    print(f"\nCopywriter Agent working...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert copywriter for Windstar Cruises, a yacht-style small ship cruise line whose tagline is '180 from ordinary.' "
                    "Windstar sails into ports larger ships cannot reach, greets every guest by name, and delivers an intimate experience that feels nothing like a traditional cruise. "
                    "Write copy that is understated and elegant, never flashy or exclamation-heavy. "
                    "Lead with the experience and feeling, not the destination name. "
                    "Avoid generic travel phrases like 'set sail', 'dream vacation', or 'adventure awaits.' "
                    "Write as if speaking quietly to one sophisticated traveler, not broadcasting to a mass audience. "
                    "Always write copy that reflects the actual destination experience — never romanticize away reality. "
                    "A cold, dramatic destination should feel thrilling and alive, not falsely warm."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Complete this copy task and give me exactly 2 things:\n\n"
                    f"1. EMAIL SUBJECT: A compelling subject line that feels premium and enticing\n"
                    f"2. EMAIL BODY: A full promotional marketing email with an opening hook, 2-3 body paragraphs, and a strong CTA. "
                    f"End with a clear call to action like 'Reserve Your Voyage' or 'Explore Itineraries' — "
                    f"not a personal letter sign-off like 'Sincerely' or 'Warm regards.' "
                    f"This is a promotional marketing email, not a personal letter.\n\n"
                    f"RESEARCH CONTEXT — use this to make the copy accurate and authentic:\n"
                    f"Actual destination conditions: {conditions}\n"
                    f"What makes it compelling right now: {highlights}\n\n"
                    f"Strategic direction: {email_angle}\n"
                    f"Key message to convey: {key_message}\n\n"
                    f"Task: {copy_task}\n\n"
                    f"Format exactly like this:\n"
                    f"EMAIL SUBJECT: ...\n"
                    f"EMAIL BODY: ..."
                )
            }
        ]
    )

    output = response.choices[0].message.content
    lines = output.strip().split('\n')
    subject = next((l.replace('EMAIL SUBJECT:', '').strip() for l in lines if 'EMAIL SUBJECT:' in l), '')

    if 'EMAIL BODY:' in output:
        body = output.split('EMAIL BODY:')[1].strip()
    else:
        body = ''

    print(f"Subject: {subject}")
    print(f"Body: {body}")

    return subject, body


def critic_agent(brief, subject, body, audience, message, email_angle, social_angle, mail_angle, sms_angle, conditions, highlights, advisories, sentiment):
    print(f"\nCritic Agent reviewing...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a senior marketing director specializing in luxury travel. Review campaign work critically using real world travel context and provide a clear score and actionable feedback."
            },
            {
                "role": "user",
                "content": (
                    f"Review this campaign work against the original brief and current travel context.\n\n"
                    f"ORIGINAL BRIEF: {brief}\n\n"
                    f"REAL WORLD CONTEXT:\n"
                    f"Actual conditions: {conditions}\n"
                    f"Experiential highlights: {highlights}\n"
                    f"Travel advisories: {advisories}\n"
                    f"Traveler sentiment: {sentiment}\n\n"
                    f"EMAIL SUBJECT: {subject}\n"
                    f"EMAIL BODY: {body}\n"
                    f"TARGET AUDIENCE: {audience}\n"
                    f"KEY MESSAGE: {message}\n"
                    f"EMAIL ANGLE: {email_angle}\n"
                    f"PAID SOCIAL ANGLE: {social_angle}\n"
                    f"DIRECT MAIL ANGLE: {mail_angle}\n"
                    f"SMS ANGLE: {sms_angle}\n\n"
                    f"Give me exactly 3 things:\n"
                    f"1. SCORE: A score out of 10 factoring in authenticity, alignment with real destination conditions, and campaign effectiveness\n"
                    f"2. STRENGTHS: What works well in one sentence\n"
                    f"3. IMPROVEMENTS: One specific improvement based on the real world context\n\n"
                    f"Format exactly like this:\n"
                    f"SCORE: ...\n"
                    f"STRENGTHS: ...\n"
                    f"IMPROVEMENTS: ..."
                )
            }
        ]
    )

    output = response.choices[0].message.content
    lines = output.strip().split('\n')
    score = next((l.replace('SCORE:', '').strip() for l in lines if 'SCORE:' in l), '')
    strengths = next((l.replace('STRENGTHS:', '').strip() for l in lines if 'STRENGTHS:' in l), '')
    improvements = next((l.replace('IMPROVEMENTS:', '').strip() for l in lines if 'IMPROVEMENTS:' in l), '')

    print(f"Score: {score}")
    print(f"Strengths: {strengths}")
    print(f"Improvements: {improvements}")

    return score, strengths, improvements


def read_brief_from_doc(filepath):
    doc = Document(filepath)
    brief = ""
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            brief += paragraph.text.strip() + " "
    return brief.strip()


def run_campaign_agent(brief):
    print(f"\n{'='*60}")
    print(f"CAMPAIGN LAUNCH AGENT")
    print(f"Brief: {brief}")
    print(f"{'='*60}")

    # Step 1 - Orchestrator breaks down the brief
    copy_task, strategy_task = orchestrator(brief)

    # Step 2 - Researcher runs first to ground everything in reality
    conditions, highlights, advisories, sentiment = researcher_agent(brief)

    # Step 3 - Strategist uses research to define direction
    audience, message, email_angle, social_angle, mail_angle, sms_angle = strategist_agent(strategy_task, conditions, highlights, sentiment)

    # Step 4 - Copywriter uses both strategy and research to write accurate copy
    subject, body = copywriter_agent(copy_task, email_angle, message, conditions, highlights)

    # Step 5 - Critic reviews everything including real world context
    score, strengths, improvements = critic_agent(
        brief, subject, body, audience, message,
        email_angle, social_angle, mail_angle, sms_angle,
        conditions, highlights, advisories, sentiment
    )

    return {
        "subject": subject,
        "body": body,
        "audience": audience,
        "message": message,
        "email_angle": email_angle,
        "social_angle": social_angle,
        "mail_angle": mail_angle,
        "sms_angle": sms_angle,
        "conditions": conditions,
        "highlights": highlights,
        "advisories": advisories,
        "sentiment": sentiment,
        "score": score,
        "strengths": strengths,
        "improvements": improvements
    }


# Read brief from Word doc and run
if __name__ == "__main__":
    brief = read_brief_from_doc("brief.docx")
    result = run_campaign_agent(brief)
    print(f"\n{'='*60}")
    print(f"CAMPAIGN PACKAGE COMPLETE")
    print(f"{'='*60}")
    for key, value in result.items():
        print(f"\n{key.upper()}: {value}")
