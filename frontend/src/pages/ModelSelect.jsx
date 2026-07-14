// frontend/src/pages/ModelSelect.jsx
import React from 'react';

const ModelSelect = () => {
  const [selectedModel, setSelectedModel] = React.useState('m1');
  const [availableModels, setAvailableModels] = React.useState([]);

  // Simulates fetching models from backend GET /models/list
  React.useEffect(() => {
    // API Call Simulation: fetch('/api/models/list')
    const simulatedModels = [
        { id: 'm1', name: 'GPT-4o', provider: 'OpenAI' },
        { id: 'm2', name: 'Llama 2 7B', provider: 'llama.cpp' },
        { id: 'm3', name: 'Claude 3 Sonnet', provider: 'LiteLLM' },
        { id: 'm4', name: 'Llama 3 8B', provider: 'llama-swap' },
    ];
    setAvailableModels(simulatedModels);
  }, []);

  return (
    <div className="page-container">
      <h2 className="page-title">Model Selection</h2>
      <p>Select the LLM provider and specific model version for testing.</p>

      <section className="model-selector">
        <h3>Select Model</h3>
        <select 
          value={selectedModel} 
          onChange={(e) => setSelectedModel(e.target.value)}
          disabled={availableModels.length === 0}
        >
          {availableModels.map(model => (
            <option key={model.id} value={model.id}>
              {model.name} ({model.provider})
            </option>
          ))}
        </select>
        <p className="hint">Model configuration is automatically fetched from the backend based on selection.</p>
      </section>
    </div>
  );
};

export default ModelSelect;