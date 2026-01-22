"""
Pydantic models for vendor commitment extraction - MVP version.
Optimized for: clarity, token efficiency, and direct mapping to business needs.
"""
from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field


class AgreedDetail(BaseModel):
    """A specific detail that's been confirmed/agreed upon."""
    category: str = Field(description="Type: decor, flowers, food, venue, timing, pricing, etc.")
    detail: str = Field(description="What was agreed, e.g. 'red roses', '200 plates', 'stage setup'")
    value: Optional[str] = Field(default=None, description="Amount/quantity if applicable, e.g. '₹500/plate', '200'")


class Commitment(BaseModel):
    """Something the vendor has committed to deliver."""
    what: str = Field(description="Brief description of the commitment")
    by_when: Optional[str] = Field(default=None, description="Deadline if mentioned (resolved to YYYY-MM-DD if possible)")
    when_confidence: Literal["exact", "approximate", "vague"] = Field(
        default="vague",
        description="exact=specific date given, approximate=relative date like 'kal', vague=unclear"
    )
    status: Literal["agreed", "done", "cancelled"] = Field(
        default="agreed",
        description="agreed=confirmed but not done, done=completed, cancelled=called off"
    )


class LooseThread(BaseModel):
    """Something mentioned but not finalized, or trailing off."""
    what: str = Field(description="What was discussed but not concluded")
    blocker: Optional[str] = Field(default=None, description="Why it's unresolved, if clear")
    urgency: Literal["high", "medium", "low"] = Field(default="medium")


class PendingPayment(BaseModel):
    """Payment that's been discussed or requested."""
    amount: Optional[float] = Field(default=None, description="Amount in INR")
    purpose: str = Field(description="e.g. 'advance', 'full payment', 'balance'")
    status: Literal["mentioned", "requested", "promised", "paid"] = Field(
        description="mentioned=just discussed, requested=vendor asked, promised=planner agreed, paid=confirmed paid"
    )


class VendorExtraction(BaseModel):
    """
    Complete extraction from a vendor conversation.
    Designed for wedding planner MVP - focuses on actionable information.
    """
    # Identity (passed through from input)
    vendor_name: str
    vendor_category: str
    
    # Core outputs
    summary: str = Field(
        description="2-3 sentence overview: what's the status with this vendor?"
    )
    
    agreed_details: list[AgreedDetail] = Field(
        default_factory=list,
        description="Specific things confirmed: decor type, flowers, counts, prices, locations, etc."
    )
    
    commitments: list[Commitment] = Field(
        default_factory=list,
        description="Things vendor has committed to deliver (with deadlines if known)"
    )
    
    completed: list[str] = Field(
        default_factory=list,
        description="Things already done/delivered (simple strings)"
    )
    
    loose_threads: list[LooseThread] = Field(
        default_factory=list,
        description="Things discussed but not finalized, or left hanging"
    )
    
    pending_payment: Optional[PendingPayment] = Field(
        default=None,
        description="Payment info if discussed"
    )
    
    next_action: Optional[str] = Field(
        default=None,
        description="Single most important next step, if any"
    )
    
    risk_flag: bool = Field(
        default=False,
        description="True if there are red flags: missed commitments, unclear terms, payment issues"
    )