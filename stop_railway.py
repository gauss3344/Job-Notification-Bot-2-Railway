import requests
import os

def trigger_stop():
    api_token = os.getenv("RAILWAY_TOKEN")
    project_id = "2ce4c16d-0dd9-47b6-b67a-89ecb6963993"
    service_id = "aa713bbd-e18a-4be4-b1b4-f1fd5b9ea624"
    environment_id = "1a47c532-de5a-438a-813e-24ae07654e6e"

    url = "https://backboard.railway.app/graphql/v2"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    
    # বর্তমান রানিং ডিপ্লয়মেন্ট আইডি খোঁজা
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

    # API এরর চেক করা
    if "errors" in data:
        print(f"❌ Railway API Error: {data['errors'][0]['message']}")
        return

    if not data.get("data") or not data["data"].get("deployments"):
        print("❌ Could not fetch deployment data. Please check your RAILWAY_TOKEN and IDs.")
        return
    
    try:
        edges = data["data"]["deployments"]["edges"]
        if not edges:
            print("❌ No active deployment found to stop.")
            return

        deploy_id = edges[0]["node"]["id"]
        status = edges[0]["node"]["status"]
        
        # যদি অলরেডি রিমুভড বা স্টপ থাকে
        if status in ["REMOVED", "FAILED"]:
            print(f"⚠️ Deployment is already in {status} state. No need to stop.")
            return

        # স্টপ করার কমান্ড
        query_stop = "mutation stop($id: String!) { deploymentStop(id: $id) }"
        stop_res = requests.post(url, json={"query": query_stop, "variables": {"id": deploy_id}}, headers=headers)
        
        if stop_res.status_code == 200:
            print(f"✅ Successfully Stopped Deployment ID: {deploy_id}")
        else:
            print(f"❌ Failed to stop deployment: {stop_res.text}")
        
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    trigger_stop()
