"""Redis alert processing utilities."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Any

from core.redis_alerts import alert_manager


class AlertManager:
    """Mixin providing alert handling logic."""

    def _setup_redis_alerts(self) -> None:
        alert_manager.add_alert_handler("cinegraph_agent", self._handle_alert)

    async def _handle_alert(self, alert_data: Dict[str, Any]):
        try:
            enrichment_prompt = f"""
            Analyze this contradiction alert and provide:
            1. Detailed explanation of the inconsistency
            2. Severity assessment (low, medium, high, critical)
            3. Potential impact on story coherence
            4. Suggested resolution steps

            Alert Data: {json.dumps(alert_data, indent=2)}
            """
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": enrichment_prompt},
                ],
                max_tokens=500,
            )
            explanation = response.choices[0].message.content
            severity = self._assess_alert_severity(alert_data)
            enriched_alert = {
                "id": alert_data.get("id", f"alert_{datetime.utcnow().isoformat()}") ,
                "story_id": alert_data.get("story_id"),
                "alert_type": alert_data.get("alert_type", "contradiction_detected"),
                "severity": severity,
                "explanation": explanation,
                "original_alert": alert_data,
                "detected_at": alert_data.get("timestamp", datetime.utcnow().isoformat()),
                "enriched_at": datetime.utcnow().isoformat(),
                "status": "active",
            }
            self.supabase.table("alerts").insert(enriched_alert).execute()
        except Exception as e:
            print(f"Error handling alert: {e}")

    def _assess_alert_severity(self, alert_data: Dict[str, Any]) -> str:
        reason = alert_data.get("reason", "").lower()
        if any(k in reason for k in ["critical", "major", "severe"]):
            return "critical"
        if any(k in reason for k in ["significant", "important", "conflict"]):
            return "high"
        if any(k in reason for k in ["minor", "inconsistent", "unclear"]):
            return "medium"
        return "low"
