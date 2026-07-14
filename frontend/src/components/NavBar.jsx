// frontend/src/components/NavBar.jsx
import React from 'react';

const NavBar = ({ onNavigate }) => {
  return (
    <nav className="navbar">
      <div className="logo">LLM Benchmark CT</div>
      <div className="nav-links">
        <button onClick={() => onNavigate('config')}>Configure Endpoints</button>
        <button onClick={() => onNavigate('model')}>Select Models</button>
        <button onClick={() => onNavigate('runner')}>Run Benchmark</button>
      </div>
    </nav>
  );
};

export default NavBar;