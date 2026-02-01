
import React, { useState } from 'react';
import { TouristPoint } from '../../types';
import { X, MapPin, Thermometer, Mountain, Calendar, ArrowRight, ChevronDown, ChevronUp } from 'lucide-react';

interface TouristPointCardProps {
  point: TouristPoint;
  onClose: () => void;
  onBuildRoute: () => void;
}

const TouristPointCard: React.FC<TouristPointCardProps> = ({ point, onClose, onBuildRoute }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-white rounded-2xl shadow-2xl overflow-hidden max-w-2xl w-full flex flex-col transition-all animate-in fade-in zoom-in duration-300">
      {/* Header Image Section */}
      <div className="relative h-64 md:h-80 overflow-hidden">
        <img 
          src={point.image_url || 'https://picsum.photos/800/600'} 
          alt={point.name} 
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 p-2 bg-white/20 hover:bg-white/40 backdrop-blur-md rounded-full text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
        <div className="absolute bottom-6 left-6 right-6 text-white">
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-blue-600/90 text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wider">
              {point.category.name}
            </span>
            <span className="flex items-center gap-1 text-xs text-blue-200">
              <MapPin className="w-3 h-3" /> {point.region.name}
            </span>
          </div>
          <h2 className="text-3xl font-bold">{point.name}</h2>
        </div>
      </div>

      {/* Content Section */}
      <div className="p-8 space-y-6 overflow-y-auto max-h-[60vh]">
        <div className="prose prose-blue max-w-none">
          <p className="text-gray-600 leading-relaxed font-medium">
            {point.description}
          </p>
          
          {isExpanded && (
            <div className="mt-4 animate-in slide-in-from-top-2 duration-300">
              <p className="text-gray-500 text-sm leading-relaxed">
                Experience the raw beauty of {point.name}. This destination offers a unique blend of geological history and cultural significance. 
                Whether you are looking for adventure or tranquility, the landscape of Southern Kazakhstan never ceases to amaze.
                The local area is known for its hospitality and rich tradition, making every visit a memorable journey into the heart of Central Asia.
              </p>
            </div>
          )}
          
          <button 
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-2 text-blue-600 font-semibold text-sm flex items-center gap-1 hover:underline"
          >
            {isExpanded ? <>Read Less <ChevronUp className="w-4 h-4" /></> : <>Read More <ChevronDown className="w-4 h-4" /></>}
          </button>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-6 pt-6 border-t border-gray-100">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-50 rounded-lg">
              <Thermometer className="w-5 h-5 text-orange-500" />
            </div>
            <div>
              <div className="text-[10px] text-gray-400 font-bold uppercase">Best Season</div>
              <div className="text-sm font-semibold text-gray-700">Apr - Oct</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <Mountain className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <div className="text-[10px] text-gray-400 font-bold uppercase">Elevation</div>
              <div className="text-sm font-semibold text-gray-700">850m</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-50 rounded-lg">
              <Calendar className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <div className="text-[10px] text-gray-400 font-bold uppercase">Accessibility</div>
              <div className="text-sm font-semibold text-gray-700">Open Daily</div>
            </div>
          </div>
        </div>

        {/* Coordinates Section */}
        <div className="p-4 bg-gray-50 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-gray-500 font-medium">
            <span className="bg-gray-200 px-2 py-0.5 rounded tracking-tighter">GPS</span>
            {point.latitude.toFixed(4)}°N, {point.longitude.toFixed(4)}°E
          </div>
          <button className="text-[10px] font-bold text-blue-600 hover:text-blue-800 transition-colors uppercase">
            Copy Coordinates
          </button>
        </div>
      </div>

      {/* Footer / CTA */}
      <div className="p-6 bg-gray-50 border-t border-gray-100">
        <button 
          onClick={onBuildRoute}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-6 rounded-xl shadow-lg shadow-blue-200 transition-all flex items-center justify-center gap-2 group transform hover:-translate-y-0.5"
        >
          <span>BUILD ROUTE FROM ALMATY</span>
          <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </div>
  );
};

export default TouristPointCard;
