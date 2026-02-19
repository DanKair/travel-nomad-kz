import React from 'react';
import { RouteResponse, RouteSegmentStep, LastMileAccess } from '../../types';
import { TRANSPORT_COLORS, ACCESS_COLORS } from '../../constants';
import { Clock, Banknote, MapPin, Leaf, Shield, ChevronRight, X, Navigation, Footprints } from 'lucide-react';

interface RouteDetailPanelProps {
    route: RouteResponse;
    onClose: () => void;
}

// SVG icons inline so they render inside the step indicator dots
const MODE_SVGS: Record<string, string> = {
    PLANE: '✈',
    TRAIN: '🚂',
    BUS: '🚌',
    TAXI: '🚕',
    MARSHRUTKA: '🚐',
    WALK: '🚶',
    // access types
    SHUTTLE: '🚌',
    CAR: '🚗',
};

function formatTime(minutes: number): string {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h === 0) return `${m}m`;
    if (m === 0) return `${h}h`;
    return `${h}h ${m}m`;
}

function getModeLabel(raw: string): string {
    const m = raw.toString().split('.').pop()?.toUpperCase() || raw.toUpperCase();
    const labels: Record<string, string> = {
        PLANE: 'Flight', TRAIN: 'Train', BUS: 'Bus',
        TAXI: 'Taxi', MARSHRUTKA: 'Marshrutka', WALK: 'Walk',
        SHUTTLE: 'Shuttle', CAR: 'Private Car',
    };
    return labels[m] || m;
}

function getModeColor(raw: string, isAccess = false): string {
    const m = raw.toString().split('.').pop()?.toUpperCase() || raw.toUpperCase();
    return isAccess
        ? ACCESS_COLORS[m] || '#6C5CE7'
        : TRANSPORT_COLORS[m] || '#3b82f6';
}

function getEmoji(raw: string): string {
    const m = raw.toString().split('.').pop()?.toUpperCase() || raw.toUpperCase();
    return MODE_SVGS[m] || '🚌';
}

interface StepProps {
    from: string;
    to: string;
    mode: string;
    distanceKm: number;
    timeMinutes: number;
    cost: number;
    co2Kg?: number;
    comfortScore?: number;
    isLast?: boolean;
    isAccess?: boolean;
    description?: string;
    color: string;
}

const Step: React.FC<StepProps> = ({
    from, to, mode, distanceKm, timeMinutes, cost,
    co2Kg, comfortScore, isLast, isAccess, description, color
}) => (
    <div className="flex gap-3">
        {/* Timeline */}
        <div className="flex flex-col items-center">
            <div
                className="w-9 h-9 rounded-full flex items-center justify-center text-base flex-shrink-0 shadow"
                style={{ backgroundColor: color, border: '2px solid white' }}
            >
                <span>{getEmoji(mode)}</span>
            </div>
            {!isLast && (
                <div className="w-0.5 flex-1 my-1" style={{ backgroundColor: color, opacity: 0.35, minHeight: 28 }} />
            )}
        </div>

        {/* Content */}
        <div className="pb-4 flex-1 min-w-0">
            {/* From node label */}
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-0.5">{from}</p>

            {/* Mode badge + route */}
            <div className="flex items-center gap-2 mb-2">
                <span
                    className="text-xs font-bold px-2 py-0.5 rounded-full text-white"
                    style={{ backgroundColor: color }}
                >
                    {getModeLabel(mode)}
                </span>
                <ChevronRight className="w-3 h-3 text-gray-400 flex-shrink-0" />
                <span className="text-xs font-semibold text-gray-700 truncate">{to}</span>
            </div>

            {/* Optional description */}
            {description && (
                <p className="text-[11px] text-gray-500 italic mb-2">{description}</p>
            )}

            {/* Stats row */}
            <div className="flex flex-wrap gap-x-3 gap-y-1">
                <span className="flex items-center gap-1 text-[11px] text-gray-500">
                    <Clock className="w-3 h-3" /> {formatTime(timeMinutes)}
                </span>
                <span className="flex items-center gap-1 text-[11px] text-gray-500">
                    <Banknote className="w-3 h-3" /> {cost.toLocaleString()} KZT
                </span>
                <span className="flex items-center gap-1 text-[11px] text-gray-500">
                    <MapPin className="w-3 h-3" /> {distanceKm.toFixed(1)} km
                </span>
                {co2Kg !== undefined && (
                    <span className="flex items-center gap-1 text-[11px] text-gray-500">
                        <Leaf className="w-3 h-3" /> {co2Kg} kg CO₂
                    </span>
                )}
                {comfortScore !== undefined && !isAccess && (
                    <span className="flex items-center gap-1 text-[11px] text-gray-500">
                        <Shield className="w-3 h-3" /> {comfortScore}/10
                    </span>
                )}
            </div>
        </div>
    </div>
);

const RouteDetailPanel: React.FC<RouteDetailPanelProps> = ({ route, onClose }) => {
    const steps = route.route_steps;
    const lm = route.last_mile_access;

    return (
        <div
            className="absolute top-0 right-0 h-full z-[1100] flex flex-col bg-white/95 backdrop-blur-md shadow-2xl border-l border-gray-200 animate-in slide-in-from-right duration-300"
            style={{ width: 340, maxWidth: '90vw' }}
        >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
                <div className="flex items-center gap-2">
                    <Navigation className="w-5 h-5 text-blue-500" />
                    <div>
                        <h2 className="text-sm font-bold text-gray-800">Route Details</h2>
                        <p className="text-[11px] text-gray-400">
                            {steps[0]?.from_node_name} → {lm?.from_node_name ?? steps[steps.length - 1]?.to_node_name}
                        </p>
                    </div>
                </div>
                <button
                    onClick={onClose}
                    className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors"
                    aria-label="Close details"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>

            {/* Summary bar */}
            <div className="grid grid-cols-4 gap-0 border-b border-gray-100">
                {[
                    { label: 'Time', value: formatTime(route.total_time_minutes), icon: <Clock className="w-3.5 h-3.5 text-blue-400" /> },
                    { label: 'Cost', value: `${route.total_cost.toLocaleString()} ₸`, icon: <Banknote className="w-3.5 h-3.5 text-green-400" /> },
                    { label: 'Comfort', value: `${route.average_comfort}/10`, icon: <Shield className="w-3.5 h-3.5 text-purple-400" /> },
                    { label: 'CO₂', value: `${route.total_co2_kg} kg`, icon: <Leaf className="w-3.5 h-3.5 text-emerald-500" /> },
                ].map(item => (
                    <div key={item.label} className="flex flex-col items-center py-3 gap-0.5 border-r last:border-r-0 border-gray-100">
                        {item.icon}
                        <span className="text-[10px] font-bold text-gray-700">{item.value}</span>
                        <span className="text-[9px] text-gray-400">{item.label}</span>
                    </div>
                ))}
            </div>

            {/* Step timeline */}
            <div className="flex-1 overflow-y-auto px-4 pt-5">
                {/* Origin dot */}
                <div className="flex gap-3 mb-1">
                    <div className="flex flex-col items-center">
                        <div className="w-9 h-9 rounded-full bg-blue-500 flex items-center justify-center shadow border-2 border-white flex-shrink-0">
                            <Navigation className="w-4 h-4 text-white" />
                        </div>
                        <div className="w-0.5 flex-1 my-1 bg-gray-200" style={{ minHeight: 12 }} />
                    </div>
                    <div className="pb-3 flex-1">
                        <p className="text-xs font-bold text-gray-800 mt-2">{steps[0]?.from_node_name ?? 'Start'}</p>
                        <p className="text-[10px] text-gray-400">Departure point</p>
                    </div>
                </div>

                {/* Backbone steps */}
                {steps.map((step: RouteSegmentStep, idx: number) => {
                    const isLastStep = idx === steps.length - 1 && !lm;
                    return (
                        <Step
                            key={idx}
                            from={step.from_node_name}
                            to={step.to_node_name}
                            mode={step.transport_mode.toString()}
                            distanceKm={step.distance_km}
                            timeMinutes={step.time_minutes}
                            cost={step.cost}
                            co2Kg={step.co2_kg}
                            comfortScore={step.comfort_score}
                            isLast={isLastStep}
                            isAccess={false}
                            color={getModeColor(step.transport_mode.toString(), false)}
                        />
                    );
                })}

                {/* Last-mile access step */}
                {lm && (
                    <Step
                        from={lm.from_node_name}
                        to="Destination"
                        mode={lm.access_type}
                        distanceKm={lm.distance_km}
                        timeMinutes={lm.time_minutes}
                        cost={lm.cost}
                        description={lm.description}
                        isLast={true}
                        isAccess={true}
                        color={getModeColor(lm.access_type, true)}
                    />
                )}

                {/* Destination */}
                <div className="flex gap-3">
                    <div className="flex-shrink-0">
                        <div className="w-9 h-9 rounded-full bg-red-500 flex items-center justify-center shadow border-2 border-white">
                            <MapPin className="w-4 h-4 text-white" />
                        </div>
                    </div>
                    <div className="flex-1 pt-2 pb-6">
                        <p className="text-xs font-bold text-gray-800">You've arrived! 🎉</p>
                        <p className="text-[10px] text-gray-400">Final destination</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RouteDetailPanel;
