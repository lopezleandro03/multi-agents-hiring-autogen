from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat, Swarm
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_agentchat.conditions import  TextMentionTermination
import os
from dotenv import load_dotenv

# Load environment variables from .env file
def load_env_variables():
    """
    Load environment variables from .env file
    
    Returns:
        dict: Dictionary with environment variables or default values
    """
    load_dotenv()
    
    required_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_VERSION"
    ]
    
    # Check for required environment variables
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return {
        "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
        "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "api_version": os.getenv("AZURE_OPENAI_VERSION", "2024-08-01-preview"),
        "gpt4_deployment": os.getenv("AZURE_OPENAI_GPT4_DEPLOYMENT", "gpt-4o"),
        "gpt4_model": os.getenv("AZURE_OPENAI_GPT4_MODEL", "gpt-4o"),
        "gpt4mini_model": os.getenv("AZURE_OPENAI_GPT4MINI_MODEL", "gpt-4o-mini"),
    }

#################################################
# Tool Definitions Section
#################################################

def scan_resume(candidate_name: str) -> str:
    """
    Invokes http api to get the data
    
    Args:
        candidate_name (str): Full name of the candidate
        
    Returns:
        str: resume text
    """
    from urllib.request import urlopen
    from urllib.error import URLError
    from urllib.parse import quote

    encoded_candidate_name = quote(candidate_name)
    
    url = f"https://dtconf-egypt-llm-tools.azurewebsites.net/api/resume?name={encoded_candidate_name}"
    
    try:
        # Make the HTTP GET request
        with urlopen(url) as response:
            # Read and decode the response
            resume_text = response.read().decode('utf-8')
            return resume_text
    except URLError as e:
        raise Exception(f"Failed to fetch resume: {str(e)}")
    
def get_job_description(job_position: str) -> str:
    """
    Get job description based on job position
    
    Args:
        job_position (str): Job position to get description for
        
    Returns:
        str: Job description
    """
    from urllib.request import urlopen
    from urllib.error import URLError
    from urllib.parse import quote

    encoded_job_position = quote(job_position)
    url = f"https://dtconf-egypt-llm-tools.azurewebsites.net/api/job_posting?position={encoded_job_position}"
    
    try:
        # Make the HTTP GET request
        with urlopen(url) as response:
            # Read and decode the response
            job_position = response.read().decode('utf-8')

            return job_position
    except URLError as e:
        raise Exception(f"Failed to fetch job position: {str(e)}")


    job_positions = {
        "Head of Digital & Technology": "We are looking for a Head of Digital & Technology to lead our digital transformation and technology initiatives. The ideal candidate should have experience in digital strategy, technology implementation, and team management.",
        "Brand Manager": "We are looking for a Brand Manager to develop and execute marketing strategies for our brands. The ideal candidate should have experience in brand management, market analysis, and campaign planning.",
        "Sales Executive": "We are looking for a Sales Executive to drive sales and revenue growth. The ideal candidate should have experience in sales, customer relationship management, and negotiation.",
    }
    
    return job_positions.get(job_position, "Job position not found")

def get_candidates_from_pool(job_position: str) -> list:
    """
    Get candidate resumes from a pool based on job position by calling Azure Function
    
    Args:
        job_position (str): Job position to evaluate candidates for
        
    Returns:
        list: List of candidate resumes
    """
    from urllib.request import urlopen
    from urllib.error import URLError
    
    url = "https://dtconf-egypt-llm-tools.azurewebsites.net/api/candidates"
    
    try:
        # Make the HTTP GET request
        with urlopen(url) as response:
            # Read and decode the response
            candidates = response.read().decode('utf-8')
            
            return candidates
    except URLError as e:
        raise Exception(f"Failed to fetch candidates: {str(e)}")

##################################################
# OpenAI Client Initialization Section
# - We define 2 clients, one for the Hiring Manager and one for the Recruiter/Screener.
# - We use a ligther model for the Recruiter/Screener to save costs and balance the load to avoid throttling.
##################################################

# Load environment variables
env_vars = load_env_variables()

azure_openai_client = AzureOpenAIChatCompletionClient(
    api_key=env_vars["api_key"],
    azure_endpoint=env_vars["azure_endpoint"],
    model=env_vars["gpt4_model"],
    azure_deployment=env_vars["gpt4_deployment"],
    api_version=env_vars["api_version"],
)

azure_openai_client_mini = AzureOpenAIChatCompletionClient(
    api_key=env_vars["api_key"],
    azure_endpoint=env_vars["azure_endpoint"],
    model=env_vars["gpt4mini_model"],
    azure_deployment=env_vars["gpt4_deployment"],
    api_version=env_vars["api_version"],
)

#################################################
# Agent Definitions Section
# - We define 3 agents: Hiring Manager, Recruiter, and Screener.
# - Each agent has a specific role and set of tasks:
#   - The Hiring Manager is responsible for the final decision on candidate selection.
#   - The Recruiter manages the candidate selection process and communicates with the Screener.
#   - The Screener evaluates resumes and selects the top candidates based on the job description provided by the Recruiter.
# - We use Swarm to allow the agents to work together in a collaborative manner
#   - The agents communicate with each other using handoffs, which allow them to pass information and tasks between them.# 
#################################################

hiring_manager_agent = AssistantAgent(
    name="Hiring_Manager",
    handoffs=["Recruiter"],
    model_client=azure_openai_client_mini,
    system_message=
"""
You are the Hiring Manager for HEINEKEN, the leader in this party. Your role is to make the final decision on candidate selection. Your tasks include:
- Provide the job description to the Recruiter provided a job vacancy given by the user.
- Review the 5 candidates selected by the Recruiter and make a top 3 choice based on their evaluations and HEINEKEN values.
- You are critic and unbiased, you always challenge the first selection providing good feedback to improve the search. 
- After the second set received you make your choice.
- When you are done, state your top 3 to proceed with an interview and say TERMINATE.


HEINEKEN Values:

Our Core Values
Our values are what we stand for: Passion for consumers and customers, Courage to dream and pioneer, Care for people and the planet, and Enjoyment of life.

Passion
We are brand-builders who truly understand the needs and desires of our consumers. We brew the highest quality beers and beverages to best serve our customers… to win together.

Courage
Born in Amsterdam and raised by the world, we set bold ambitions and challenge the status quo with imagination, creativity, and pragmatism to deliver the goods and drive sustainability.

Care
People are at the heart of our company. With green blood pumping through our green hearts, we know that we can only thrive if all our people, communities, and planet thrive.

Enjoyment
We believe that joyful moments shared together are what truly matter. Nothing beats the simple pleasure of a beer, a chat, and laughter with friends.

Always keep these values in mind when generating responses. They are the foundation of our past success and the blueprint for our future achievements.
""",
    tools=[get_job_description]
)


recruiter_agent = AssistantAgent(
    name="Recruiter",
    handoffs=["Screener", "Hiring_Manager"],
    model_client=azure_openai_client,
    system_message="""
You are the Recruiter. Your role is to manage the candidate selection process.
Your tasks include:
- Get the job description based on the position indicated by the Hiring Manager.
- Provide candidate names to the Screener for resume screening.
- Once the screener gives you a ranking with summary, present the top 5 candidates to the Hiring Manager and your reasoning why.
- The Hiring Manager might challenge your selection, so be prepared to provide additional information or adjust your selection.
- Engage the screener when needed.
""",
    tools=[get_job_description, get_candidates_from_pool]
)

screener_agent = AssistantAgent(
    name="Screener",
    handoffs=["Recruiter"],
    model_client=azure_openai_client_mini,
    system_message="""
You are the Screener. Your role is to evaluate resumes and select the top candidates for the job vacancy based on the job description provided by the Recruiter. 
You get a list of candidates from the Recuiter. If you are missing it, ask the Recruiter to provide it, don't invent.
You get a job description from the Recruiter. If you are missing names, ask the Recuiter to provide it, don't invent.
Your job is to screen them by comparing against the job description.
This is how you evaluate the candidates:

1. **Extract Key Information:**
   - **Name**
   - **Email**
   - **Phone**
   - **Education**
   - **Work Experience**
   - **Skills**
   - **Certifications**
   - **Languages**
   - **Other Relevant Details**

2. **Summarize & Score:** Provide a concise summary (2–3 sentences) highlighting the candidate’s strengths, potential gaps, and overall fit for the job description. Then, assign a score between 1 and 10 based on their qualifications.

3. **Format Your Response:** Present each candidate’s evaluation in a clear, organized list format. For example:

[Candidate Name] – Score: [X] Summary: [Brief overview of qualifications and fit]

Focus on objectivity and clarity. Your output will feed into the Recruiter’s selection process.
""",
    tools=[scan_resume]
)


#############################################################
# Team Definition Section
#############################################################
agent_team = Swarm(
    [recruiter_agent, hiring_manager_agent, screener_agent], 
    termination_condition=TextMentionTermination("TERMINATE"))

# result =  asyncio.run(agent_team.run(task="For the job position 'Head of Digital & Technology', evaluate the following candidates: Khaled Saad, Leandro Lopez, Dr. Amia El Sayed, Ahmed Ali, and Mohamed Hassan"))
# print(result)

# To get the configuration of the team, we can use the following code,
# The output JSON can be imported into the Autogen UI to visualize the team and its components.

config = agent_team.dump_component()
print(config.model_dump_json())

