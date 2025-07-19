from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class WalletAnalysisRequest(BaseModel):
    """Request model for wallet analysis."""
    address: str = Field(..., description="Wallet address to analyze")
    networks: Optional[List[str]] = Field(None, description="List of networks to analyze (default: all)")
    limit: Optional[int] = Field(100, description="Maximum number of transactions to fetch")
    analyze_risk: bool = Field(True, description="Whether to perform AI risk analysis")
    
    @validator('address')
    def validate_address(cls, v):
        if not v or len(v) < 20:
            raise ValueError('Invalid wallet address')
        return v.lower()
    
    @validator('limit')
    def validate_limit(cls, v):
        if v is not None and (v < 1 or v > 1000):
            raise ValueError('Limit must be between 1 and 1000')
        return v


class TransactionResponse(BaseModel):
    """Response model for transaction data."""
    hash: str
    network: str
    timestamp: datetime
    from_address: str
    to_address: str
    from_label: Optional[str] = None
    to_label: Optional[str] = None
    amount: float
    token_symbol: str
    token_address: Optional[str] = None
    usd_value: Optional[float] = None
    risk_score: int = 0
    risk_level: Optional[str] = None
    status: str = "success"
    transaction_type: Optional[str] = None
    gas_used: Optional[int] = None
    gas_fee_usd: Optional[float] = None


class WalletResponse(BaseModel):
    """Response model for wallet data."""
    address: str
    network: str
    label: Optional[str] = None
    risk_score: int = 0
    is_flagged: bool = False
    transaction_count: int = 0
    total_balance_usd: float = 0.0
    last_activity: Optional[datetime] = None
    first_seen: Optional[datetime] = None


class TransactionAnalysisResponse(BaseModel):
    """Response model for transaction analysis."""
    wallet: Optional[WalletResponse] = None
    transactions: List[TransactionResponse] = []
    total_count: int = 0
    networks_analyzed: List[str] = []
    analysis_summary: Optional[Dict[str, Any]] = None


class RiskAssessmentResponse(BaseModel):
    """Response model for risk assessment."""
    risk_score: int
    risk_level: str
    risk_factors: List[str] = []
    explanation: str
    recommended_actions: List[str] = []
    confidence_score: float
    analyzed_by: str
    analysis_timestamp: datetime


class DashboardStatsResponse(BaseModel):
    """Response model for dashboard statistics."""
    total_wallets: int
    total_transactions: int
    high_risk_wallets: int
    total_volume: float
    recent_alerts: int = 0
    active_monitors: int = 0


class DashboardResponse(BaseModel):
    """Response model for dashboard data."""
    stats: DashboardStatsResponse
    recent_transactions: List[TransactionResponse] = []
    high_risk_wallets: List[WalletResponse] = []
    recent_alerts: List[Dict[str, Any]] = []


class AlertResponse(BaseModel):
    """Response model for alerts."""
    id: int
    alert_type: str
    severity: str
    title: str
    message: str
    related_wallet_address: Optional[str] = None
    related_transaction_hash: Optional[str] = None
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime


class MonitoringRuleRequest(BaseModel):
    """Request model for creating monitoring rules."""
    name: str = Field(..., description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    rule_type: str = Field(..., description="Rule type (amount, frequency, pattern, blacklist)")
    conditions: Dict[str, Any] = Field(..., description="Rule conditions")
    action: str = Field(..., description="Action to take (flag, alert, block)")
    severity: str = Field(..., description="Severity level (low, medium, high, critical)")
    is_active: bool = Field(True, description="Whether the rule is active")
    
    @validator('rule_type')
    def validate_rule_type(cls, v):
        allowed_types = ['amount', 'frequency', 'pattern', 'blacklist']
        if v not in allowed_types:
            raise ValueError(f'Rule type must be one of: {allowed_types}')
        return v
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ['flag', 'alert', 'block']
        if v not in allowed_actions:
            raise ValueError(f'Action must be one of: {allowed_actions}')
        return v
    
    @validator('severity')
    def validate_severity(cls, v):
        allowed_severities = ['low', 'medium', 'high', 'critical']
        if v not in allowed_severities:
            raise ValueError(f'Severity must be one of: {allowed_severities}')
        return v


class MonitoringRuleResponse(BaseModel):
    """Response model for monitoring rules."""
    id: int
    name: str
    description: Optional[str] = None
    rule_type: str
    conditions: Dict[str, Any]
    action: str
    severity: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class PatternAnalysisRequest(BaseModel):
    """Request model for pattern analysis."""
    wallet_addresses: List[str] = Field(..., description="List of wallet addresses to analyze")
    time_range_days: int = Field(30, description="Number of days to analyze")
    min_transaction_count: int = Field(5, description="Minimum transactions required for analysis")
    networks: Optional[List[str]] = Field(None, description="Networks to include in analysis")
    
    @validator('wallet_addresses')
    def validate_addresses(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one wallet address is required')
        return [addr.lower() for addr in v]
    
    @validator('time_range_days')
    def validate_time_range(cls, v):
        if v < 1 or v > 365:
            raise ValueError('Time range must be between 1 and 365 days')
        return v


class PatternAnalysisResponse(BaseModel):
    """Response model for pattern analysis."""
    pattern_risk_score: int
    pattern_types: List[str] = []
    suspicious_indicators: List[str] = []
    analysis: str
    recommendations: List[str] = []
    wallets_analyzed: int = 0
    transactions_analyzed: int = 0
    time_range: str
    confidence_score: float = 0.0


class NetworkStatusResponse(BaseModel):
    """Response model for network status."""
    network: str
    status: str  # active, error, rate_limited
    api_key_configured: bool
    last_request: Optional[datetime] = None
    requests_remaining: Optional[int] = None
    error_message: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    status: str  # healthy, degraded, unhealthy
    database_connected: bool
    llm_service_available: bool
    blockchain_apis: List[NetworkStatusResponse] = []
    uptime_seconds: float
    version: str
    timestamp: datetime