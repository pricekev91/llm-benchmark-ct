import React from 'react';
import NavBar from './components/NavBar';
import './App.css'; // Assume global styling

// Dummy page components
const EndpointConfig = () => <div><h1>Endpoint Configuration Page</h1><p>UI to define API endpoints goes here.</p></div>;
const ModelSelect = () => <div><h1>Model Selection Page</h1><p>UI to choose LLM providers and models goes here.</p></div>;
const BenchmarkRunner = () => <div><h1>Benchmark Runner</h1><p>Main dashboard to run benchmarks goes here.</p></div>;

function App() {
  const [currentPage, setCurrentPage] = React.useState('runner');

  const renderPage = () => {
    switch (currentPage) {
      case 'config':
        return <EndpointConfig />;
      case 'model':
        return <ModelSelect />;
      case 'runner':
      default:
        return <BenchmarkRunner />;
    }
  };

  return (
    <div className="app-container">
      <NavBar onNavigate={setCurrentPage} />
      <main className="content">
        {renderPage()}
      </main>
    </div>
  );
}

export default App;