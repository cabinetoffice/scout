import React from 'react';
import { Box, FormControl, InputLabel, Select, MenuItem, SelectChangeEvent } from '@mui/material';

interface LLMModel {
  id: string;
  name: string;
  model_id: string;
  description: string | null;
  is_default: boolean;
}

interface ModelSelectorProps {
  models: LLMModel[];
  selectedModelId: string;
  handleModelChange: (event: SelectChangeEvent) => void;
  loading: boolean;
  loadingModels: boolean;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({ 
  models, 
  selectedModelId, 
  handleModelChange, 
  loading, 
  loadingModels 
}) => {
  return (
    <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
      <FormControl sx={{ minWidth: 200 }}>
        <InputLabel id="model-select-label">LLM Model</InputLabel>
        <Select
          labelId="model-select-label"
          id="model-select"
          value={selectedModelId}
          onChange={handleModelChange}
          label="LLM Model"
          disabled={loadingModels || loading}
          size="small"
        >
          {loadingModels ? (
            <MenuItem value="">
              <em>Loading models...</em>
            </MenuItem>
          ) : (
            models.map((model) => (
              <MenuItem key={model.id} value={model.model_id}>
                {model.name} {model.is_default && "(Default)"}
              </MenuItem>
            ))
          )}
        </Select>
      </FormControl>
    </Box>
  );
};
