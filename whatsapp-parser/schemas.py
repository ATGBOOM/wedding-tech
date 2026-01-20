"""
Pydantic models for vendor commitment extraction output validation.
"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Price(BaseModel):
    """Price information extracted from conversation."""
    amount: Optional[float] = Field(default=None, description="Numeric amount")
    currency: Optional[str] = Field(default="INR", description="Currency code")
    type: Optional[Literal["total", "per_unit", "additional"]] = Field(
        default=None, 
        description="Whether price is total, per unit, or additional"
    )
    raw_text: Optional[str] = Field(default=None, description="Original text from conversation")


class Commitment(BaseModel):
    """A vendor commitment or deliverable."""
    id: str = Field(description="Unique identifier for this commitment")
    description: str = Field(description="What the vendor committed to deliver")
    deadline_raw: Optional[str] = Field(default=None, description="Original deadline text from conversation")
    deadline_resolved: Optional[str] = Field(default=None, description="ISO date string of resolved deadline")
    deadline_confidence: Literal["high", "medium", "low"] = Field(
        default="low",
        description="Confidence level in deadline resolution"
    )
    price: Optional[Price] = Field(default=None, description="Price information if discussed")
    status: Literal["pending", "in_progress", "completed", "cancelled"] = Field(
        default="pending",
        description="Current status of commitment"
    )
    status_evidence: Optional[str] = Field(default=None, description="Evidence from messages supporting the status")
    source_message_ids: list[str] = Field(
        default_factory=list,
        description="IDs of messages where this commitment was discussed"
    )


class Payment(BaseModel):
    """Payment information discussed or made."""
    id: str = Field(description="Unique identifier for this payment")
    type: Literal["advance", "partial", "full", "balance"] = Field(
        description="Type of payment"
    )
    amount: Optional[float] = Field(default=None, description="Payment amount")
    currency: Optional[str] = Field(default="INR", description="Currency code")
    status: Literal["discussed", "requested", "paid", "confirmed_received"] = Field(
        description="Payment status"
    )
    date: Optional[str] = Field(default=None, description="ISO date string of payment")
    raw_text: Optional[str] = Field(default=None, description="Original text from conversation")
    source_message_ids: list[str] = Field(
        default_factory=list,
        description="IDs of messages where this payment was discussed"
    )


class OpenItem(BaseModel):
    """Open item or follow-up needed."""
    id: str = Field(description="Unique identifier for this open item")
    description: str = Field(description="What needs to be resolved")
    priority: Literal["high", "medium", "low"] = Field(description="Priority level")
    source_message_ids: list[str] = Field(
        default_factory=list,
        description="IDs of related messages"
    )


class SuggestedFollowup(BaseModel):
    """Suggested follow-up action."""
    date: Optional[str] = Field(default=None, description="ISO date string for suggested follow-up")
    reason: Optional[str] = Field(default=None, description="Why follow-up is needed")


class VendorSummary(BaseModel):
    """High-level summary of vendor conversation."""
    vendor_name: Optional[str] = Field(default=None, description="Vendor's name")
    vendor_category: Optional[str] = Field(default=None, description="Vendor category (e.g., florist, caterer)")
    conversation_summary: Optional[str] = Field(default=None, description="Brief summary of the conversation")
    overall_status: Literal["on_track", "needs_attention", "at_risk"] = Field(
        description="Overall status assessment"
    )
    last_contact_date: Optional[str] = Field(default=None, description="ISO date string of last contact")
    suggested_followup: Optional[SuggestedFollowup] = Field(
        default=None,
        description="Suggested follow-up if needed"
    )


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process."""
    model: str = Field(description="LLM model used for extraction")
    extracted_at: str = Field(description="ISO timestamp of extraction")
    conversation_messages_count: int = Field(description="Number of messages processed")
    upload_date_used: str = Field(description="Upload date used for relative date resolution")


class VendorCommitmentExtraction(BaseModel):
    """Complete extraction output schema."""
    extraction_metadata: ExtractionMetadata
    vendor_summary: VendorSummary
    commitments: list[Commitment] = Field(default_factory=list)
    payments: list[Payment] = Field(default_factory=list)
    open_items: list[OpenItem] = Field(default_factory=list)