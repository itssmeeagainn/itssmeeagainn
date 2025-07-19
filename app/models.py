from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

Base = declarative_base()


class Wallet(Base):
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(42), unique=True, index=True, nullable=False)
    network = Column(String(20), nullable=False)
    label = Column(String(255), nullable=True)
    risk_score = Column(Integer, default=0)
    is_monitored = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), nullable=True)
    total_balance_usd = Column(Float, default=0.0)
    transaction_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    outgoing_transactions = relationship("Transaction", foreign_keys="Transaction.from_address_id", back_populates="from_wallet")
    incoming_transactions = relationship("Transaction", foreign_keys="Transaction.to_address_id", back_populates="to_wallet")
    risk_assessments = relationship("RiskAssessment", back_populates="wallet")
    
    # Indexes
    __table_args__ = (
        Index('idx_wallet_address_network', 'address', 'network'),
        Index('idx_wallet_risk_score', 'risk_score'),
        Index('idx_wallet_monitored', 'is_monitored'),
    )


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String(66), unique=True, index=True, nullable=False)
    network = Column(String(20), nullable=False)
    block_number = Column(Integer, nullable=False)
    block_timestamp = Column(DateTime(timezone=True), nullable=False)
    from_address = Column(String(42), nullable=False)
    to_address = Column(String(42), nullable=False)
    from_address_id = Column(Integer, ForeignKey("wallets.id"), nullable=True)
    to_address_id = Column(Integer, ForeignKey("wallets.id"), nullable=True)
    amount = Column(String(78), nullable=False)  # Store as string to avoid precision loss
    amount_float = Column(Float, nullable=False)
    token_address = Column(String(42), nullable=True)
    token_symbol = Column(String(20), nullable=True)
    token_name = Column(String(255), nullable=True)
    token_decimals = Column(Integer, nullable=True)
    usd_value = Column(Float, nullable=True)
    gas_used = Column(Integer, nullable=True)
    gas_price = Column(String(78), nullable=True)
    gas_fee_usd = Column(Float, nullable=True)
    status = Column(String(10), default="success")  # success, failed, pending
    transaction_type = Column(String(20), nullable=True)  # transfer, swap, bridge, etc.
    risk_score = Column(Integer, default=0)
    is_flagged = Column(Boolean, default=False)
    flagged_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    from_wallet = relationship("Wallet", foreign_keys=[from_address_id], back_populates="outgoing_transactions")
    to_wallet = relationship("Wallet", foreign_keys=[to_address_id], back_populates="incoming_transactions")
    risk_assessments = relationship("RiskAssessment", back_populates="transaction")
    
    # Indexes
    __table_args__ = (
        Index('idx_transaction_hash_network', 'hash', 'network'),
        Index('idx_transaction_addresses', 'from_address', 'to_address'),
        Index('idx_transaction_timestamp', 'block_timestamp'),
        Index('idx_transaction_amount', 'amount_float'),
        Index('idx_transaction_risk', 'risk_score'),
        Index('idx_transaction_flagged', 'is_flagged'),
    )


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    assessment_type = Column(String(20), nullable=False)  # wallet, transaction
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(10), nullable=False)  # low, medium, high, critical
    risk_factors = Column(Text, nullable=True)  # JSON string of risk factors
    llm_analysis = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    assessed_by = Column(String(50), nullable=False)  # system, user, llm
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    wallet = relationship("Wallet", back_populates="risk_assessments")
    transaction = relationship("Transaction", back_populates="risk_assessments")
    
    # Indexes
    __table_args__ = (
        Index('idx_risk_assessment_type', 'assessment_type'),
        Index('idx_risk_assessment_score', 'risk_score'),
        Index('idx_risk_assessment_level', 'risk_level'),
    )


class TokenPrice(Base):
    __tablename__ = "token_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    token_address = Column(String(42), nullable=True)  # Null for native tokens
    token_symbol = Column(String(20), nullable=False)
    network = Column(String(20), nullable=False)
    price_usd = Column(Float, nullable=False)
    market_cap = Column(Float, nullable=True)
    volume_24h = Column(Float, nullable=True)
    price_change_24h = Column(Float, nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_token_price_symbol_network', 'token_symbol', 'network'),
        Index('idx_token_price_address', 'token_address'),
        Index('idx_token_price_updated', 'last_updated'),
    )


class MonitoringRule(Base):
    __tablename__ = "monitoring_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(20), nullable=False)  # amount, frequency, pattern, blacklist
    conditions = Column(Text, nullable=False)  # JSON string of conditions
    action = Column(String(20), nullable=False)  # flag, alert, block
    severity = Column(String(10), nullable=False)  # low, medium, high, critical
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_monitoring_rule_type', 'rule_type'),
        Index('idx_monitoring_rule_active', 'is_active'),
    )


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(20), nullable=False)  # transaction, wallet, pattern
    severity = Column(String(10), nullable=False)  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    related_wallet_address = Column(String(42), nullable=True)
    related_transaction_hash = Column(String(66), nullable=True)
    rule_id = Column(Integer, ForeignKey("monitoring_rules.id"), nullable=True)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(255), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    rule = relationship("MonitoringRule")
    
    # Indexes
    __table_args__ = (
        Index('idx_alert_type_severity', 'alert_type', 'severity'),
        Index('idx_alert_acknowledged', 'is_acknowledged'),
        Index('idx_alert_created', 'created_at'),
    )