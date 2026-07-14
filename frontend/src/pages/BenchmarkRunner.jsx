// frontend/src/pages/BenchmarkRunner.jsx
import React, { useState } from 'react';
import MetricCard from '../components/MetricCard';

const BenchmarkRunner = () => {
  const [prompt, setPrompt] = useState('');
  const [modelId, setModelId] = useState('m1');
  const [endpointId, setEndpointId] = useState('e1');
  const [maxTokens, setMaxTokens] = useState(1024);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [isHtmlMode, setIsHtmlMode] = useState(false);

  // Placeholder for preset prompts
  const presets = ["Explain quantum computing simply.", "Write a short poem about a lonely satellite.", "Debug this code: [code snippet]"];

  const handleRunBenchmark = async () => {
    if (!prompt) return;
    setIsLoading(true);
    setResults(null);
    
    // --- API Call Simulation ---
    console.log("Sending request to /benchmark/run...");
    // In a real app: fetch('/api/benchmark/run', { method: 'POST', body: JSON.stringify({ model_id: modelId, endpoint_id: endpointId, prompt_text: prompt, max_tokens: maxTokens }) })
    
    // Simulation of successful response from the new backend engine
    await new Promise(resolve => setTimeout(resolve, 1500)); 
    
    const simulatedResponse = {
        status: "success",
        message: "Benchmark completed successfully.",
        run_data: {
            run_id: "a1b2c3d4",
            model_name: "GPT-4o",
            endpoint_id: "e1",
            prompt_text: prompt,
            response_text: "The simulation generated a complex and detailed response covering all requirements. It is very long and informative.",
            latency_ms: 1234.56,
            tokens_generated: 512,
            output_length: 100,
            timestamp: new Date().toISOString()
        },
        metrics: {
            latency_ms: 1234.56,
            tokens_generated: 512
        }
    };
    
    setResults(simulatedResponse);
    setIsLoading(false);
  };

  const handleRenderHtml = () => {
    if (results && results.run_data) {
        alert("Switching to HTML Viewer mode! Displaying full response text.");
        setIsHtmlMode(true);
    }
  };

  return (
    <div className="page-container benchmark-runner">
      <h2 className="runner-title">🚀 Benchmark Runner</h2>
      <p>Define inputs and execute multi-backend LLM benchmarks.</p>

      {/* Input Section */}
      <section className="input-panel">
        <h3>1. Configuration</h3>
        
        {/* Model Selection */}
        <div className="input-group">
            <label>Select Model:</label>
            <select value={modelId} onChange={(e) => setModelId(e.target.value)}>
                <option value="m1">GPT-4o (OpenAI)</option>
                {/* Other models loaded dynamically */}
            </select>
        </div>
        
        {/* Endpoint Selection */}
        <div className="input-group">
            <label>Select Endpoint:</label>
            <select value={endpointId} onChange={(e) => setEndpointId(e.target.value)}>
                <option value="e1">Test API (http://test.com)</option>
                {/* Other endpoints loaded dynamically */}
            </select>
        </div>

        {/* Prompt Input */}
        <div className="input-group">
            <label>Prompt:</label>
            <textarea 
                rows="5" 
                value={prompt} 
                onChange={(e) => setPrompt(e.target.value)} 
                placeholder="Enter your prompt here..." 
                disabled={isLoading}
            />
            <select value="" onChange={(e) => {
                const preset = e.target.value;
                setPrompt(presets[parseInt(preset)]);
            }}>
                <option value="">-- Preset Prompts --</option>
                {presets.map((p, i) => (<option key={i} value={i}>{p}</option>))}
            </select>
        </div>

        <div className="input-controls">
            <button onClick={handleRunBenchmark} disabled={isLoading}>
                {isLoading ? 'Running Benchmark...' : '▶️ Run Benchmark'}
            </button>
            <button onClick={handleRenderHtml} disabled={!results || results.status !== 'success'}>
                HTML Viewer 📄
            </button>
        </div>
      </section>

      {/* Results Display Section */}
      {results && results.status === 'success' && (
        <section className="results-panel">
          <h3>✅ Benchmark Results</h3>
          
          <div className="metrics-summary">
            <h4>Key Performance Indicators:</h4>
            <div className="card-grid">
              <MetricCard title="Latency" value={results.metrics.latency_ms.toFixed(2)} unit="ms" />
              <MetricCard title="Tokens Generated" value={results.run_data.tokens_generated} unit="" />
              <MetricCard title="Output Length" value={results.run_data.output_length} unit="chars" />
            </div>
          </div>

          {isHtmlMode ? (
            <div className="html-viewer">
              <h4>HTML Output Viewer</h4>
              <div dangerouslySetInnerHTML={{ __html: results.run_data.response_text.includes('<html') ? results.run_data.response_text : 'Error: Content not valid HTML.' }} />
            </div>
          ) : (
            <div className="response-output">
                <h4>Raw Response Text:</h4>
                <pre>{results.run_data.response_text}</pre>
            </div>
          )}

        </section>
      )}
    </div>
  );
};

export default BenchmarkRunner;