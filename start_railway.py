import requests
import os

def trigger_start():
    api_token = os.getenv("RAILWAY_TOKEN")
    project_id = "2ce4c16d-0dd9-47b6-b67a-89ecb6963993"
    service_id = "aa713bbd-e18a-4be4-b1b4-f1fd5b9ea624"
    environment_id = "1a47c532-de5a-438a-813e-24ae07654e6e"

    url = "https://backboard.railway.app/graphql/v2"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    
    query = """
    mutation envDeploy($input: EnvironmentTriggersDeployInput!) {
      environmentTriggersDeploy(input: $input)
    }
    """
    variables = {"input": {"projectId": project_id, "serviceId": service_id, "environmentId": environment_id}}
    
    response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
    if response.status_code == 200:
        print("✅ Railway Service Started Successfully!")
    else:
        print(f"❌ Failed to start: {response.text}")

if __name__ == "__main__":
    trigger_start()
