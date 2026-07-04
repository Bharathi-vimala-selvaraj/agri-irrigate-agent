'use client';

import React, { useState } from 'react';
import { MapPin, Sprout, Droplet, ChevronRight, ChevronLeft, Check, X } from 'lucide-react';
import { api } from '../lib/api';
import FarmLocationPicker from './FarmLocationPicker';

interface FarmProfileWizardProps {
  onClose: () => void;
  onFarmCreated: () => void;
}

const CROP_TYPES = [
  'Rice', 'Wheat', 'Cotton', 'Tomato', 'Sugarcane', 'Maize', 'Potato', 'Soybean', 'Groundnut', 'Sugarcane'
];

const IRRIGATION_METHODS = ['drip', 'sprinkler', 'flood', 'subsurface'];
const SOIL_TYPES = ['loam', 'clay', 'sandy', 'silt', 'peat'];
const WATER_SOURCES = ['well', 'canal', 'river', 'tank', 'borewell'];

const GROWTH_STAGES = ['seedling', 'vegetative', 'flowering', 'fruiting', 'maturity'];

export default function FarmProfileWizard({ onClose, onFarmCreated }: FarmProfileWizardProps) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    crop_type: '',
    crop_variety: '',
    sowing_date: '',
    farm_size_acres: 2.0,
    growth_stage: 'vegetative',
    irrigation_method: 'drip',
    soil_type: 'loam',
    water_source: 'well',
    pump_capacity_hp: '',
    latitude: 11.0168,
    longitude: 76.9558,
  });

  const [showLocationPicker, setShowLocationPicker] = useState(false);

  const handleNext = () => {
    if (step < 4) setStep(step + 1);
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await api.createFarm({
        name: formData.name,
        crop_type: formData.crop_type,
        crop_variety: formData.crop_variety || undefined,
        sowing_date: formData.sowing_date || undefined,
        farm_size_acres: formData.farm_size_acres,
        irrigation_method: formData.irrigation_method,
        soil_type: formData.soil_type,
        water_source: formData.water_source,
        pump_capacity_hp: formData.pump_capacity_hp ? parseFloat(formData.pump_capacity_hp) : undefined,
        latitude: formData.latitude,
        longitude: formData.longitude,
      });
      onFarmCreated();
      onClose();
    } catch (error) {
      console.error('Failed to create farm:', error);
      alert('Failed to create farm. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleLocationSelect = (lat: number, lng: number) => {
    setFormData({ ...formData, latitude: lat, longitude: lng });
    setShowLocationPicker(false);
  };

  const isStepValid = () => {
    switch (step) {
      case 1:
        return formData.name.trim() !== '' && formData.crop_type !== '';
      case 2:
        return formData.sowing_date !== '' && formData.farm_size_acres > 0;
      case 3:
        return formData.irrigation_method !== '' && formData.soil_type !== '';
      case 4:
        return true;
      default:
        return false;
    }
  };

  return (
    <div className="wizard-overlay">
      <div className="wizard-modal">
        <div className="wizard-header">
          <h2><Sprout size={20} /> Farm Profile Setup</h2>
          <button onClick={onClose} className="close-btn"><X size={18} /></button>
        </div>

        <div className="wizard-progress">
          {[1, 2, 3, 4].map((s) => (
            <div key={s} className={`progress-step ${s <= step ? 'active' : ''}`}>
              <div className="step-number">{s}</div>
              <div className="step-label">
                {s === 1 && 'Basic Info'}
                {s === 2 && 'Crop Details'}
                {s === 3 && 'Irrigation'}
                {s === 4 && 'Location'}
              </div>
            </div>
          ))}
        </div>

        <div className="wizard-content">
          {step === 1 && (
            <div className="wizard-step">
              <h3>Basic Farm Information</h3>
              <div className="form-group">
                <label>Farm Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Field A - Cotton"
                />
              </div>
              <div className="form-group">
                <label>Crop Type *</label>
                <select
                  value={formData.crop_type}
                  onChange={(e) => setFormData({ ...formData, crop_type: e.target.value })}
                >
                  <option value="">Select crop</option>
                  {CROP_TYPES.map((crop) => (
                    <option key={crop} value={crop}>{crop}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Crop Variety (optional)</label>
                <input
                  type="text"
                  value={formData.crop_variety}
                  onChange={(e) => setFormData({ ...formData, crop_variety: e.target.value })}
                  placeholder="e.g., BT Cotton"
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="wizard-step">
              <h3>Crop & Farm Details</h3>
              <div className="form-group">
                <label>Sowing Date *</label>
                <input
                  type="date"
                  value={formData.sowing_date}
                  onChange={(e) => setFormData({ ...formData, sowing_date: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Farm Size (acres) *</label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.farm_size_acres}
                  onChange={(e) => setFormData({ ...formData, farm_size_acres: parseFloat(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label>Current Growth Stage</label>
                <select
                  value={formData.growth_stage || 'vegetative'}
                  onChange={(e) => setFormData({ ...formData, growth_stage: e.target.value })}
                >
                  {GROWTH_STAGES.map((stage) => (
                    <option key={stage} value={stage}>{stage.charAt(0).toUpperCase() + stage.slice(1)}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="wizard-step">
              <h3>Irrigation Setup</h3>
              <div className="form-group">
                <label><Droplet size={14} /> Irrigation Method *</label>
                <select
                  value={formData.irrigation_method}
                  onChange={(e) => setFormData({ ...formData, irrigation_method: e.target.value })}
                >
                  {IRRIGATION_METHODS.map((method) => (
                    <option key={method} value={method}>{method.charAt(0).toUpperCase() + method.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Soil Type *</label>
                <select
                  value={formData.soil_type}
                  onChange={(e) => setFormData({ ...formData, soil_type: e.target.value })}
                >
                  {SOIL_TYPES.map((soil) => (
                    <option key={soil} value={soil}>{soil.charAt(0).toUpperCase() + soil.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Water Source *</label>
                <select
                  value={formData.water_source}
                  onChange={(e) => setFormData({ ...formData, water_source: e.target.value })}
                >
                  {WATER_SOURCES.map((source) => (
                    <option key={source} value={source}>{source.charAt(0).toUpperCase() + source.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Pump Capacity (HP) (optional)</label>
                <input
                  type="number"
                  step="0.5"
                  value={formData.pump_capacity_hp}
                  onChange={(e) => setFormData({ ...formData, pump_capacity_hp: e.target.value })}
                  placeholder="e.g., 5.0"
                />
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="wizard-step">
              <h3><MapPin size={18} /> Farm Location</h3>
              <div className="form-group">
                <label>Latitude</label>
                <input
                  type="number"
                  step="0.000001"
                  value={formData.latitude}
                  onChange={(e) => setFormData({ ...formData, latitude: parseFloat(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label>Longitude</label>
                <input
                  type="number"
                  step="0.000001"
                  value={formData.longitude}
                  onChange={(e) => setFormData({ ...formData, longitude: parseFloat(e.target.value) })}
                />
              </div>
              <button
                type="button"
                onClick={() => setShowLocationPicker(true)}
                className="btn btn-secondary"
                style={{ width: '100%', marginTop: '1rem' }}
              >
                <MapPin size={14} /> Select Location on Map
              </button>
              <p className="form-hint">
                Location is used for weather forecasting and terrain analysis.
              </p>
            </div>
          )}
        </div>

        <div className="wizard-footer">
          <button
            onClick={handleBack}
            disabled={step === 1}
            className="btn btn-secondary"
          >
            <ChevronLeft size={14} /> Back
          </button>
          {step < 4 ? (
            <button
              onClick={handleNext}
              disabled={!isStepValid()}
              className="btn btn-primary"
            >
              Next <ChevronRight size={14} />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!isStepValid() || loading}
              className="btn btn-primary"
            >
              {loading ? 'Creating...' : <><Check size={14} /> Create Farm</>}
            </button>
          )}
        </div>
      </div>

      {showLocationPicker && (
        <FarmLocationPicker
          onLocationSelect={handleLocationSelect}
          initialLat={formData.latitude}
          initialLng={formData.longitude}
          onClose={() => setShowLocationPicker(false)}
        />
      )}
    </div>
  );
}
