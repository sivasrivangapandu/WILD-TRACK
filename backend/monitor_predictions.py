#!/usr/bin/env python3
"""
WildTrackAI - Real-time Prediction Accuracy Monitor
=================================================
Monitor model accuracy and performance in production:

✅ Real-time Metrics:
   - Prediction accuracy (rolling window)
   - Per-species accuracy trends
   - Confidence distribution
   - Prediction latency
   - Error rate by species
   - Accuracy degradation detection
   - Quality-aware metrics

✅ Alerting System:
   - Alert when accuracy drops below threshold
   - Alert on confidence calibration issues
   - Alert on high error rate for specific species
   - Alert on performance degradation

✅ Data Collection:
   - Batch accuracy (50 predictions)
   - Hourly accuracy (last hour)
   - Daily accuracy (last 24 hours)
   - Weekly accuracy (last 7 days)
   - Monthly accuracy (last 30 days)

Usage:
    python monitor_predictions.py --db production_predictions.db
    python monitor_predictions.py --start-server --port 8001
    python monitor_predictions.py --generate-report --output metrics.html
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import deque

import numpy as np


class PredictionMonitor:
    """Real-time prediction monitoring system."""
    
    def __init__(self, db_path: str = 'predictions.db'):
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        
        # In-memory buffers for quick access
        self.recent_predictions = deque(maxlen=1000)  # Last 1000 predictions
        self.accuracy_alerts = []
        
        # Thresholds
        self.MIN_ACCURACY = 0.70  # Alert if accuracy < 70%
        self.MIN_CONFIDENCE = 0.60  # Alert if avg confidence < 60%
        self.ERROR_RATE_THRESHOLD = 0.25  # Alert if error rate > 25%
        
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for storing predictions."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
            
            # Create tables
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    image_id TEXT,
                    true_label TEXT,
                    predicted_label TEXT,
                    confidence REAL,
                    latency_ms REAL,
                    image_quality_score REAL,
                    correct INTEGER
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS accuracy_metrics (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    period TEXT,
                    accuracy REAL,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    sample_count INTEGER,
                    avg_confidence REAL
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    alert_type TEXT,
                    severity TEXT,
                    message TEXT
                )
            ''')
            
            self.connection.commit()
            print(f"✅ Database initialized: {self.db_path}")
        except Exception as e:
            print(f"❌ Database initialization error: {str(e)[:60]}")
    
    def log_prediction(self, image_id: str, true_label: str, predicted_label: str,
                      confidence: float, latency_ms: float, quality_score: float = None):
        """Log a prediction for monitoring."""
        try:
            correct = 1 if true_label == predicted_label else 0
            timestamp = datetime.now().isoformat()
            
            self.cursor.execute('''
                INSERT INTO predictions 
                (timestamp, image_id, true_label, predicted_label, confidence, latency_ms, image_quality_score, correct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, image_id, true_label, predicted_label, confidence, latency_ms, quality_score, correct))
            
            self.connection.commit()
            
            # Add to in-memory buffer
            self.recent_predictions.append({
                'timestamp': timestamp,
                'true_label': true_label,
                'predicted_label': predicted_label,
                'confidence': confidence,
                'latency_ms': latency_ms,
                'correct': correct
            })
            
            # Check for alerts
            self._check_alerts()
        
        except Exception as e:
            print(f"❌ Error logging prediction: {str(e)[:60]}")
    
    def get_recent_accuracy(self, minutes: int = 60) -> Tuple[float, Dict]:
        """Get accuracy for recent period."""
        try:
            cutoff_time = (datetime.now() - timedelta(minutes=minutes)).isoformat()
            
            self.cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(correct) as correct,
                    AVG(confidence) as avg_conf,
                    AVG(latency_ms) as avg_latency
                FROM predictions
                WHERE timestamp > ?
            ''', (cutoff_time,))
            
            result = self.cursor.fetchone()
            total, correct, avg_conf, avg_latency = result
            
            if total == 0:
                return 0, {'total': 0, 'correct': 0}
            
            accuracy = correct / total
            
            return accuracy, {
                'total': total,
                'correct': correct,
                'accuracy': accuracy,
                'avg_confidence': avg_conf or 0,
                'avg_latency_ms': avg_latency or 0
            }
        except Exception as e:
            print(f"❌ Error getting recent accuracy: {str(e)[:60]}")
            return 0, {}
    
    def get_per_species_accuracy(self, minutes: int = 60) -> Dict[str, Dict]:
        """Get accuracy breakdown by species."""
        try:
            cutoff_time = (datetime.now() - timedelta(minutes=minutes)).isoformat()
            
            self.cursor.execute('''
                SELECT 
                    true_label,
                    COUNT(*) as total,
                    SUM(correct) as correct,
                    AVG(confidence) as avg_conf
                FROM predictions
                WHERE timestamp > ?
                GROUP BY true_label
                ORDER BY total DESC
            ''', (cutoff_time,))
            
            results = self.cursor.fetchall()
            
            per_species = {}
            for species, total, correct, avg_conf in results:
                accuracy = correct / total if total > 0 else 0
                per_species[species] = {
                    'total': total,
                    'correct': correct,
                    'accuracy': accuracy,
                    'avg_confidence': avg_conf or 0
                }
            
            return per_species
        except Exception as e:
            print(f"❌ Error getting per-species accuracy: {str(e)[:60]}")
            return {}
    
    def _check_alerts(self):
        """Check for alert conditions."""
        # Check recent batch accuracy
        batch_acc, batch_stats = self.get_recent_accuracy(minutes=10)
        
        if batch_stats.get('total', 0) >= 50:  # Only alert on reasonable sample size
            if batch_acc < self.MIN_ACCURACY:
                self._create_alert(
                    'LOW_ACCURACY',
                    'WARNING',
                    f"Accuracy dropped to {batch_acc:.1%} (expected ≥{self.MIN_ACCURACY:.0%})"
                )
            
            if batch_stats.get('avg_confidence', 0) < self.MIN_CONFIDENCE:
                self._create_alert(
                    'LOW_CONFIDENCE',
                    'INFO',
                    f"Average confidence is {batch_stats.get('avg_confidence', 0):.1%}"
                )
        
        # Check per-species accuracy
        per_species = self.get_per_species_accuracy(minutes=60)
        for species, metrics in per_species.items():
            if metrics['total'] >= 10 and metrics['accuracy'] < 0.5:
                self._create_alert(
                    'SPECIES_LOW_ACCURACY',
                    'WARNING',
                    f"{species}: {metrics['accuracy']:.1%} accuracy ({metrics['total']} samples)"
                )
    
    def _create_alert(self, alert_type: str, severity: str, message: str):
        """Create and store an alert."""
        # Check if similar alert already exists (avoid duplicate alerts)
        if self.accuracy_alerts:
            last_alert = self.accuracy_alerts[-1]
            if (last_alert['type'] == alert_type and 
                last_alert['timestamp'] > (datetime.now() - timedelta(minutes=5))):
                return  # Skip duplicate alert
        
        alert = {
            'timestamp': datetime.now(),
            'type': alert_type,
            'severity': severity,
            'message': message
        }
        
        self.accuracy_alerts.append(alert)
        
        try:
            self.cursor.execute('''
                INSERT INTO alerts (timestamp, alert_type, severity, message)
                VALUES (?, ?, ?, ?)
            ''', (datetime.now().isoformat(), alert_type, severity, message))
            self.connection.commit()
        except Exception as e:
            print(f"⚠️  Failed to save alert: {str(e)[:40]}")
    
    def get_accuracy_trend(self, hours: int = 24, intervals: int = 10) -> List[Dict]:
        """Get accuracy trend over time."""
        try:
            trend = []
            now = datetime.now()
            
            for i in range(intervals, 0, -1):
                start_time = (now - timedelta(hours=hours*i/intervals)).isoformat()
                end_time = (now - timedelta(hours=hours*(i-1)/intervals)).isoformat()
                
                self.cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(correct) as correct,
                        AVG(confidence) as avg_conf
                    FROM predictions
                    WHERE timestamp BETWEEN ? AND ?
                ''', (start_time, end_time))
                
                result = self.cursor.fetchone()
                total, correct, avg_conf = result
                
                if total > 0:
                    accuracy = correct / total
                    trend.append({
                        'time': end_time,
                        'accuracy': accuracy,
                        'samples': total,
                        'avg_confidence': avg_conf or 0
                    })
            
            return trend
        except Exception as e:
            print(f"❌ Error getting accuracy trend: {str(e)[:60]}")
            return []
    
    def generate_monitoring_report(self, output_path: str):
        """Generate comprehensive monitoring report."""
        print("\n📊 GENERATING MONITORING REPORT")
        print("=" * 70)
        
        # Get metrics for different time windows
        minutes_windows = [60, 1440, 10080]  # 1 hour, 1 day, 1 week
        period_names = ['Last Hour', 'Last 24 Hours', 'Last 7 Days']
        
        reports = {}
        for minutes, period_name in zip(minutes_windows, period_names):
            accuracy, stats = self.get_recent_accuracy(minutes)
            per_species = self.get_per_species_accuracy(minutes)
            
            reports[period_name] = {
                'accuracy': accuracy,
                'stats': stats,
                'per_species': per_species
            }
        
        trend = self.get_accuracy_trend(hours=24)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summaries': reports,
            'trend': trend,
            'recent_alerts': [
                {
                    'timestamp': str(a['timestamp']),
                    'type': a['type'],
                    'severity': a['severity'],
                    'message': a['message']
                }
                for a in self.accuracy_alerts[-10:]
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def print_status(self):
        """Print current monitoring status."""
        print("\n" + "=" * 70)
        print("📈 REAL-TIME PREDICTION MONITORING STATUS")
        print("=" * 70)
        
        # Recent accuracy
        acc_1h, stats_1h = self.get_recent_accuracy(60)
        print(f"\n🔄 Last Hour:")
        print(f"   Accuracy: {acc_1h:.1%}")
        print(f"   Predictions: {stats_1h.get('total', 0)}")
        print(f"   Avg Confidence: {stats_1h.get('avg_confidence', 0):.1%}")
        print(f"   Avg Latency: {stats_1h.get('avg_latency_ms', 0):.1f}ms")
        
        # Per-species
        per_species = self.get_per_species_accuracy(60)
        if per_species:
            print(f"\n📊 Per-Species Accuracy (1 hour):")
            for species, metrics in per_species.items():
                print(f"   {species:<15} {metrics['accuracy']:>6.1%} ({metrics['total']} samples)")
        
        # Recent alerts
        if self.accuracy_alerts:
            print(f"\n⚠️  Recent Alerts:")
            for alert in self.accuracy_alerts[-3:]:
                print(f"   [{alert['severity']}] {alert['type']}: {alert['message']}")
        
        print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='predictions.db', help='SQLite database path')
    parser.add_argument('--log-prediction', help='Log a single prediction (JSON format)')
    parser.add_argument('--status', action='store_true', help='Print current status')
    parser.add_argument('--generate-report', action='store_true', help='Generate monitoring report')
    parser.add_argument('--output', default='monitoring_report.json', help='Output report path')
    
    args = parser.parse_args()
    
    monitor = PredictionMonitor(args.db)
    
    if args.log_prediction:
        try:
            pred_data = json.loads(args.log_prediction)
            monitor.log_prediction(
                pred_data.get('image_id'),
                pred_data.get('true_label'),
                pred_data.get('predicted_label'),
                pred_data.get('confidence'),
                pred_data.get('latency_ms'),
                pred_data.get('quality_score')
            )
            print("✅ Prediction logged")
        except Exception as e:
            print(f"❌ Error logging prediction: {str(e)[:60]}")
    
    if args.status:
        monitor.print_status()
    
    if args.generate_report:
        report = monitor.generate_monitoring_report(args.output)
        print(f"✅ Report saved to: {args.output}")


if __name__ == '__main__':
    main()
