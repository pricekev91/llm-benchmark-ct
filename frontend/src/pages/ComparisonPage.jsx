// frontend/src/pages/ComparisonPage.jsx
import React from 'react';
import MetricCard from '../components/MetricCard';

const ComparisonPage = () => {
  // This component would fetch data from /analytics/compare/run and /analytics/compare/trends
  return (
    <div className="page-container comparison-page">
      <h2 className="page-title">📈 Comparison & Trend Analysis</h2>
      <p>Compare current runs against past performance and track model trends.</p>

      <section className="comparison-tool">
        <h3>Run Comparison</h3>
        <div className="input-group">
            <select defaultValue="m1">
                <option value="m1">GPT-4o</option>
                {/* Other models */}
            </select>
            <select defaultValue="p1">
                <option value="p1">Explain QC</option>
                {/* Other presets */}
            </select>
        </div>
        <button>Compare Now</button>
        <div className="comparison-result">
            {/* Displays the result from /analytics/compare/run */}
            <p><strong>Result:</strong> Model performance is 15% faster than historical average for this task.</p>
        </div>
      </section>

      <section className="trend-charts">
        <h3>Performance Trends</h3>
        {/* Placeholder for a chart library (e.g., Chart.js) */}
        <div className="chart-placeholder">
            {/* Chart displaying Avg Latency over time */}
            <p>Latency Trend: 1200ms -> 1150ms (Improving)</p>
        </div>
      </section>
    </div>
  );
};

export default ComparisonPage;