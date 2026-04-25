"""
Query Engine - PromQL-like query language for metrics
Provides flexible querying, aggregation, and export capabilities
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import numpy as np


@dataclass
class QueryResult:
    """Result of a query"""
    query: str
    timestamp: datetime
    results: List[Dict[str, Any]]
    execution_time_ms: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'query': self.query,
            'timestamp': self.timestamp.isoformat(),
            'results': self.results,
            'execution_time_ms': self.execution_time_ms,
            'error': self.error
        }


class QueryParser:
    """Parses PromQL-like query language"""
    
    @staticmethod
    def parse(query: str) -> Dict[str, Any]:
        """Parse query string into components"""
        # Simple parser for queries like:
        # metric_name{tag1="value1"} [5m]
        # sum(metric_name) by (tag)
        # rate(metric_name[5m])
        
        query = query.strip()
        
        # Extract function if present
        function = None
        match = re.match(r'(\w+)\((.*)\)', query)
        if match:
            function = match.group(1)
            query = match.group(2)
            
        # Extract metric name
        metric_match = re.match(r'(\w+)', query)
        metric_name = metric_match.group(1) if metric_match else None
        
        # Extract labels/tags
        labels = {}
        label_match = re.findall(r'(\w+)="([^"]*)"', query)
        for key, value in label_match:
            labels[key] = value
            
        # Extract range
        range_match = re.search(r'\[([0-9]+)([mhd])\]', query)
        time_range = None
        if range_match:
            value = int(range_match.group(1))
            unit = range_match.group(2)
            if unit == 'm':
                time_range = timedelta(minutes=value)
            elif unit == 'h':
                time_range = timedelta(hours=value)
            elif unit == 'd':
                time_range = timedelta(days=value)
                
        # Extract grouping
        group_by = None
        group_match = re.search(r'by\s*\(([^)]+)\)', query)
        if group_match:
            group_by = [x.strip() for x in group_match.group(1).split(',')]
            
        return {
            'function': function,
            'metric_name': metric_name,
            'labels': labels,
            'time_range': time_range,
            'group_by': group_by
        }


class QueryExecutor:
    """Executes parsed queries against metrics"""
    
    def __init__(self, analytics_engine):
        self.analytics = analytics_engine
        
    def execute(self, query: str) -> QueryResult:
        """Execute query"""
        start_time = datetime.now()
        
        try:
            parsed = QueryParser.parse(query)
            results = self._execute_parsed(parsed)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return QueryResult(
                query=query,
                timestamp=datetime.now(),
                results=results,
                execution_time_ms=execution_time
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return QueryResult(
                query=query,
                timestamp=datetime.now(),
                results=[],
                execution_time_ms=execution_time,
                error=str(e)
            )
            
    def _execute_parsed(self, parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute parsed query"""
        metric_name = parsed.get('metric_name')
        if not metric_name:
            raise ValueError("No metric specified")
            
        # Build time range
        time_range = parsed.get('time_range') or timedelta(hours=1)
        end = datetime.now()
        start = end - time_range
        
        # Query metrics
        labels = parsed.get('labels')
        metrics = self.analytics.query(
            metric_name=metric_name,
            start=start,
            end=end,
            tags=labels if labels else None
        )
        
        if not metrics:
            # Return empty results instead of raising error
            function = parsed.get('function')
            if function:
                return []  # Aggregation on empty set
            return []
            
        # Apply function
        function = parsed.get('function')
        results = self._apply_function(function, metrics, parsed)
        
        return results
        
    def _apply_function(self, function: Optional[str], metrics: List,
                       parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply aggregation function"""
        if not function:
            # Return raw metrics
            return [m.to_dict() for m in metrics]
            
        results = []
        
        if not metrics:
            return results
            
        if function == 'sum':
            total = sum(m.metric_value for m in metrics)
            results = [{'value': total, 'timestamp': datetime.now().isoformat()}]
            
        elif function == 'avg':
            values = [m.metric_value for m in metrics]
            if values:
                avg = sum(values) / len(values)
                results = [{'value': avg, 'timestamp': datetime.now().isoformat()}]
            
        elif function == 'min':
            min_val = min((m.metric_value for m in metrics), default=0)
            results = [{'value': min_val, 'timestamp': datetime.now().isoformat()}]
            
        elif function == 'max':
            max_val = max((m.metric_value for m in metrics), default=0)
            results = [{'value': max_val, 'timestamp': datetime.now().isoformat()}]
            
        elif function == 'rate':
            if len(metrics) >= 2:
                sorted_metrics = sorted(metrics, key=lambda m: m.timestamp)
                time_diff = (sorted_metrics[-1].timestamp - sorted_metrics[0].timestamp).total_seconds()
                value_diff = sorted_metrics[-1].metric_value - sorted_metrics[0].metric_value
                rate = value_diff / time_diff if time_diff > 0 else 0
                results = [{'value': rate, 'timestamp': datetime.now().isoformat()}]
                
        elif function == 'count':
            results = [{'value': len(metrics), 'timestamp': datetime.now().isoformat()}]
            
        else:
            # Return raw metrics for unknown functions
            results = [m.to_dict() for m in metrics]
            
        return results


class QueryBuilder:
    """Helper to build queries programmatically"""
    
    @staticmethod
    def metric(name: str) -> str:
        """Start query with metric name"""
        return name
        
    @staticmethod
    def with_labels(query: str, labels: Dict[str, str]) -> str:
        """Add labels to query"""
        label_str = ','.join(f'{k}="{v}"' for k, v in labels.items())
        return f'{query}{{{label_str}}}'
        
    @staticmethod
    def with_range(query: str, value: int, unit: str) -> str:
        """Add time range"""
        return f'{query}[{value}{unit}]'
        
    @staticmethod
    def with_function(query: str, function: str) -> str:
        """Wrap with function"""
        return f'{function}({query})'
        
    @staticmethod
    def with_grouping(query: str, tags: List[str]) -> str:
        """Add grouping"""
        tag_str = ','.join(tags)
        return f'{query} by ({tag_str})'


class ExportFormatter:
    """Formats query results for export"""
    
    @staticmethod
    def to_json(result: QueryResult) -> str:
        """Export as JSON"""
        return json.dumps(result.to_dict(), indent=2)
        
    @staticmethod
    def to_csv(result: QueryResult) -> str:
        """Export as CSV"""
        if not result.results:
            return ""
            
        lines = []
        # Header
        headers = list(result.results[0].keys())
        lines.append(','.join(str(h) for h in headers))
        
        # Data
        for row in result.results:
            values = [str(row.get(h, '')) for h in headers]
            lines.append(','.join(values))
                
        return '\n'.join(lines)
        
    @staticmethod
    def to_prometheus(result: QueryResult) -> str:
        """Export in Prometheus format"""
        lines = []
        for entry in result.results:
            if 'metric_name' in entry and 'metric_value' in entry:
                metric = entry['metric_name']
                value = entry['metric_value']
                timestamp = int(datetime.fromisoformat(
                    entry.get('timestamp', datetime.now().isoformat())
                ).timestamp() * 1000)
                lines.append(f'{metric} {value} {timestamp}')
                
        return '\n'.join(lines)


class QueryEngine:
    """Main query engine"""
    
    def __init__(self, analytics_engine):
        self.analytics = analytics_engine
        self.executor = QueryExecutor(analytics_engine)
        self.query_history: List[QueryResult] = []
        
    def query(self, query: str) -> QueryResult:
        """Execute query"""
        result = self.executor.execute(query)
        self.query_history.append(result)
        return result
        
    def explain(self, query: str) -> Dict[str, Any]:
        """Explain query execution"""
        parsed = QueryParser.parse(query)
        return {
            'original_query': query,
            'parsed': parsed,
            'explanation': f"Query for metric '{parsed.get('metric_name')}' "
                          f"with function '{parsed.get('function')}' "
                          f"over {parsed.get('time_range')}"
        }
        
    def export(self, result: QueryResult, format: str = 'json') -> str:
        """Export results"""
        formats = {
            'json': ExportFormatter.to_json,
            'csv': ExportFormatter.to_csv,
            'prometheus': ExportFormatter.to_prometheus
        }
        
        formatter = formats.get(format, ExportFormatter.to_json)
        return formatter(result)
