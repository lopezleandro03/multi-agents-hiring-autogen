import azure.functions as func
import logging
import io
import random
import requests
from bs4 import BeautifulSoup
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError
from PyPDF2 import PdfReader
from urllib.parse import quote, unquote

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="resume")
def resume(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    candidate_name = req.params.get('name')
    filename = f"{candidate_name.strip()}.pdf"
    
    connection_string = (
        "DefaultEndpointsProtocol=https;"
        "AccountName=dtconfdemo;"
        "EndpointSuffix=core.windows.net"
    )
    container_name = "resumes"
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(filename)
        
        # Download blob content
        blob_data = blob_client.download_blob()
        pdf_stream = io.BytesIO(blob_data.readall())
        
        # Create a PDF reader object
        pdf_reader = PdfReader(pdf_stream)
        
        # Extract text from all pages
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        if text:
            return func.HttpResponse(text)
        else:
            return func.HttpResponse(
                "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
                status_code=200
        )
        
    except Exception as e:
        raise Exception(f"Error processing {filename} from blob storage: {str(e)}")

@app.route(route="candidates", auth_level=func.AuthLevel.ANONYMOUS)
def candidates(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    candidate_names = [ 
                       "Khaled Saad",
                       "Leandro Lopez", 
                       "Dr. Amia El Sayed", 
                       "Omar Fahmy",
                       "Mohamed Hossam",
                       "Youssef Ahmed",
                       "Sara Ismail",
                       ]
    
    # Select 5 candidates randomly, make sure to shuffle the list first
    candidate_names = random.sample(candidate_names, 5)
    
    # format each candidate with a blank line for better readability
    candidate_names_str = "\n".join(candidate_names)

    if candidate_names_str:
        return func.HttpResponse(candidate_names_str)
    
    else:
        return func.HttpResponse(
            "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
                status_code=200
        )


@app.route(route="job_posting", auth_level=func.AuthLevel.ANONYMOUS)
def job_posting(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    position = req.params.get('position')
    if not position:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            position = req_body.get('position')

    position = unquote(position)
    print(f"Requested position: {position}")

    # Dictionary mapping position names to their respective URLs
    position_urls = {
        "Engineering Malt Plant Team Leader": "https://careers.theheinekencompany.com/Egypt/job/Cairo-Maintenance-Team-Leader-Engineering-Malt-Plant-11311/1156366201/",
        "Head of Digital": "https://careers.theheinekencompany.com/Egypt/job/Cairo-Head-of-Digital-&-Technology-11311/1165598501/",
        "Communications Manager": "https://careers.theheinekencompany.com/Egypt/job/Cairo-Communications-Manager-11311/1148591701/",
        "Medical Coordinator": "https://careers.theheinekencompany.com/Egypt/job/Cairo-Medical-Coordinator-Medical-11311/1151351101/"
    }

    if position and position in position_urls:
        try:
            # Get the URL for the specified position
            url = position_urls[position]
            
            # Fetch the webpage content
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract the job details (you might need to adjust these selectors based on the actual website structure)
            job_details = soup.find('span', class_='jobdescription')
            if job_details:
                return func.HttpResponse(job_details.get_text())
            else:
                return func.HttpResponse(
                    f"Could not extract job details for position: {position}",
                    status_code=404
                )
                
        except Exception as e:
            return func.HttpResponse(
                f"Error fetching job details: {str(e)}",
                status_code=500
            )
    else:
        available_positions = "\n".join(position_urls.keys())
        return func.HttpResponse(
            f"Please specify a valid position. Available positions are:\n{available_positions}",
            status_code=200
        )