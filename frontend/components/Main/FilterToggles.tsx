
import React from 'react';
import { FilterType, RouteAlternative } from '../../types';
import { Zap, Banknote, Scale, Shield, Leaf, Loader2, Star, Route } from 'lucide-react';

interface FilterTogglesProps {
  alternatives: RouteAlternative[];
  onFilterChange: (filter: FilterType) => void;
  activeFilter: FilterType;
  isLoading: boolean;
}

const PROFILE_META: Record<FilterType, { icon: React.ReactNode; color: string; bg: string }> = {
  optimal:  { icon: <Scale  className="w-4 h-4" />, color: 'text-blue-600',   bg: 'bg-blue-500'    },
  fastest:  { icon: <Zap    className="w-4 h-4" />, color: 'text-orange-600', bg: 'bg-orange-500'  },
  cheapest: { icon: <Banknote className="w-4 h-4" />, color: 'text-green-600', bg: 'bg-green-500' },
  comfort:  { icon: <Shield className="w-4 h-4" />, color: 'text-purple-600', bg: 'bg-purple-500'  },
  eco:      { icon: <Leaf   className="w-4 h-4" />, color: 'text-emerald-600', bg: 'bg-emerald-600'},
};

const PROFILE_ORDER: FilterType[] = ['optimal', 'fastest', 'cheapest', 'comfort', 'eco'];

function formatTime(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function formatCost(cost: number): string {
  return cost.toLocaleString('ru-KZ') + ' ₸';
}

const FilterToggles: React.FC<FilterTogglesProps> = ({
  alternatives,
  onFilterChange,
  activeFilter,
  isLoading,
}) => {
  // Build a lookup of profile → alternative for fast access
  const altMap = new Map<FilterType, RouteAlternative>(alternatives.map((a) => [a.profile, a]));

  // Profiles to render: if alternatives loaded, only show existing profiles in order
  const profilesToShow: FilterType[] =
    alternatives.length > 0
      ? PROFILE_ORDER.filter((p) => altMap.has(p))
      : PROFILE_ORDER; // show skeletons while loading

  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-2 border border-white/50 flex flex-col gap-1 w-72 overflow-hidden">
      {/* Header */}
      <div className="px-3 pt-1 pb-2 border-b border-gray-100">
        <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
          Route Alternatives
        </p>
      </div>

      {profilesToShow.map((profileId) => {
        const meta   = PROFILE_META[profileId];
        const alt    = altMap.get(profileId);
        const isActive = activeFilter === profileId;

        return (
          <button
            key={profileId}
            onClick={() => onFilterChange(profileId)}
            disabled={isLoading || !alt}
            className={`
              flex items-center justify-between px-3 py-2.5 rounded-xl transition-all duration-200
              ${isActive
                ? 'bg-white shadow-md border border-gray-100 ring-1 ring-blue-100'
                : 'hover:bg-white/60 text-gray-500'}
              ${!alt && !isLoading ? 'opacity-40 cursor-not-allowed' : ''}
            `}
          >
            {/* Left: icon + label + tags */}
            <div className="flex items-center gap-2.5 min-w-0">
              <div className={`p-1.5 rounded-lg text-white flex-shrink-0 ${isActive ? (alt?.label ? meta.bg : 'bg-slate-500') : 'bg-gray-300'}`}>
                {alt?.label ? meta.icon : <Route className="w-4 h-4" />}
              </div>
              <div className="text-left min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  {alt?.label ? (
                    <span className={`font-bold text-sm leading-tight ${isActive ? 'text-gray-800' : 'text-gray-500'}`}>
                      {alt.label}
                    </span>
                  ) : (
                    // Unlabeled: route exists but didn't win any single criterion
                    <span className={`font-semibold text-sm leading-tight italic ${isActive ? 'text-gray-500' : 'text-gray-400'}`}>
                      Alternative
                    </span>
                  )}

                  {/* Recommended badge */}
                  {alt?.is_recommended && (
                    <span className="flex items-center gap-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 uppercase tracking-wide">
                      <Star className="w-2.5 h-2.5" /> Best
                    </span>
                  )}

                  {/* Deduplication tags (e.g. "Also Cheapest") */}
                  {alt?.tags?.map((tag) => (
                    <span
                      key={tag}
                      className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 uppercase tracking-wide"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                {/* Metric summary — skeleton while loading */}
                {isLoading && !alt ? (
                  <div className="h-3 w-28 mt-0.5 rounded bg-gray-200 animate-pulse" />
                ) : alt ? (
                  <p className={`text-[11px] mt-0.5 font-medium ${isActive ? (alt.label ? meta.color : 'text-slate-500') : 'text-gray-400'}`}>
                    {formatTime(alt.total_time_minutes)} · {formatCost(alt.total_cost)}
                  </p>
                ) : null}
              </div>
            </div>

            {/* Right: active indicator or loading spinner */}
            <div className="flex-shrink-0 ml-2">
              {isLoading && isActive ? (
                <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
              ) : isActive ? (
                <div className={`w-2 h-2 rounded-full ${alt?.label ? meta.bg : 'bg-slate-500'}`} />
              ) : null}
            </div>
          </button>
        );
      })}
    </div>
  );
};

export default FilterToggles;
