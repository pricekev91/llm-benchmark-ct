// frontend/src/components/MetricCard.jsx
import React from 'react';

const MetricCard = ({ title, value, unit }) => {
  return (
    <div className="metric-card">
      <h3>{title}</h3>
      <p className="value">{value}</p>
      <small>{unit}</small>
    </div>
  );
};

export default MetricCard;