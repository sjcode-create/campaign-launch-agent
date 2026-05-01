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
                             'EMAIL SUBJECT', 'EMAIL BODY', 'PROSPECT VERSION', 'YCM VERSION',
                             'TRAVEL ADVISOR VERSION', 'AUDIENCES', 'SCORE', 'STRENGTHS', 'IMPROVEMENTS']:
            if other_label != label and other_label + ':' in after:
                pos = after.index(other_label + ':')
                if pos < next_label_pos:
                    next_label_pos = pos
        return after[:next_label_pos].strip()
    return ''


def orchestrator(brief):
    print(f"\nOrchestrator reading brief...")

    output = call_claude(
        "You are a campaign orchestrator. Extract key information from a campaign brief concisely.",
        (
            f"Read this campaign brief and give me exactly 3 things:\n\n"
            f"COPY TASK: One sentence on what copy needs to be written.\n"
            f"STRATEGY TASK: One sentence on what strategy needs to be defined.\n"
            f"AUDIENCES: List which of these audiences are relevant based on the brief: Prospects, YCM (Yacht Club Members / past guests), Travel Advisors. List only the ones mentioned or implied.\n\n"
            f"Brief: {brief}\n\n"
            f"Format exactly like this:\n"
            f"COPY TASK: ...\n"
            f"STRATEGY TASK: ...\n"
            f"AUDIENCES: ..."
        ),
        max_tokens=300
    )

    copy_task = parse_field(output, 'COPY TASK')
    strategy_task = parse_field(output, 'STRATEGY TASK')
    audiences_raw = parse_field(output, 'AUDIENCES')

    audiences = []
    if 'Prospect' in audiences_raw or 'prospect' in audiences_raw:
        audiences.append('Prospects')
    if 'YCM' in audiences_raw or 'past guest' in audiences_raw.lower() or 'yacht club' in audiences_raw.lower():
        audiences.append('YCM')
    if 'Travel Advisor' in audiences_raw or 'travel advisor' in audiences_raw.lower():
        audiences.append('Travel Advisors')
    if not audiences:
        audiences = ['Prospects']

    print(f"Copy task: {copy_task[:100]}...")
    print(f"Audiences identified: {audiences}")

    return copy_task, strategy_task, audiences


def researcher_agent(brief):
    print(f"\nResearcher Agent searching for current travel context...")

    tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

    search_query_raw = call_claude(
        "Extract the destination and travel months from a campaign brief. Return only 3-5 words.",
        f"Extract destination and travel months as a short search query: {brief}",
        max_tokens=30
    )
    search_query = search_query_raw.strip()
    print(f"  Searching for: {search_query}")

    try:
        conditions_result = tavily.search(query=f"{search_query} weather climate", search_depth="basic", max_results=2)
        sentiment_result = tavily.search(query=f"{search_query} traveler reviews 2026", search_depth="basic", max_results=2)
        advisories_result = tavily.search(query=f"{search_query} travel advisory 2026", search_depth="basic", max_results=2)

        conditions_text = " ".join([r.get("content", "") for r in conditions_result.get("results", [])])[:1000]
        sentiment_text = " ".join([r.get("content", "") for r in sentiment_result.get("results", [])])[:1000]
        advisories_text = " ".join([r.get("content", "") for r in advisories_result.get("results", [])])[:1000]

    except Exception as e:
        print(f"  Search error: {str(e)}")
        conditions_text = ""
        sentiment_text = ""
        advisories_text = ""

    output = call_claude(
        "You are a travel analyst. One sentence per field. Plain text only, no markdown.",
        (
            f"Summarize this research in one sentence per field:\n\n"
            f"ACTUAL CONDITIONS: One sentence on climate during travel months.\n"
            f"EXPERIENTIAL HIGHLIGHTS: One sentence on what makes this destination special this season.\n"
            f"TRAVEL ADVISORIES: One sentence on any risks. If none, say no major advisories.\n"
            f"TRAVELER SENTIMENT: One sentence on what travelers are saying.\n\n"
            f"Brief: {brief}\n"
            f"Conditions: {conditions_text}\n"
            f"Sentiment: {sentiment_text}\n"
            f"Advisories: {advisories_text}\n\n"
            f"Format exactly like this:\n"
            f"ACTUAL CONDITIONS: ...\n"
            f"EXPERIENTIAL HIGHLIGHTS: ...\n"
            f"TRAVEL ADVISORIES: ...\n"
            f"TRAVELER SENTIMENT: ..."
        ),
        max_tokens=400
    )

    conditions = parse_field(output, 'ACTUAL CONDITIONS')
    highlights = parse_field(output, 'EXPERIENTIAL HIGHLIGHTS')
    advisories = parse_field(output, 'TRAVEL ADVISORIES')
    sentiment = parse_field(output, 'TRAVELER SENTIMENT')

    print(f"  Conditions: {conditions}")
    print(f"  Highlights: {highlights}")
    print(f"  Advisories: {advisories}")
    print(f"  Sentiment: {sentiment}")

    return conditions, highlights, advisories, sentiment


def strategist_agent(strategy_task, conditions, highlights, sentiment):
    print(f"\nStrategist Agent working...")

    output = call_claude(
        "You are a marketing strategist for luxury travel. Be brief. One to two sentences per field. Plain text only.",
        (
            f"Complete this strategy. One to two sentences per field maximum.\n\n"
            f"Context: {conditions} {highlights} {sentiment}\n\n"
            f"Task: {strategy_task}\n\n"
            f"Format exactly like this:\n"
            f"TARGET AUDIENCE: ...\n"
            f"KEY MESSAGE: ...\n"
            f"EMAIL ANGLE: ...\n"
            f"PAID SOCIAL ANGLE: ...\n"
            f"DIRECT MAIL ANGLE: ...\n"
            f"SMS ANGLE: ..."
        ),
        max_tokens=500
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
        "Prospects": (
            "PROSPECT VERSION: They have never sailed with Windstar. "
            "Open with something that makes them feel like they are being let in on a secret — "
            "a world of travel they did not know existed. Make them feel welcome before they have even booked."
        ),
        "YCM": (
            "YCM VERSION: They have sailed with Windstar before but have not been back in a while. "
            "Open with something that makes them feel genuinely remembered — not by a system, but by people. "
            "Make them feel like they belong here and that coming back is the most natural thing in the world."
        ),
        "Travel Advisors": (
            "TRAVEL ADVISOR VERSION: They are travel professionals who recommend Windstar to their clients. "
            "Open with something that reinforces why Windstar is the right recommendation — "
            "a detail or insight that makes them feel like an insider and expert."
        )
    }

    audience_prompts = "\n".join([audience_instructions[a] for a in audiences if a in audience_instructions])
    audience_labels = "\n".join([f"{a.upper().replace(' ', '_')} VERSION: ..." for a in audiences])

    output = call_claude(
        (
            "You are a copywriter for Windstar Cruises. Tagline: 180 from ordinary.\n\n"
            "Every guest should feel four things: welcome, special, like they belong, and excited about a unique experience.\n\n"
            "Windstar greets every guest by name. The crew knows your preferences before you ask.\n"
            "You sail into ports larger ships cannot enter. You are never one of thousands.\n\n"
            "Rules:\n"
            "- Lead with feeling, not facts\n"
            "- Never use: set sail, dream vacation, adventure awaits, once in a lifetime\n"
            "- Subject line must be emotionally clear — no ambiguity, no geography lesson required\n"
            "- Each version shares the same core email body — only the opening line and closing CTA change\n"
            "- Plain text only, no markdown"
        ),
        (
            f"Write one promotional email campaign with audience-specific variations.\n\n"
            f"Destination context: {highlights}\n"
            f"Current conditions: {conditions}\n"
            f"Strategic direction: {email_angle}\n"
            f"Core message: {key_message}\n"
            f"Campaign task: {copy_task}\n\n"
            f"Step 1 — Write a shared subject line and core email body (2-3 paragraphs) that works for all audiences.\n"
            f"Step 2 — Write a short opening line variation for each audience listed below. "
            f"This replaces only the first sentence of the email for each audience. Everything else stays the same.\n\n"
            f"Audience variations needed:\n{audience_prompts}\n\n"
            f"Format exactly like this:\n"
            f"EMAIL SUBJECT: ...\n"
            f"EMAIL BODY: ...\n"
            f"{audience_labels}"
        ),
        max_tokens=2048
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
        "You are a senior marketing director. One sentence per field. Plain text only.",
        (
            f"Review this email. One sentence per field.\n\n"
            f"Brief summary: {brief[:200]}\n"
            f"Subject: {subject}\n"
            f"Email opening: {body[:300]}\n\n"
            f"Format exactly like this:\n"
            f"SCORE: X/10\n"
            f"STRENGTHS: One sentence.\n"
            f"IMPROVEMENTS: One sentence."
        ),
        max_tokens=150
    )

    score = parse_field(output, 'SCORE')
    strengths = parse_field(output, 'STRENGTHS')
    improvements = parse_field(output, 'IMPROVEMENTS')

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
    print(f"\nCRITIC SCORE: {result['score']}")
    print(f"STRENGTHS: {result['strengths']}")
    print(f"IMPROVEMENTS: {result['improvements']}")
