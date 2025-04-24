import os
import json
from datetime import datetime
import app.utils.mongo_utils as mongo_utils
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# crewai imports
from crewai import Agent, Task, Crew
from crewai.tools import tool

# ---------------------------------------------------------------------
# 0. Disable Telemetry & Load Environment
# Done to remove connection issues and error
# ---------------------------------------------------------------------
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
load_dotenv()
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
# ---------------------------------------------------------------------
# 1. Initialize GPT-4 via Azure
# ---------------------------------------------------------------------
llm = ChatOpenAI(
    api_key=os.environ['OPENAI_API_KEY'],
    model="gpt-4o",
    temperature=0.1,
)

# ---------------------------------------------------------------------
# 2. Summarization Helper
# ---------------------------------------------------------------------
def summarize_text_with_gpt(text: str, llm, style: str = "bullet_points") -> str:
    """
    Summarize SR Letter text with GPT, focusing on key points:
    - Key regulatory changes
    - Superseded letters
    - Important dates/conditions
    - Notes/caveats
    """
    if style == "bullet_points":
        prompt = f"""
Summarize the following SR Letter text in concise bullet points, highlighting:
1) Key regulatory points
2) Any superseded letters
3) Important dates and conditions
4) Notes or caveats

TEXT:
{text}
"""
    else:
        prompt = f"Please summarize:\n\n{text}"

    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"Error during summarization: {str(e)}"

# ---------------------------------------------------------------------
# 3. Detail Fetch Function (Exact 'Debug Test' Approach)
# ---------------------------------------------------------------------
def fetch_sr_detail_page(url: str) -> str:
    """
    Attempt to fetch the detail page for an SR Letter using the SAME logic
    as the successful 'debug test' approach. If the status is not 200, we raise.
    """
    import requests
    from bs4 import BeautifulSoup

    # Minimal, known-good headers (same as your debug test)
    test_headers = {"User-Agent": "Mozilla/5.0"}

    # Send request
    r = requests.get(url, headers=test_headers, timeout=30)
    print("DEBUG detail status:", r.status_code, url)
    print("DEBUG detail snippet:", r.text[:300])  # optional

    if r.status_code != 200:
        # If not 200, raise error so we can handle it
        raise ValueError(f"Detail page returned {r.status_code}")

    # Parse HTML
    soup = BeautifulSoup(r.text, "html.parser")
    main_content = soup.select_one("div.article, div#article, main")
    if main_content:
        return main_content.get_text(separator="\n", strip=True)
    else:
        return soup.get_text(separator="\n", strip=True)

# ---------------------------------------------------------------------
# 4. SR Letter Scraper with Summaries (Uses 'fetch_sr_detail_page')
# Arun checked with Sam but still running into issues, could be due to
# proxy and i need to check this with Clinet
# ---------------------------------------------------------------------
@tool("Federal Reserve SR Letter Scraper with Summaries")
def sr_letter_scraper_with_summaries() -> str:
    """
    Scrape the 2024 SR Letters from the Federal Reserve main page,
    follow each letter's link, fetch the detail page with the EXACT
    minimal approach, then summarize if successful.
    """
    import requests
    from bs4 import BeautifulSoup

    base_url = "https://www.federalreserve.gov"
    main_url = f"{base_url}/supervisionreg/srletters/2024.htm"

    # You can also use the minimal headers for the main page if you like:
    main_headers = {"User-Agent": "Mozilla/5.0"}

    letters = []
    try:
        # Fetch main page
        resp = requests.get(main_url, headers=main_headers, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        article_div = soup.select_one("div#article")
        if not article_div:
            return json.dumps([])

        # Each letter is in .row => first col has link, second col has desc
        row_divs = article_div.select("div.row")
        for row in row_divs:
            link_tag = row.select_one("div.col-xs-3 a")
            desc_tag = row.select_one("div.col-xs-9 p")

            if not link_tag or not desc_tag:
                continue

            letter_id = link_tag.get_text(strip=True)
            description = desc_tag.get_text(strip=True)
            href = link_tag.get("href", "").strip()

            # Build the full link if relative
            if not href.startswith("http"):
                href = f"{base_url}{href}"

            print(f"DEBUG: Found letter_id={letter_id}, link={href}")

            # Attempt detail fetch with 'fetch_sr_detail_page'
            try:
                full_text = fetch_sr_detail_page(href)  # replicate debug approach
                # Summarize
                summary = summarize_text_with_gpt(full_text, llm, "bullet_points")
            except Exception as e:
                summary = f"Error during summarization: {str(e)}"

            # Collect results
            letters.append({
                "letter_id": letter_id,
                "description": description,
                "link": href,
                "summary": summary
            })

        return json.dumps(letters)

    except requests.exceptions.HTTPError as http_err:
        return json.dumps({
            "error": f"HTTP error fetching main page: {str(http_err)}",
            "letters": []
        })
    except Exception as ex:
        return json.dumps({
            "error": f"Generic scraping error: {str(ex)}",
            "letters": []
        })

# ---------------------------------------------------------------------
# 5. Policy Change Analyzer
# This need some work
# ---------------------------------------------------------------------
@tool("Policy Change Analyzer")
def policy_change_analyzer(current_data: str, previous_data: str = "") -> str:
    """
    Compare policy changes using GPT-4.
    If previous_data is not provided, default to empty => initial_scan.
    Returns JSON with new/modified/removed letters, etc.
    """
    import json

    def safe_parse(json_str):
        try:
            return json.loads(json_str)
        except (TypeError, json.JSONDecodeError):
            return json_str
   
    parsed_current = safe_parse(current_data)
    parsed_previous = safe_parse(previous_data) if previous_data else None
   
    if not parsed_previous or parsed_previous == "No previous data":
        return json.dumps({
            "status": "initial_scan",
            "available_letters": parsed_current,
            "message": "First time scanning - no previous data to compare"
        })

    prompt = f"""Analyze these SR Letters:

Previous Data:
{parsed_previous}

Current Data:
{parsed_current}

Format response with:
- new_letters: List of new additions
- modified_letters: List of changes
- removed_letters: List of removed items
- summary: Brief overview
"""
    try:
        response = llm.invoke(prompt)
        return json.dumps({
            "status": "analysis_complete",
            "results": response.content,
            "analysis_date": datetime.now().isoformat()
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

# ---------------------------------------------------------------------
# 6. Agents
# ---------------------------------------------------------------------
scraper_agent = Agent(
    role="Federal Reserve SR Letter Researcher",
    goal="Scrape and monitor SR Letters from Federal Reserve website",
    backstory="Expert in financial regulation documentation extraction.",
    tools=[sr_letter_scraper_with_summaries],
    verbose=True,
    llm=llm,
    allow_delegation=False
)

analyst_agent = Agent(
    role="Policy Change Analyst",
    goal="Analyze and report on SR Letter changes",
    backstory="Specialist in financial regulatory analysis",
    tools=[policy_change_analyzer],
    verbose=True,
    llm=llm,
    allow_delegation=False
)

changes_reporter_agent = Agent(
    role="Policy Change Reporter",
    goal="Report on SR Letter changes",
    backstory="Give Points on the changes in the SR Letters with the latest once",
    tools=[],
    verbose=True,
    llm=llm,
    allow_delegation=False
)
# ---------------------------------------------------------------------
# 7. Tasks
# ---------------------------------------------------------------------
scrape_task = Task(
    description=(
        "Scrape and verify 2024 SR Letters (Supervision and Regulation Letters) "
        "from the Federal Reserve website, including short bullet-point summaries."
    ),
    expected_output="Structured JSON list of SR Letters with metadata and short summaries. output must be saved in a Json format",
    agent=scraper_agent,
    output_file="sr_letters.json",
    async_execution=False
)

analysis_task = Task(
    description="Analyze SR Letters for changes and new publications",
    expected_output="Comprehensive change report with available documents",
    agent=analyst_agent,
    context=[scrape_task],
    output_file="analysis_report.json",
    human_input=False
)

changes_reporter_task = Task(
    description="Report on SR Letter changes",
    expected_output="List out all changes in the SR Letters in points.All changes must be in points. Points must be comparision based. follow a sequence of the changes done.",
    agent=changes_reporter_agent,
    context=[analysis_task,scrape_task],
    output_file="changes_report.json",
    human_input=False
)

# ---------------------------------------------------------------------
# 8. Crew + Execution
# ---------------------------------------------------------------------
crew = Crew(
    agents=[scraper_agent, analyst_agent, changes_reporter_agent],
    tasks=[scrape_task, analysis_task, changes_reporter_task],
    verbose=True,
    memory=False
)

async def run():
    try:
        result = crew.kickoff()
        print("\n=== CREW OUTPUT ===")
        print("1")
        if os.path.exists("analysis_report.json"):
            with open("analysis_report.json", "r", encoding="utf-8") as f:
                Analysis_Report = f.read()
        print("2")
        if os.path.exists("sr_letters.json"):
            with open("sr_letters.json", "r", encoding="utf-8") as f:
                sr_letter = f.read()
        print("3")
        if os.path.exists("changes_report.json"):
            with open("changes_report.json", "r", encoding="utf-8") as f:
                changes_report = f.read()
        ## SAVING THE DATA
        await mongo_utils.save_letter_info(sr_letter)
        # mongo_utils.save_analysis_report(json.loads(Analysis_Report))
        # mongo_utils.save_changes_report(json.loads(changes_report))
        return {
            'Analysis Report': Analysis_Report,
            'SR Letters': sr_letter,
            "Changes Report": changes_report
        }
        # print(result)

    except Exception as e:
        raise ValueError(f"An error occurred: {e}")

    # finally:
    #     if os.path.exists("sr_letters.json"):
    #         with open("sr_letters.json", "r", encoding="utf-8") as f:
    #             print("\nSaved SR Letters:")
    #             print(f.read())
    #     if os.path.exists("analysis_report.json"):
    #         with open("analysis_report.json", "r", encoding="utf-8") as f:
    #             print("\nAnalysis Report:")
    #             print(f.read())


async def get_all_sr_letters():
    try:
        await mongo_utils.get_all_sr_letters()
    except Exception as e:
        raise ValueError(f"An error occurred: {e}")
    
async def get_all_sr_letters_by_id(letter_id):
    try:
        return await mongo_utils.get_all_sr_letters_by_id(letter_id)
    except Exception as e:
        raise ValueError(f"An error occurred: {e}")