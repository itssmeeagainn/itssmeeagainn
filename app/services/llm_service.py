import httpx
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from ..config import settings, RISK_THRESHOLDS, AMOUNT_THRESHOLDS

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.ollama_host = settings.ollama_host
        self.model_name = settings.llm_model_name
        self.session = httpx.AsyncClient(timeout=120.0)
        
    async def close(self):
        """Close the HTTP session."""
        await self.session.aclose()
    
    async def _call_ollama(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """Make a call to the local Ollama LLM."""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower temperature for more consistent analysis
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = await self.session.post(
                f"{self.ollama_host}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except Exception as e:
            logger.error(f"Failed to call Ollama: {str(e)}")
            return None
    
    async def analyze_transaction_risk(self, transaction_data: Dict) -> Dict[str, Any]:
        """Analyze a single transaction for AML risk factors."""
        system_prompt = """You are an expert AML (Anti-Money Laundering) analyst specialized in cryptocurrency transactions. 
Your task is to analyze cryptocurrency transactions and identify potential risk factors related to money laundering, 
terrorist financing, sanctions violations, and other illicit activities.

Focus on these key risk indicators:
1. Transaction amounts (especially large or unusual amounts)
2. Known high-risk addresses (mixers, darknet markets, sanctioned entities)
3. Transaction patterns (rapid movement, structuring, round amounts)
4. Geographic risk factors
5. Time-based patterns
6. Counterparty analysis

Provide a risk score from 0-100 and explain your reasoning."""

        # Prepare transaction summary
        tx_summary = self._format_transaction_for_analysis(transaction_data)
        
        prompt = f"""Analyze this cryptocurrency transaction for AML risk:

{tx_summary}

Please provide:
1. Risk Score (0-100): 
2. Risk Level (low/medium/high/critical):
3. Key Risk Factors:
4. Explanation:
5. Recommended Actions:

Format your response as JSON with these exact keys: risk_score, risk_level, risk_factors, explanation, recommended_actions"""

        response = await self._call_ollama(prompt, system_prompt)
        
        if response:
            try:
                # Try to parse JSON response
                result = json.loads(response)
                return self._validate_risk_analysis(result)
            except json.JSONDecodeError:
                # Fallback: parse structured text response
                return self._parse_text_analysis(response, transaction_data)
        
        # Fallback risk analysis
        return self._fallback_risk_analysis(transaction_data)
    
    async def analyze_wallet_risk(self, wallet_data: Dict, transactions: List[Dict]) -> Dict[str, Any]:
        """Analyze a wallet's overall risk profile."""
        system_prompt = """You are an expert AML analyst specialized in cryptocurrency wallet risk assessment. 
Analyze wallet behavior patterns to identify potential money laundering, terrorist financing, or other illicit activities.

Key analysis areas:
1. Transaction volume and frequency patterns
2. Counterparty risk (interactions with high-risk addresses)
3. Geographic and jurisdictional risks
4. Behavioral patterns (mixing, layering, integration phases)
5. Known entity associations
6. Unusual activity patterns

Provide comprehensive risk assessment with scoring and recommendations."""

        # Prepare wallet summary
        wallet_summary = self._format_wallet_for_analysis(wallet_data, transactions)
        
        prompt = f"""Analyze this cryptocurrency wallet for AML risk:

{wallet_summary}

Provide a comprehensive analysis including:
1. Overall Risk Score (0-100):
2. Risk Level (low/medium/high/critical):
3. Key Risk Factors:
4. Behavioral Patterns:
5. Recommendations:

Format as JSON with keys: risk_score, risk_level, risk_factors, behavioral_patterns, recommendations"""

        response = await self._call_ollama(prompt, system_prompt)
        
        if response:
            try:
                result = json.loads(response)
                return self._validate_risk_analysis(result)
            except json.JSONDecodeError:
                return self._parse_text_analysis(response, wallet_data)
        
        return self._fallback_wallet_analysis(wallet_data, transactions)
    
    async def analyze_transaction_pattern(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns across multiple transactions."""
        system_prompt = """You are an AML pattern recognition expert. Analyze sequences of cryptocurrency transactions 
to identify suspicious patterns that may indicate money laundering, structuring, or other illicit activities.

Focus on:
1. Structuring patterns (amounts just below reporting thresholds)
2. Rapid movement patterns (funds moving quickly through multiple addresses)
3. Mixing patterns (use of mixing services or complex routing)
4. Round number patterns
5. Time-based patterns
6. Geographic patterns
7. Counterparty patterns"""

        # Prepare transaction pattern summary
        pattern_summary = self._format_transactions_for_pattern_analysis(transactions)
        
        prompt = f"""Analyze these cryptocurrency transactions for suspicious patterns:

{pattern_summary}

Identify:
1. Pattern Risk Score (0-100):
2. Pattern Types Detected:
3. Suspicious Indicators:
4. Analysis:
5. Recommendations:

Format as JSON with keys: pattern_risk_score, pattern_types, suspicious_indicators, analysis, recommendations"""

        response = await self._call_ollama(prompt, system_prompt)
        
        if response:
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                return self._parse_pattern_analysis(response)
        
        return self._fallback_pattern_analysis(transactions)
    
    def _format_transaction_for_analysis(self, tx: Dict) -> str:
        """Format transaction data for LLM analysis."""
        amount_usd = tx.get("usd_value", 0) or 0
        
        return f"""
Transaction Hash: {tx.get('hash', 'N/A')}
Network: {tx.get('network', 'N/A')}
Timestamp: {tx.get('timestamp', 'N/A')}
From Address: {tx.get('from_address', 'N/A')}
From Label: {tx.get('from_label', 'Unknown')}
To Address: {tx.get('to_address', 'N/A')}
To Label: {tx.get('to_label', 'Unknown')}
Amount: {tx.get('amount', 0)} {tx.get('token_symbol', 'ETH')}
USD Value: ${amount_usd:,.2f}
Transaction Type: {tx.get('transaction_type', 'N/A')}
Gas Fee: ${tx.get('gas_fee_usd', 0):.2f}
Status: {tx.get('status', 'N/A')}
"""
    
    def _format_wallet_for_analysis(self, wallet: Dict, transactions: List[Dict]) -> str:
        """Format wallet data for LLM analysis."""
        total_tx_count = len(transactions)
        total_volume = sum(tx.get("usd_value", 0) or 0 for tx in transactions)
        avg_tx_amount = total_volume / total_tx_count if total_tx_count > 0 else 0
        
        # Get counterparty analysis
        counterparties = set()
        high_risk_counterparties = []
        
        for tx in transactions[:10]:  # Analyze recent transactions
            from_addr = tx.get("from_address")
            to_addr = tx.get("to_address")
            from_label = tx.get("from_label")
            to_label = tx.get("to_label")
            
            if from_addr:
                counterparties.add(from_addr)
                if from_label and any(keyword in from_label.lower() for keyword in ["mixer", "tornado", "dark", "illicit"]):
                    high_risk_counterparties.append(from_label)
            
            if to_addr:
                counterparties.add(to_addr)
                if to_label and any(keyword in to_label.lower() for keyword in ["mixer", "tornado", "dark", "illicit"]):
                    high_risk_counterparties.append(to_label)
        
        return f"""
Wallet Address: {wallet.get('address', 'N/A')}
Network: {wallet.get('network', 'N/A')}
Label: {wallet.get('label', 'Unknown')}
Total Transactions: {total_tx_count}
Total Volume (USD): ${total_volume:,.2f}
Average Transaction (USD): ${avg_tx_amount:,.2f}
Unique Counterparties: {len(counterparties)}
High-Risk Counterparties: {high_risk_counterparties}
Current Risk Score: {wallet.get('risk_score', 0)}
Is Flagged: {wallet.get('is_flagged', False)}
First Seen: {wallet.get('first_seen', 'N/A')}
Last Activity: {wallet.get('last_activity', 'N/A')}
"""
    
    def _format_transactions_for_pattern_analysis(self, transactions: List[Dict]) -> str:
        """Format multiple transactions for pattern analysis."""
        if not transactions:
            return "No transactions to analyze"
        
        # Sort by timestamp
        sorted_txs = sorted(transactions, key=lambda x: x.get("timestamp", datetime.min))
        
        summary = f"Total Transactions: {len(transactions)}\n"
        summary += f"Time Range: {sorted_txs[0].get('timestamp')} to {sorted_txs[-1].get('timestamp')}\n\n"
        
        # Analyze amounts
        amounts = [tx.get("usd_value", 0) or 0 for tx in transactions]
        total_volume = sum(amounts)
        avg_amount = total_volume / len(amounts) if amounts else 0
        
        summary += f"Total Volume: ${total_volume:,.2f}\n"
        summary += f"Average Amount: ${avg_amount:,.2f}\n"
        summary += f"Min Amount: ${min(amounts):,.2f}\n"
        summary += f"Max Amount: ${max(amounts):,.2f}\n\n"
        
        # Recent transactions sample
        summary += "Recent Transactions:\n"
        for i, tx in enumerate(sorted_txs[:5]):
            summary += f"{i+1}. {tx.get('timestamp')} - ${tx.get('usd_value', 0):,.2f} {tx.get('token_symbol', 'ETH')}\n"
            summary += f"   From: {tx.get('from_label') or tx.get('from_address', 'N/A')[:10]}...\n"
            summary += f"   To: {tx.get('to_label') or tx.get('to_address', 'N/A')[:10]}...\n\n"
        
        return summary
    
    def _validate_risk_analysis(self, result: Dict) -> Dict[str, Any]:
        """Validate and normalize risk analysis results."""
        # Ensure required fields exist
        risk_score = result.get("risk_score", 0)
        if isinstance(risk_score, str):
            try:
                risk_score = int(risk_score)
            except ValueError:
                risk_score = 0
        
        risk_score = max(0, min(100, risk_score))  # Clamp to 0-100
        
        # Determine risk level from score
        if risk_score < RISK_THRESHOLDS["low"]:
            risk_level = "low"
        elif risk_score < RISK_THRESHOLDS["medium"]:
            risk_level = "medium"
        elif risk_score < RISK_THRESHOLDS["high"]:
            risk_level = "high"
        else:
            risk_level = "critical"
        
        return {
            "risk_score": risk_score,
            "risk_level": result.get("risk_level", risk_level),
            "risk_factors": result.get("risk_factors", []),
            "explanation": result.get("explanation", "LLM analysis completed"),
            "recommended_actions": result.get("recommended_actions", []),
            "confidence_score": 0.8,  # Default confidence
            "analyzed_by": "llm",
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _parse_text_analysis(self, response: str, data: Dict) -> Dict[str, Any]:
        """Parse non-JSON text response from LLM."""
        # Basic parsing logic for structured text
        risk_score = 25  # Default low risk
        risk_level = "low"
        
        # Look for risk indicators in text
        response_lower = response.lower()
        if any(word in response_lower for word in ["high risk", "critical", "suspicious", "illicit"]):
            risk_score = 75
            risk_level = "high"
        elif any(word in response_lower for word in ["medium risk", "moderate", "caution"]):
            risk_score = 50
            risk_level = "medium"
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": ["LLM text analysis"],
            "explanation": response[:500],  # Truncate long responses
            "recommended_actions": ["Review manually"],
            "confidence_score": 0.5,
            "analyzed_by": "llm",
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _fallback_risk_analysis(self, transaction_data: Dict) -> Dict[str, Any]:
        """Fallback risk analysis when LLM is unavailable."""
        amount_usd = transaction_data.get("usd_value", 0) or 0
        risk_score = 0
        risk_factors = []
        
        # Basic rule-based risk scoring
        if amount_usd > AMOUNT_THRESHOLDS["whale"]:
            risk_score += 40
            risk_factors.append("Very large transaction amount")
        elif amount_usd > AMOUNT_THRESHOLDS["very_large"]:
            risk_score += 25
            risk_factors.append("Large transaction amount")
        elif amount_usd > AMOUNT_THRESHOLDS["large"]:
            risk_score += 15
            risk_factors.append("Significant transaction amount")
        
        # Check for known high-risk labels
        from_label = transaction_data.get("from_label", "").lower()
        to_label = transaction_data.get("to_label", "").lower()
        
        if any(keyword in from_label or keyword in to_label for keyword in ["mixer", "tornado", "dark"]):
            risk_score += 50
            risk_factors.append("High-risk counterparty")
        
        # Determine risk level
        if risk_score >= 75:
            risk_level = "critical"
        elif risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "explanation": "Fallback rule-based analysis",
            "recommended_actions": ["Manual review recommended"] if risk_score > 50 else [],
            "confidence_score": 0.6,
            "analyzed_by": "system",
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _fallback_wallet_analysis(self, wallet_data: Dict, transactions: List[Dict]) -> Dict[str, Any]:
        """Fallback wallet analysis when LLM is unavailable."""
        total_volume = sum(tx.get("usd_value", 0) or 0 for tx in transactions)
        tx_count = len(transactions)
        
        risk_score = 0
        risk_factors = []
        
        if total_volume > AMOUNT_THRESHOLDS["whale"] * 10:
            risk_score += 30
            risk_factors.append("Very high total volume")
        
        if tx_count > 1000:
            risk_score += 20
            risk_factors.append("High transaction frequency")
        
        # Check existing risk score
        existing_risk = wallet_data.get("risk_score", 0)
        risk_score = max(risk_score, existing_risk)
        
        return {
            "risk_score": min(risk_score, 100),
            "risk_level": "medium" if risk_score > 50 else "low",
            "risk_factors": risk_factors,
            "behavioral_patterns": ["High volume activity"] if total_volume > AMOUNT_THRESHOLDS["large"] else [],
            "recommendations": ["Enhanced monitoring"] if risk_score > 50 else [],
            "confidence_score": 0.7,
            "analyzed_by": "system",
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _fallback_pattern_analysis(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Fallback pattern analysis when LLM is unavailable."""
        if not transactions:
            return {"pattern_risk_score": 0, "pattern_types": [], "analysis": "No transactions"}
        
        amounts = [tx.get("usd_value", 0) or 0 for tx in transactions]
        
        # Look for structuring patterns (amounts just below thresholds)
        structuring_count = sum(1 for amount in amounts if 9000 <= amount <= 9999)
        
        pattern_risk_score = 0
        pattern_types = []
        
        if structuring_count > 3:
            pattern_risk_score += 60
            pattern_types.append("Potential structuring")
        
        # Look for rapid movement
        time_sorted = sorted(transactions, key=lambda x: x.get("timestamp", datetime.min))
        if len(time_sorted) > 5:
            time_diffs = []
            for i in range(1, len(time_sorted)):
                if isinstance(time_sorted[i]["timestamp"], datetime) and isinstance(time_sorted[i-1]["timestamp"], datetime):
                    diff = (time_sorted[i]["timestamp"] - time_sorted[i-1]["timestamp"]).total_seconds()
                    time_diffs.append(diff)
            
            if time_diffs and sum(1 for diff in time_diffs if diff < 3600) > len(time_diffs) * 0.5:
                pattern_risk_score += 40
                pattern_types.append("Rapid transaction pattern")
        
        return {
            "pattern_risk_score": min(pattern_risk_score, 100),
            "pattern_types": pattern_types,
            "suspicious_indicators": pattern_types,
            "analysis": "Basic pattern analysis completed",
            "recommendations": ["Manual review"] if pattern_risk_score > 50 else []
        }
    
    def _parse_pattern_analysis(self, response: str) -> Dict[str, Any]:
        """Parse pattern analysis from text response."""
        return {
            "pattern_risk_score": 25,
            "pattern_types": ["Text analysis"],
            "analysis": response[:500],
            "recommendations": ["Review manually"]
        }


# Global instance
llm_service = LLMService()