import azure.functions as func
import logging
from bs4 import BeautifulSoup
import requests
from requests.auth import HTTPBasicAuth 
import json
import os

#Authentication setup, pulling jira key from environment variables
jira_key = os.environ["jira_key"]
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
auth = HTTPBasicAuth("i47chen@uwaterloo.ca", jira_key)

#Parses the HTML content to extract relevant data using BeautifulSoup - hardcoded
def parse_html(soup):
    first_cols = soup.find_all('th', class_="small-12 large-4 columns first")
    labels = [col.get_text(strip=True).replace('\\r\\n', '') for col in first_cols]
    last_cols = soup.find_all('th', class_="small-12 large-8 columns last")[:-1]
    values = [col.get_text(strip=True).replace('\\r\\n', '') for col in last_cols]
    last_msg = soup.find_all('th', class_="small-12 large-12 columns first last")
    msg1 = last_msg[0].get_text(strip=True).replace('\\r\\n', '')[20:]
    msg2 = last_msg[1].get_text(strip=True).replace('\\r\\n', '') #.replace("\\", "").replace("'", "")
    data = [labels, values, msg1, msg2] 
    return data

#add time/date to it
#Post method to create jira issue using jira api
def create_jira_issue(data):
  description = ""
  title = data[2]
  for label, value in zip(data[0], data[1]):
    description += label + ": " + value + "\n"
  description += "\nDescription:\n"
  description += data[3]
  url = "https://uwaterloo.atlassian.net/rest/api/3/issue"
  headers = {
      "Accept": "application/json",
      "Content-Type": "application/json"
  }
  payload = json.dumps({
    "fields": {
      "project": {
        "key": "WDSD"
      },
      "assignee": {
        "id": "712020:d7a81d15-ca45-494e-93bf-728a646ff787"
      },
      "summary": title,
      "description": {
        "content": [
          {
            "content": [
              {
                "text": description,
                "type": "text"
              }
            ],
            "type": "paragraph"
          }
        ],
        "type": "doc",
        "version": 1
      },
      "issuetype": {
        "id": "19285"
      }
    }
  })
  try:
    response = requests.request(
      "POST",
      url,
      data = payload,
      headers = headers,
      auth = auth
    )
    response.raise_for_status()
    print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))
  except requests.exceptions.RequestException as e:
    print(f"Error creating Jira issue: {e}")
    if hasattr(e, 'response') and e.response is not None:
      print(f"Response content: {e.response.text}")
    return None


#Azure function entry point handling HTTP requests
@app.route(route="jsmwc")
def jsmwc(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    #type this in body of Post request in power autoamte: 
    #{
    #    "htmlBody": @{triggerBody()?['body']}
    #}
    # = req.get_json()
    #html_content = req_body.get('htmlBody')
    try:
        html_content = req.get_body().decode('utf-8')
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return func.HttpResponse(
             "Error getting html content",
             status_code=500
        )
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        data = parse_html(soup)
    except Exception as e:
        logging.error(f"Error creating Jira issue: {e}")
        return func.HttpResponse(
             "Error parsing data",
             status_code=500
        )
    try:
        create_jira_issue(data)
    except Exception as e:
        logging.error(f"Error creating Jira issue: {e}")
        return func.HttpResponse(
             "Error creating Jira issue",
             status_code=500
        )
    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )










