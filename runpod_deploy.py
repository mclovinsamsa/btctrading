#!/usr/bin/env python3
"""
RunPod Deployment Manager - Easy pod creation and management
Save and reuse configurations for repeated deployments
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional
import requests


class RunPodConfig:
    """Manage RunPod pod configurations"""
    
    CONFIG_DIR = Path.home() / ".runpod"
    CONFIG_DIR.mkdir(exist_ok=True)
    
    def __init__(self, name: str = "btc-xgb-poc"):
        self.name = name
        self.config_file = self.CONFIG_DIR / f"{name}_config.json"
    
    def save(self, config: Dict) -> bool:
        """Save configuration to disk"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✅ Configuraton saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False
    
    def load(self) -> Optional[Dict]:
        """Load configuration from disk"""
        try:
            if not self.config_file.exists():
                print(f"❌ Configuration file not found: {self.config_file}")
                return None
            
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return None
    
    def list_templates(self):
        """List all saved templates"""
        configs = list(self.CONFIG_DIR.glob("*_config.json"))
        if not configs:
            print("No templates found")
            return
        
        print("\n📋 Saved Templates:")
        for config_file in configs:
            print(f"  • {config_file.stem.replace('_config', '')}")


class RunPodDeployer:
    """Deploy and manage pods on RunPod"""
    
    API_URL = "https://api.runpod.io/graphql"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "RunPod-Manager/1.0"
        }
    
    def _request(self, query: str, variables: Dict = None) -> Optional[Dict]:
        """Make GraphQL request to RunPod API"""
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        try:
            response = requests.post(
                self.API_URL,
                headers={**self.headers, "api_key": self.api_key},
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                print(f"❌ GraphQL Error: {data['errors']}")
                return None
            
            return data.get("data")
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return None
    
    def create_pod(self, config: Dict) -> Optional[str]:
        """Create a new pod"""
        query = """
        mutation($input: PodFindAndDeployOnDemandInput!) {
          podFindAndDeployOnDemand(input: $input) {
            pod {
              id
              name
              status
              runtime {
                ports {
                  containerPort
                  exposePort
                }
              }
            }
          }
        }
        """
        
        # Convert config to RunPod format
        pod_name = config.get("pod_name", "btc-xgb-pod")
        
        variables = {
            "input": {
                "cloudType": config.get("cloud_type", "on-demand"),
                "gpuCount": config.get("gpu_count", 0),
                "gpuType": config.get("gpu_type", "RTX_4090") if config.get("gpu_count", 0) > 0 else None,
                "containerImage": config.get("image"),
                "containerDiskInGb": config.get("container_disk", 20),
                "volumeInGb": config.get("volume_size", 0),
                "minVolumeInGb": config.get("volume_size", 0),
                "name": pod_name,
            }
        }
        
        result = self._request(query, variables)
        if not result:
            return None
        
        pod = result.get("podFindAndDeployOnDemand", {}).get("pod", {})
        pod_id = pod.get("id")
        
        if pod_id:
            print(f"✅ Pod created successfully!")
            print(f"   ID: {pod_id}")
            print(f"   Name: {pod.get('name')}")
            print(f"   Status: {pod.get('status')}")
            
            # Display port information
            runtime = pod.get("runtime", {})
            ports = runtime.get("ports", [])
            if ports:
                print(f"\n   🔌 Ports:")
                for port in ports:
                    print(f"      Container {port.get('containerPort')} → {port.get('exposePort')}")
            
            return pod_id
        else:
            print(f"❌ Failed to create pod")
            return None
    
    def terminate_pod(self, pod_id: str) -> bool:
        """Terminate a pod"""
        query = """
        mutation($input: PodTerminateInput!) {
          podTerminate(input: $input) {
            success
          }
        }
        """
        
        result = self._request(query, {"input": {"podId": pod_id}})
        if result and result.get("podTerminate", {}).get("success"):
            print(f"✅ Pod {pod_id} terminated")
            return True
        else:
            print(f"❌ Failed to terminate pod")
            return False
    
    def get_pod_status(self, pod_id: str) -> Optional[Dict]:
        """Get detailed pod status"""
        query = """
        query($input: PodInput!) {
          pod(input: $input) {
            id
            name
            status
            gpuCount
            podType
            runtime {
              gpuCount
              gpuIds
              uptimeInSeconds
            }
            containerDiskInGb
            volumeInGb
            machine {
              gpuType
            }
          }
        }
        """
        
        result = self._request(query, {"input": {"podId": pod_id}})
        if result:
            return result.get("pod")
        return None
    
    def list_pods(self) -> Optional[list]:
        """List all user pods"""
        query = """
        query {
          myself {
            pods {
              id
              name
              status
              gpuType
              machine {
                gpuType
              }
            }
          }
        }
        """
        
        result = self._request(query)
        if result:
            return result.get("myself", {}).get("pods", [])
        return None


# CLI
def main():
    api_key = os.getenv("RUNPOD_API_KEY")
    
    if not api_key:
        print("❌ Error: RUNPOD_API_KEY environment variable not set")
        print("   Set it with: export RUNPOD_API_KEY='your_key'")
        sys.exit(1)
    
    deployer = RunPodDeployer(api_key)
    config_manager = RunPodConfig()
    
    # Default config
    default_config = {
        "pod_name": "btc-xgb-poc",
        "image": "yourusername/btc-xgb-poc:latest",
        "gpu_count": 1,
        "gpu_type": "RTX_4090",
        "container_disk": 20,
        "volume_size": 10,
        "cloud_type": "on-demand"
    }
    
    if len(sys.argv) < 2:
        print("""
🚀 RunPod Manager

Usage:
  python runpod_deploy.py [command] [args]

Commands:
  create [template]        Create a new pod (use saved template or default)
  terminate <pod_id>       Terminate a pod
  status <pod_id>          Get pod status
  list                     List all pods
  save <template_name>     Save current config as template
  load <template_name>     Load a template
  templates                List all templates
  config                   Show default configuration

Examples:
  python runpod_deploy.py create
  python runpod_deploy.py create btc-xgb-poc
  python runpod_deploy.py status pod_xxxxx
  python runpod_deploy.py save my-xgb-config
        """)
        return
    
    command = sys.argv[1]
    
    if command == "create":
        # Load template if provided
        if len(sys.argv) > 2:
            config = config_manager.load()
            if not config:
                config = default_config
        else:
            config = default_config
        
        print(f"\n📦 Creating pod with config:")
        print(json.dumps(config, indent=2))
        print()
        
        pod_id = deployer.create_pod(config)
        if pod_id:
            print(f"\n💾 Save this ID: {pod_id}")
    
    elif command == "terminate":
        if len(sys.argv) < 3:
            print("❌ Usage: python runpod_deploy.py terminate <pod_id>")
            return
        deployer.terminate_pod(sys.argv[2])
    
    elif command == "status":
        if len(sys.argv) < 3:
            print("❌ Usage: python runpod_deploy.py status <pod_id>")
            return
        
        status = deployer.get_pod_status(sys.argv[2])
        if status:
            print("\n📊 Pod Status:")
            print(json.dumps(status, indent=2))
    
    elif command == "list":
        pods = deployer.list_pods()
        if pods:
            print("\n📋 Your Pods:")
            for pod in pods:
                print(f"  • {pod.get('name')} ({pod.get('id')})")
                print(f"    Status: {pod.get('status')}")
                print(f"    GPU: {pod.get('machine', {}).get('gpuType', 'CPU')}")
        else:
            print("No pods found")
    
    elif command == "save":
        if len(sys.argv) < 3:
            print("❌ Usage: python runpod_deploy.py save <template_name>")
            return
        
        template_name = sys.argv[2]
        config_manager.name = template_name
        config_manager.save(default_config)
    
    elif command == "load":
        if len(sys.argv) < 3:
            print("❌ Usage: python runpod_deploy.py load <template_name>")
            return
        
        template_name = sys.argv[2]
        config_manager.name = template_name
        config = config_manager.load()
        if config:
            print("\n📋 Loaded Config:")
            print(json.dumps(config, indent=2))
    
    elif command == "templates":
        config_manager.list_templates()
    
    elif command == "config":
        print("\n📋 Default Configuration:")
        print(json.dumps(default_config, indent=2))


if __name__ == "__main__":
    main()
