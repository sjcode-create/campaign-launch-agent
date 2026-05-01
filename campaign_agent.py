import os
from dotenv import load_dotenv
import anthropic
from docx import Document
from tavily import TavilyClient

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

print("Campaign Launch Agent ready!")


def call_claude(system_prompt, user_prompt, max_tokens=2048):
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
                             'EMAIL SUBJECT', 'EMAIL BODY', 'SCORE', 'STRENGTHS', 'IMPROVEMENTS']:
            if other_label != label and other_label + ':' in after:
                pos = after.index(other_label + ':')
                if pos < next_label_pos:
                    next_label_pos = pos
        return after[:next_label_pos].strip()
    return ''


def orchestrator(brief):
    print(f"\nOrchestrator reading brief...")

    output = call_claude(
        "You are a campaign orchestrator. Break down a campaign brief into clear tasks for a copywriter and a strategist.",
        (
            f"Read this campaign brief and break it into exactly 2 tasks:\n\n"
            f"1. COPY TASK: What should the copywriter write?\n"
            f"2. STRATEGY TASK: What should the strategist define?\n\n"
            f"Brief: {brief}\n\n"
            f"Format exactly like this with no markdown or asterisks:\n"
            f"COPY TASK: ...\n"
            f"STRATEGY TASK: ..."
        )
    )

    copy_task = parse_field(output, 'COPY TASK')
    strategy_task = parse_field(output, 'STRATEGY TASK')

    print(f"Copy task: {copy_task[:100]}...")
    print(f"Strategy task: {strategy_task[:100]}...")

    return copy_task, strategy_task


def researcher_agent(brief):
    print(f"\nResearcher Agent searching for current travel context...")

    # Initialize Tavily here so secrets are already loaded
    tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

    search_query_raw = call_claude(
        "Extract the destination and travel months from a campaign brief. Return only a short search query, no markdown.",
        f"Extract the destination and travel months from this brief as a short web search query: {brief}"
    )
    search_query = search_query_raw.strip()
    print(f"  Searching for: {search_query}")

    try:
        conditions_result = tavily.search(
            query=f"{search_query} weather climate conditions",
            search_depth="basic",
            max_results=3
        )
        sentiment_result = tavily.search(
            query=f"{search_query} traveler reviews sentiment 2026",
            search_depth="basic",
            max_results=3
        )
        advisories_result = tavily.search(
            query=f"{search_query} travel advisory safety news 2026",
            search_depth="basic",
            max_results=3
        )

        conditions_text = " ".join([r.get("content", "") for r in conditions_result.get("results", [])])[:2000]
        sentiment_text = " ".join([r.get("content", "") for r in sentiment_result.get("results", [])])[:2000]
        advisories_text = " ".join([r.get("content", "") for r in advisories_result.get("results", [])])[:2000]

    except Exception as e:
        print(f"  Search error: {str(e)}")
        conditions_text = ""
        sentiment_text = ""
        advisories_text = ""

    output = call_claude(
        (
            "You are a travel industry analyst. Give real-world context to help a marketing team write accurate campaign copy. "
            "Be specific and factual. Do not use markdown, asterisks, or bold formatting. Write in plain text only."
        ),
        (
            f"Based on this research and the campaign brief, answer these 4 questions in plain text:\n\n"
            f"ACTUAL CONDITIONS: What are the real climate and physical conditions at this destination during the travel months?\n"
            f"EXPERIENTIAL HIGHLIGHTS: What makes this destination uniquely compelling in this specific season?\n"
            f"TRAVEL ADVISORIES: Are there any current travel advisories or news stories that could make this campaign tone-deaf?\n"
            f"TRAVELER SENTIMENT: What are travelers currently saying about this destination?\n\n"
            f"Campaign brief: {brief}\n\n"
            f"Conditions research: {conditions_text}\n\n"
            f"Sentiment research: {sentiment_text}\n\n"
            f"Advisories research: {advisories_text}\n\n"
            f"Format exactly like this with no markdown:\n"
            f"ACTUAL CONDITIONS: ...\n"
            f"EXPERIENTIAL HIGHLIGHTS: ...\n"
            f"TRAVEL ADVISORIES: ...\n"
            f"TRAVELER SENTIMENT: ..."
        )
    )

    conditions = parse_field(output, 'ACTUAL CONDITIONS')
    highlights = parse_field(output, 'EXPERIENTIAL HIGHLIGHTS')
    advisories = parse_field(output, 'TRAVEL ADVISORIES')
    sentiment = parse_field(output, 'TRAVELER SENTIMENT')

    print(f"  Conditions: {conditions[:100]}...")
    print(f"  Highlights: {highlights[:100]}...")
    print(f"  Advisories: {advisories[:100]}...")
    print(f"  Sentiment: {sentiment[:100]}...")

    return conditions, highlights, advisories, sentiment


def strategist_agent(strategy_task, conditions, highlights, sentiment):
    print(f"\nStrategist Agent working...")

    output = call_claude(
        "You are an expert marketing strategist for luxury travel brands. Write in plain text with no markdown or asterisks.",
        (
            f"Complete this strategy task using the research context. Write in plain text only, no markdown.\n\n"
            f"RESEARCH CONTEXT:\n"
            f"Actual destination conditions: {conditions}\n"
            f"What makes it compelling right now: {highlights}\n"
            f"Current traveler sentiment: {sentiment}\n\n"
            f"Task: {strategy_task}\n\n"
            f"Format exactly like this:\n"
            f"TARGET AUDIENCE: ...\n"
            f"KEY MESSAGE: ...\n"
            f"EMAIL ANGLE: ...\n"
            f"PAID SOCIAL ANGLE: ...\n"
            f"DIRECT MAIL ANGLE: ...\n"
            f"SMS ANGLE: ..."
        )
    )

    audience = parse_field(output, 'TARGET AUDIENCE')
    message = parse_field(output, 'KEY MESSAGE')
    email_angle = parse_field(output, 'EMAIL ANGLE')
    social_angle = parse_field(output, 'PAID SOCIAL ANGLE')
    mail_angle = parse_field(output, 'DIRECT MAIL ANGLE')
    sms_angle = parse_field(output, 'SMS ANGLE')

    print(f"Audience: {audience[:100]}...")
    print(f"Key message: {message[:100]}...")

    return audience, message, email_angle, social_angle, mail_angle, sms_angle


def copywriter_agent(copy_task, email_angle, key_message, conditions, highlights):
    print(f"\nCopywriter Agent working...")

    output = call_claude(
        (
            "You are an expert copywriter for Windstar Cruises, a yacht-style small ship cruise line whose tagline is '180 from ordinary.' "
            "Windstar sails into ports larger ships cannot reach, greets every guest by name, and delivers an intimate experience. "
            "Write copy that is understated and elegant, never flashy. Lead with experience and feeling. "
            "Avoid phrases like 'set sail', 'dream vacation', or 'adventure awaits.' "
            "End emails with a strong CTA like 'Reserve Your Voyage' — not a letter sign-off. "
            "Write in plain text only, no markdown or asterisks."
        ),
        (
            f"Complete this copy task. Write the full complete email, do not truncate.\n\n"
            f"1. EMAIL SUBJECT: A compelling premium subject line\n"
            f"2. EMAIL BODY: Full promotional email with opening hook, 2-3 paragraphs, and a CTA at the end.\n\n"
            f"Research context:\n"
            f"Actual conditions: {conditions}\n"
            f"Highlights: {highlights}\n\n"
            f"Strategic direction: {email_angle}\n"
            f"Key message: {key_message}\n\n"
            f"Task: {copy_task}\n\n"
            f"Format exactly like this:\n"
            f"EMAIL SUBJECT: ...\n"
            f"EMAIL BODY: ..."
        ),
        max_tokens=2048
    )

    subject = parse_field(output, 'EMAIL SUBJECT')

    if 'EMAIL BODY:' in output:
        body = output.split('EMAIL BODY:')[1].strip()
    else:
        body = ''

    print(f"Subject: {subject}")
    print(f"Body preview: {body[:150]}...")

    return subject, body


def critic_agent(brief, subject, body, audience, message, email_angle, social_angle, mail_angle, sms_angle, conditions, highlights, advisories, sentiment):
    print(f"\nCritic Agent reviewing...")

    output = call_claude(
        "You are a senior marketing director for luxury travel. Be concise and direct. Write in plain text only, no markdown.",
        (
            f"Review this campaign against the brief and travel context. Be brief.\n\n"
            f"ORIGINAL BRIEF: {brief[:500]}\n\n"
            f"REAL WORLD CONTEXT:\n"
            f"Actual conditions: {conditions}\n"
            f"Advisories: {advisories}\n"
            f"Sentiment: {sentiment}\n\n"
            f"EMAIL SUBJECT: {subject}\n"
            f"EMAIL BODY: {body[:500]}\n\n"
            f"Give me exactly 3 things in 1-2 sentences each:\n"
            f"SCORE: X/10\n"
            f"STRENGTHS: One sentence on what works best.\n"
            f"IMPROVEMENTS: One specific thing to fix.\n\n"
            f"Format exactly like this:\n"
            f"SCORE: X/10\n"
            f"STRENGTHS: ...\n"
            f"IMPROVEMENTS: ..."
        ),
        max_tokens=300
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

    copy_task, strategy_task = orchestrator(brief)
    conditions, highlights, advisories, sentiment = researcher_agent(brief)
    audience, message, email_angle, social_angle, mail_angle, sms_angle = strategist_agent(strategy_task, conditions, highlights, sentiment)
    subject, body = copywriter_agent(copy_task, email_angle, message, conditions, highlights)
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


if __name__ == "__main__":
    brief = read_brief_from_doc("brief.docx")
    result = run_campaign_agent(brief)
    for key, value in result.items():
        print(f"\n{key.upper()}: {value}")
