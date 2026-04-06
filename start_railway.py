import requests
import os

def trigger_start():
    api_token = os.getenv("RAILWAY_TOKEN")
    project_id = "32a48d1b-d4a9-477f-91ac-0ae4b8048d71"
    service_id = "bc2b59b7-91fb-44b9-b2bf-d0506ecf1335"
    environment_id = "30545d52-6cbf-444a-97f1-6075a82a5312"

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
