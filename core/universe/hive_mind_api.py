"""
Hive Mind REST API with WebSocket Support
Provides endpoints for message bus, skill library, and knowledge base management
"""

from fastapi import FastAPI, WebSocket, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .agent_communication import (
    MessageBus, HiveMind, AgentCommunicationBridge,
    Message, MessageType, MessagePriority
)

logger = logging.getLogger(__name__)

# Global instances
message_bus: Optional[MessageBus] = None
hive_mind: Optional[HiveMind] = None
app = FastAPI(
    title="UniVerse Hive Mind API",
    description="Agent communication and hive mind system",
    version="1.0.0"
)

# WebSocket connections
active_connections: List[WebSocket] = []

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_message_bus() -> MessageBus:
    """Get message bus instance"""
    global message_bus
    if not message_bus:
        raise HTTPException(status_code=500, detail="Message bus not initialized")
    return message_bus


def get_hive_mind() -> HiveMind:
    """Get hive mind instance"""
    global hive_mind
    if not hive_mind:
        raise HTTPException(status_code=500, detail="Hive mind not initialized")
    return hive_mind


# ============================================
# System Initialization
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    global message_bus, hive_mind
    
    encryption_key = "your-secure-key-here"  # Should be from config/env
    message_bus = MessageBus(encryption_key=encryption_key)
    hive_mind = HiveMind()
    
    logger.info("Hive Mind API initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Hive Mind API shutting down")


# ============================================
# Message Bus Endpoints
# ============================================

@app.post("/api/v1/messages/send")
async def send_message(
    sender_id: str,
    recipient_id: str,
    content: Dict[str, Any],
    message_type: str = "request",
    priority: str = "normal",
    requires_response: bool = False,
    bus: MessageBus = Depends(get_message_bus)
) -> Dict[str, Any]:
    """Send a message through the bus"""
    try:
        message = Message(
            id=str(datetime.now().timestamp()),
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=MessageType[message_type.upper()],
            content=content,
            priority=MessagePriority[priority.upper()],
            requires_response=requires_response
        )
        
        success = await bus.send(message)
        
        return {
            "status": "success" if success else "failed",
            "message_id": message.id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Send message error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/messages/batch-send")
async def batch_send_messages(
    messages: List[Dict[str, Any]],
    bus: MessageBus = Depends(get_message_bus)
) -> Dict[str, Any]:
    """Send multiple messages in batch"""
    try:
        message_objects = []
        for msg_data in messages:
            message = Message(
                id=str(datetime.now().timestamp()),
                sender_id=msg_data.get("sender_id"),
                recipient_id=msg_data.get("recipient_id"),
                message_type=MessageType[msg_data.get("message_type", "request").upper()],
                content=msg_data.get("content", {}),
                priority=MessagePriority[msg_data.get("priority", "normal").upper()],
                requires_response=msg_data.get("requires_response", False)
            )
            message_objects.append(message)
        
        results = await bus.batch_send(message_objects)
        
        return {
            "status": "success",
            "sent": sum(1 for v in results.values() if v),
            "failed": sum(1 for v in results.values() if not v),
            "total": len(results),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Batch send error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/messages/receive/{agent_id}")
async def receive_messages(
    agent_id: str,
    bus: MessageBus = Depends(get_message_bus)
) -> Dict[str, Any]:
    """Receive messages for an agent"""
    try:
        messages = []
        while True:
            msg = await bus.receive(agent_id)
            if not msg:
                break
            messages.append({
                "id": msg.id,
                "sender_id": msg.sender_id,
                "type": msg.message_type.value,
                "priority": msg.priority.value,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None
            })
        
        return {
            "agent_id": agent_id,
            "messages": messages,
            "count": len(messages),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Receive error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/messages/history/{agent_id}")
async def get_message_history(
    agent_id: str,
    message_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    bus: MessageBus = Depends(get_message_bus)
) -> Dict[str, Any]:
    """Get message history with optional filtering"""
    try:
        msg_type = MessageType[message_type.upper()] if message_type else None
        msg_priority = MessagePriority[priority.upper()] if priority else None
        
        messages = await bus.filter_messages(agent_id, msg_type, msg_priority)
        
        return {
            "agent_id": agent_id,
            "count": len(messages),
            "messages": [
                {
                    "id": m.id,
                    "sender_id": m.sender_id,
                    "type": m.message_type.value,
                    "priority": m.priority.value,
                    "created_at": m.created_at.isoformat()
                }
                for m in messages
            ],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/messages/dead-letter")
async def get_dead_letter_queue(
    bus: MessageBus = Depends(get_message_bus)
) -> Dict[str, Any]:
    """Get messages in dead letter queue"""
    return {
        "count": len(bus.dead_letter_queue),
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "recipient_id": m.recipient_id,
                "type": m.message_type.value,
                "reason": "Failed delivery or signature verification"
            }
            for m in bus.dead_letter_queue[:100]  # Limit to 100
        ],
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v1/messages/recover")
async def recover_dead_letters(
    message_id: Optional[str] = None,
    bus: MessageBus = Depends(get_message_bus)
) -> Dict[str, Any]:
    """Recover messages from dead letter queue"""
    try:
        recovered = await bus.recover_from_dead_letter(message_id)
        
        return {
            "status": "success",
            "recovered": recovered,
            "remaining": len(bus.dead_letter_queue),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Recovery error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/messages/queue-stats")
async def get_queue_stats(
    bus: MessageBus = Depends(get_message_bus)
) -> Dict[str, Any]:
    """Get message queue statistics"""
    return {
        "queue_stats": bus.get_queue_stats(),
        "metrics": bus.get_metrics(),
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# Hive Mind / Knowledge Base Endpoints
# ============================================

@app.post("/api/v1/knowledge/share")
async def share_knowledge(
    source_agent: str,
    knowledge_key: str,
    knowledge_value: Any,
    scope: str = "public",
    mind: HiveMind = Depends(get_hive_mind)
) -> Dict[str, Any]:
    """Share knowledge with the hive mind"""
    try:
        success = await mind.share_knowledge(source_agent, knowledge_key, knowledge_value, scope)
        
        return {
            "status": "success" if success else "failed",
            "key": knowledge_key,
            "scope": scope,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Knowledge share error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/knowledge/{knowledge_key}")
async def request_knowledge(
    knowledge_key: str,
    mind: HiveMind = Depends(get_hive_mind)
) -> Dict[str, Any]:
    """Request knowledge from shared knowledge base"""
    try:
        value = await mind.request_knowledge(knowledge_key)
        
        if value is None:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        
        return {
            "key": knowledge_key,
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Knowledge request error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/knowledge")
async def list_knowledge(
    mind: HiveMind = Depends(get_hive_mind)
) -> Dict[str, Any]:
    """List all shared knowledge"""
    try:
        knowledge_items = []
        for key, data in mind.state.shared_knowledge.items():
            knowledge_items.append({
                "key": key,
                "source": data.get("source"),
                "scope": data.get("scope"),
                "timestamp": data.get("timestamp", "").isoformat() if isinstance(data.get("timestamp"), datetime) else str(data.get("timestamp"))
            })
        
        return {
            "count": len(knowledge_items),
            "items": knowledge_items,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"List knowledge error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# Skill Library Endpoints
# ============================================

@app.post("/api/v1/skills/register")
async def register_skill(
    agent_id: str,
    skill_name: str,
    skill_code: str,
    success_rate: float = 0.0,
    mind: HiveMind = Depends(get_hive_mind)
) -> Dict[str, Any]:
    """Register a new skill with the hive mind"""
    try:
        skill_id = await mind.register_skill(agent_id, skill_name, skill_code, success_rate)
        
        return {
            "status": "success",
            "skill_id": skill_id,
            "skill_name": skill_name,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Skill register error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/skills/{skill_name}")
async def get_skill(
    skill_name: str,
    version: int = -1,
    mind: HiveMind = Depends(get_hive_mind)
) -> Dict[str, Any]:
    """Get a skill from the library"""
    try:
        skill = await mind.get_skill(skill_name, version)
        
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        return {
            "skill_name": skill_name,
            "skill": {
                "id": skill.get("id"),
                "agent_id": skill.get("agent_id"),
                "success_rate": skill.get("success_rate"),
                "usage_count": skill.get("usage_count"),
                "created_at": skill.get("created_at").isoformat() if isinstance(skill.get("created_at"), datetime) else str(skill.get("created_at"))
            },
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get skill error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/skills")
async def list_skills(
    mind: HiveMind = Depends(get_hive_mind)
) -> Dict[str, Any]:
    """List all available skills"""
    try:
        skills_list = []
        for skill_name, versions in mind.skill_versions.items():
            if versions:
                latest = versions[-1]
                skills_list.append({
                    "name": skill_name,
                    "versions": len(versions),
                    "success_rate": latest.get("success_rate"),
                    "usage_count": latest.get("usage_count")
                })
        
        return {
            "count": len(skills_list),
            "skills": skills_list,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"List skills error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/skills/recommend")
async def recommend_skills(
    agent_id: str,
    task_description: str,
    top_n: int = 3,
    mind: HiveMind = Depends(get_hive_mind)
) -> Dict[str, Any]:
    """Recommend relevant skills for a task"""
    try:
        recommendations = await mind.recommend_skill(agent_id, task_description, top_n)
        
        return {
            "agent_id": agent_id,
            "task": task_description,
            "recommendations": recommendations,
            "count": len(recommendations),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Recommend error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# Admin & Monitoring Endpoints
# ============================================

@app.get("/api/v1/admin/hive-state")
async def get_hive_state(
    mind: HiveMind = Depends(get_hive_mind)
) -> Dict[str, Any]:
    """Get current state of the hive mind"""
    try:
        return {
            "hive_state": mind.get_hive_state(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Hive state error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/admin/health")
async def health_check(
    bus: MessageBus = Depends(get_message_bus),
    mind: HiveMind = Depends(get_hive_mind)
) -> Dict[str, Any]:
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "message_bus": {
                "queues": len(bus.message_queues),
                "metrics": bus.get_metrics()
            },
            "hive_mind": mind.get_hive_state(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.post("/api/v1/admin/clear-dead-letter")
async def clear_dead_letter(
    bus: MessageBus = Depends(get_message_bus)
) -> Dict[str, Any]:
    """Clear the dead letter queue"""
    try:
        cleared = bus.clear_dead_letter_queue()
        
        return {
            "status": "success",
            "cleared": cleared,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Clear dead letter error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# WebSocket Endpoints (Real-time Updates)
# ============================================

@app.websocket("/ws/messages/{agent_id}")
async def websocket_messages(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint for real-time message updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        bus = get_message_bus()
        
        # Subscribe to messages
        async def message_callback(message: Message):
            if message.recipient_id == agent_id:
                await websocket.send_json({
                    "type": "message",
                    "id": message.id,
                    "sender_id": message.sender_id,
                    "content": message.content,
                    "timestamp": datetime.now().isoformat()
                })
        
        await bus.subscribe(agent_id, message_callback)
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)


@app.websocket("/ws/hive-mind")
async def websocket_hive_mind(websocket: WebSocket):
    """WebSocket endpoint for hive mind updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        mind = get_hive_mind()
        
        # Send initial state
        await websocket.send_json({
            "type": "state",
            "data": mind.get_hive_state(),
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive and send periodic updates
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "state": mind.get_hive_state(),
                    "timestamp": datetime.now().isoformat()
                })
    except Exception as e:
        logger.error(f"WebSocket hive error: {e}")
    finally:
        active_connections.remove(websocket)


# ============================================
# Root Endpoint
# ============================================

@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint"""
    return {
        "name": "UniVerse Hive Mind API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/api/v1/admin/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
