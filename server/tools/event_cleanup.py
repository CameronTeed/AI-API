"""
Event cleanup service for managing expired events and automatic cleanup
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import psycopg

from ..db_config import get_db_pool

logger = logging.getLogger(__name__)

class EventCleanupService:
    """Service for managing event expiry and cleanup operations"""
    
    def __init__(self):
        self.db_pool = None
    
    async def initialize(self):
        """Initialize the cleanup service"""
        self.db_pool = await get_db_pool()
        logger.info("Event cleanup service initialized")
    
    async def run_cleanup_cycle(self) -> Dict[str, Any]:
        """Run a complete cleanup cycle"""
        if not self.db_pool:
            await self.initialize()
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "soft_deleted": 0,
            "hard_deleted": 0,
            "statistics": {},
            "errors": []
        }
        
        try:
            # Step 1: Soft delete expired events
            soft_delete_result = await self._soft_delete_expired_events()
            results["soft_deleted"] = soft_delete_result["count"]
            results["soft_deleted_ids"] = soft_delete_result["event_ids"]
            
            # Step 2: Hard delete old soft-deleted events (older than 90 days)
            hard_delete_count = await self._hard_delete_old_events()
            results["hard_deleted"] = hard_delete_count
            
            # Step 3: Get updated statistics
            stats = await self._get_cleanup_statistics()
            results["statistics"] = stats
            
            logger.info(f"Cleanup cycle completed: {results}")
            
        except Exception as e:
            logger.error(f"Error during cleanup cycle: {e}")
            results["errors"].append(str(e))
        
        return results
    
    async def _soft_delete_expired_events(self) -> Dict[str, Any]:
        """Soft delete expired events"""
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM soft_delete_expired_events()")
                result = await cursor.fetchone()
                
                if result:
                    count, event_ids = result
                    logger.info(f"Soft deleted {count} expired events: {event_ids}")
                    return {"count": count, "event_ids": event_ids or []}
                
                return {"count": 0, "event_ids": []}
    
    async def _hard_delete_old_events(self, days_old: int = 90) -> int:
        """Hard delete events that have been soft deleted for a while"""
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT hard_delete_old_events(%s)", (days_old,))
                result = await cursor.fetchone()
                
                count = result[0] if result else 0
                logger.info(f"Hard deleted {count} old events (>{days_old} days old)")
                return count
    
    async def _get_cleanup_statistics(self) -> Dict[str, int]:
        """Get current cleanup statistics"""
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM get_cleanup_statistics()")
                result = await cursor.fetchone()
                
                if result:
                    total, active, expired, soft_deleted, expiring_soon = result
                    return {
                        "total_events": total,
                        "active_events": active,
                        "expired_events": expired,
                        "soft_deleted_events": soft_deleted,
                        "events_expiring_soon": expiring_soon
                    }
                
                return {}
    
    async def restore_event(self, event_id: int) -> bool:
        """Restore a soft-deleted event"""
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT restore_event(%s)", (event_id,))
                result = await cursor.fetchone()
                
                success = result[0] if result else False
                if success:
                    logger.info(f"Successfully restored event {event_id}")
                else:
                    logger.warning(f"Failed to restore event {event_id} (may not exist or already active)")
                
                return success
    
    async def set_event_expiry(self, event_id: int, expiry_date: datetime, 
                              auto_cleanup: bool = True) -> bool:
        """Set expiry date for an event"""
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE event 
                    SET expiry_date = %s, 
                        auto_cleanup_enabled = %s,
                        modified_time = NOW()
                    WHERE event_id = %s AND is_active = true
                    """,
                    (expiry_date, auto_cleanup, event_id)
                )
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Set expiry date for event {event_id}: {expiry_date}")
                else:
                    logger.warning(f"Failed to set expiry for event {event_id} (may not exist or inactive)")
                
                return success
    
    async def get_expiring_events(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Get events expiring within specified days"""
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT 
                        e.event_id,
                        e.title,
                        e.expiry_date,
                        l.city,
                        (e.expiry_date - NOW()) as time_until_expiry
                    FROM event e
                    LEFT JOIN location l ON e.location_id = l.location_id
                    WHERE e.is_active = true
                      AND e.expiry_date IS NOT NULL
                      AND e.expiry_date > NOW()
                      AND e.expiry_date <= NOW() + INTERVAL '%s days'
                    ORDER BY e.expiry_date ASC
                    """,
                    (days_ahead,)
                )
                
                results = await cursor.fetchall()
                
                expiring_events = []
                for row in results:
                    event_id, title, expiry_date, city, time_until = row
                    expiring_events.append({
                        "event_id": event_id,
                        "title": title,
                        "expiry_date": expiry_date.isoformat() if expiry_date else None,
                        "city": city,
                        "time_until_expiry_hours": time_until.total_seconds() / 3600 if time_until else None
                    })
                
                return expiring_events
    
    async def get_cleanup_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent cleanup audit entries"""
        async with self.db_pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT 
                        audit_id,
                        event_id,
                        event_title,
                        cleanup_date,
                        cleanup_type,
                        cleanup_reason,
                        restored_date,
                        created_by
                    FROM event_cleanup_audit
                    ORDER BY cleanup_date DESC
                    LIMIT %s
                    """,
                    (limit,)
                )
                
                results = await cursor.fetchall()
                
                audit_entries = []
                for row in results:
                    audit_id, event_id, title, cleanup_date, cleanup_type, reason, restored_date, created_by = row
                    audit_entries.append({
                        "audit_id": audit_id,
                        "event_id": event_id,
                        "event_title": title,
                        "cleanup_date": cleanup_date.isoformat() if cleanup_date else None,
                        "cleanup_type": cleanup_type,
                        "cleanup_reason": reason,
                        "restored_date": restored_date.isoformat() if restored_date else None,
                        "created_by": created_by
                    })
                
                return audit_entries

# Global cleanup service instance
_cleanup_service = None

async def get_cleanup_service() -> EventCleanupService:
    """Get global cleanup service instance"""
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = EventCleanupService()
        await _cleanup_service.initialize()
    return _cleanup_service

class CleanupScheduler:
    """Scheduler for running periodic cleanup tasks"""
    
    def __init__(self, cleanup_service: EventCleanupService):
        self.cleanup_service = cleanup_service
        self.running = False
        self._task = None
    
    def start(self, interval_hours: int = 24):
        """Start the cleanup scheduler"""
        if self.running:
            logger.warning("Cleanup scheduler already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._run_schedule(interval_hours))
        logger.info(f"Started cleanup scheduler with {interval_hours}h interval")
    
    def stop(self):
        """Stop the cleanup scheduler"""
        self.running = False
        if self._task:
            self._task.cancel()
        logger.info("Stopped cleanup scheduler")
    
    async def _run_schedule(self, interval_hours: int):
        """Run the scheduled cleanup task"""
        while self.running:
            try:
                # Run cleanup cycle
                await self.cleanup_service.run_cleanup_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(interval_hours * 3600)
                
            except asyncio.CancelledError:
                logger.info("Cleanup scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup scheduler: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes