
import React from 'react';
import { FilterType } from '../../types';
import { Zap, Banknote, Scale, Loader2 } from 'lucide-react';

interface FilterTogglesProps {
  onFilterChange: (filter: FilterType) => void;
  activeFilter: FilterType;
  isLoading: boolean;
}

const FilterToggles: React.FC<FilterTogglesProps> = ({ onFilterChange, activeFilter, isLoading }) => {
  const options: { id: FilterType; label: string; icon: React.ReactNode; color: string }[] = [
    { id: 'fastest', label: 'Fastest', icon: <Zap className="w-4 h-4" />, color: 'bg-orange-500' },
    { id: 'cheapest', label: 'Cheapest', icon: <Banknote className="w-4 h-4" />, color: 'bg-green-500' },
    { id: 'optimal', label: 'Optimal', icon: <Scale className="w-4 h-4" />, color: 'bg-blue-500' },
  ];

  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-2 border border-white/50 flex flex-col gap-1 w-64 overflow-hidden">
      {options.map((option) => (
        <button
          key={option.id}
          onClick={() => onFilterChange(option.id)}
          disabled={isLoading}
          className={`flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 ${
            activeFilter === option.id 
              ? 'bg-white shadow-sm border border-gray-100' 
              : 'hover:bg-white/50 text-gray-500'
          }`}
        >
          <div className="flex items-center gap-3">
            <div className={`p-1.5 rounded-lg text-white ${activeFilter === option.id ? option.color : 'bg-gray-300'}`}>
              {option.icon}
            </div>
            <span className={`font-bold text-sm ${activeFilter === option.id ? 'text-gray-800' : 'text-gray-500'}`}>
              {option.label}
            </span>
          </div>
          {isLoading && activeFilter === option.id && (
            <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
          )}
          {!isLoading && activeFilter === option.id && (
            <div className="w-2 h-2 rounded-full bg-blue-500" />
          )}
        </button>
      ))}
    </div>
  );
};

export default FilterToggles;
