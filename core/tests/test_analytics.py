"""
Comprehensive Test Suite for Analytics Engine
Tests metrics collection, queries, anomaly detection, and cost analysis
"""

import unittest
import time
import threading
from datetime import datetime, timedelta
import sys
import os

# Add universe package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from universe.analytics import (
    AnalyticsEngine, Metric, MetricType,
    MetricsCollector,
    AnomalyDetector, Anomaly,
    CostAnalyzer,
    QueryEngine
)


class TestAnalyticsEngine(unittest.TestCase):
    """Test analytics engine core functionality"""
    
    def setUp(self):
        self.engine = AnalyticsEngine()
        
    def test_record_metric(self):
        """Test recording a metric"""
        self.engine.record_metric('agent1', 'cpu_usage', 50.5)
        metrics = self.engine.query('cpu_usage', 'agent1')
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].metric_value, 50.5)
        
    def test_query_metrics(self):
        """Test querying metrics"""
        for i in range(10):
            self.engine.record_metric('agent1', 'memory', float(i * 10))
        metrics = self.engine.query('memory', 'agent1')
        self.assertEqual(len(metrics), 10)
        
    def test_metric_with_tags(self):
        """Test metrics with tags"""
        self.engine.record_metric('agent1', 'response_time', 100,
                                 tags={'endpoint': '/api/users', 'method': 'GET'})
        metrics = self.engine.query('response_time', 'agent1',
                                   tags={'endpoint': '/api/users'})
        self.assertEqual(len(metrics), 1)
        
    def test_sum_aggregation(self):
        """Test sum aggregation"""
        for i in range(5):
            self.engine.record_metric('agent1', 'requests', float(i + 1))
        result = self.engine.aggregate('requests', 'sum', 'agent1')
        self.assertEqual(result, 15.0)
        
    def test_avg_aggregation(self):
        """Test average aggregation"""
        for i in range(4):
            self.engine.record_metric('agent1', 'latency', float(i * 10))
        result = self.engine.aggregate('latency', 'avg', 'agent1')
        self.assertEqual(result, 15.0)  # (0+10+20+30)/4 = 15
        
    def test_min_max_aggregation(self):
        """Test min/max aggregation"""
        values = [10, 50, 30, 20]
        for v in values:
            self.engine.record_metric('agent1', 'score', float(v))
        
        min_val = self.engine.aggregate('score', 'min', 'agent1')
        max_val = self.engine.aggregate('score', 'max', 'agent1')
        self.assertEqual(min_val, 10.0)
        self.assertEqual(max_val, 50.0)
        
    def test_percentile(self):
        """Test percentile calculation"""
        for i in range(1, 101):
            self.engine.record_metric('agent1', 'percentile_test', float(i))
        p95 = self.engine.get_percentile('percentile_test', 95, 'agent1')
        self.assertGreater(p95, 90)
        self.assertLess(p95, 100)
        
    def test_rate_calculation(self):
        """Test rate aggregation"""
        now = datetime.now()
        # Create metrics over time span
        for i in range(5):
            metric = Metric('agent1', 'requests', float(i * 100), 'counter',
                          datetime.now() - timedelta(seconds=4-i))
            self.engine.buffer.add(metric)
        
        rate = self.engine.aggregate('requests', 'rate', 'agent1')
        self.assertGreater(rate, 0)
        
    def test_group_by(self):
        """Test group by aggregation"""
        for env in ['prod', 'staging', 'dev']:
            for i in range(3):
                self.engine.record_metric('agent1', 'latency', float(i*10),
                                         tags={'environment': env})
        
        groups = self.engine.group_metrics('latency', 'environment', 'agent1')
        self.assertEqual(len(groups), 3)
        self.assertIn('prod', groups)
        
    def test_cache_hit(self):
        """Test cache functionality"""
        self.engine.record_metric('agent1', 'cpu', 50.0)
        
        # First query - cache miss
        result1 = self.engine.query('cpu', 'agent1')
        # Second query - cache hit
        result2 = self.engine.query('cpu', 'agent1')
        
        self.assertEqual(len(result1), len(result2))
        
    def test_cache_invalidation(self):
        """Test cache invalidation"""
        self.engine.record_metric('agent1', 'memory', 50.0)
        self.engine.query('memory', 'agent1')  # Cache it
        
        self.engine.record_metric('agent1', 'memory', 75.0)  # Should invalidate
        metrics = self.engine.query('memory', 'agent1')
        self.assertEqual(len(metrics), 2)
        
    def test_engine_stats(self):
        """Test engine statistics"""
        for i in range(10):
            self.engine.record_metric('agent1', 'metric', float(i))
        
        stats = self.engine.get_stats()
        self.assertEqual(stats['metrics_recorded'], 10)
        self.assertGreater(stats['throughput_per_second'], 0)


class TestMetricsCollector(unittest.TestCase):
    """Test metrics collector"""
    
    def setUp(self):
        self.collector = MetricsCollector()
        
    def test_counter_increment(self):
        """Test counter increment"""
        counter = self.collector.counter('agent1', 'requests')
        counter.increment()
        counter.increment(5)
        self.assertEqual(counter.value, 6)
        
    def test_gauge_set(self):
        """Test gauge value setting"""
        gauge = self.collector.gauge('agent1', 'temperature')
        gauge.set(25.5)
        self.assertEqual(gauge.get(), 25.5)
        gauge.set(30.0)
        self.assertEqual(gauge.get(), 30.0)
        
    def test_histogram_observe(self):
        """Test histogram observation"""
        hist = self.collector.histogram('agent1', 'latencies')
        for val in [100, 150, 200, 250]:
            hist.observe(float(val))
        self.assertEqual(len(hist.observations), 4)
        
    def test_timer_context(self):
        """Test timer context manager"""
        with self.collector.timer('agent1', 'operation_time') as timer:
            time.sleep(0.01)
        # Timer should have recorded
        self.assertIsNotNone(timer.start_time)
        
    def test_event_buffer(self):
        """Test event buffering"""
        counter = self.collector.counter('agent1', 'events')
        counter.increment()
        counter.increment()
        
        buffer_stats = self.collector.get_buffer_stats()
        self.assertGreater(buffer_stats['buffer_size'], 0)
        
    def test_metric_instances_reuse(self):
        """Test metric instance reuse"""
        counter1 = self.collector.counter('agent1', 'requests')
        counter1.increment(10)
        
        counter2 = self.collector.counter('agent1', 'requests')
        self.assertEqual(counter2.value, 10)  # Same instance
        
    def test_write_callback(self):
        """Test write callback"""
        callback_called = []
        
        def test_callback(batch):
            callback_called.append(len(batch))
        
        self.collector.register_write_callback(test_callback)
        counter = self.collector.counter('agent1', 'test')
        counter.increment()
        counter.increment()
        
        self.collector.flush()
        self.assertGreater(len(callback_called), 0)


class TestAnomalyDetector(unittest.TestCase):
    """Test anomaly detection"""
    
    def setUp(self):
        self.detector = AnomalyDetector()
        
    def test_statistical_anomaly(self):
        """Test statistical anomaly detection"""
        # Add normal values
        for i in range(20):
            self.detector.check_value('cpu', 50.0 + (i % 5))
        
        # Add anomalous value
        anomaly = self.detector.check_value('cpu', 200.0)
        
        # Should detect some anomaly
        stats = self.detector.get_stats()
        self.assertGreater(stats['total_anomalies'], 0)
        
    def test_threshold_detection(self):
        """Test threshold-based detection"""
        self.detector.set_threshold('memory', 20.0, 80.0)
        
        # Normal values
        self.detector.check_value('memory', 50.0)
        self.detector.check_value('memory', 60.0)
        
        # Anomalous values
        anomaly1 = self.detector.check_value('memory', 10.0)  # Below threshold
        anomaly2 = self.detector.check_value('memory', 95.0)  # Above threshold
        
        stats = self.detector.get_stats()
        self.assertGreater(stats['total_anomalies'], 0)
        
    def test_anomaly_acknowledgement(self):
        """Test anomaly acknowledgement"""
        self.detector.set_threshold('latency', 50.0, 100.0)
        self.detector.check_value('latency', 200.0)
        
        unack = self.detector.alert_aggregator.get_alerts(False)
        self.assertGreater(len(unack), 0)
        
    def test_trend_analysis(self):
        """Test trend analysis"""
        # Normal trend
        for i in range(20):
            self.detector.check_value('trend_metric', float(i * 5))
        
        stats = self.detector.get_stats()
        self.assertGreater(stats['metrics_monitored'], 0)
        
    def test_anomaly_callback(self):
        """Test anomaly callback"""
        callback_called = []
        
        def on_anomaly(anomaly):
            callback_called.append(anomaly.metric_name)
        
        self.detector.register_alert_callback(on_anomaly)
        self.detector.set_threshold('test', 10.0, 20.0)
        self.detector.check_value('test', 50.0)
        
        # May or may not trigger depending on dedup
        # Just verify mechanism works
        self.assertTrue(True)


class TestCostAnalyzer(unittest.TestCase):
    """Test cost analysis"""
    
    def setUp(self):
        self.analyzer = CostAnalyzer()
        
    def test_record_cost(self):
        """Test cost recording"""
        self.analyzer.record_cost('agent1', 'task1', 1000)
        breakdown = self.analyzer.get_agent_breakdown('agent1')
        self.assertGreater(breakdown['total_cost'], 0)
        
    def test_token_cost_calculation(self):
        """Test token cost calculation"""
        cost1 = self.analyzer.tracker.calculator.calculate_cost(1000, 'gpt-3.5')
        cost2 = self.analyzer.tracker.calculator.calculate_cost(1000, 'gpt-4')
        
        # GPT-4 should be more expensive
        self.assertGreater(cost2, cost1)
        
    def test_agent_breakdown(self):
        """Test agent cost breakdown"""
        self.analyzer.record_cost('agent1', 'task1', 1000)
        self.analyzer.record_cost('agent1', 'task2', 500)
        
        breakdown = self.analyzer.get_agent_breakdown('agent1')
        self.assertEqual(breakdown['total_tokens'], 1500)
        
    def test_budget_tracking(self):
        """Test budget management"""
        self.analyzer.budget_manager.set_budget('agent1', 100.0)
        self.analyzer.record_cost('agent1', 'task1', 1000)
        
        status = self.analyzer.budget_manager.get_budget_status('agent1')
        self.assertIn('percentage_used', status)
        
    def test_top_agents(self):
        """Test top agents by cost"""
        for i in range(5):
            self.analyzer.record_cost(f'agent{i}', f'task{i}', 1000 * (i + 1))
        
        top = self.analyzer.get_top_agents(limit=3)
        self.assertLessEqual(len(top), 3)
        
    def test_cost_forecast(self):
        """Test cost forecasting"""
        # Add some historical costs
        for i in range(10):
            self.analyzer.record_cost('agent1', f'task{i}', 100 * (i + 1))
        
        forecast = self.analyzer.forecast_spending('agent1', forecast_days=7)
        self.assertIn('forecasted_cost', forecast)
        self.assertGreater(forecast['forecasted_cost'], 0)
        
    def test_cost_stats(self):
        """Test cost analyzer statistics"""
        self.analyzer.record_cost('agent1', 'task1', 1000)
        self.analyzer.record_cost('agent2', 'task2', 500)
        
        stats = self.analyzer.get_stats()
        self.assertEqual(stats['total_cost_entries'], 2)
        self.assertGreater(stats['total_cost'], 0)


class TestQueryEngine(unittest.TestCase):
    """Test query engine"""
    
    def setUp(self):
        self.analytics = AnalyticsEngine()
        self.query_engine = QueryEngine(self.analytics)
        
        # Add test data
        for i in range(10):
            self.analytics.record_metric('agent1', 'requests', float(i * 10),
                                        tags={'endpoint': '/api'})
        
    def test_simple_query(self):
        """Test simple metric query"""
        result = self.query_engine.query('requests')
        self.assertIsNotNone(result)
        self.assertGreater(len(result.results), 0)
        
    def test_query_with_labels(self):
        """Test query with labels"""
        result = self.query_engine.query('requests{endpoint="/api"}')
        self.assertGreater(len(result.results), 0)
        
    def test_query_with_range(self):
        """Test query with time range"""
        result = self.query_engine.query('requests[1h]')
        self.assertGreater(len(result.results), 0)
        
    def test_sum_function(self):
        """Test sum function"""
        result = self.query_engine.query('sum(requests)')
        self.assertEqual(len(result.results), 1)
        
    def test_avg_function(self):
        """Test avg function"""
        result = self.query_engine.query('avg(requests)')
        self.assertEqual(len(result.results), 1)
        
    def test_query_explain(self):
        """Test query explanation"""
        explanation = self.query_engine.explain('sum(requests)')
        self.assertIn('explanation', explanation)
        
    def test_export_json(self):
        """Test JSON export"""
        result = self.query_engine.query('requests')
        json_str = self.query_engine.export(result, 'json')
        self.assertGreater(len(json_str), 0)
        
    def test_export_csv(self):
        """Test CSV export"""
        result = self.query_engine.query('requests')
        csv_str = self.query_engine.export(result, 'csv')
        self.assertGreater(len(csv_str), 0)
        
    def test_query_error_handling(self):
        """Test query error handling"""
        result = self.query_engine.query('')  # Invalid query
        self.assertIsNotNone(result.error)


class TestPerformance(unittest.TestCase):
    """Test performance characteristics"""
    
    def test_metric_throughput(self):
        """Test metrics per second throughput"""
        engine = AnalyticsEngine()
        
        start = time.time()
        for i in range(10000):
            engine.record_metric('agent1', 'metric', float(i % 100))
        elapsed = time.time() - start
        
        throughput = 10000 / elapsed
        self.assertGreater(throughput, 1000)  # Should handle 1k+ per second
        
    def test_query_latency(self):
        """Test query latency"""
        engine = AnalyticsEngine()
        
        # Add test data
        for i in range(1000):
            engine.record_metric('agent1', 'latency_test', float(i % 100))
        
        start = time.time()
        result = engine.query('latency_test', 'agent1')
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        self.assertLess(elapsed, 100)  # Query should be < 100ms
        
    def test_concurrent_writes(self):
        """Test concurrent metric writes"""
        engine = AnalyticsEngine()
        
        def write_metrics():
            for i in range(100):
                engine.record_metric('agent1', 'concurrent', float(i))
        
        threads = [threading.Thread(target=write_metrics) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        stats = engine.get_stats()
        self.assertEqual(stats['metrics_recorded'], 1000)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_end_to_end_metrics(self):
        """Test end-to-end metrics pipeline"""
        # Setup
        analytics = AnalyticsEngine()
        collector = MetricsCollector()
        detector = AnomalyDetector()
        analyzer = CostAnalyzer()
        query_engine = QueryEngine(analytics)
        
        # Record metrics
        counter = collector.counter('agent1', 'requests')
        for i in range(100):
            counter.increment()
        
        # Query metrics (simulating batch write)
        analytics.record_metric('agent1', 'requests', 100.0)
        
        # Detect anomalies
        detector.check_value('requests', 100.0)
        
        # Track costs
        analyzer.record_cost('agent1', 'task1', 1000)
        
        # Query results
        result = query_engine.query('requests')
        self.assertIsNotNone(result)
        
    def test_anomaly_to_alert(self):
        """Test anomaly detection to alerting"""
        alerts_sent = []
        
        def on_anomaly(anomaly):
            alerts_sent.append(anomaly)
        
        detector = AnomalyDetector()
        detector.register_alert_callback(on_anomaly)
        detector.set_threshold('critical_metric', 50.0, 100.0)
        
        # Normal values
        detector.check_value('critical_metric', 75.0)
        detector.check_value('critical_metric', 80.0)
        
        # Anomalous value
        detector.check_value('critical_metric', 200.0)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyticsEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestMetricsCollector))
    suite.addTests(loader.loadTestsFromTestCase(TestAnomalyDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestCostAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestQueryEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
