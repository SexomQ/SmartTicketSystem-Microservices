"""
Shared ticket data models for Smart Ticket System Microservices
"""
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class Ticket:
    """Ticket data model"""
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    user_name: str = ""
    user_email: str = ""
    department: Optional[str] = None
    confidence_score: Optional[int] = None
    status: str = "pending"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert ticket to dictionary"""
        result = asdict(self)
        if self.created_at:
            result['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            result['updated_at'] = self.updated_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Ticket':
        """Create ticket from dictionary"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class CategorizationResult:
    """AI Categorization result model"""
    ticket_id: int
    department: str
    confidence_score: int
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        if self.timestamp:
            result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class RoutingResult:
    """Routing result model"""
    ticket_id: int
    department: str
    confidence_score: int
    routed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        if self.routed_at:
            result['routed_at'] = self.routed_at.isoformat()
        return result
