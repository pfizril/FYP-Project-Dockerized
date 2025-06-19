'use client';

import React, { useState, useEffect } from 'react';
import { apiConfigManager, APIConfig } from '../lib/apiConfig';
import { apiClient } from '../lib/apiClient';

export const APIConfigManager: React.FC = () => {
  const [configs, setConfigs] = useState<APIConfig[]>([]);
  const [newConfig, setNewConfig] = useState({ baseUrl: '', name: '' });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    setConfigs(apiConfigManager.getAllConfigs());
  }, []);

  const handleAddConfig = () => {
    setError(null);
    setSuccess(null);

    if (!newConfig.name.trim() || !newConfig.baseUrl.trim()) {
      setError('Name and Base URL are required');
      return;
    }

    if (!apiConfigManager.validateConfig(newConfig)) {
      setError('Invalid Base URL format');
      return;
    }

    try {
      apiConfigManager.addConfig(newConfig);
      setConfigs(apiConfigManager.getAllConfigs());
      setNewConfig({ baseUrl: '', name: '' });
      setSuccess('Configuration added successfully');
    } catch (err) {
      setError('Failed to add configuration');
    }
  };

  const handleSetActive = (name: string) => {
    setError(null);
    setSuccess(null);

    try {
      apiConfigManager.setActiveConfig(name);
      setConfigs(apiConfigManager.getAllConfigs());
      apiClient.updateClient();
      setSuccess('Active configuration updated');
    } catch (err) {
      setError('Failed to update active configuration');
    }
  };

  const handleRemoveConfig = (name: string) => {
    setError(null);
    setSuccess(null);

    try {
      apiConfigManager.removeConfig(name);
      setConfigs(apiConfigManager.getAllConfigs());
      setSuccess('Configuration removed successfully');
    } catch (err) {
      setError('Failed to remove configuration');
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">API Configuration Manager</h2>
      
      {/* Add new config form */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4">Add New Configuration</h3>
        <div className="space-y-4">
          <div>
            <label htmlFor="configName" className="block text-sm font-medium text-gray-700">
              Configuration Name
            </label>
            <input
              id="configName"
              type="text"
              value={newConfig.name}
              onChange={(e) => setNewConfig({ ...newConfig, name: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="e.g., Production API"
            />
          </div>
          <div>
            <label htmlFor="baseUrl" className="block text-sm font-medium text-gray-700">
              Base URL
            </label>
            <input
              id="baseUrl"
              type="text"
              value={newConfig.baseUrl}
              onChange={(e) => setNewConfig({ ...newConfig, baseUrl: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="e.g., https://api.example.com"
            />
          </div>
          <button
            onClick={handleAddConfig}
            className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Add Configuration
          </button>
        </div>
      </div>

      {/* Status messages */}
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
          {success}
        </div>
      )}

      {/* Config list */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold mb-4">Saved Configurations</h3>
        <div className="space-y-4">
          {configs.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No configurations saved yet</p>
          ) : (
            configs.map((config) => (
              <div
                key={config.name}
                className={`p-4 rounded-lg border ${
                  config.isActive ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">{config.name}</h4>
                    <p className="text-sm text-gray-600">{config.baseUrl}</p>
                  </div>
                  <div className="flex space-x-2">
                    {!config.isActive && (
                      <button
                        onClick={() => handleSetActive(config.name)}
                        className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                      >
                        Set Active
                      </button>
                    )}
                    {config.isActive && (
                      <span className="px-3 py-1 text-sm bg-green-100 text-green-800 rounded">
                        Active
                      </span>
                    )}
                    <button
                      onClick={() => handleRemoveConfig(config.name)}
                      className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}; 