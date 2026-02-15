#!/usr/bin/env python3
"""
Structured Logging Module with Rotation and Metrics
====================================================
Provides production-ready logging with:
- Structured JSON logging for machine parsing
- Log rotation by size and time
- Performance metrics collection
- Rich console output
- Correlation IDs for request tracing
"""

import json
import logging
import logging.handlers
import sys
import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from functools import wraps
import threading

# Try to import rich for pretty console output
try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    gas_used: Optional[int] = None
    gas_price_gwei: Optional[float] = None
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None
    
    def finalize(self, success: bool = True, error: Optional[str] = None):
        """Finalize the metrics with result."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error = error
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'operation': self.operation,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'end_time': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            'duration_ms': round(self.duration_ms, 2) if self.duration_ms else None,
            'success': self.success,
            'error': self.error,
            'gas_used': self.gas_used,
            'gas_price_gwei': self.gas_price_gwei,
            'tx_hash': self.tx_hash,
            'block_number': self.block_number,
            'extra': self.extra or {}
        }


class MetricsCollector:
    """Collects and aggregates performance metrics."""
    
    def __init__(self):
        self.metrics: list = []
        self._lock = threading.Lock()
        self._operation_counts: Dict[str, Dict[str, int]] = {}
        self._operation_times: Dict[str, list] = {}
        
    def add_metric(self, metric: PerformanceMetrics):
        """Add a metric to the collector."""
        with self._lock:
            self.metrics.append(metric)
            
            # Update operation counts
            op = metric.operation
            if op not in self._operation_counts:
                self._operation_counts[op] = {'total': 0, 'success': 0, 'failure': 0}
            self._operation_counts[op]['total'] += 1
            if metric.success:
                self._operation_counts[op]['success'] += 1
            else:
                self._operation_counts[op]['failure'] += 1
            
            # Update operation times
            if metric.duration_ms:
                if op not in self._operation_times:
                    self._operation_times[op] = []
                self._operation_times[op].append(metric.duration_ms)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        with self._lock:
            summary = {
                'total_operations': len(self.metrics),
                'operations': {},
                'overall_success_rate': 0,
                'avg_duration_ms': 0
            }
            
            total_success = 0
            total_duration = 0
            count_duration = 0
            
            for op, counts in self._operation_counts.items():
                times = self._operation_times.get(op, [])
                avg_time = sum(times) / len(times) if times else 0
                min_time = min(times) if times else 0
                max_time = max(times) if times else 0
                
                summary['operations'][op] = {
                    'total': counts['total'],
                    'success': counts['success'],
                    'failure': counts['failure'],
                    'success_rate': round(counts['success'] / counts['total'] * 100, 2) if counts['total'] > 0 else 0,
                    'avg_duration_ms': round(avg_time, 2),
                    'min_duration_ms': round(min_time, 2),
                    'max_duration_ms': round(max_time, 2)
                }
                total_success += counts['success']
                
                if times:
                    total_duration += sum(times)
                    count_duration += len(times)
            
            if self.metrics:
                summary['overall_success_rate'] = round(total_success / len(self.metrics) * 100, 2)
            if count_duration > 0:
                summary['avg_duration_ms'] = round(total_duration / count_duration, 2)
            
            return summary
    
    def clear(self):
        """Clear all metrics."""
        with self._lock:
            self.metrics.clear()
            self._operation_counts.clear()
            self._operation_times.clear()
    
    def save_to_file(self, filepath: str):
        """Save all metrics to a JSON file."""
        with self._lock:
            data = {
                'summary': self.get_summary(),
                'metrics': [m.to_dict() for m in self.metrics]
            }
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_correlation_id: bool = True):
        super().__init__()
        self.include_correlation_id = include_correlation_id
        self._correlation_id = threading.local()
    
    def set_correlation_id(self, cid: str):
        """Set the correlation ID for the current thread."""
        self._correlation_id.value = cid
    
    def get_correlation_id(self) -> str:
        """Get the correlation ID for the current thread."""
        return getattr(self._correlation_id, 'value', None) or str(uuid.uuid4())[:8]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'source': {
                'file': record.filename,
                'line': record.lineno,
                'function': record.funcName
            }
        }
        
        if self.include_correlation_id:
            log_data['correlation_id'] = self.get_correlation_id()
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data['extra'] = record.extra
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class StructuredLogger:
    """
    Production-ready structured logger with rotation and metrics.
    
    Usage:
        logger = StructuredLogger('bot', 'logs/bot.log')
        logger.info('Starting bot', extra={'version': '1.0.0'})
        
        # With metrics
        with logger.timed_operation('swap', extra={'token': 'COMPUTE'}):
            # do swap
            pass
    """
    
    def __init__(
        self,
        name: str,
        log_file: Optional[str] = None,
        log_level: str = 'INFO',
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        use_rich_console: bool = True,
        json_format_file: bool = True,
        json_format_console: bool = False
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.handlers = []  # Clear existing handlers
        
        self.metrics = MetricsCollector()
        self._json_formatter = JSONFormatter()
        
        # Console handler
        if use_rich_console and RICH_AVAILABLE and not json_format_console:
            console_handler = RichHandler(
                rich_tracebacks=True,
                show_time=True,
                show_path=True
            )
            console_handler.setLevel(logging.DEBUG)
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            if json_format_console:
                console_handler.setFormatter(self._json_formatter)
            else:
                console_handler.setFormatter(
                    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                )
        
        self.logger.addHandler(console_handler)
        
        # File handler with rotation
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setLevel(logging.DEBUG)
            
            if json_format_file:
                file_handler.setFormatter(self._json_formatter)
            else:
                file_handler.setFormatter(
                    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                )
            
            self.logger.addHandler(file_handler)
        
        # Also add time-based rotation for daily logs
        daily_log = log_file.replace('.log', '_daily.log') if log_file else None
        if daily_log:
            daily_handler = logging.handlers.TimedRotatingFileHandler(
                daily_log,
                when='midnight',
                interval=1,
                backupCount=30  # Keep 30 days
            )
            daily_handler.setLevel(logging.DEBUG)
            if json_format_file:
                daily_handler.setFormatter(self._json_formatter)
            daily_handler.suffix = "%Y-%m-%d"
            self.logger.addHandler(daily_handler)
    
    def _log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Internal log method."""
        log_extra = {'extra': extra} if extra else {}
        getattr(self.logger, level.lower())(message, extra=log_extra, **kwargs)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log('debug', message, extra)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log('info', message, extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log('warning', message, extra)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = True):
        self._log('error', message, extra, exc_info=exc_info)
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = True):
        self._log('critical', message, extra, exc_info=exc_info)
    
    def set_correlation_id(self, cid: str):
        """Set correlation ID for the current thread."""
        self._json_formatter.set_correlation_id(cid)
    
    def generate_correlation_id(self) -> str:
        """Generate and set a new correlation ID."""
        cid = str(uuid.uuid4())[:8]
        self.set_correlation_id(cid)
        return cid
    
    class TimedOperation:
        """Context manager for timing operations and collecting metrics."""
        
        def __init__(self, logger: 'StructuredLogger', operation: str, extra: Optional[Dict[str, Any]] = None):
            self.logger = logger
            self.operation = operation
            self.extra = extra or {}
            self.metric: Optional[PerformanceMetrics] = None
            
        def __enter__(self):
            self.metric = PerformanceMetrics(
                operation=self.operation,
                start_time=time.time(),
                extra=self.extra
            )
            self.logger.info(f"Starting {self.operation}", extra=self.extra)
            return self.metric
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.metric.finalize(success=False, error=str(exc_val))
                self.logger.error(
                    f"{self.operation} failed after {self.metric.duration_ms:.2f}ms",
                    extra={'error': str(exc_val), 'duration_ms': self.metric.duration_ms}
                )
            else:
                self.metric.finalize(success=True)
                self.logger.info(
                    f"{self.operation} completed in {self.metric.duration_ms:.2f}ms",
                    extra={'duration_ms': self.metric.duration_ms}
                )
            
            self.logger.metrics.add_metric(self.metric)
            return False  # Don't suppress exceptions
    
    def timed_operation(self, operation: str, extra: Optional[Dict[str, Any]] = None):
        """Create a context manager for timing an operation."""
        return self.TimedOperation(self, operation, extra)
    
    def log_trade(self, tx_hash: str, operation: str, amount_in: float, amount_out: float,
                  gas_used: int, gas_price_gwei: float, success: bool, block_number: int,
                  extra: Optional[Dict[str, Any]] = None):
        """Log a trade with all relevant details."""
        log_data = {
            'tx_hash': tx_hash,
            'operation': operation,
            'amount_in': amount_in,
            'amount_out': amount_out,
            'gas_used': gas_used,
            'gas_price_gwei': gas_price_gwei,
            'gas_cost_eth': (gas_used * gas_price_gwei) / 1e9,
            'success': success,
            'block_number': block_number
        }
        if extra:
            log_data.update(extra)
        
        level = 'info' if success else 'error'
        self._log(level, f"Trade {operation}: {'success' if success else 'failed'}", log_data)
    
    def print_metrics_summary(self):
        """Print a formatted metrics summary to console."""
        summary = self.metrics.get_summary()
        
        if not RICH_AVAILABLE:
            self.logger.info(f"Metrics Summary: {json.dumps(summary, indent=2)}")
            return
        
        console = Console()
        
        table = Table(title="Performance Metrics Summary")
        table.add_column("Operation", style="cyan")
        table.add_column("Total", justify="right")
        table.add_column("Success", justify="right", style="green")
        table.add_column("Failure", justify="right", style="red")
        table.add_column("Success %", justify="right")
        table.add_column("Avg ms", justify="right")
        table.add_column("Min ms", justify="right")
        table.add_column("Max ms", justify="right")
        
        for op, stats in summary['operations'].items():
            table.add_row(
                op,
                str(stats['total']),
                str(stats['success']),
                str(stats['failure']),
                f"{stats['success_rate']:.1f}%",
                f"{stats['avg_duration_ms']:.2f}",
                f"{stats['min_duration_ms']:.2f}",
                f"{stats['max_duration_ms']:.2f}"
            )
        
        console.print(Panel(
            f"Total Operations: {summary['total_operations']}\n"
            f"Overall Success Rate: {summary['overall_success_rate']:.1f}%\n"
            f"Average Duration: {summary['avg_duration_ms']:.2f}ms",
            title="Summary",
            border_style="blue"
        ))
        console.print(table)
    
    def save_metrics(self, filepath: str):
        """Save metrics to a JSON file."""
        self.metrics.save_to_file(filepath)
        self.info(f"Metrics saved to {filepath}")


# Global logger instance
_global_logger: Optional[StructuredLogger] = None


def get_logger(name: str = 'bot', log_file: str = 'logs/bot.log', **kwargs) -> StructuredLogger:
    """Get or create the global logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(name, log_file, **kwargs)
    return _global_logger


def log_operation(operation: str, extra: Optional[Dict[str, Any]] = None):
    """Decorator for logging function execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            with logger.timed_operation(operation, extra):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience functions for module-level logging
def info(message: str, extra: Optional[Dict[str, Any]] = None):
    get_logger().info(message, extra)


def error(message: str, extra: Optional[Dict[str, Any]] = None):
    get_logger().error(message, extra)


def warning(message: str, extra: Optional[Dict[str, Any]] = None):
    get_logger().warning(message, extra)


def debug(message: str, extra: Optional[Dict[str, Any]] = None):
    get_logger().debug(message, extra)


if __name__ == '__main__':
    # Demo
    logger = StructuredLogger('demo', 'logs/demo.log', log_level='DEBUG')
    
    logger.info('Bot starting', extra={'version': '1.0.0', 'chain': 'Base'})
    
    # Simulate operations
    for i in range(5):
        cid = logger.generate_correlation_id()
        with logger.timed_operation('swap', {'iteration': i}):
            time.sleep(0.1)
            if i == 2:
                logger.warning('High slippage detected', extra={'slippage': 5.5})
    
    # Simulate a failed operation
    try:
        with logger.timed_operation('failed_op'):
            raise ValueError('Something went wrong')
    except:
        pass
    
    # Log a trade
    logger.log_trade(
        tx_hash='0xabc123',
        operation='buy',
        amount_in=0.1,
        amount_out=1000.0,
        gas_used=150000,
        gas_price_gwei=2.5,
        success=True,
        block_number=12345678
    )
    
    # Print summary
    logger.print_metrics_summary()
    logger.save_metrics('logs/metrics.json')
