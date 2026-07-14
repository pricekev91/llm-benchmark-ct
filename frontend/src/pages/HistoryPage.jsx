// frontend/src/pages/HistoryPage.jsx
import React from 'react';
import MetricCard from '../components/MetricCard';

const HistoryPage = () => {
  // This component would fetch data from GET /analytics/history/filter
  // and display it using tables and charts.
  return (
    <div className="page-container history-page">
      <h2 className="page-title">📊 Benchmark History</h2>
      <p>View, filter, and analyze past benchmark runs.</p>

      <section className="filters">
        <h3>Filters</h3>
        {/* Filter controls: Model dropdown, Endpoint dropdown, Date range picker */}
        <div className="filter-controls">
            <input type="text" placeholder="Filter by Model/Endpoint" />
            <button>Apply Filters</button>
        </div>
      </section>

      <section className="analytics-summary">
        <h3>Overall Summary</h3>
        <div className="card-grid">
            <MetricCard title="Avg. Latency" value="1200" unit="ms" />
            <MetricCard title="Total Runs" value="45" unit="" />
            <MetricCard title="Best Throughput" value="X" unit="/s" />
        </div>
      </section>

      <section className="history-table">
        <h3>Run Log</h3>
        <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <thead>
                <tr><th>Run ID</th><th>Model</th><th>Endpoint</th><th>Timestamp</th><th>Latency (ms)</th><th>View</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>h1</td>
                    <td>GPT-4o</td>
                    <td>Test API</td>
                    <td>2026-07-13 10:00:00</td>
                    <td>100.0</td>
                    <td><button>View</button></td>
                </tr>
                {/* More historical runs go here */}
            </tbody>
        </table>
      </section>
    </div>
  );
};

export default HistoryPage;