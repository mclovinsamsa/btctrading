#!/bin/bash

# RunPod Quick Deploy Script
# Usage: ./runpod_quick_deploy.sh [action] [args]

set -e

# Load environment
if [ -f ".env.runpod" ]; then
    source .env.runpod
else
    echo "❌ .env.runpod not found"
    echo "   Copy .env.runpod.example to .env.runpod and fill it in"
    exit 1
fi

# Check dependencies
command -v python3 &> /dev/null || { echo "❌ Python3 required"; exit 1; }
command -v docker &> /dev/null || { echo "❌ Docker required"; exit 1; }

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 RunPod Quick Deploy${NC}"

# Functions
push_image() {
    echo -e "${YELLOW}📦 Pushing Docker image to registry...${NC}"
    
    if [ -z "$DOCKER_USERNAME" ] || [ "$DOCKER_USERNAME" = "your_docker_username" ]; then
        echo -e "${RED}❌ DOCKER_USERNAME not configured${NC}"
        exit 1
    fi
    
    docker tag btc-xgb-poc:latest "$CONTAINER_IMAGE"
    docker push "$CONTAINER_IMAGE"
    echo -e "${GREEN}✅ Image pushed${NC}"
}

create_pod() {
    echo -e "${YELLOW}🎯 Creating pod on RunPod...${NC}"
    
    if [ -z "$RUNPOD_API_KEY" ] || [ "$RUNPOD_API_KEY" = "your_api_key_here" ]; then
        echo -e "${RED}❌ RUNPOD_API_KEY not configured${NC}"
        exit 1
    fi
    
    export RUNPOD_API_KEY
    python3 runpod_deploy.py create
}

save_template() {
    if [ -z "$1" ]; then
        echo -e "${RED}❌ Usage: ./runpod_quick_deploy.sh save <template_name>${NC}"
        exit 1
    fi
    
    export RUNPOD_API_KEY
    python3 runpod_deploy.py save "$1"
    echo -e "${GREEN}✅ Template saved as: $1${NC}"
}

terminate_pod() {
    if [ -z "$1" ]; then
        echo -e "${RED}❌ Usage: ./runpod_quick_deploy.sh terminate <pod_id>${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}🛑 Terminating pod $1...${NC}"
    export RUNPOD_API_KEY
    python3 runpod_deploy.py terminate "$1"
}

get_status() {
    if [ -z "$1" ]; then
        export RUNPOD_API_KEY
        python3 runpod_deploy.py list
    else
        export RUNPOD_API_KEY
        python3 runpod_deploy.py status "$1"
    fi
}

full_deploy() {
    echo -e "${BLUE}=== Full Deployment Pipeline ===${NC}"
    echo ""
    
    echo -e "${YELLOW}Step 1: Build Docker image${NC}"
    docker build -t btc-xgb-poc:latest .
    echo -e "${GREEN}✅ Build complete${NC}"
    echo ""
    
    push_image
    echo ""
    
    create_pod
    echo ""
    
    echo -e "${GREEN}=== Deployment Complete ===${NC}"
}

# Main
case "${1:-help}" in
    push)
        push_image
        ;;
    create)
        create_pod
        ;;
    terminate)
        terminate_pod "$2"
        ;;
    status)
        get_status "$2"
        ;;
    list)
        get_status
        ;;
    save)
        save_template "$2"
        ;;
    deploy)
        full_deploy
        ;;
    config)
        echo -e "${YELLOW}Current Configuration:${NC}"
        echo "POD_NAME: $POD_NAME"
        echo "IMAGE: $CONTAINER_IMAGE"
        echo "GPU: $GPU_COUNT × $GPU_TYPE"
        echo "DISK: ${CONTAINER_DISK}GB"
        echo "VOLUME: ${VOLUME_SIZE}GB"
        ;;
    *)
        echo "Usage: ./runpod_quick_deploy.sh [command] [args]"
        echo ""
        echo "Commands:"
        echo "  push <image>     Push Docker image to registry"
        echo "  create           Create a new pod"
        echo "  terminate <pod>  Terminate a pod"
        echo "  status [pod]     Get pod status (or list all)"
        echo "  list             List all pods"
        echo "  save <name>      Save current config as template"
        echo "  deploy           Full pipeline (build + push + create)"
        echo "  config           Show current configuration"
        echo ""
        echo "Examples:"
        echo "  ./runpod_quick_deploy.sh deploy"
        echo "  ./runpod_quick_deploy.sh status pod_xxxxx"
        echo "  ./runpod_quick_deploy.sh terminate pod_xxxxx"
        ;;
esac
