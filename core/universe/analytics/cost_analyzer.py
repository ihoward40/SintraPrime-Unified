"""
Cost Analyzer - Token usage and compute cost tracking
Provides detailed cost breakdowns and spending forecasts
"""

import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np


@dataclass
class CostEntry:
    """Represents a cost entry"""
    agent_id: str
    task_id: str
    tokens_used: int
    compute_cost: float
    timestamp: datetime = field(default_factory=datetime.now)
    cost_breakdown: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'agent_id': self.agent_id,
            'task_id': self.task_id,
            'tokens_used': self.tokens_used,
            'compute_cost': self.compute_cost,
            'timestamp': self.timestamp.isoformat(),
            'cost_breakdown': self.cost_breakdown,
            'metadata': self.metadata
        }


class TokenCostCalculator:
    """Calculates token costs based on model pricing"""
    
    def __init__(self):
        # Pricing per 1K tokens
        self.model_prices = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-3.5': {'input': 0.0005, 'output': 0.0015},
            'claude': {'input': 0.01, 'output': 0.03},
            'custom': {'input': 0.01, 'output': 0.01},
        }
        self.lock = threading.RLock()
        
    def calculate_cost(self, tokens: int, model: str = 'gpt-3.5',
                      token_type: str = 'total') -> float:
        """Calculate cost for tokens"""
        with self.lock:
            prices = self.model_prices.get(model, self.model_prices['custom'])
            
        if token_type == 'input':
            price = prices['input']
        elif token_type == 'output':
            price = prices['output']
        else:  # total - estimate 30% input, 70% output
            price = (prices['input'] * 0.3 + prices['output'] * 0.7)
            
        return (tokens / 1000) * price
        
    def set_model_price(self, model: str, input_price: float, output_price: float) -> None:
        """Set custom model pricing"""
        with self.lock:
            self.model_prices[model] = {'input': input_price, 'output': output_price}


class CostTracker:
    """Tracks costs for agents and tasks"""
    
    def __init__(self):
        self.entries: List[CostEntry] = []
        self.agent_costs: Dict[str, float] = defaultdict(float)
        self.task_costs: Dict[str, float] = defaultdict(float)
        self.lock = threading.RLock()
        self.calculator = TokenCostCalculator()
        
    def record_cost(self, agent_id: str, task_id: str, tokens: int,
                   model: str = 'gpt-3.5', metadata: Optional[Dict] = None) -> CostEntry:
        """Record a cost entry"""
        compute_cost = self.calculator.calculate_cost(tokens, model)
        
        entry = CostEntry(
            agent_id=agent_id,
            task_id=task_id,
            tokens_used=tokens,
            compute_cost=compute_cost,
            metadata=metadata or {}
        )
        
        with self.lock:
            self.entries.append(entry)
            self.agent_costs[agent_id] += compute_cost
            self.task_costs[task_id] += compute_cost
            
        return entry
        
    def get_agent_cost(self, agent_id: str, start: Optional[datetime] = None,
                      end: Optional[datetime] = None) -> float:
        """Get total cost for agent"""
        start = start or (datetime.now() - timedelta(days=30))
        end = end or datetime.now()
        
        with self.lock:
            total = sum(e.compute_cost for e in self.entries
                       if e.agent_id == agent_id and start <= e.timestamp <= end)
        return total
        
    def get_task_cost(self, task_id: str) -> float:
        """Get total cost for task"""
        with self.lock:
            return sum(e.compute_cost for e in self.entries if e.task_id == task_id)
            
    def get_agent_token_count(self, agent_id: str, start: Optional[datetime] = None,
                             end: Optional[datetime] = None) -> int:
        """Get total tokens used by agent"""
        start = start or (datetime.now() - timedelta(days=30))
        end = end or datetime.now()
        
        with self.lock:
            total = sum(e.tokens_used for e in self.entries
                       if e.agent_id == agent_id and start <= e.timestamp <= end)
        return total


class BudgetManager:
    """Manages spending budgets"""
    
    def __init__(self):
        self.budgets: Dict[str, float] = {}  # agent_id -> budget
        self.spending: Dict[str, float] = defaultdict(float)
        self.lock = threading.RLock()
        self.alerts: Dict[str, callable] = {}
        
    def set_budget(self, agent_id: str, budget: float) -> None:
        """Set budget for agent"""
        with self.lock:
            self.budgets[agent_id] = budget
            
    def add_spending(self, agent_id: str, amount: float) -> bool:
        """Add spending and check if over budget"""
        with self.lock:
            self.spending[agent_id] += amount
            budget = self.budgets.get(agent_id)
            
            if budget and self.spending[agent_id] > budget:
                # Trigger alert if available
                if agent_id in self.alerts:
                    try:
                        self.alerts[agent_id](agent_id, self.spending[agent_id], budget)
                    except Exception as e:
                        print(f"Error in budget alert: {e}")
                return False
                
        return True
        
    def get_budget_status(self, agent_id: str) -> Dict[str, Any]:
        """Get budget status"""
        with self.lock:
            budget = self.budgets.get(agent_id, 0)
            spending = self.spending.get(agent_id, 0)
            
        return {
            'agent_id': agent_id,
            'budget': budget,
            'spending': spending,
            'remaining': max(0, budget - spending),
            'percentage_used': (spending / budget * 100) if budget > 0 else 0
        }
        
    def register_alert(self, agent_id: str, callback: callable) -> None:
        """Register budget alert callback"""
        with self.lock:
            self.alerts[agent_id] = callback


class CostForecaster:
    """Forecasts future spending"""
    
    def __init__(self, history_window_days: int = 30):
        self.history_window = timedelta(days=history_window_days)
        self.lock = threading.RLock()
        
    def forecast(self, cost_tracker: CostTracker, agent_id: str,
                forecast_days: int = 7) -> Dict[str, Any]:
        """Forecast future costs"""
        now = datetime.now()
        start = now - self.history_window
        end = now
        
        with cost_tracker.lock:
            historical_entries = [
                e for e in cost_tracker.entries
                if e.agent_id == agent_id and start <= e.timestamp <= end
            ]
            
        if not historical_entries:
            return {
                'agent_id': agent_id,
                'forecast_days': forecast_days,
                'daily_average': 0,
                'forecasted_cost': 0,
                'confidence': 0
            }
            
        # Calculate daily costs
        daily_costs = defaultdict(float)
        for entry in historical_entries:
            day = entry.timestamp.date()
            daily_costs[day] += entry.compute_cost
            
        if not daily_costs:
            return {
                'agent_id': agent_id,
                'forecast_days': forecast_days,
                'daily_average': 0,
                'forecasted_cost': 0,
                'confidence': 0
            }
            
        costs = list(daily_costs.values())
        daily_avg = np.mean(costs)
        daily_std = np.std(costs)
        
        # Simple linear forecast
        forecasted_cost = daily_avg * forecast_days
        
        # Confidence based on consistency (lower std = higher confidence)
        confidence = max(0, 1.0 - (daily_std / (daily_avg or 1)))
        
        return {
            'agent_id': agent_id,
            'forecast_days': forecast_days,
            'daily_average': daily_avg,
            'daily_std_dev': daily_std,
            'forecasted_cost': forecasted_cost,
            'confidence': min(1.0, confidence),
            'sample_days': len(costs)
        }


class CostAnalyzer:
    """Main cost analysis system"""
    
    def __init__(self):
        self.tracker = CostTracker()
        self.budget_manager = BudgetManager()
        self.forecaster = CostForecaster()
        
    def record_cost(self, agent_id: str, task_id: str, tokens: int,
                   model: str = 'gpt-3.5', metadata: Optional[Dict] = None) -> None:
        """Record cost and check budget"""
        entry = self.tracker.record_cost(agent_id, task_id, tokens, model, metadata)
        self.budget_manager.add_spending(agent_id, entry.compute_cost)
        
    def get_agent_breakdown(self, agent_id: str,
                           start: Optional[datetime] = None,
                           end: Optional[datetime] = None) -> Dict[str, Any]:
        """Get cost breakdown for agent"""
        start = start or (datetime.now() - timedelta(days=30))
        end = end or datetime.now()
        
        total_cost = self.tracker.get_agent_cost(agent_id, start, end)
        token_count = self.tracker.get_agent_token_count(agent_id, start, end)
        
        return {
            'agent_id': agent_id,
            'total_cost': total_cost,
            'total_tokens': token_count,
            'avg_cost_per_token': total_cost / token_count if token_count > 0 else 0,
            'period': {'start': start.isoformat(), 'end': end.isoformat()}
        }
        
    def get_top_agents(self, limit: int = 10,
                      start: Optional[datetime] = None,
                      end: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get top agents by cost"""
        start = start or (datetime.now() - timedelta(days=30))
        end = end or datetime.now()
        
        agent_costs = defaultdict(float)
        with self.tracker.lock:
            for entry in self.tracker.entries:
                if start <= entry.timestamp <= end:
                    agent_costs[entry.agent_id] += entry.compute_cost
                    
        sorted_agents = sorted(agent_costs.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{'agent_id': aid, 'cost': cost} for aid, cost in sorted_agents]
        
    def forecast_spending(self, agent_id: str, forecast_days: int = 7) -> Dict[str, Any]:
        """Forecast spending for agent"""
        return self.forecaster.forecast(self.tracker, agent_id, forecast_days)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics"""
        with self.tracker.lock:
            total_entries = len(self.tracker.entries)
            total_cost = sum(e.compute_cost for e in self.tracker.entries)
            total_tokens = sum(e.tokens_used for e in self.tracker.entries)
            
        return {
            'total_cost_entries': total_entries,
            'total_cost': total_cost,
            'total_tokens': total_tokens,
            'avg_cost_per_entry': total_cost / total_entries if total_entries > 0 else 0,
            'agents_tracked': len(self.tracker.agent_costs)
        }
