"""
AutoCloud Architect - WebSocket Handler
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import logging
import json
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

# Connected WebSocket clients per job
connected_clients: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, job_id: str):
        """Accept and register a new connection."""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        logger.info(f"WebSocket connected for job: {job_id}")
    
    def disconnect(self, websocket: WebSocket, job_id: str):
        """Remove a connection."""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        logger.info(f"WebSocket disconnected for job: {job_id}")
    
    async def send_update(self, job_id: str, message: dict):
        """Send update to all clients watching a job."""
        if job_id in self.active_connections:
            disconnected = set()
            for websocket in self.active_connections[job_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.add(websocket)
            
            # Clean up disconnected clients
            self.active_connections[job_id] -= disconnected
    
    async def broadcast(self, message: dict):
        """Broadcast to all connected clients."""
        for job_id in self.active_connections:
            await self.send_update(job_id, message)


manager = ConnectionManager()


@router.websocket("/deploy/{job_id}")
async def websocket_deployment_updates(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time deployment updates.
    
    Clients connect here to receive live status updates for a deployment job.
    """
    await manager.connect(websocket, job_id)
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle client messages (e.g., ping)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket, job_id)


async def notify_deployment_update(job_id: str, status: dict):
    """
    Send deployment status update to all connected clients.
    
    This function is called by the deployment service when status changes.
    """
    await manager.send_update(job_id, {
        "type": "deployment_update",
        "job_id": job_id,
        "status": status
    })
