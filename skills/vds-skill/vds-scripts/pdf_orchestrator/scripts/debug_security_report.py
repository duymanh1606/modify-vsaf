#!/usr/bin/env python3
"""Debug script for security report generation."""

import logging
from datetime import UTC, datetime, timedelta

from vds_pdf_orchestrator.compliance.security_operations import (
    SecurityEventType,
    SecurityOperationsCenter,
    SecuritySeverity,
    ThreatType,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create SOC
soc = SecurityOperationsCenter()

# Create test data
start_time = datetime.now(UTC) - timedelta(hours=2)
end_time = datetime.now(UTC)

logger.info(f"Time range: {start_time} to {end_time}")

# Create events and incidents
for i in range(5):
    logger.info(f"Creating event {i}...")
    event = soc.log_security_event(
        event_type=SecurityEventType.AUTHENTICATION_FAILURE,
        severity=SecuritySeverity.HIGH,
        event_description=f"Failed login attempt {i}",
        threat_type=ThreatType.BRUTE_FORCE,
        source_ip=f"192.168.1.{100 + i}",  # Add source IP
    )
    logger(f"  Event timestamp: {event.timestamp}")
    logger(f"  Event in range: {start_time <= event.timestamp <= end_time}")
    logger(f"  Source IP: {event.source_ip}")

# Check events in SOC
logger(f"\nTotal events in SOC: {len(soc._events)}")
logger(f"Events by ID: {list(soc._events.keys())}")

# Filter events manually
filtered_events = []
for event in soc._events.values():
    if start_time <= event.timestamp <= end_time:
        filtered_events.append(event)
        logger(f"Event {event.event_id} is in range: {event.timestamp}")

logger(f"\nFiltered events: {len(filtered_events)}")

# Test report generation
logger("\nGenerating report...")
report = soc.generate_security_report(start_time, end_time)
logger(f"Report total_events: {report['summary']['total_events']}")
