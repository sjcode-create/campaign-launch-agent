import os
from dotenv import load_dotenv
import anthropic
from docx import Document
from tavily import TavilyClient

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

print("Campaign Launch Agent ready!")


def call_claude(system_prompt, user_prompt, max_tokens=1024):
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )
    return message.content[0].text


def parse_field(output, label):
    if label + ':' in output:
        after = output.split(label + ':')[1]
        next_label_pos = len(after)
        for other_label in ['COPY TASK', 'STRATEGY TASK', 'ACTUAL CONDITIONS', 'EXPERIENTIAL HIGHLIGHTS',
                             'TRAVEL ADVISORIES', 'TRAVELER SENTIMENT', 'TARGET AUDIENCE', 'KEY MESSAGE',
                             'EMAIL ANGLE', 'PAID SOCIAL ANGLE', 'DIRECT MAIL ANGLE', 'SMS ANGLE',
                             'EMAIL SUBJECT', 'EMAIL BODY', 'PROSPECTS VERSION', 'YCM VERSION',
                             'TRAVEL ADVISORS VERSION', 'AUDIENCES', 'SCORE', 'STRENGTHS', 'IMPROVEMENTS']:
            if other_label != label and other_label + ':' in after:
                pos = after.index(other_label + ':')
                if pos < next_label_pos:
                    next_label_pos = pos
        return after[:next_label_pos].strip()
    return ''


def orchestrator(brief):
    print(f"\nOrchestrator reading brief...")

    output = call_claude(
        "You are a campaign orchestrator. Be extremely concise.",
        (
            f"Read this brief and give me 3 things in one sentence each:\n\n"
            f"COPY TASK: What copy needs to be written.\n"
            f"STRATEGY TASK: What strategy needs to be defined.\n"
            f"AUDIENCES: Which apply: Prospects, YCM, Travel Advisors.\n\n"
            f"Brief: {brief}\n\n"
            f"Format:\n"
            f"COPY TASK: ...\n"
            f"STRATEGY TASK: ...\n"
            f"AUDIENCES: ..."
        ),
        max_tokens=200
    )

    copy_task = parse_field(output, 'COPY TASK')
    strategy_task = parse_field(output, 'STRATEGY TASK')
    audiences_raw = parse_field(output, 'AUDIENCES')

    audiences = []
    if 'prospect' in audiences_raw.lower():
        audiences.append('Prospects')
    if 'ycm' in audiences_raw.lower() or 'past guest' in audiences_raw.lower() or 'yacht club' in audiences_raw.lower():
        audiences.append('YCM')
    if 'travel advisor' in audiences_raw.lower():
        audiences.append('Travel Advisors')
    if not audiences:
        audiences = ['Prospects']

    print(f"Audiences: {audiences}")
    return copy_task, strategy_task, audiences


def researcher_agent(brief):
    print(f"\nResearcher Agent searching...")

    tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

    search_query_raw = call_claude(
        "Extract destination and travel months as 3-5 words only.",
        f"Short search query for: {brief}",
        max_tokens=20
    )
    search_query = search_query_raw.strip()
    print(f"  Searching: {search_query}")

    try:
        conditions_result = tavily.search(query=f"{search_query} weather climate", search_depth="basic", max_results=2)
        sentiment_result = tavily.search(query=f"{search_query} traveler reviews 2026", search_depth="basic", max_results=2)
        advisories_result = tavily.search(query=f"{search_query} travel advisory 2026", search_depth="basic", max_results=2)

        conditions_text = " ".join([r.get("content", "") for r in conditions_result.get("results", [])])[:800]
        sentiment_text = " ".join([r.get("content", "") for r in sentiment_result.get("results", [])])[:800]
        advisories_text = " ".join([r.get("content", "") for r in advisories_result.get("results", [])])[:800]

    except Exception as e:
        print(f"  Search error: {str(e)}")
        conditions_text = sentiment_text = advisories_text = ""

    output = call_claude(
        "Travel analyst. One short sentence per field. Plain text only.",
        (
            f"One sentence each:\n\n"
            f"ACTUAL CONDITIONS: Climate during travel months.\n"
            f"EXPERIENTIAL HIGHLIGHTS: What makes this destination special this season.\n"
            f"TRAVEL ADVISORIES: Any risks. If none, say no major advisories.\n"
            f"TRAVELER SENTIMENT: What travelers are saying.\n\n"
            f"Brief: {brief}\n"
            f"Data: {conditions_text} {sentiment_text} {advisories_text}\n\n"
            f"Format:\n"
            f"ACTUAL CONDITIONS: ...\n"
            f"EXPERIENTIAL HIGHLIGHTS: ...\n"
            f"TRAVEL ADVISORIES: ...\n"
            f"TRAVELER SENTIMENT: ..."
        ),
        max_tokens=250
    )

    conditions = parse_field(output, 'ACTUAL CONDITIONS')
    highlights = parse_field(output, 'EXPERIENTIAL HIGHLIGHTS')
    advisories = parse_field(output, 'TRAVEL ADVISORIES')
    sentiment = parse_field(output, 'TRAVELER SENTIMENT')

    print(f"  Conditions: {conditions}")
    print(f"  Highlights: {highlights}")

    return conditions, highlights, advisories, sentiment


def strategist_agent(strategy_task, conditions, highlights, sentiment):
    print(f"\nStrategist Agent working...")

    output = call_claude(
        "Marketing strategist. One sentence per field. No exceptions. Plain text only.",
        (
            f"One sentence per field. Be direct.\n\n"
            f"Context: {highlights} {sentiment}\n"
            f"Task: {strategy_task}\n\n"
            f"Format:\n"
            f"TARGET AUDIENCE: ...\n"
            f"KEY MESSAGE: ...\n"
            f"EMAIL ANGLE: ...\n"
            f"PAID SOCIAL ANGLE: ...\n"
            f"DIRECT MAIL ANGLE: ...\n"
            f"SMS ANGLE: ..."
        ),
        max_tokens=300
    )

    audience = parse_field(output, 'TARGET AUDIENCE')
    message = parse_field(output, 'KEY MESSAGE')
    email_angle = parse_field(output, 'EMAIL ANGLE')
    social_angle = parse_field(output, 'PAID SOCIAL ANGLE')
    mail_angle = parse_field(output, 'DIRECT MAIL ANGLE')
    sms_angle = parse_field(output, 'SMS ANGLE')

    print(f"Key message: {message}")
    return audience, message, email_angle, social_angle, mail_angle, sms_angle


def copywriter_agent(copy_task, email_angle, key_message, conditions, highlights, audiences):
    print(f"\nCopywriter Agent working...")

    audience_instructions = {
        "Prospects": "PROSPECTS VERSION: Opening line only. Make them feel invited into something they didn't know existed.",
        "YCM": "YCM VERSION: Opening line only. Make them feel genuinely remembered by people, not a system.",
        "Travel Advisors": "TRAVEL ADVISORS VERSION: Opening line only. Make them feel like an insider with knowledge their clients need."
    }

    audience_prompts = "\n".join([audience_instructions[a] for a in audiences if a in audience_instructions])
    audience_labels = "\n".join([f"{a.upper().replace(' ', '_')} VERSION: ..." for a in audiences])

    output = call_claude(
        (
            "Expert copywriter for Windstar Cruises. Tagline: 180 from ordinary.\n\n"
            "The reader should feel: welcome, special, like they belong, excited.\n\n"
            "Email rules:\n"
            "- 3 short paragraphs. 2-3 sentences each. That is the entire email.\n"
            "- Lead with one vivid sensory moment. No facts yet.\n"
            "- Middle paragraph: what awaits them, in feeling not features.\n"
            "- Final paragraph: the offer, simply stated. Warm CTA.\n"
            "- Never use: set sail, dream vacation, adventure awaits, once in a lifetime\n"
            "- Subject line: emotionally clear, no geography lesson required\n"
            "- Plain text only"
        ),
        (
            f"Write a short promotional email. 3 paragraphs, 2-3 sentences each.\n\n"
            f"Context: {highlights} {conditions}\n"
            f"Direction: {email_angle}\n"
            f"Message: {key_message}\n"
            f"Task: {copy_task}\n\n"
            f"Then write one opening line variation for each audience below.\n"
            f"These replace only the first sentence of the email:\n\n"
            f"{audience_prompts}\n\n"
            f"Format:\n"
            f"EMAIL SUBJECT: ...\n"
            f"EMAIL BODY: ...\n"
            f"{audience_labels}"
        ),
        max_tokens=1200
    )

    subject = parse_field(output, 'EMAIL SUBJECT')

    if 'EMAIL BODY:' in output:
        body = output.split('EMAIL BODY:')[1].strip()
        for a in audiences:
            label = a.upper().replace(' ', '_') + ' VERSION:'
            if label in body:
                body = body.split(label)[0].strip()
    else:
        body = ''

    versions = {}
    for a in audiences:
        label = a.upper().replace(' ', '_') + ' VERSION'
        versions[a] = parse_field(output, label)

    print(f"Subject: {subject}")
    print(f"Body preview: {body[:150]}...")
    return subject, body, versions


def critic_agent(brief, subject, body):
    print(f"\nCritic Agent reviewing...")

    output = call_claude(
        "Senior marketing director. One sentence per field. Plain text only.",
        (
            f"Review this email. One sentence each.\n\n"
            f"Subject: {subject}\n"
            f"Email: {body[:400]}\n\n"
            f"SCORE: X/10\n"
            f"STRENGTHS: ...\n"
            f"IMPROVEMENTS: ..."
        ),
        max_tokens=120
    )

    score = parse_field(output, 'SCORE')
    strengths = parse_field(output, 'STRENGTHS')
    improvements = parse_field(output, 'IMPROVEMENTS')

    print(f"Score: {score}")
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
    print(f"{'='*60}")

    copy_task, strategy_task, audiences = orchestrator(brief)
    conditions, highlights, advisories, sentiment = researcher_agent(brief)
    audience, message, email_angle, social_angle, mail_angle, sms_angle = strategist_agent(strategy_task, conditions, highlights, sentiment)
    subject, body, versions = copywriter_agent(copy_task, email_angle, message, conditions, highlights, audiences)
    score, strengths, improvements = critic_agent(brief, subject, body)

    return {
        "subject": subject,
        "body": body,
        "versions": versions,
        "audiences": audiences,
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


if __name__ == "__main__":
    brief = read_brief_from_doc("brief.docx")
    result = run_campaign_agent(brief)
    print(f"\nEMAIL SUBJECT: {result['subject']}")
    print(f"\nEMAIL BODY:\n{result['body']}")
    print(f"\nAUDIENCE VARIATIONS:")
    for audience, version in result['versions'].items():
        print(f"\n{audience}: {version}")
    print(f"\nKEY MESSAGE: {result['message']}")
    print(f"\nCHANNEL ANGLES:")
    print(f"Email: {result['email_angle']}")
    print(f"Social: {result['social_angle']}")
    print(f"Direct Mail: {result['mail_angle']}")
    print(f"SMS: {result['sms_angle']}")
    print(f"\nRESEARCH:")
    print(f"Conditions: {result['conditions']}")
    print(f"Highlights: {result['highlights']}")
    print(f"Advisories: {result['advisories']}")
    print(f"Sentiment: {result['sentiment']}")
    print(f"\nCRITIC: {result['score']}")
    print(f"Strengths: {result['strengths']}")
    print(f"Improvements: {result['improvements']}")
