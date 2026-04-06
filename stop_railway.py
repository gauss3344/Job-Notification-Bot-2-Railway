import requests
import os

def trigger_stop():
    api_token = os.getenv("RAILWAY_TOKEN")
    project_id = "32a48d1b-d4a9-477f-91ac-0ae4b8048d71"
    service_id = "bc2b59b7-91fb-44b9-b2bf-d0506ecf1335"
    environment_id = "30545d52-6cbf-444a-97f1-6075a82a5312"

    url = "https://backboard.railway.app/graphql/v2"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    
    # বর্তমান রানিং ডিপ্লয়মেন্ট আইডি খোঁজা
    query_get_id = """
    query deployments($input: DeploymentListInput!) {
      deployments(input: $input, first: 1) {
        edges { node { id status } }
      }
    }
    """
    variables_get = {"input": {"projectId": project_id, "serviceId": service_id, "environmentId": environment_id}}
    
    res = requests.post(url, json={"query": query_get_id, "variables": variables_get}, headers=headers)
    data = res.json()
    
    try:
        deploy_id = data["data"]["deployments"]["edges"][0]["node"]["id"]
        status = data["data"]["deployments"]["edges"][0]["node"]["status"]
        
        if status not in ["SUCCESS", "CRASHED", "INITIALIZING"]:
            print(f"⚠️ Deployment is already in {status} state.")
            return

        # স্টপ করার কমান্ড
        query_stop = "mutation stop($id: String!) { deploymentStop(id: $id) }"
        requests.post(url, json={"query": query_stop, "variables": {"id": deploy_id}}, headers=headers)
        print(f"✅ Stopped Deployment ID: {deploy_id}")
        
    except (IndexError, KeyError):
        print("❌ No active deployment found to stop.")

if __name__ == "__main__":
    trigger_stop()
